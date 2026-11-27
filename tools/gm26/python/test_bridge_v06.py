"""Cloud-only mock/fixture tests; no actual terrain or Global Mapper execution."""
import ast, contextlib, importlib.util, io, json, re, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from pyproj import Transformer

HERE=Path(__file__).parent

def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
bridge=load('bridge','GM-Bridge-v06.py'); client=load('client','GM-Bridge-Client-v06.py')
FWD=Transformer.from_crs(32636,4326,always_xy=True); REV=Transformer.from_crs(4326,32636,always_xy=True)

def value(x,y): return 100+(x-30)*100+(y-51)*100

class MockGM:
    GM_INVALID_ELEV_VALUE=-999999.; GM_Rectangle_t=SimpleNamespace; GM_Export_Arc_ASCII_Grid=8; GM_Export_ElevGeoTIFF=9; GM_ExportFlags_GenPRJFile=2; GM_ExportFlags_NoCompression=1048576; GM_ExportFlags_FillSmallGaps=128; GM_ElevUnit_Meters=0
    def __init__(self,mode='ok'): self.layers=0; self.epsg=None; self.mode=mode; self.commands=[]
    def GetSDKVersion(self): return 2621
    def IsRegistered(self): return 1
    def GetLoadedLayerList(self): return (11,1) if self.layers else 0
    def LoadProjectionFromEPSGCode(self,code): return 0,code
    def SetProjection(self,code): self.epsg=code; return 0
    def GetOnlineSourceInfo(self,name): return 0,None
    def LoadOnlineLayer(self,*a): self.layers=1; return 0,11
    def GetLayerInfo(self,h): return {'mHasRasterData':True,'mGlobalRect':dict(zip(('mMinX','mMinY','mMaxX','mMaxY'),(30.041,51.395,30.074,51.417)))}
    def ProjectPointAtElev(self,x,y,src,dest,z): return (0,*((FWD if src==32636 else REV).transform(x,y)))
    def GetLocationElevation(self,h,x,y): return (13,-999999.) if self.mode=='nodata' else (0,value(x,y))
    def CloseLayer(self,h): self.layers=0; return 0
    def ExportElevationEx(self,filename,fmt,layers,bounds,w,h,flags,units,extra):
        self.commands.append((fmt,layers,w,h,flags,units,extra))
        assert self.epsg==4326 and layers==[11] and (w,h)==(64,64)
        assert (bounds.mMinX,bounds.mMinY,bounds.mMaxX,bounds.mMaxY)==(30.047,51.396,30.067,51.416)
        assert units==self.GM_ElevUnit_Meters and not flags & self.GM_ExportFlags_FillSmallGaps
        if self.mode=='export_error': return 8
        # Fake file markers only, not a real DEM or export validation.
        p=Path(filename); p.write_text('mock only'); p.with_suffix('.prj').write_text('mock only'); return 0

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'reports'/'MAP-003'/'dc-bridge-v06-20261126'; self.root.mkdir(parents=True)
    def probe(self,mode='ok'):
        g=MockGM(mode)
        with contextlib.redirect_stdout(io.StringIO()): r=bridge.export_wgs84_diagnostic(g,True,self.root)
        return g,r
    def test_ast39(self):
        for p in HERE.glob('*.py'): ast.parse(p.read_text(),feature_version=(3,9))
    def test_native_call(self):
        g,r=self.probe(); self.assertEqual(r['status'],'WGS84_DIAGNOSTIC_EXPORTED'); self.assertEqual(len(g.commands),1); self.assertEqual(r['grid']['valid'],4096); self.assertTrue(r['cleanup_ok'])
    def test_nodata(self):
        g,r=self.probe('nodata'); self.assertEqual(r['status'],'BLOCKED_CONTROL_COVERAGE'); self.assertEqual(g.commands,[])
    def test_native_error(self):
        g,r=self.probe('export_error'); self.assertEqual(r['status'],'BLOCKED_WGS84_EXPORT_ASC'); self.assertTrue(r['cleanup_ok']); self.assertEqual(r['export_commands'][0]['code'],8)
    def test_output_gate(self):
        g=MockGM(); r=bridge.export_wgs84_diagnostic(g,True,self.root.parent); self.assertEqual(r['status'],'BLOCKED_OUTPUT_PARENT'); self.assertEqual(g.layers,0)
    def test_payload_rejected(self):
        p=self.root/'request.json'; id='a'*32; p.write_text(json.dumps({'schema':6,'id':id,'op':'export_wgs84_diagnostic','path':'bad'}))
        with self.assertRaises(ValueError): bridge.read_request(p,id)
if __name__=='__main__': unittest.main()
