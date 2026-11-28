import tempfile
import unittest
from pathlib import Path
import shapefile
from pyproj import CRS
from verify_shapes import compare_exports


class ShapeQC(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = [([(0, 0), (1, 1)], 'A'), ([(3, 3), (4, 4)], 'B')]
        self.base = self.make('base', self.rows)

    def make(self, name, rows, epsg=32636, width=8):
        path = self.root / (name + '.shp')
        with shapefile.Writer(str(path), shapeType=3, encoding='utf-8') as w:
            w.field('ID', 'C', width)
            for pts, value in rows:
                w.line([pts]); w.record(value)
        path.with_suffix('.prj').write_text(CRS.from_epsg(epsg).to_wkt(), encoding='utf-8')
        return path

    def compare(self, path):
        return compare_exports(self.base, path, 'utf-8')

    def test_exact(self):
        self.assertEqual(self.compare(self.make('a', self.rows))['status'], 'PASS')
    def test_feature_reorder(self):
        self.assertEqual(self.compare(self.make('a', self.rows[::-1]))['status'], 'PASS')
    def test_vertex_change(self):
        self.assertEqual(self.compare(self.make('a', [([(0,0),(1,2)], 'A'), self.rows[1]]))['status'], 'DIFFERENT')
    def test_attribute_change(self):
        self.assertEqual(self.compare(self.make('a', [(self.rows[0][0], 'B'), self.rows[1]]))['status'], 'DIFFERENT')
    def test_missing(self):
        self.assertEqual(self.compare(self.make('a', self.rows[:1]))['missing_or_changed'], 1)
    def test_duplicate(self):
        self.assertEqual(self.compare(self.make('a', self.rows + self.rows[:1]))['extra_or_changed'], 1)
    def test_crs(self):
        with self.assertRaisesRegex(ValueError, 'CRS mismatch'):
            self.compare(self.make('a', self.rows, epsg=32635))
    def test_schema(self):
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.compare(self.make('a', self.rows, width=9))
    def test_missing_sidecar(self):
        p = self.make('a', self.rows); p.with_suffix('.prj').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.compare(p)
    def test_empty(self):
        with self.assertRaisesRegex(ValueError, 'empty export'):
            self.compare(self.make('a', []))
    def test_deleted_record(self):
        p = self.make('a', self.rows)
        dbf = p.with_suffix('.dbf'); data = bytearray(dbf.read_bytes()); data[int.from_bytes(data[8:10], 'little')] = 42; dbf.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'deleted'):
            self.compare(p)


if __name__ == '__main__':
    unittest.main()
