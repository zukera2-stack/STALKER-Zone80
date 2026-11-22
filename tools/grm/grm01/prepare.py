"""Prepare a square TB-01 import candidate from an isolated GRM-01 run."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from export import CELL, MODES, NODATA, SIDE, SIZE, X_SHIFT, heights, owner, read_objects, write_asc

EXPECTED = {
    "west": ("absolute", 32, 48, 105.75),
    "outer": ("absolute", 512, 256, 98.25),
    "east": ("relative", 480, 72, -1.25),
    "seam": ("relative", 256, 80, 2.5),
}


def inspect_objects(run):
    expected_ids = Counter(EXPECTED.keys())
    seen = Counter()
    for tile, offset in (("W", 0), ("E", SIDE)):
        directory = run / tile
        ids = json.loads((directory / "source_ids.json").read_text(encoding="ascii"))
        for mode in MODES:
            for key, row in zip(ids[mode], read_objects(directory / f"{mode}_fixture.txt"),
                                strict=True):
                x, y, yaw, pitch, roll, scale, z = row[1:]
                world_x = x - X_SHIFT + offset
                if (owner(world_x, y) != tile or
                        EXPECTED.get(key) != (mode, world_x, y, z) or
                        (yaw, pitch, roll, scale) != (35, -7, 12, 1.25)):
                    raise ValueError("Unexpected sector placement")
                seen[key] += 1
    if seen != expected_ids:
        raise ValueError("Missing or duplicate sector placements")
    world = run / "world"
    for mode in MODES:
        expected = Counter(("FixtureMarker", X_SHIFT + x, y, 35, -7, 12, 1.25, z)
                           for actual, x, y, z in EXPECTED.values() if actual == mode)
        if Counter(read_objects(world / f"{mode}_fixture.txt")) != expected:
            raise ValueError("Unexpected world placements")


def read_rectangle(path):
    lines = path.read_text(encoding="ascii").splitlines()
    metadata = {key.lower(): float(value) for key, value in
                (line.split() for line in lines[:6])}
    expected = {"ncols": 2 * SIZE, "nrows": SIZE, "xllcorner": X_SHIFT,
                "yllcorner": 0, "cellsize": CELL, "nodata_value": NODATA}
    if metadata != expected:
        raise ValueError("Unexpected rectangular grid")
    rows = [[float(value) for value in line.split()] for line in lines[6:]]
    w, e = heights(0), heights(SIDE)
    if rows != [a + b for a, b in zip(w, e)]:
        raise ValueError("Unexpected elevation or NoData at source coordinates")
    return rows


def prepare(run, output):
    inspect_objects(run)
    world = run / "world"
    rows = read_rectangle(world / "elevation.asc")
    template = run / "probe-templates/fixture.tml"
    if template.is_file():
        library = ET.parse(template).getroot()
        names = [(item.findtext("Name"), item.findtext("File"))
                 for item in library.findall("Template")]
        if library.tag != "Library" or names != [("FixtureMarker", r"fixture\marker.p3d")]:
            raise ValueError("Unexpected TML model binding")
    output.mkdir()
    shutil.copyfile(world / "elevation.asc", output / "elevation_rect.asc")
    write_asc(output / "elevation_square.asc", [[NODATA] * (2 * SIZE)] * SIZE + rows)
    for mode in MODES:
        name = f"{mode}_fixture.txt"
        shutil.copyfile(world / name, output / name)
    if template.is_file():
        shutil.copyfile(template, output / "fixture.tml")
    digest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.iterdir())}
    (output / "sha256.json").write_text(json.dumps(digest, indent=2) + "\n",
                                       encoding="ascii", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="existing GRM-01 run name in reports/")
    parser.add_argument("output", help="fresh TB-01 directory name in reports/")
    args = parser.parse_args()
    for name in (args.run, args.output):
        if not name.isascii() or not name.replace("-", "").isalnum():
            parser.error("expected a simple ASCII directory name")
    reports = Path(__file__).resolve().parents[3] / "reports"
    run, output = (reports / name for name in (args.run, args.output))
    if run.resolve() != run or output.resolve() != output:
        parser.error("expected local directories inside reports/")
    prepare(run, output)
