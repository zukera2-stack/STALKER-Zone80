"""Portable regression tests; no Arma binaries and no network."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).with_name('validate_tb_inputs.py')
spec = importlib.util.spec_from_file_location('tb_synthetic', FILE)
tb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tb)

ASC = '''ncols 2
nrows 2
xllcorner 200000
yllcorner 0
cellsize 8
NODATA_value -9999
101 -9999
102 103
'''
ROW = '"FixtureMarker";200004.000;4.000;35.000;-7.000;12.000;1.250;105.750;\n'


class TestSafeInput(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.asc = self.base / 'test.asc'
        self.asc.write_text(ASC)
        self.csv = self.base / 'absolute.txt'
        self.csv.write_text(ROW)

    def test_asc_header_and_nodata(self):
        info = tb.read_asc(self.asc)
        self.assertEqual((info['ncols'], info['nrows'], info['nodata_cells']), (2, 2, 1))
        self.assertEqual(info['bbox'], (200000, 0, 200016, 16))

    def test_asc_center_coordinates(self):
        self.asc.write_text(ASC.replace('xllcorner 200000', 'xllcenter 200004')
                            .replace('yllcorner 0', 'yllcenter 4'))
        self.assertEqual(tb.read_asc(self.asc)['xllcorner'], 200000)

    def test_invalid_asc_width(self):
        self.asc.write_text(ASC.replace('ncols 2', 'ncols 3'))
        with self.assertRaisesRegex(tb.InputError, 'width'):
            tb.read_asc(self.asc)

    def test_invalid_asc_nan(self):
        self.asc.write_text(ASC.replace('102 103', '102 nan'))
        with self.assertRaisesRegex(tb.InputError, 'Non-finite'):
            tb.read_asc(self.asc)

    def test_csv_transforms(self):
        area = tb.read_asc(self.asc)['bbox']
        self.assertEqual(tb.read_objects(self.csv, area)['objects'], 1)
        for bad in (ROW.replace('200004.000', '200020.000'),
                    ROW.replace('1.250', '0.000'), ROW.replace('35.000', 'nan')):
            self.csv.write_text(bad)
            with self.assertRaises(tb.InputError):
                tb.read_objects(self.csv, area)

    def test_empty_and_outer_edge(self):
        area = tb.read_asc(self.asc)['bbox']
        self.csv.write_text('')
        self.assertEqual(tb.read_objects(self.csv, area)['objects'], 0)
        self.csv.write_text(ROW.replace('200004.000', '200016.000').replace(';4.000;', ';16.000;'))
        self.assertEqual(tb.read_objects(self.csv, area)['objects'], 1)

    def test_reports_boundary(self):
        reports = self.base / 'reports'
        reports.mkdir()
        inside = reports / 'test.asc'
        inside.write_text(ASC)
        self.assertEqual(tb.reports_input(str(inside), reports), inside.resolve())
        with self.assertRaises(tb.InputError):
            tb.reports_input(str(self.asc), reports)

    def test_skill_files(self):
        folder = FILE.parents[1]
        self.assertTrue((folder / 'SKILL.md').read_text().startswith('---\nname: arma3-tools-zone80\n'))
        for reference in ('TOOLCHAIN.md', 'TERRAIN_BUILDER.md', 'PROVENANCE.md'):
            self.assertTrue((folder / 'references' / reference).is_file())


if __name__ == '__main__':
    unittest.main()
