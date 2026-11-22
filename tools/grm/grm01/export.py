"""Offline Terrain Builder format fixture for the GRM v0.11.1 export contract."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

X_SHIFT = 200000
SIDE = 256
CELL = 8
SIZE = SIDE // CELL
NODATA = -9999
OFFSETS = {"W": (0, 0), "E": (SIDE, 0)}
MODES = ("absolute", "relative")


def owner(x, y):
    if 0 <= x <= 2 * SIDE and 0 <= y <= SIDE:
        return "W" if x < SIDE else "E"
    return None


def translate(row, offset):
    """Read TB easting, recover sector XY, and write world-local TB fields."""
    model, x, y, yaw, pitch, roll, scale, elevation = row
    fields = (x, y, yaw, pitch, roll, scale, elevation)
    if not all(math.isfinite(value) for value in fields) or scale <= 0:
        raise ValueError("Invalid TB object transform")
    local_x = x - X_SHIFT
    if not (0 <= local_x <= SIDE and 0 <= y <= SIDE):
        raise ValueError("TB object outside sector")
    global_x, global_y = local_x + offset[0], y + offset[1]
    return model, global_x + X_SHIFT, global_y, yaw, pitch, roll, scale, elevation


def object_text(rows):
    return "".join(f'"{row[0]}";' + ";".join(f"{v:.3f}" for v in row[1:]) + ";\n"
                   for row in rows)


def read_objects(path):
    rows = []
    for row in csv.reader(io.StringIO(path.read_text(encoding="ascii")), delimiter=";"):
        if len(row) != 9 or row[-1] or row[0] != "FixtureMarker":
            raise ValueError("Invalid fixture object row")
        rows.append((row[0], *map(float, row[1:-1])))
    return rows


def write_asc(path, rows):
    header = (f"ncols {len(rows[0])}\nnrows {len(rows)}\nxllcorner {X_SHIFT}\n"
              f"yllcorner 0\ncellsize {CELL}\nNODATA_value {NODATA}\n")
    path.write_text(header + "".join(" ".join(map(str, row)) + "\n" for row in rows),
                    encoding="ascii", newline="\n")


def read_sector_asc(path):
    lines = path.read_text(encoding="ascii").splitlines()
    header = {key.lower(): float(value) for key, value in
              (line.split() for line in lines[:6])}
    origin = (header.get("xllcorner"), header.get("yllcorner"))
    if origin == (None, None) and "xllcenter" in header and "yllcenter" in header:
        origin = (header["xllcenter"] - CELL / 2, header["yllcenter"] - CELL / 2)
    if (origin, header.get("cellsize"), header.get("ncols"), header.get("nrows"),
            header.get("nodata_value")) != ((X_SHIFT, 0), CELL, SIZE, SIZE, NODATA):
        raise ValueError("Unexpected sector ASC grid")
    rows = [list(map(float, line.split())) for line in lines[6:]]
    if len(rows) != SIZE or any(len(row) != SIZE or not all(map(math.isfinite, row))
                                for row in rows):
        raise ValueError("Unexpected sector ASC values")
    return rows


def heights(offset_x):
    return [[NODATA if row == 4 and offset_x // CELL + col in (31, 32)
             else 100 + row * 2 + abs(offset_x // CELL + col - 31.5) * 0.5
             for col in range(SIZE)] for row in range(SIZE)]


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n",
                    encoding="ascii", newline="\n")


def clip_fixture(tile):
    """Clip the fixture's horizontal line and axis-aligned rectangle on X."""
    left = OFFSETS[tile][0]
    right = left + SIDE
    line = [[max(180, left), 64], [min(320, right), 64]]
    xmin, xmax = max(220, left), min(300, right)
    ring = [[xmin, 100], [xmax, 100], [xmax, 140], [xmin, 140], [xmin, 100]]
    return [{"source_id": key, "part_id": f"{key}:{tile}", "owner": tile,
             "type": kind, "coordinates": coords}
            for key, kind, coords in (("road", "LineString", line),
                                      ("area", "Polygon", [ring]))]


def export_sector(path, tile):
    path.mkdir()
    offset, _ = OFFSETS[tile]
    write_asc(path / "elevation.asc", heights(offset))
    candidates = [("west", "absolute", 32, 48, 105.75),
                  ("east", "relative", 480, 72, -1.25),
                  ("seam", "relative", 256, 80, 2.5),
                  ("outer", "absolute", 512, 256, 98.25)]
    ids_by_mode = {}
    for mode in MODES:
        owned = [(key, ("FixtureMarker", X_SHIFT + x - offset, y, 35, -7, 12, 1.25, z))
                 for key, height_mode, x, y, z in candidates
                 if height_mode == mode and owner(x, y) == tile]
        (path / f"{mode}_fixture.txt").write_text(
            object_text(row for _, row in owned), encoding="ascii", newline="\n")
        ids_by_mode[mode] = [key for key, _ in owned]
    write_json(path / "source_ids.json", ids_by_mode)
    write_json(path / "clipped_parts.json", clip_fixture(tile))


def merge_sectors(root):
    sector_rows = [read_sector_asc(root / tile / "elevation.asc") for tile in OFFSETS]
    if any(w[-1] != e[0] for w, e in zip(*sector_rows)):
        raise ValueError("Fixture DEM seam mismatch")
    merged = root / "world"
    merged.mkdir()
    write_asc(merged / "elevation.asc", [w + e for w, e in zip(*sector_rows)])
    seen = set()
    rows_by_mode = {mode: [] for mode in MODES}
    objects = []
    parts = []
    for tile, offset in OFFSETS.items():
        folder = root / tile
        ids = json.loads((folder / "source_ids.json").read_text(encoding="ascii"))
        tile_parts = json.loads((folder / "clipped_parts.json").read_text(encoding="ascii"))
        if tile_parts != clip_fixture(tile):
            raise ValueError("Invalid fixture clipping or owner")
        parts.extend(tile_parts)
        for mode in MODES:
            rows = read_objects(folder / f"{mode}_fixture.txt")
            for source_id, row in zip(ids[mode], rows, strict=True):
                converted = translate(row, offset)
                x, y = converted[1] - X_SHIFT, converted[2]
                if source_id in seen or owner(x, y) != tile:
                    raise ValueError("Duplicate source ID or wrong owner")
                seen.add(source_id)
                rows_by_mode[mode].append(converted)
                objects.append({"id": source_id, "owner": tile, "mode": mode,
                                "world_xy": [x, y]})
    for mode, rows in rows_by_mode.items():
        (merged / f"{mode}_fixture.txt").write_text(
            object_text(rows), encoding="ascii", newline="\n")
    write_json(merged / "objects.json", objects)
    write_json(merged / "clipped_parts.json", parts)


def export(root):
    root.mkdir()
    for tile in OFFSETS:
        export_sector(root / tile, tile)
    merge_sectors(root)
    write_manifest(root)


def write_manifest(root):
    manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.glob("*/*"))}
    write_json(root / "sha256.json", manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="run directory under reports/")
    parser.add_argument("action", nargs="?", choices=("all", "W", "E", "merge"), default="all")
    args = parser.parse_args()
    if not args.name.isascii() or not args.name.replace("-", "").isalnum():
        parser.error("expected a single ASCII run name")
    reports = Path(__file__).resolve().parents[3] / "reports"
    reports.mkdir(exist_ok=True)
    root = reports / args.name
    if root.resolve() != root:
        parser.error("expected a local reports directory")
    if args.action == "all":
        export(root)
    elif args.action == "merge":
        if any((root / tile).resolve() != root / tile for tile in OFFSETS):
            parser.error("expected local sector directories")
        merge_sectors(root)
        write_manifest(root)
    else:
        root.mkdir(exist_ok=True)
        export_sector(root / args.action, args.action)


if __name__ == "__main__":
    main()
