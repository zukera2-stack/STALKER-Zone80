"""MAP-003 fixed target grid contract; tests independent of the remote COG."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("map003_fixed", ROOT/"tools/map003/build_fixed_grid.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestMap003Grid(unittest.TestCase):
    def test_exact_grid_is_power_of_two(self):
        self.assertEqual((mod.WIDTH, mod.HEIGHT, mod.CELL_M),(64,64,30))
        self.assertEqual(mod.WIDTH * mod.HEIGHT,4096)

    def test_correct_metric_extent(self):
        g=mod.grid()
        self.assertEqual(g["bounds_utm36"],[294373.084,5698122.108,296293.084,5700042.108])
        self.assertEqual(g["crs"],"EPSG:32636")

    def test_old_grid_is_centred_with_fixed_margins(self):
        # Prior verified 60×62 / 30m lower-left as recorded in PR #41.
        old_x,old_y=294433.084,5698152.108
        self.assertAlmostEqual(old_x-mod.XLL_M,60)
        self.assertAlmostEqual(old_y-mod.YLL_M,30)
        self.assertAlmostEqual(mod.XLL_M + 64*30 - (old_x + 60*30),60)
        self.assertAlmostEqual(mod.YLL_M + 64*30 - (old_y + 62*30),30)

    def test_arc_ascii_north_first_and_data_shape(self):
        import tempfile
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            rows = np.arange(4096,dtype=np.float32).reshape(64,64)
            path=Path(tmp)/"grid.asc"
            mod.write_arc_ascii(path,rows)
            txt=path.read_text().splitlines()
            self.assertEqual(len(txt),70)
            self.assertEqual(txt[:6],[
                "ncols 64","nrows 64","xllcorner 294373.084",
                "yllcorner 5698122.108","cellsize 30","NODATA_value -9999"
            ])
            self.assertTrue(txt[6].startswith("0.000000 1.000000"))
            self.assertTrue(txt[-1].startswith("4032.000000"))

    def test_bbox_corners_fit_target_when_proj_available(self):
        margins=mod.verify_geo_coverage()["minGridMargins_m"]
        self.assertEqual(len(margins),4)
        self.assertGreater(min(margins),0)
        self.assertLess(max(margins),150) # small deliberate margin, not a new map.


if __name__=="__main__":
    unittest.main()
