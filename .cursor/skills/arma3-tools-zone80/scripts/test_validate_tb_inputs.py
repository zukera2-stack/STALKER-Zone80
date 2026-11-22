"""Portable tests for the skill's syntax validator; do not start Arma tools."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("validate_tb_inputs.py")
spec = importlib.util.spec_from_file_location("tb_input_validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

ASC = """ncols 2
nrows 2
xllcorner 200000
yllcorner 0
cellsize 8
NODATA_value -9999
101 -9999
102 103
"""
OBJECT = '"FixtureMarker";200004.000;4.000;35.000;-7.000;12.000;1.250;105.750;\n'


class TestSyntheticInput(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.asc = self.work / "elevation.asc"
        self.asc.write_text(ASC, encoding="utf-8")
        self.absolute = self.work / "absolute.txt"
        self.absolute.write_text(OBJECT, encoding="utf-8")

    def test_asc_corner_nodata_and_csv(self):
        info = validator.read_asc(self.asc)
        self.assertEqual((info["ncols"], info["nrows"], info["nodata_cells"]), (2, 2, 1))
        self.assertEqual(info["bbox"], (200000, 0, 200016, 16))
        self.assertEqual(validator.read_objects(self.absolute, info["bbox"])["objects"], 1)

    def test_center_is_transformed_to_corner(self):
        self.asc.write_text(ASC.replace("xllcorner 200000", "xllcenter 200004")
                            .replace("yllcorner 0", "yllcenter 4"), encoding="utf-8")
        self.assertEqual(validator.read_asc(self.asc)["xllcorner"], 200000)

    def test_invalid_grid_and_nodata(self):
        self.asc.write_text(ASC.replace("ncols 2", "ncols 3"), encoding="utf-8")
        with self.assertRaisesRegex(validator.InputError, "row width"):
            validator.read_asc(self.asc)
        self.asc.write_text(ASC.replace("102 103", "102 nan"), encoding="utf-8")
        with self.assertRaisesRegex(validator.InputError, "non-finite"):
            validator.read_asc(self.asc)

    def test_reject_csv_outside_nonfinite_bad_scale(self):
        info = validator.read_asc(self.asc)
        for bad in (OBJECT.replace("200004.000", "200020.000"),
                    OBJECT.replace("1.250", "0.000"),
                    OBJECT.replace("35.000", "nan")):
            self.absolute.write_text(bad, encoding="utf-8")
            with self.assertRaises(validator.InputError):
                validator.read_objects(self.absolute, info["bbox"])

    def test_empty_relative_and_outer_edge(self):
        info = validator.read_asc(self.asc)
        self.absolute.write_text("", encoding="utf-8")
        self.assertEqual(validator.read_objects(self.absolute, info["bbox"])["objects"], 0)
        self.absolute.write_text(OBJECT.replace("200004.000", "200016.000")
                                 .replace(";4.000;", ";16.000;"), encoding="utf-8")
        self.assertEqual(validator.read_objects(self.absolute, info["bbox"])["objects"], 1)

    def test_reports_only_and_symlink_escape(self):
        base = self.work / "reports"
        base.mkdir()
        inside = base / "ok.asc"
        inside.write_text(ASC, encoding="utf-8")
        self.assertEqual(validator.reports_input(str(inside), base), inside.resolve())
        with self.assertRaisesRegex(validator.InputError, "Only synthetic"):
            validator.reports_input(str(self.asc), base)
        try:
            (base / "escape.asc").symlink_to(self.asc)
        except (OSError, NotImplementedError):
            return
        with self.assertRaisesRegex(validator.InputError, "Only synthetic"):
            validator.reports_input(str(base / "escape.asc"), base)

    def test_skill_frontmatter_and_references(self):
        skill = SCRIPT.parents[1] / "SKILL.md"
        doc = skill.read_text(encoding="utf-8")
        self.assertTrue(doc.startswith("---\nname: arma3-tools-zone80\n"))
        self.assertIn("\ndescription:", doc[:500])
        self.assertIn("AGENT_START.md", doc)
        for filename in ("TOOLCHAIN.md", "TERRAIN_BUILDER.md", "PROVENANCE.md"):
            self.assertTrue((skill.parent / "references" / filename).is_file())


if __name__ == "__main__":
    unittest.main()
