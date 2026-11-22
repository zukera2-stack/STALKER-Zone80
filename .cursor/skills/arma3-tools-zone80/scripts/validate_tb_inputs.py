"""Read-only TB-01 synthetic ASC/CSV checker; never starts Arma tools or writes files."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_GRID_SIDE = 512
MAX_INPUT_BYTES = 12 * 1024 * 1024


class InputError(ValueError):
    pass


def reports_input(raw: str, reports: Path | None = None) -> Path:
    """Reject data outside reports/, including paths escaping via symlinks."""
    base = (reports or (REPO_ROOT / "reports")).resolve()
    candidate = Path(raw).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise InputError("Only synthetic inputs inside the ignored reports/ directory are allowed") from exc
    if not candidate.is_file():
        raise InputError("Input file not found: " + str(candidate))
    if candidate.stat().st_size > MAX_INPUT_BYTES:
        raise InputError("Synthetic input exceeds the small-test size limit")
    return candidate


def read_asc(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 7:
        raise InputError("ASC needs six header lines and raster values")
    header = {}
    for line in lines[:6]:
        words = line.split()
        if len(words) != 2 or words[0].lower() in header:
            raise InputError("Invalid ASC header")
        header[words[0].lower()] = words[1]
    try:
        width, height = int(header["ncols"]), int(header["nrows"])
        step, nodata = float(header["cellsize"]), float(header["nodata_value"])
        corner = "xllcorner" in header and "yllcorner" in header
        center = "xllcenter" in header and "yllcenter" in header
        if corner == center:
            raise InputError("ASC must define matching corner OR center origins")
        x0 = float(header["xllcorner" if corner else "xllcenter"])
        y0 = float(header["yllcorner" if corner else "yllcenter"])
    except (KeyError, ValueError, OverflowError) as exc:
        raise InputError("Invalid ASC dimensions, origin or NoData") from exc
    if not (1 <= width <= MAX_GRID_SIDE and 1 <= height <= MAX_GRID_SIDE):
        raise InputError("ASC dimensions outside small synthetic test bounds")
    if not all(map(math.isfinite, (step, nodata, x0, y0))) or step <= 0:
        raise InputError("Non-finite or invalid ASC header value")
    if center:
        x0 -= step / 2
        y0 -= step / 2
    if len(lines[6:]) != height:
        raise InputError("ASC row count differs from nrows")
    invalid = 0
    for line in lines[6:]:
        tokens = line.split()
        if len(tokens) != width:
            raise InputError("ASC row width differs from ncols")
        try:
            values = [float(token) for token in tokens]
        except ValueError as exc:
            raise InputError("ASC has a non-numeric cell") from exc
        if not all(map(math.isfinite, values)):
            raise InputError("ASC has a non-finite raster value")
        invalid += sum(value == nodata for value in values)
    return {
        "ncols": width, "nrows": height, "xllcorner": x0, "yllcorner": y0,
        "cellsize": step, "nodata": nodata, "nodata_cells": invalid,
        "bbox": (x0, y0, x0 + width * step, y0 + height * step),
    }


def read_objects(path: Path, bbox: tuple[float, float, float, float]) -> dict:
    """Validate GRM/TB semicolon rows; caller preserves absolute/relative mode."""
    rows = csv.reader(io.StringIO(path.read_text(encoding="utf-8")), delimiter=";")
    count, names = 0, set()
    x0, y0, x1, y1 = bbox
    for row in rows:
        if not row or row == [""]:
            continue
        if len(row) != 9 or row[-1] != "" or not row[0].strip():
            raise InputError("TB CSV requires model;X;Y;yaw;pitch;roll;scale;elevation;")
        try:
            x, y, yaw, pitch, roll, scale, elevation = [float(v) for v in row[1:8]]
        except ValueError as exc:
            raise InputError("Non-numeric TB CSV transform") from exc
        if not all(map(math.isfinite, (x, y, yaw, pitch, roll, scale, elevation))) or scale <= 0:
            raise InputError("Non-finite TB transform or non-positive scale")
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            raise InputError("TB object position outside synthetic ASC bounds")
        names.add(row[0])
        count += 1
    return {"objects": count, "symbolic_models": sorted(names)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asc", required=True)
    ap.add_argument("--absolute")
    ap.add_argument("--relative")
    args = ap.parse_args(argv)
    try:
        asc = read_asc(reports_input(args.asc))
        result = {"status": "VALIDATED_INPUT_FORMAT_ONLY", "terrain": asc, "layers": {}}
        for mode in ("absolute", "relative"):
            raw = getattr(args, mode)
            if raw is not None:
                result["layers"][mode] = read_objects(reports_input(raw), tuple(asc["bbox"]))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (InputError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
