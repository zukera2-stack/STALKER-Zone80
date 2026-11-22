#!/usr/bin/env python3
"""Optional local CRS probe. Requires explicitly installed pyproj and user-supplied anchor.

Does not select/approve a CRS automatically and downloads no source data.
"""
from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, required=True, help="Owner-validated WGS84 center latitude")
    parser.add_argument("--lon", type=float, required=True, help="Owner-validated WGS84 center longitude")
    parser.add_argument("--crs", required=True, help="Candidate projected metric CRS (e.g. EPSG:32636)")
    parser.add_argument("--size", type=float, default=81920.0)
    args = parser.parse_args()
    if not (-90 <= args.lat <= 90 and -180 <= args.lon <= 180 and args.size > 0):
        parser.error("Invalid geographic center or size")
    try:
        from pyproj import CRS, Geod, Transformer
    except ImportError:
        parser.exit(2, "pyproj is not installed; this optional tool was NOT TESTED.\n")
    dst = CRS.from_user_input(args.crs)
    if not dst.is_projected or not dst.axis_info or any(a.unit_name.lower() not in {"metre", "meter"} for a in dst.axis_info[:2]):
        parser.error("CRS must be a projected metric system")
    forward = Transformer.from_crs("EPSG:4326", dst, always_xy=True)
    inverse = Transformer.from_crs(dst, "EPSG:4326", always_xy=True)
    xc, yc = forward.transform(args.lon, args.lat)
    half = args.size / 2
    geod = Geod(ellps="WGS84")
    probes = {
        "center": (xc, yc),
        "west": (xc - half, yc),
        "east": (xc + half, yc),
        "north": (xc, yc + half),
        "south": (xc, yc - half),
        "southwest": (xc-half, yc-half),
        "southeast": (xc+half, yc-half),
        "northwest": (xc-half, yc+half),
        "northeast": (xc+half, yc+half),
    }
    results = {}
    for name, (x, y) in probes.items():
        lon, lat = inverse.transform(x, y)
        xx, yy = forward.transform(lon, lat)
        lon2, lat2 = inverse.transform(x + 1000, y)
        _, _, ground_m = geod.inv(lon, lat, lon2, lat2)
        results[name] = {
            "lon": lon, "lat": lat,
            "roundtrip_residual_m": ((xx-x)**2 + (yy-y)**2)**0.5,
            "east_1km_scale_error_m": 1000 - ground_m,
        }
    print(json.dumps({
        "candidate_crs": dst.to_string(), "input_wgs84_center": [args.lon, args.lat],
        "world_size_m": args.size, "probes": results,
        "status": "CANDIDATE_ONLY — not CRS approval",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
