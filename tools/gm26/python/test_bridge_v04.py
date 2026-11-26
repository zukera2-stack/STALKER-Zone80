"""Cloud-only mock/fixture tests; no actual terrain or Global Mapper execution."""
import ast, contextlib, importlib.util, io, json, re, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from pyproj import Transformer
import numpy as np
import rasterio
from rasterio.transform import from_origin

HERE=Path(__file__).parent

def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
bridge=load('bridge','GM-Bridge-v04.py'); qc=load('qc','QC-MAP003-v04.py'); client=load('client','GM-Bridge-Client-v04.py')
FWD=Transformer.from_crs(32636,4326,always_xy=True); REV=Transformer.from_crs(4326,32636,always_xy=True)

def value(x,y): return 100+(x-30)*100+(y-51)*100

class MockGM:
    GM_INVALID_ELEV_VALUE=-999999.; GM_Rectangle_t=SimpleNamespace; GM_LoadFlags_UseDefaultLoadOpts=0
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
    def RunScript(self,cmd,*a):
        self.commands.append(cmd)
        if self.mode=='export_error': return 12,0,0
        p=Path(re.search(r'FILENAME="([^"]+)"',cmd)[1])
        # Synthetic fixture from mock values, never a production DEM.
        z=np.array([[value(*FWD.transform(qc.X+15+c*30,qc.Y+1920-15-r*30)) for c in range(64)] for r in range(64)],dtype='float32')
        if p.suffix=='.asc':
            header=f'ncols 64\nnrows 64\nxllcorner {qc.X}\nyllcorner {qc.Y}\ncellsize 30\nNODATA_value -9999\n'
            p.write_text(header+'\n'.join(' '.join(f'{v:.3f}' for v in row) for row in z)+'\n')
            p.with_suffix('.prj').write_text(rasterio.crs.CRS.from_epsg(32636).to_wkt())
        else:
            with rasterio.open(p,'w',driver='GTiff',width=64,height=64,count=1,dtype='float32',crs='EPSG:32636',transform=from_origin(qc.X,qc.Y+1920,30,30),nodata=-9999,compress='none') as ds: ds.write(z,1)
        return 0,0,0

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'reports'/'MAP-003'/'dc-bridge-v04-20261126'; self.root.mkdir(parents=True)
    def probe(self,mode='ok'):
        g=MockGM(mode)
        with contextlib.redirect_stdout(io.StringIO()): r=bridge.export_candidate(g,True,self.root)
        return g,r
    def test_ast39(self):
        for p in HERE.glob('*.py'): ast.parse(p.read_text(),feature_version=(3,9))
    def test_export_qc(self):
        g,r=self.probe(); self.assertEqual(r['status'],'CANDIDATE_EXPORTED_QC_REQUIRED'); self.assertEqual(len(g.commands),2)
        self.assertTrue(all('FILL_GAPS=NO' in c and 'OVERWRITE_EXISTING=NO' in c for c in g.commands)); self.assertTrue(r['cleanup_ok'])
        report=qc.qc(Path(r['output_directory']),{'schema':4,'op':'export_candidate','ok':True,'result':r}); self.assertEqual(report['valid'],4096); self.assertEqual(report['status'],'DIAGNOSTIC_EXPORT_QC_PASS')
    def test_nodata_no_export(self):
        g,r=self.probe('nodata'); self.assertEqual(r['status'],'BLOCKED_CONTROL_COVERAGE'); self.assertEqual(g.commands,[])
    def test_native_error(self):
        g,r=self.probe('export_error'); self.assertEqual(r['status'],'BLOCKED_EXPORT_ASC'); self.assertTrue(r['cleanup_ok'])
    def test_output_gate(self):
        g=MockGM(); r=bridge.export_candidate(g,True,self.root.parent); self.assertEqual(r['status'],'BLOCKED_OUTPUT_PARENT'); self.assertEqual(g.layers,0)
    def test_wrong_grid(self):
        g,r=self.probe(); p=Path(r['output_directory'])/'MAP003_SRTM.asc'; raw=p.read_bytes().replace(b'ncols 64',b'ncols 65',1)
        with self.assertRaisesRegex(ValueError,'ASC_GRID'): qc.read_asc(raw)
    def test_invalid_height(self):
        g,r=self.probe(); p=Path(r['output_directory'])/'MAP003_SRTM.asc'; lines=p.read_text().splitlines(); cells=lines[6].split(); cells[0]='-9999'; lines[6]=' '.join(cells)
        with self.assertRaisesRegex(ValueError,'INVALID_HEIGHT'): qc.read_asc(('\n'.join(lines)+'\n').encode())
    def test_wrong_projection(self):
        g,r=self.probe(); p=Path(r['output_directory'])/'MAP003_SRTM.prj'
        with self.assertRaises(ValueError): qc.read_prj(p.read_bytes().replace(b'33',b'39'))
    def test_payload_rejected(self):
        p=self.root/'request.json'; id='a'*32; p.write_text(json.dumps({'schema':4,'id':id,'op':'export_candidate','path':'bad'}))
        with self.assertRaises(ValueError): bridge.read_request(p,id)
    def test_truncated_tiff(self):
        with self.assertRaises(ValueError): qc.read_tiff(b'II*\x00\x08\x00\x00\x00')

if __name__=='__main__': unittest.main()
