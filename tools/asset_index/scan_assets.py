#!/usr/bin/env python3
"""Read-only loose-PBO/P3D inventory. Does NOT unpack archives or parse configs.

Example: python tools/asset_index/scan_assets.py --root "D:\\OwnerApprovedAddons"
Writes only to project-local assets/catalog/scan.csv (gitignored).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "assets" / "catalog" / "scan.csv"
FIELDS = ["relative_path", "kind", "size_bytes", "mtime_ns", "sha256",
          "p3d_magic", "license_status", "extraction_performed",
          "config_parsed", "bbox_verified", "required_addons_verified"]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_assets(root: Path):
    """Sorted walk, no symlink follow, no file bytes modified."""
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if not (Path(base) / name).is_symlink())
        for name in sorted(files):
            path = Path(base) / name
            if path.is_symlink() or path.suffix.lower() not in {".pbo", ".p3d"}:
                continue
            yield path


def row_for(path: Path, root: Path, hash_mode: str) -> dict:
    stat = path.stat()
    kind = path.suffix[1:].upper()
    magic = ""
    if kind == "P3D":
        with path.open("rb") as stream:
            first4 = stream.read(4)
        magic = first4.decode("ascii", errors="replace") if first4 in {b"ODOL", b"MLOD"} else "UNVERIFIED"
    need_hash = hash_mode == "all" or (hash_mode == "pbo" and kind == "PBO")
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "kind": kind, "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        "sha256": checksum(path) if need_hash else "NOT_HASHED",
        "p3d_magic": magic, "license_status": "UNKNOWN",
        "extraction_performed": False, "config_parsed": False,
        "bbox_verified": False, "required_addons_verified": False,
    }


def scan(root: Path, destination: Path, hash_mode: str = "pbo", limit: int = 250000) -> int:
    root = root.resolve(strict=True)
    destination = destination.resolve()
    if not root.is_dir():
        raise ValueError("Not a directory")
    if destination != OUTPUT.resolve():
        raise ValueError("Only project-local ignored assets/catalog/scan.csv is permitted")
    if destination == root or root in destination.parents:
        raise ValueError("Refusing to write output inside scanned addon tree")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Do not create a report claiming to be complete if the limit is hit.
    import tempfile
    count = 0
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=destination.parent,
                                         prefix=".scan-", suffix=".csv", delete=False) as out:
            temp_path = Path(out.name)
            writer = csv.DictWriter(out, fieldnames=FIELDS)
            writer.writeheader()
            for path in iter_assets(root):
                if count >= limit:
                    raise ValueError("Scan limit exceeded; previous complete report retained")
                writer.writerow(row_for(path, root, hash_mode))
                count += 1
        os.replace(temp_path, destination)
        return count
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Owner-approved directory of existing addons")
    parser.add_argument("--hash-mode", choices=["none", "pbo", "all"], default="pbo")
    parser.add_argument("--max-files", type=int, default=250000)
    args = parser.parse_args()
    if args.max_files <= 0:
        parser.error("--max-files must be >0")
    try:
        amount = scan(args.root, OUTPUT, args.hash_mode, args.max_files)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"FAILED (no source modifications): {exc}\n")
    print(f"Indexed {amount} loose PBO/P3D files. No archives extracted. Metadata: {OUTPUT}")
    print("Important: this is NOT a validated PBO interior/config/LOD/license catalogue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
