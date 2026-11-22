"""Synthetic, no-Arma/no-GDAL foundation tests."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("validate_config", HERE / "validate_config.py")
validate_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_config)
import sys
sys.modules["validate_config"] = validate_config
spec2 = importlib.util.spec_from_file_location("build_sector_manifests", HERE / "build_sector_manifests.py")
builder = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(builder)


class FoundationTests(unittest.TestCase):
    def test_geometry(self):
        result = validate_config.validate(ROOT)
        self.assertEqual(result["world_size_m"], 81920)
        self.assertEqual(result["sector_count"], 64)

    def test_sectors_unique_and_cover_world(self):
        items = builder.manifests(ROOT)
        self.assertEqual(len(items), 64)
        self.assertEqual(len({x["sector_id"] for x in items}), 64)
        tiles = {(x["column"], x["row"]): x["local_xy_bbox_m"] for x in items}
        self.assertEqual(tiles[(0, 0)], [0, 0, 10240, 10240])
        self.assertEqual(tiles[(7, 7)], [71680, 71680, 81920, 81920])
        for y in range(8):
            for x in range(7):
                self.assertEqual(tiles[(x, y)][2], tiles[(x+1, y)][0])
        for y in range(7):
            for x in range(8):
                self.assertEqual(tiles[(x, y)][3], tiles[(x, y+1)][1])

    def test_reproducible_json(self):
        items = builder.manifests(ROOT)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            a = builder.write_manifests(out, items)
            before = [p.read_bytes() for p in a]
            b = builder.write_manifests(out, items)
            self.assertEqual(before, [p.read_bytes() for p in b])

    def test_safety_flags(self):
        terrain, profile, geojson = validate_config.load_configuration(ROOT)
        self.assertIsNone(terrain["production_crs"])
        self.assertFalse(profile["downloads_enabled"])
        self.assertFalse(profile["full_world_generation_enabled"])
        self.assertEqual(geojson["features"], [])


if __name__ == "__main__":
    unittest.main()
