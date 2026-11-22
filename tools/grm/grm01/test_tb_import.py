import json
from pathlib import Path
import tempfile
import unittest

from export import export
from prepare import prepare


class ImportCandidateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.run = Path(temporary.name) / "grm"
        self.output = self.run.parent / "tb"
        export(self.run)

    def test_square_padding_preserves_world_grid_and_csv(self):
        prepare(self.run, self.output)
        rect = (self.output / "elevation_rect.asc").read_text().splitlines()
        square = (self.output / "elevation_square.asc").read_text().splitlines()
        self.assertEqual(square[:6], ["ncols 64", "nrows 64", "xllcorner 200000",
                                     "yllcorner 0", "cellsize 8", "NODATA_value -9999"])
        self.assertEqual(square[38:], rect[6:])
        self.assertEqual(sum(float(value) == -9999 for row in square[6:] for value in row.split()), 2050)
        self.assertEqual((64 - 32 - 0.5) * 8, 252)
        for mode in ("absolute", "relative"):
            name = f"{mode}_fixture.txt"
            self.assertEqual((self.output / name).read_bytes(),
                             (self.run / "world" / name).read_bytes())

    def test_duplicate_or_wrong_owner_rejected(self):
        ids_path = self.run / "E/source_ids.json"
        ids = json.loads(ids_path.read_text())
        ids["relative"][0] = "seam"
        ids_path.write_text(json.dumps(ids))
        with self.assertRaisesRegex(ValueError, "placement"):
            prepare(self.run, self.output)

    def test_half_cell_shift_rejected(self):
        asc = self.run / "world/elevation.asc"
        asc.write_text(asc.read_text().replace("xllcorner 200000", "xllcorner 200004"))
        with self.assertRaisesRegex(ValueError, "grid"):
            prepare(self.run, self.output)

    def test_tml_model_binding(self):
        templates = self.run / "probe-templates"
        templates.mkdir()
        (templates / "fixture.tml").write_text(
            r"<Library><Template><Name>FixtureMarker</Name>"
            r"<File>fixture\marker.p3d</File></Template></Library>")
        prepare(self.run, self.output)
        self.assertTrue((self.output / "fixture.tml").is_file())

    def test_mismatched_tml_rejected(self):
        templates = self.run / "probe-templates"
        templates.mkdir()
        (templates / "fixture.tml").write_text("<Library />")
        with self.assertRaisesRegex(ValueError, "TML"):
            prepare(self.run, self.output)
