"""Offline mocks only. Does not import native Global Mapper or access network."""
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

HERE = Path(__file__).parent

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

bridge = load('bridge', 'GM-Bridge-v02.py')
client = load('client', 'GM-Bridge-Client-v02.py')

POINTS = [(294688.084, 5699727.108, 30.047580700382, 51.411534691737),
          (294988.084, 5699427.108, 30.052062010081, 51.408949230160),
          (295348.084, 5699067.108, 30.057438915213, 51.405846437886),
          (295708.084, 5698707.108, 30.062815093355, 51.402743385634),
          (295978.084, 5698437.108, 30.066846749945, 51.400415925884)]

class MockGM:
    NULL = 0
    GM_INVALID_ELEV_VALUE = -999999.0
    GM_Rectangle_t = SimpleNamespace
    def __init__(self, mode='ok'):
        self.mode, self.layers, self.calls, self.epsg = mode, 0, 0, None
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
        vals = (30, 51, 31, 52) if self.epsg == 4326 else (294000, 5698000, 297000, 5701000)
        if self.mode == 'extent': vals = (0, 0, 1, 1)
        box = dict(zip(('mMinX','mMinY','mMaxX','mMaxY'), vals))
        return {'mGlobalRect':box,'mNativeRect':box,'mHasRasterData':True}
    def ProjectPointAtElev(self, lon, lat, src, dest, z):
        if self.mode == 'projection': return 0, 0, 0
        if self.epsg == 4326: return 0, lon, lat
        e,n,_,_ = next(p for p in POINTS if p[2:] == (lon,lat))
        return 0,e,n
    def GetLocationElevation(self, handle, x, y):
        self.calls += 1
        if self.mode == 'nodata' or (self.mode == 'partial' and self.epsg == 32636): return 13, self.GM_INVALID_ELEV_VALUE
        return 0, 120.0
    def CloseLayer(self, handle):
        if self.mode != 'cleanup': self.layers -= 1
        return 0

class Tests(unittest.TestCase):
    def probe(self, mode, expected):
        gm = MockGM(mode)
        with contextlib.redirect_stdout(io.StringIO()): r = bridge.elevation_v03(gm, True)
        self.assertEqual(r['status'], expected)
        self.assertEqual(r['grid'], 'NOT_RUN'); self.assertEqual(r['export'], 'NOT_RUN')
        return gm, r
    def test_ast39(self):
        for f in ('GM-Bridge-v02.py','GM-Bridge-Client-v02.py'):
            ast.parse((HERE/f).read_text(), feature_version=(3,9))
    def test_pass(self):
        gm,r = self.probe('ok','DIAGNOSTIC_CONTROLS_PASS_GRID_NOT_RUN'); self.assertEqual(gm.calls,20); self.assertTrue(r['cleanup_ok'])
    def test_nodata(self): self.probe('nodata','BLOCKED_NODATA_BOTH_PROJECTIONS')
    def test_partial(self): self.probe('partial','BLOCKED_INCONSISTENT_OR_PARTIAL_READBACK')
    def test_extent(self): self.probe('extent','BLOCKED_EXTENT_MISMATCH')
    def test_projection(self): self.probe('projection','BLOCKED_PROJECTION_READBACK')
    def test_cleanup(self): self.probe('cleanup','BLOCKED_CLEANUP')
    def test_host_gate(self):
        gm=MockGM(); r=bridge.elevation_v03(gm,False); self.assertEqual(r['status'],'BLOCKED_HOST'); self.assertEqual(gm.layers,0)
    def test_occupied(self):
        gm=MockGM(); gm.layers=1; r=bridge.elevation_v03(gm,True); self.assertEqual(r['status'],'BLOCKED_WORKSPACE'); self.assertEqual(gm.layers,1)
    def handshake(self, mode, expected):
        gm=MockGM(mode)
        with tempfile.TemporaryDirectory(prefix='Zone80-GM-Bridge-v02-') as name, patch.object(bridge,'host_ok',return_value=True), contextlib.redirect_stdout(io.StringIO()):
            root=Path(name); t=threading.Thread(target=bridge.serve,args=(gm,root,5,5)); t.start()
            try:
                for _ in range(100):
                    if (root/'ready.json').exists(): break
                    time.sleep(.01)
                self.assertTrue((root/'ready.json').exists())
                # Probe before ping rejected; never touches layers.
                self.assertFalse(client.request(root,'elevation_v03',2)['ok']); self.assertEqual(gm.calls,0)
                self.assertEqual(client.request(root,'ping',2)['result'],'PONG')
                self.assertEqual(client.request(root,'status',2)['result']['layers'],0)
                r=client.request(root,'elevation_v03',2); self.assertTrue(r['ok']); self.assertEqual(r['result']['status'],expected)
                t.join(2); self.assertFalse(t.is_alive())
                self.assertEqual(client.read_json(root/'finished.json')['reason'],'PROBE_COMPLETE')
                with self.assertRaises(ValueError): client.request(root,'elevation_v03',1)
            finally: t.join(6)
    def test_roundtrip_pass(self): self.handshake('ok','DIAGNOSTIC_CONTROLS_PASS_GRID_NOT_RUN')
    def test_roundtrip_nodata(self): self.handshake('nodata','BLOCKED_NODATA_BOTH_PROJECTIONS')
    def test_reject_payload(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name)/'request.json'; id='a'*32
            for payload in ({'schema':2,'id':id,'op':'exec'}, {'schema':2,'id':id,'op':'elevation_v03','path':'other.py'}, {'schema':1,'id':id,'op':'ping'}):
                p.write_text(json.dumps(payload));
                with self.assertRaises(ValueError): bridge.read_request(p,id)
    def test_client_unknown(self):
        with self.assertRaises(ValueError): client.request(Path('.'),'exec',1)

if __name__ == '__main__': unittest.main()
