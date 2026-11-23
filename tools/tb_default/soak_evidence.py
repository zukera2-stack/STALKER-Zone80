"""Crash-tolerant, append-only evidence for TB-UIA SOAK (stdlib, no Windows API).

A committed cycle lives in fsynced cycles.jsonl. SUMMARY.json is an atomic
checkpoint, never the sole source of truth. Missing terminal evidence means
PARTIAL/CAUSE_UNKNOWN, never PASS. Nothing here interacts with Terrain Builder.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


class EvidenceError(ValueError):
    """Malformed or unsafe SOAK evidence."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def atomic_json(path: Path, data: dict) -> None:
    """fsync same-directory temporary file before atomic replace.

    The write is atomic on a local filesystem; Windows/network storage may
    have different durability guarantees after abrupt power loss.
    """
    tmp = path.parent / ("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _scan_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    """Return valid newline-terminated prefix without modifying originals."""
    if not path.is_file():
        return [], ["file missing: " + path.name]
    raw = path.read_bytes()
    if not raw:
        return [], []
    rows: list[dict] = []
    problems: list[str] = []
    chunks = raw.splitlines(keepends=True)
    for i, chunk in enumerate(chunks, 1):
        if not chunk.endswith(b"\n"):
            problems.append("unterminated line " + str(i))
            break
        try:
            row = json.loads(chunk.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            problems.append("invalid JSON line " + str(i))
            break
        if not isinstance(row, dict):
            problems.append("non-object JSON line " + str(i))
            break
        rows.append(row)
    return rows, problems


def scan_cycles(path: Path, *, snapshot_every: int = 10) -> dict:
    """Count only a contiguous, internally consistent prefix (never guess)."""
    rows, errors = _scan_jsonl(path)
    cycles = 0
    inventories = 0
    previous_elapsed = -1.0
    for row in rows:
        expected = cycles + 1
        if type(row.get("cycle")) is not int or row["cycle"] != expected:
            errors.append("out-of-order or duplicate cycle at " + str(expected))
            break
        elapsed = row.get("elapsedSec")
        if not isinstance(elapsed, (float, int)) or isinstance(elapsed, bool) or elapsed < previous_elapsed:
            errors.append("invalid/retrograde elapsedSec at " + str(expected))
            break
        previous_elapsed = float(elapsed)
        has_inventory = "inventory" in row
        if has_inventory != (expected % snapshot_every == 0):
            errors.append("unexpected/missing inventory at cycle " + str(expected))
            break
        if row.get("statusCode") != 0:
            errors.append("nonzero/missing statusCode at " + str(expected))
            break
        if has_inventory:
            inv = row.get("inventory")
            if not isinstance(inv, dict) or type(inv.get("nodes")) is not int or inv["nodes"] < 1:
                errors.append("invalid inventory at " + str(expected))
                break
            inventories += 1
        cycles += 1
    return {
        "cycles": cycles,
        "inventories": inventories,
        "lastElapsedSec": previous_elapsed if cycles else None,
        "problems": errors,
        "sha256": sha256_file(path) if path.exists() else None,
        "sizeBytes": path.stat().st_size if path.exists() else None,
    }


class EvidenceSession:
    """One run, exclusively created output files; never resumes a partial run."""

    def __init__(self, runroot: Path, meta: dict):
        self.runroot = runroot
        self.summary_path = runroot / "SUMMARY.json"
        self.cycles_path = runroot / "cycles.jsonl"
        self.events_path = runroot / "EVENTS.jsonl"
        self.state = {
            **meta,
            "evidenceVersion": 1,
            "runId": runroot.name,
            "runnerPid": os.getpid(),
            "startUTC": utc_now(),
            "status": "RUNNING/PARTIAL",
            "cycles": 0,
            "inventories": 0,
            "lastCommitUTC": None,
            "stopReason": None,
            "finishedUTC": None,
        }
        # Refuse an already occupied evidence namespace.
        with self.cycles_path.open("x", encoding="utf-8"):
            pass
        with self.events_path.open("x", encoding="utf-8"):
            pass
        atomic_json(self.summary_path, self.state)
        self.event("START", runnerPid=os.getpid(), runId=runroot.name)

    def event(self, kind: str, **info) -> None:
        append_jsonl(self.events_path, {
            "kind": kind, "utc": utc_now(), "monotonicNs": time.monotonic_ns(),
            "runId": self.state["runId"], **info
        })

    def commit(self, item: dict) -> None:
        expected = self.state["cycles"] + 1
        if item.get("cycle") != expected:
            raise EvidenceError("unexpected cycle number")
        has_inventory = "inventory" in item
        if has_inventory != (expected % 10 == 0):
            raise EvidenceError("unexpected/missing inventory")
        if item.get("statusCode") != 0:
            raise EvidenceError("status code is not zero")
        # The durable cycle is the authoritative record; summary follows.
        append_jsonl(self.cycles_path, item)
        self.event("CYCLE_COMMITTED", cycle=expected)
        if has_inventory:
            self.event("INVENTORY_COMMITTED", cycle=expected)
        self.state["cycles"] = expected
        self.state["inventories"] += int(has_inventory)
        self.state["lastCommitUTC"] = utc_now()
        self.state["lastElapsedSec"] = item.get("elapsedSec")
        atomic_json(self.summary_path, self.state)

    def finish(self, status: str, elapsed: float, *, reason: str | None = None,
               resources: dict | None = None, timing: dict | None = None) -> None:
        if status == "PASS" and not (
            self.state["cycles"] == 120 and self.state["inventories"] == 12 and elapsed >= 3600
        ):
            raise EvidenceError("PASS requires 120 cycles / 12 snapshots / >=3600 s")
        self.state["status"] = status
        self.state["finishedUTC"] = utc_now()
        self.state["elapsedSec"] = round(elapsed, 3)
        self.state["stopReason"] = reason
        if resources is not None:
            self.state["resources"] = resources
        if timing is not None:
            self.state["statusMs"] = timing
        self.event("NORMAL_EXIT" if status == "PASS" else "STOP",
                   status=status, cycles=self.state["cycles"],
                   inventories=self.state["inventories"], reason=reason)
        atomic_json(self.summary_path, self.state)


def recover_run(runroot: Path, *, write: bool = True) -> dict:
    """Forensic reconstruction; raw logs and original summary stay untouched."""
    result = scan_cycles(runroot / "cycles.jsonl")
    events_path = runroot / "EVENTS.jsonl"
    legacy_events_missing = not events_path.exists()
    events, event_errors = _scan_jsonl(events_path) if not legacy_events_missing else ([], [])
    summary_path = runroot / "SUMMARY.json"
    summary = None
    summary_error = None
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(summary, dict):
                raise ValueError("summary is not an object")
        except (ValueError, UnicodeError) as exc:
            summary_error = type(exc).__name__
    else:
        summary_error = "missing"
    # Even a complete cycles file cannot prove normal finalisation by itself.
    terminal_event = any(e.get("kind") in ("STOP", "NORMAL_EXIT") for e in events)
    recorded_pass = bool(
        isinstance(summary, dict) and summary.get("status") == "PASS"
        and summary.get("cycles") == 120 and summary.get("inventories") == 12
        and result["cycles"] == 120 and result["inventories"] == 12
        and not result["problems"] and terminal_event
    )
    complete_probe = bool(
        isinstance(summary, dict) and summary.get("status") == "PROBE_COMPLETE"
        and not result["problems"] and terminal_event
    )
    recorded_reason = summary.get("stopReason") if isinstance(summary, dict) else None
    evidence = {
        "provenance": "offline read-only reconstruction; not Windows/TB test",
        "recoveryUTC": utc_now(),
        "rawSummarySha256": sha256_file(summary_path) if summary_path.is_file() else None,
        "cyclesSha256": result["sha256"],
        "cycles": result["cycles"],
        "inventories": result["inventories"],
        "lastElapsedSec": result["lastElapsedSec"],
        "status": ("COMPLETED_RECORDED" if recorded_pass else
                   "COMPLETED_PROBE_RECORDED" if complete_probe else "INTERRUPTED/PARTIAL"),
        "cause": None if recorded_pass or complete_probe else (recorded_reason or "CAUSE_UNKNOWN"),
        "firstKnownStop": recorded_reason,
        "legacyEventsMissing": legacy_events_missing,
        "summaryError": summary_error,
        "evidenceProblems": result["problems"] + event_errors,
        "terminalEventRecorded": terminal_event,
        "recordedEvents": len(events),
        "notAResumedRun": True,
    }
    if write:
        # Must not overwrite a prior recovery or any original evidence.
        dest = runroot / "RECOVERY.json"
        with dest.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(evidence, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return evidence
