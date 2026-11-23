"""Portable crash/recovery regression tests. No Terrain Builder or Windows API."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "tools" / "tb_default"
sys.path.insert(0, str(TOOL_DIR))
try:
    import soak_evidence as ev
    spec = importlib.util.spec_from_file_location("tb_soak_durable", TOOL_DIR / "soak60.py")
    soak = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(soak)
finally:
    sys.path.pop(0)


def item(n):
    result = {"cycle": n, "elapsedSec": (n - 1) * 30.0,
              "statusCode": 0, "identity": {"pid": 3856}}
    if n % 10 == 0:
        result["inventory"] = {"nodes": 203}
    return result


class DurableEvidenceTests(unittest.TestCase):
    def setUp(self):
        reports = ROOT / "reports" / "TB-UIA-06"
        reports.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="durable-", dir=reports)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def session(self):
        return ev.EvidenceSession(self.root / "run", {"pid": 3856, "tbLaunched": False})

    def open_run(self):
        run = self.root / "run"
        run.mkdir()
        return ev.EvidenceSession(run, {"pid": 3856, "tbLaunched": False})

    def record(self, n):
        session = self.open_run()
        for i in range(1, n + 1):
            session.commit(item(i))
        return session

    def test_summary_created_before_first_cycle(self):
        run = self.open_run()
        s = json.loads(run.summary_path.read_text())
        self.assertEqual((s["cycles"], s["inventories"]), (0, 0))
        self.assertEqual(s["status"], "RUNNING/PARTIAL")
        self.assertEqual(s["runnerPid"], os.getpid())
        self.assertEqual(len(run.events_path.read_text().splitlines()), 1)

    def test_cycle_checkpoints_ten(self):
        run = self.record(10)
        s = json.loads(run.summary_path.read_text())
        self.assertEqual((s["cycles"], s["inventories"]), (10, 1))
        self.assertEqual(ev.scan_cycles(run.cycles_path)["inventories"], 1)

    def test_historical_50_5_missing_terminal(self):
        run = self.record(50)
        result = ev.recover_run(run.runroot, write=False)
        self.assertEqual((result["cycles"], result["inventories"]), (50, 5))
        self.assertEqual(result["cause"], "CAUSE_UNKNOWN")
        self.assertEqual(result["status"], "INTERRUPTED/PARTIAL")

    def test_at_49_no_snapshot_missing(self):
        run = self.record(49)
        r = ev.scan_cycles(run.cycles_path)
        self.assertEqual((r["cycles"], r["inventories"]), (49, 4))

    def test_one_cycle_missing_final(self):
        run = self.record(1)
        self.assertEqual(ev.recover_run(run.runroot, write=False)["cycles"], 1)

    def test_simulated_crash_between_cycle_and_checkpoint(self):
        run = self.open_run()
        with patch.object(ev, "atomic_json", side_effect=OSError("disk unavailable")):
            with self.assertRaises(OSError):
                run.commit(item(1))
        # The fsynced log is authoritative when the JSON summary remains stale.
        self.assertEqual(json.loads(run.summary_path.read_text())["cycles"], 0)
        self.assertEqual(ev.recover_run(run.runroot, write=False)["cycles"], 1)

    def test_torn_last_jsonl_line(self):
        run = self.record(2)
        with run.cycles_path.open("ab") as f:
            f.write(b'{"cycle":3,"elapsedSec":')
        scan = ev.scan_cycles(run.cycles_path)
        self.assertEqual(scan["cycles"], 2)
        self.assertIn("unterminated line", scan["problems"][0])

    def test_duplicate_cycle_is_not_counted(self):
        run = self.record(2)
        ev.append_jsonl(run.cycles_path, item(2))
        r = ev.scan_cycles(run.cycles_path)
        self.assertEqual(r["cycles"], 2)
        self.assertTrue(r["problems"])

    def test_out_of_order_cycle(self):
        run = self.record(1)
        ev.append_jsonl(run.cycles_path, item(3))
        self.assertEqual(ev.scan_cycles(run.cycles_path)["cycles"], 1)

    def test_missing_inventory_at_tenth_cycle(self):
        run = self.record(9)
        ev.append_jsonl(run.cycles_path, {"cycle": 10, "statusCode": 0, "elapsedSec": 270})
        r = ev.scan_cycles(run.cycles_path)
        self.assertEqual((r["cycles"], r["inventories"]), (9, 0))
        self.assertTrue(r["problems"])

    def test_extra_inventory_is_rejected(self):
        run = self.open_run()
        obj = item(1)
        obj["inventory"] = {"nodes": 203}
        with self.assertRaises(ev.EvidenceError):
            run.commit(obj)

    def test_corrupt_summary_recovery_is_partial(self):
        run = self.record(1)
        run.summary_path.write_text("{not json", encoding="utf-8")
        recovery = ev.recover_run(run.runroot, write=False)
        self.assertEqual(recovery["summaryError"], "JSONDecodeError")
        self.assertEqual(recovery["status"], "INTERRUPTED/PARTIAL")

    def test_recovery_never_overwrites_original_evidence(self):
        run = self.record(2)
        hashes = {p: ev.sha256_file(p) for p in (run.cycles_path, run.summary_path, run.events_path)}
        result = ev.recover_run(run.runroot, write=True)
        self.assertEqual(result["cycles"], 2)
        for path, original in hashes.items():
            self.assertEqual(ev.sha256_file(path), original)
        with self.assertRaises(FileExistsError):
            ev.recover_run(run.runroot, write=True)

    def test_final_pass_requires_continuity(self):
        run = self.record(50)
        with self.assertRaises(ev.EvidenceError):
            run.finish("PASS", 3600)
        self.assertEqual(json.loads(run.summary_path.read_text())["status"], "RUNNING/PARTIAL")

    def test_complete_mock_120_is_not_windows_evidence(self):
        run = self.record(120)
        run.finish("PASS", 3600.1)
        r = ev.recover_run(run.runroot, write=False)
        self.assertEqual((r["cycles"], r["inventories"]), (120, 12))
        self.assertEqual(r["status"], "COMPLETED_RECORDED")
        self.assertIn("not Windows/TB test", r["provenance"])

    def test_no_terminal_event_is_not_pass(self):
        run = self.record(120)
        run.state["status"] = "PASS"
        ev.atomic_json(run.summary_path, run.state)
        self.assertEqual(ev.recover_run(run.runroot, write=False)["status"],
                         "INTERRUPTED/PARTIAL")

    def test_normal_blocked_stop_has_reason(self):
        run = self.record(1)
        run.finish("PARTIAL / BLOCKED", 32.1, reason="Blocked: test failure")
        stored = json.loads(run.summary_path.read_text())
        self.assertIn("test failure", stored["stopReason"])
        self.assertEqual(stored["cycles"], 1)
        self.assertIn("STOP", run.events_path.read_text())

    def test_atomic_failed_replace_keeps_existing_summary(self):
        run = self.open_run()
        before = ev.sha256_file(run.summary_path)
        with patch.object(ev.os, "replace", side_effect=OSError("simulated replace failure")):
            with self.assertRaises(OSError):
                ev.atomic_json(run.summary_path, {"cycles": 123})
        self.assertEqual(ev.sha256_file(run.summary_path), before)
        self.assertEqual(list(run.runroot.glob(".SUMMARY.json.*.tmp")), [])

    def test_duplicate_run_namespace_is_refused(self):
        self.open_run()
        with self.assertRaises(FileExistsError):
            ev.EvidenceSession(self.root / "run", {})

    def test_legacy_50_cycles_without_summary(self):
        run = self.root / "legacy"
        run.mkdir()
        with (run / "cycles.jsonl").open("x", encoding="utf-8") as stream:
            for i in range(1, 51):
                stream.write(json.dumps(item(i)) + "\n")
        result = ev.recover_run(run, write=False)
        self.assertEqual((result["cycles"], result["inventories"]), (50, 5))
        self.assertEqual(result["summaryError"], "missing")
        self.assertIsNone(result["rawSummarySha256"])

    def test_recover_cli_rejects_outside_reports(self):
        result = soak.main(["recover", "--run-dir", str(self.root.parent.parent.parent)])
        self.assertEqual(result, 2)

    def test_recover_cli_on_synthetic_run(self):
        run = self.record(2)
        result = soak.main(["recover", "--run-dir", str(run.runroot)])
        self.assertEqual(result, 0)
        self.assertTrue((run.runroot / "RECOVERY.json").is_file())


if __name__ == "__main__":
    unittest.main()
