#!/usr/bin/env python3
"""Write deterministic coordinate-only sector manifests, not Arma terrain."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_config import ROOT, validate


def manifests(root: Path = ROOT) -> list[dict]:
    settings = validate(root)
    n = settings["sector_count"]
    side = int(n**0.5)
    step = settings["sector_size_m"]
    results = []
    for row in range(side):
        for column in range(side):
            x0, y0 = column * step, row * step
            results.append({
                "schema_version": 1,
                "sector_id": f"S{column:02d}_{row:02d}",
                "column": column,
                "row": row,
                "local_xy_bbox_m": [x0, y0, x0 + step, y0 + step],
                "ownership": "half-open [min,max), clipped at world boundary",
                "production_crs": None,
                "source_features": 0,
                "generation_status": "manifest-only",
            })
    return results


def write_manifests(output: Path, items: list[dict]) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    saved = []
    for item in items:
        path = output / f"{item['sector_id']}.json"
        body = json.dumps(item, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        # Only generated project-local directory should be passed.
        if path.exists() and path.read_text(encoding="utf-8") == body:
            saved.append(path)
            continue
        path.write_text(body, encoding="utf-8")
        saved.append(path)
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    items = manifests(args.root)
    if not args.dry_run:
        folder = (args.root / "sectors/manifests").resolve()
        target = (args.output or folder).resolve()
        if target != folder:
            raise SystemExit("Refusing output outside project-local sectors/manifests")
        files = write_manifests(target, items)
        print(f"Wrote/verified {len(files)} deterministic JSON manifests in {target}")
    else:
        print(f"DRY RUN: {len(items)} sectors, no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
