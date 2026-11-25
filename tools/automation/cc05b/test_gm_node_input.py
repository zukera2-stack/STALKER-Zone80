import unittest, hashlib, dataclasses
from decimal import Decimal as D
from gm_node_input import Contract,inspect,Blocked

ASC=b'ncols 3\nnrows 3\nxllcorner 985\nyllcorner 1985\ncellsize 30\nNODATA_value -9999\n31 32 33\n21 22 23\n11 12 13\n'
PRJ=b'synthetic test metadata (not a real CRS WKT)'
def contract(a=ASC,p=PRJ,**kwargs):
    c=Contract(3,D(30),D(1000),D(2000),'EPSG:32636','EGM2008','m',hashlib.sha256(a).hexdigest(),hashlib.sha256(p).hexdigest(),'synthetic fixture only')
    return dataclasses.replace(c,**kwargs)
class Tests(unittest.TestCase):
    def test_orientation(self):
        report,rows=inspect(ASC,PRJ,contract()); self.assertEqual(rows,((11.,12.,13.),(21.,22.,23.),(31.,32.,33.))); self.assertFalse(report['native_generation_authorized']); self.assertEqual(report['max_float32_rounding_m'],'0')
    def test_deterministic(self): self.assertEqual(inspect(ASC,PRJ,contract()),inspect(ASC,PRJ,contract()))
    def test_pixel_shift(self):
        with self.assertRaisesRegex(Blocked,'coincide'): inspect(ASC,PRJ,contract(east=D(985),north=D(1985)))
    def test_nodata(self):
        a=ASC.replace(b'31 32',b'-9999 32')
        with self.assertRaisesRegex(Blocked,'NoData=1'): inspect(a,PRJ,contract(a))
    def test_metadata(self):
        for kw in ({'crs':'EPSG:32635'},{'datum':'UNKNOWN'},{'units':'ft'},{'source_evidence':''},{'grid_semantics':'pixel_area'}):
            with self.subTest(kw=kw), self.assertRaises(Blocked): inspect(ASC,PRJ,contract(**kw))
    def test_hash(self):
        for a,p in ((ASC+b' ',PRJ),(ASC,PRJ+b' ')):
            with self.assertRaisesRegex(Blocked,'hash'): inspect(a,p,contract())
    def test_bad_grid(self):
        for a in [ASC.replace(b'nrows 3',b'nrows 2'),ASC.replace(b'cellsize 30',b'cellsize 20'),ASC.replace(b'31 32 33',b'31 32'),ASC.replace(b'31 32 33',b'NaN 32 33'),ASC.replace(b'31 32 33',b'Inf 32 33'),ASC.replace(b'31 32 33',b'1e999 32 33'),ASC.replace(b'yllcorner',b'xllcorner'),ASC+b'0 0 0\n']:
            with self.subTest(a=a),self.assertRaises(Blocked): inspect(a,PRJ,contract(a))
    def test_quantization(self):
        a=ASC.replace(b'31 32 33',b'31.123456 32 33'); r,_=inspect(a,PRJ,contract(a)); self.assertGreater(D(r['max_float32_rounding_m']),0); self.assertLess(D(r['max_float32_rounding_m']),D('0.00001'))
if __name__=='__main__': unittest.main()
