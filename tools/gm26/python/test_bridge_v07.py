"""Synthetic-only tests: no real terrain generation."""
import ast, contextlib, importlib.util, io, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import rasterio
from rasterio.transform import from_origin
from pyproj import Transformer
HERE=Path(__file__).parent
def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
bridge=load('bridge','GM-Bridge-v07.py');qc=load('qc','QC-MAP003-v07.py')
FWD=Transformer.from_crs(32636,4326,always_xy=True);REV=Transformer.from_crs(4326,32636,always_xy=True)
def value(x,y):return 100+(x-30)*100+(y-51)*100
class GM:
 GM_INVALID_ELEV_VALUE=-999999.;GM_Rectangle_t=SimpleNamespace;GM_Export_Arc_ASCII_Grid=8;GM_Export_ElevGeoTIFF=9;GM_ExportFlags_GenPRJFile=2;GM_ExportFlags_NoCompression=1048576;GM_ExportFlags_FillSmallGaps=128;GM_ElevUnit_Meters=0;GM_LoadFlags_NoWebDownload=65536;GM_LoadFlags_NoProjPrompt=4
 def __init__(self,mode='ok'):self.layers=0;self.mode=mode;self.commands=[];self.epsg=None
 def GetSDKVersion(self):return 2621
 def IsRegistered(self):return 1
 def GetLoadedLayerList(self):return (self.layers,1) if self.layers else 0
 def LoadProjectionFromEPSGCode(self,e):return 0,e
 def SetProjection(self,e):self.epsg=e;return 0
 def GetOnlineSourceInfo(self,n):return 0,None
 def LoadOnlineLayer(self,*a):self.layers=11;return 0,11
 def GetLayerInfo(self,h):return {'mHasRasterData':True,'mTypeName':'mock','mGlobalRect':dict(zip(('mMinX','mMinY','mMaxX','mMaxY'),(30.041,51.395,30.074,51.417)))}
 def ProjectPointAtElev(self,x,y,src,dest,z):return (0,*((FWD if src==32636 else REV).transform(x,y)))
 def GetLocationElevation(self,h,x,y):return (13,-999999.) if self.mode=='source_nodata' else (0,value(x,y)+(2 if self.mode=='local_delta' and h==22 else 0))
 def CloseLayer(self,h):assert h==self.layers;self.layers=0;return 0
 def LoadLayer(self,p,flags):
  assert self.layers==0 and self.epsg==4326 and flags==self.GM_LoadFlags_NoWebDownload|self.GM_LoadFlags_NoProjPrompt
  if self.mode=='reload_error':return 8,None
  self.layers=22;return 0,22
 def ExportElevationEx(self,p,fmt,layers,b,w,h,flags,units,extra):
  assert layers==[self.layers] and not flags & self.GM_ExportFlags_FillSmallGaps and units==0
  self.commands.append((self.epsg,layers,w,h,fmt));p=Path(p)
  if self.epsg==4326:
   assert (w,h)==(131,87) and self.layers==11
   assert (b.mMinX,b.mMinY,b.mMaxX,b.mMaxY)==(30.04125,51.39525,30.07375,51.41675)
   z=[[value(30.04125+c*.00025,51.41675-r*.00025) for c in range(w)] for r in range(h)]
   if self.mode=='mid_nodata':z[0][0]=-9999
   p.write_text('ncols 131\nnrows 87\nxllcorner 30.041125\nyllcorner 51.395125\ncellsize 0.00025\nnodata_value -9999\n'+'\n'.join(' '.join(f'{v:.4f}' for v in row) for row in z)+'\n')
   p.with_suffix('.prj').write_text('GEOGCS["GCS_WGS_1984",DATUM["D_WGS84",SPHEROID["WGS84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]');return 0
  assert self.epsg==32636 and self.layers==22 and (w,h)==(64,64)
  if self.mode=='utm_error':return 8
  z=np.array([[value(*FWD.transform(qc.X+15+c*30,qc.Y+1920-15-r*30)) for c in range(w)] for r in range(h)],dtype='float32')
  if p.suffix=='.asc':
   p.write_text(f'ncols 64\nnrows 64\nxllcorner {qc.X}\nyllcorner {qc.Y}\ncellsize 30\nnodata_value -9999\n'+'\n'.join(' '.join(f'{v:.3f}' for v in row) for row in z)+'\n');p.with_suffix('.prj').write_text(rasterio.crs.CRS.from_epsg(32636).to_wkt())
  else:
   with rasterio.open(p,'w',driver='GTiff',width=64,height=64,count=1,dtype='float32',crs='EPSG:32636',transform=from_origin(qc.X,qc.Y+1920,30,30),nodata=-9999,compress='none') as ds:ds.write(z,1)
  return 0
class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'reports'/'MAP-003'/'dc-bridge-v07-20261126';self.root.mkdir(parents=True)
 def run_probe(self,mode='ok'):
  g=GM(mode)
  with contextlib.redirect_stdout(io.StringIO()):r=bridge.export_candidate(g,True,self.root)
  self.assertTrue(r['cleanup_ok']);return g,r
 def test_success(self):
  g,r=self.run_probe();self.assertEqual(r['status'],'CANDIDATE_EXPORTED_QC_REQUIRED');self.assertEqual(r['intermediate']['valid'],11397);self.assertEqual(len(g.commands),3);report=qc.qc(Path(r['output_directory']),{'schema':7,'op':'export_candidate','ok':True,'result':r});self.assertEqual(report['valid'],4096)
 def test_failures(self):
  for mode,status,count in [('source_nodata','BLOCKED_CONTROL_COVERAGE',0),('mid_nodata','BLOCKED_INTERMEDIATE_NODATA',1),('reload_error','BLOCKED_LOCAL_LOAD',1),('local_delta','BLOCKED_LOCAL_CONTROL_DELTA',1),('utm_error','BLOCKED_UTM_EXPORT_ASC',2)]:
   with self.subTest(mode=mode):g,r=self.run_probe(mode);self.assertEqual(r['status'],status);self.assertEqual(len(g.commands),count)
 def test_tamper(self):
  g,r=self.run_probe();p=Path(r['output_directory']);f=p/'SRTM_WGS84_INTERMEDIATE.asc';f.write_bytes(f.read_bytes()+b'\n');
  with self.assertRaisesRegex(ValueError,'INTERMEDIATE_HASH'):qc.qc(p,{'schema':7,'op':'export_candidate','ok':True,'result':r})
 def test_ast39(self):
  for p in HERE.glob('*.py'):ast.parse(p.read_text(),feature_version=(3,9))
 def test_payload(self):
  p=self.root/'request.json';i='a'*32;p.write_text(json.dumps({'schema':7,'id':i,'op':'export_candidate','path':'bad'}))
  with self.assertRaises(ValueError):bridge.read_request(p,i)
if __name__=='__main__':unittest.main()
