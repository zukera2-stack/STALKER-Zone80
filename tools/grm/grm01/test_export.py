import json
from pathlib import Path
import tempfile
import unittest

from export import (X_SHIFT, export, export_sector, merge_sectors, owner,
                    read_objects, read_sector_asc, translate, write_manifest)


class ModularExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)

    def test_two_exports_are_reproducible(self):
        first, second = self.work / "first", self.work / "second"
        export(first)
        second.mkdir()
        for tile in ("E", "W"):
            export_sector(second / tile, tile)
        merge_sectors(second)
        write_manifest(second)
        self.assertEqual((first / "sha256.json").read_bytes(),
                         (second / "sha256.json").read_bytes())
        world = first / "world"
        objects = json.loads((world / "objects.json").read_text())
        self.assertEqual({item["id"]: (item["world_xy"], item["mode"]) for item in objects},
                         {"west": ([32, 48], "absolute"), "east": ([480, 72], "relative"),
                          "seam": ([256, 80], "relative"), "outer": ([512, 256], "absolute")})
        self.assertEqual(len(objects), 4)
        rows = read_objects(world / "relative_fixture.txt")
        self.assertEqual(rows, [("FixtureMarker", 200480, 72, 35, -7, 12, 1.25, -1.25),
                                ("FixtureMarker", 200256, 80, 35, -7, 12, 1.25, 2.5)])
        self.assertEqual(read_objects(world / "absolute_fixture.txt"),
                         [("FixtureMarker", 200032, 48, 35, -7, 12, 1.25, 105.75),
                          ("FixtureMarker", 200512, 256, 35, -7, 12, 1.25, 98.25)])

    def test_dem_half_cells_seam_and_nodata(self):
        root = self.work / "run"
        export(root)
        lines = (root / "world/elevation.asc").read_text().splitlines()
        self.assertEqual(lines[:6], ["ncols 64", "nrows 32", "xllcorner 200000",
                                    "yllcorner 0", "cellsize 8", "NODATA_value -9999"])
        rows = [list(map(float, row.split())) for row in lines[6:]]
        self.assertTrue(all(row[31] == row[32] for row in rows))
        self.assertEqual([(y, x) for y, row in enumerate(rows) for x, h in enumerate(row)
                          if h == -9999], [(4, 31), (4, 32)])
        self.assertEqual([X_SHIFT + 4 + x * 8 for x in (31, 32)], [200252, 200260])
        self.assertEqual([256 - 4 - y * 8 for y in (0, 31)], [252, 4])
        grid = root / "E/elevation.asc"
        data = grid.read_text()
        grid.write_text(data.replace("xllcorner 200000", "xllcenter 200004")
                        .replace("yllcorner 0", "yllcenter 4"))
        self.assertEqual(read_sector_asc(grid)[0], rows[0][32:])
        grid.write_text(data.replace("xllcorner 200000", "xllcorner 200004"))
        with self.assertRaisesRegex(ValueError, "grid"):
            read_sector_asc(grid)

    def test_fixture_clips_both_shapes_without_duplicate_parts(self):
        root = self.work / "run"
        export(root)
        parts = json.loads((root / "world/clipped_parts.json").read_text())
        self.assertEqual(len({p["part_id"] for p in parts}), 4)
        by_id = {p["part_id"]: p["coordinates"] for p in parts}
        self.assertEqual(by_id["road:W"], [[180, 64], [256, 64]])
        self.assertEqual(by_id["road:E"], [[256, 64], [320, 64]])
        self.assertEqual(by_id["area:W"][0][1:3], [[256, 100], [256, 140]])
        self.assertEqual([by_id["area:E"][0][i] for i in (0, 3)], [[256, 100], [256, 140]])

    def test_owner_and_invalid_transform(self):
        self.assertEqual(owner(256, 80), "E")
        self.assertEqual(owner(512, 256), "E")
        self.assertIsNone(owner(512.1, 256))
        self.assertEqual(translate(("FixtureMarker", 200020, 44, 2, -4, 7, 1.2, 9),
                                   (256, 16))[1:3], (200276, 60))
        with self.assertRaisesRegex(ValueError, "Invalid"):
            translate(("FixtureMarker", 200020, 36, 0, 0, 0, 0, 0), (256, 0))
        with self.assertRaisesRegex(ValueError, "outside"):
            translate(("FixtureMarker", 20, 36, 0, 0, 0, 1, 0), (256, 0))

    def test_merge_rejects_duplicate_source(self):
        for tile in ("W", "E"):
            export_sector(self.work / tile, tile)
        ids = self.work / "E/source_ids.json"
        obj = json.loads(ids.read_text())
        obj["relative"][0] = "west"
        ids.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            merge_sectors(self.work)


if __name__ == "__main__":
    unittest.main()
