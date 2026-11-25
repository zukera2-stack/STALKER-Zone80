import unittest
from decimal import Decimal as D
from gm_adapter import *

def fixture():
    head='ncols 64\nnrows 64\nxllcorner 294373.084\nyllcorner 5698122.108\ncellsize 30\nNODATA_value -9999\n'
    # In-memory nongeographic asymmetric fixture; never write a raster.
    return (head+'\n'.join(' '.join(str(1000*(63-r)+c) for c in range(64)) for r in range(64))+'\n').encode()

def read(b,meta=None,prj=SYN_PRJ):
    return parse(b,prj,metadata(b,prj,True) if meta is None else meta,synthetic=True)

class Tests(unittest.TestCase):
    def test_full_grid(self):
        r=read(fixture()).report();self.assertEqual(r['valid_cells'],4096);self.assertEqual(r['grid_validation'],'PASS');self.assertFalse(r['native_grm_authorized'])
    def test_orientation(self):
        g=read(fixture())
        for x,y in [(0,0),(63,0),(0,63),(63,63),(12,45)]:
            self.assertEqual(g.sample_center(*g.center(x,y)),1000*y+x)
    def test_half_cell(self):
        g=read(fixture());self.assertEqual(g.center(0,0),(SW[0]+15,SW[1]+15))
        for x,y in [SW,(SW[0]+30,SW[1]+30),g.center(0,0)[:1]+(SW[1]+1920,)]:
            with self.assertRaises(Rejected):g.sample_center(x,y)
    def test_nodata(self):
        b=fixture().replace(b'63000 ',b'-9999 ',1);g=read(b);self.assertEqual(g.report()['nodata_cells'],1);self.assertEqual(g.report()['grid_validation'],'BLOCKED_NODATA')
        with self.assertRaises(Rejected):g.sample_center(*g.center(0,63))
    def test_all_nodata(self):
        b=fixture();h=b.splitlines()[:6];b=b'\n'.join(h+[b' '.join([b'-9999']*64)]*64)+b'\n';r=read(b).report();self.assertEqual(r['nodata_cells'],4096);self.assertIsNone(r['min_m'])
    def test_geometry(self):
        for a,b in [(b'ncols 64',b'ncols 65'),(b'nrows 64',b'nrows 63'),(b'cellsize 30',b'cellsize 20'),(b'294373.084',b'294388.084'),(b'5698122.108',b'5698137.108'),(b'xllcorner',b'xllcenter'),(b'NODATA_value',b'ncols'),(b'-9999',b'-999')]:
            with self.subTest(a=a):
                with self.assertRaises(Rejected):read(fixture().replace(a,b,1))
    def test_malformed(self):
        b=fixture()
        for x in [b.replace(b'63000 ',b'NaN ',1),b.replace(b'63000 ',b'inf ',1),b.replace(b'63000 ',b'1e999 ',1),b.replace(b'63000 ',b'',1),b+b'\n',b'\xff'+b]:
            with self.assertRaises(Rejected):read(x)
    def test_meta(self):
        b=fixture()
        for k,v in [('crs','EPSG:32635'),('vertical_datum','UNKNOWN'),('vertical_unit','ft'),('horizontal_unit','ft'),('pixel','point'),('producer','GRM'),('asc_sha256','0'*64),('prj_sha256','0'*64)]:
            m=metadata(b,SYN_PRJ,True);m[k]=v
            with self.subTest(k=k):
                with self.assertRaises(Rejected):read(b,m)
    def test_projection(self):
        with self.assertRaises(Rejected):read(fixture(),prj=b'fake')
    def test_actual_mode_block(self):
        b=fixture()
        with self.assertRaises(Rejected):parse(b,SYN_PRJ,metadata(b,SYN_PRJ))
    def test_determinism(self):
        self.assertEqual(read(fixture()).report(),read(fixture()).report())
    def test_outside(self):
        g=read(fixture())
        for i,j in [(-1,0),(64,0),(0,64),(True,0)]:
            with self.assertRaises(Rejected):g.center(i,j)

if __name__=='__main__':unittest.main()
