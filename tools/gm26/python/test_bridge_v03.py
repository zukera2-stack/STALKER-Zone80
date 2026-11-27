"""Offline mocks only; pyproj is a test dependency, never creates terrain."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pyproj import Transformer

HERE = Path(__file__).parent

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

bridge = load('bridge', 'GM-Bridge-v03.py')
client = load('client', 'GM-Bridge-Client-v03.py')
TRANSFORM = Transformer.from_crs(32636, 4326, always_xy=True)

class MockGM:
    GM_INVALID_ELEV_VALUE = -999999.0
    GM_Rectangle_t = SimpleNamespace
    def __init__(self, mode='ok'):
        self.mode, self.layers, self.calls, self.epsg = mode, 0, 0, None
        self.positions = []
    def GetSDKVersion(self): return 2621
    def IsRegistered(self): return 1
    def GetLoadedLayerList(self): return 0 if self.layers == 0 else (11, self.layers)
    def LoadProjectionFromEPSGCode(self, code): return 0, code
    def SetProjection(self, code): self.epsg = code; return 0
    def GetOnlineSourceInfo(self, name): return 0, None
    def LoadOnlineLayer(self, name, bounds, options):
        self.layers += 1
        return 0, 11
    def GetLayerInfo(self, handle):
        vals = (30.041, 51.395, 30.074, 51.417) if self.mode != 'extent' else (30.05,51.4,30.06,51.41)
        box = dict(zip(('mMinX','mMinY','mMaxX','mMaxY'), vals))
        return {'mGlobalRect':box,'mHasRasterData':True}
    def ProjectPointAtElev(self, e, n, src, dest, z):
        assert src == 32636 and dest is None and self.epsg == 4326
        if self.mode == 'projection': return 0,0,0
        if self.mode == 'grid_transform' and self.calls >= 5: return 13,0,0
        x,y = TRANSFORM.transform(e,n)
        return 0,x,y
    def GetLocationElevation(self, handle, x, y):
        assert self.epsg == 4326 and handle == 11
        self.calls += 1; self.positions.append((x,y))
        if self.mode == 'nodata' or (self.mode == 'grid_nodata' and self.calls == 7): return 13,self.GM_INVALID_ELEV_VALUE
        if self.mode == 'nan' and self.calls == 7: return 0,float('nan')
        if self.mode == 'exception' and self.calls == 7: raise TypeError('mock')
        return 0,120.0 if self.mode == 'constant' else 120.0 + (x-30)*100 + (y-51)*100
    def CloseLayer(self, handle):
        if self.mode != 'cleanup': self.layers -= 1
        return 0

class Tests(unittest.TestCase):
    def probe(self, mode, expected):
        gm=MockGM(mode)
        with contextlib.redirect_stdout(io.StringIO()): r=bridge.elevation_grid(gm,True)
        self.assertEqual(r['status'],expected); self.assertEqual(r['export'],'NOT_RUN')
        return gm,r
    def test_ast39(self):
        for f in ('GM-Bridge-v03.py','GM-Bridge-Client-v03.py','test_bridge_v03.py'):
            ast.parse((HERE/f).read_text(), feature_version=(3,9))
    def test_pass(self):
        gm,r=self.probe('ok','DIAGNOSTIC_GRID_PASS'); g=r['grid']
        self.assertEqual(gm.calls,4101); self.assertEqual(g['valid'],4096); self.assertEqual(g['invalid'],0)
        self.assertEqual(len(set(gm.positions[5:])),4096); self.assertEqual(len(g['rows']),64)
        self.assertEqual(gm.positions[5],TRANSFORM.transform(294388.084,5700027.108))
        self.assertEqual(gm.positions[-1],TRANSFORM.transform(296278.084,5698137.108))
        self.assertEqual(len(r['control_grid_readback']),5); self.assertTrue(r['cleanup_ok'])
    def test_nodata(self):
        gm,r=self.probe('nodata','BLOCKED_CONTROL_COVERAGE'); self.assertEqual(gm.calls,5)
    def test_grid_nodata(self):
        gm,r=self.probe('grid_nodata','BLOCKED_GRID_COVERAGE'); self.assertEqual(r['grid']['invalid'],1)
    def test_nan(self): self.probe('nan','BLOCKED_GRID_COVERAGE')
    def test_constant(self): self.probe('constant','BLOCKED_CONSTANT_GRID')
    def test_projection(self): self.probe('projection','BLOCKED_CONTROL_PROJECTION_READBACK')
    def test_extent(self): self.probe('extent','BLOCKED_CONTROL_OUTSIDE_BOUNDS')
    def test_transform(self): self.probe('grid_transform','BLOCKED_GRID_TRANSFORM')
    def test_exception(self):
        gm,r=self.probe('exception','BLOCKED_EXCEPTION'); self.assertEqual(r['error']['type'],'TypeError'); self.assertTrue(r['cleanup_ok'])
    def test_cleanup(self): self.probe('cleanup','BLOCKED_CLEANUP')
    def test_host_gate(self):
        gm=MockGM(); r=bridge.elevation_grid(gm,False); self.assertEqual(r['status'],'BLOCKED_HOST'); self.assertEqual(gm.layers,0)
    def test_occupied(self):
        gm=MockGM(); gm.layers=1; r=bridge.elevation_grid(gm,True); self.assertEqual(r['status'],'BLOCKED_WORKSPACE'); self.assertEqual(gm.layers,1)
    def test_roundtrip(self):
        gm=MockGM()
        with tempfile.TemporaryDirectory(prefix='Zone80-GM-Bridge-v03-') as name, patch.object(bridge,'host_ok',return_value=True), contextlib.redirect_stdout(io.StringIO()):
            root=Path(name); t=threading.Thread(target=bridge.serve,args=(gm,root,5,5)); t.start()
            try:
                for _ in range(100):
                    if (root/'ready.json').exists(): break
                    time.sleep(.01)
                self.assertFalse(client.request(root,'elevation_grid',2)['ok']); self.assertEqual(gm.calls,0)
                self.assertEqual(client.request(root,'ping',2)['result'],'PONG')
                self.assertEqual(client.request(root,'status',2)['result']['layers'],0)
                r=client.request(root,'elevation_grid',2); self.assertTrue(r['ok']); self.assertEqual(r['result']['status'],'DIAGNOSTIC_GRID_PASS')
                t.join(2); self.assertFalse(t.is_alive()); self.assertEqual(client.read_json(root/'finished.json')['reason'],'PROBE_COMPLETE')
                with self.assertRaises(ValueError): client.request(root,'elevation_grid',1)
            finally: t.join(6)
    def test_reject_payload(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name)/'request.json'; id='a'*32
            for payload in ({'schema':3,'id':id,'op':'exec'}, {'schema':3,'id':id,'op':'elevation_grid','path':'other.py'}, {'schema':2,'id':id,'op':'ping'}):
                p.write_text(json.dumps(payload))
                with self.assertRaises(ValueError): bridge.read_request(p,id)
    def test_client_unknown(self):
        with self.assertRaises(ValueError): client.request(Path('.'),'exec',1)

if __name__ == '__main__': unittest.main()
