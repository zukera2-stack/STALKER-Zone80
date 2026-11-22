#!/usr/bin/env python3
"""Validate the non-generating Zone80 foundation using Python standard library."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_configuration(root: Path = ROOT) -> tuple[dict, dict, dict]:
    folder = root / "config"
    terrain = json.loads((folder / "terrain_extent.json").read_text(encoding="utf-8"))
    profile = json.loads((folder / "generation_profile.json").read_text(encoding="utf-8"))
    locations = json.loads((folder / "stalker_locations.geojson").read_text(encoding="utf-8"))
    return terrain, profile, locations


def validate(root: Path = ROOT) -> dict:
    terrain, profile, locations = load_configuration(root)
    n = terrain["heightmap_cells_per_side"]
    cell = terrain["terrain_cell_size_m"]
    size = terrain["world_size_m"]
    sect = terrain["sector_size_m"]
    sectors = terrain["sector_count_per_axis"]
    cell_sector = terrain["sector_cells_per_side"]
    if any(type(v) is not int or v <= 0 for v in (n, cell, size, sect, sectors, cell_sector)):
        raise ValueError("All core dimensions must be positive integers")
    if n != 4096 or cell != 20 or size != 81920:
        raise ValueError("Target world geometry changed without review")
    if n * cell != size or cell_sector * cell != sect:
        raise ValueError("Terrain/sector dimensions disagree")
    if sectors * sect != size or sectors * cell_sector != n or sectors**2 != 64:
        raise ValueError("Sector coverage is not exactly 8 by 8")
    if terrain["source_crs"] != "EPSG:4326":
        raise ValueError("WGS84 source storage invariant violated")
    if terrain["status"] == "PENDING_CRS_AND_EXTENT_APPROVAL":
        if terrain["production_crs"] is not None or terrain["local_origin_easting_northing_m"] is not None:
            raise ValueError("Pending CRS contains fabricated production CRS/origin")
    elif not terrain.get("crs_approval_evidence"):
        raise ValueError("Approved CRS must point to evidence")
    if profile["stage"] != "foundation-only":
        raise ValueError("Stage promotion requires an explicit review")
    if profile["enabled"] or profile["full_world_generation_enabled"] or profile["downloads_enabled"]:
        raise ValueError("Foundation safeguards cannot be enabled")
    if profile["builder_parallelism"] != 1:
        raise ValueError("Do not increase builder parallelism before profiling")
    memory = profile["memory_policy"]
    if not (0 < memory["soft_target_gib"] <= memory["warn_private_bytes_gib"] < memory["stop_private_bytes_gib"] <= 24):
        raise ValueError("Memory guard order invalid")
    if locations.get("type") != "FeatureCollection" or not isinstance(locations.get("features"), list):
        raise ValueError("Gameplay locations must be a GeoJSON FeatureCollection")
    if locations["features"]:
        raise ValueError("Foundation stage must not fabricate gameplay features")
    return {
        "status": "PASS",
        "world_size_m": size,
        "sector_size_m": sect,
        "sector_count": sectors**2,
        "crs_status": terrain["status"],
        "generation_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.root), ensure_ascii=False, indent=2))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
