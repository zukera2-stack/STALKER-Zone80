import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import config_builder as c


def fixture():
    usages=[['Default','Meadow'],['DefaultUrban','Grass'],['DefaultIndustrial'],['IceSurface'],['ScreeSurface','RockGround'],['Coastline','Sand'],['OceanGround'],['ForestGround'],['FarmLand'],['RiverGround','LakeGround'],['Asphalt']]
    a={k:{} for keys in c.GROUPS.values() for k in keys}
    a.update(BaseWorldName='SyntheticWorld',BaseDependency='SyntheticBase',Dependencies=[],Sidewalks=[],Ponds={'Size5':None},Roads=[])
    defs=[]
    for i,u in enumerate(usages):
        stem=f'a3\\synthetic\\gdt_test{i}'
        defs.append({'Usages':u,'Material':{'Id':f'{i:06X}FF','ColorTexture':stem+'_co.paa','NormalTexture':stem+'_nopx.paa'},'Surface':{'Name':f'SyntheticSurface{i}','Files':f'gdt_test{i}*','Character':[]}})
    a['Materials']={'Definitions':defs,'TextureSizeInMeters':4}
    for i in range(9):
        a['Roads'].append({'Id':f'SyntheticRoad{i}','Texture':r'a3\synthetic\road_ca.paa','TextureEnd':r'a3\synthetic\road_end_ca.paa','Material':r'a3\synthetic\road.rvmat','Width':4,'TextureWidth':5,'ClearWidth':6,'ProceduralStreetLamps':'None','DistanceBetweenStreetLamps':None,'DistanceBetweenStreetLampsMax':None,'HasSideWalks':False})
    a['Objects']={'Synthetic':[{'Model':r'a3\synthetic\test.p3d'}]}
    inv={'schema_version':1,'status':'READ_ONLY_LOOSE_FILE_INVENTORY','references':[{'virtual_path':p,'exists_as_loose_file':True} for p in sorted(set(c.references(a)))],'ground_texture_candidates':[],'errors':[]}
    return a,inv


def zpb_fixture():
    return {'schema_version':1,'addon_release':None,'source_commit':None,'assets':[{'model_id':'zpb.test.v01','package':'buildings_60','p3d_path':r'\z\stalker_pripyat_buildings\addons\buildings_60\models\test.p3d','classname':'ZPB_Test','cfgpatches':'ZPB_Buildings_60','pbo_filename':'zpb_buildings_60.pbo','status':'CANDIDATE'}]}


class Tests(unittest.TestCase):
    def setUp(self):self.a,self.inv=fixture()
    def report(self,a=None,inv=None):return c.compile_review(c.split_config(self.a if a is None else a),self.a,self.inv if inv is None else inv)
    def test_assembly_deterministic(self):
        m=c.split_config(self.a); r=self.report();self.assertEqual(r,c.compile_review(dict(reversed(list(m.items()))),self.a,self.inv));self.assertEqual(r['config_sha256_canonical'],c.digest(self.a));self.assertEqual(r['resource_counts']['runtime_approved'],0);self.assertFalse(r['native_generation_authorized'])
        self.assertEqual(len(r['material_lock']),16)
    def test_material_lock_negative(self):
        mutations=[lambda d:d[0]['Usages'].append('Default'),lambda d:d[0]['Usages'].remove('Meadow'),lambda d:d[0]['Usages'].append('Unknown'),lambda d:d[0]['Material'].update(Id=d[1]['Material']['Id']),lambda d:d[0]['Material'].update(Id='FF0000FF'),lambda d:d[0]['Material'].update(Id='00000000'),lambda d:d[0]['Material'].update(NormalTexture=r'a3\synthetic\wrong_nopx.paa'),lambda d:d[0]['Surface'].update(Files='other*'),lambda d:d[0]['Surface'].update(Name=d[1]['Surface']['Name'])]
        for i,f in enumerate(mutations):
            with self.subTest(i=i):
                a=copy.deepcopy(self.a);f(a['Materials']['Definitions']);self.assertRaises(ValueError,self.report,a)
    def test_road_and_feature_negative(self):
        mutations=[lambda a:a['Roads'][0].update(Id='Unknown'),lambda a:a['Roads'][0].update(Width=0),lambda a:a['Roads'][0].update(HasSideWalks=True),lambda a:a['Roads'][0].update(ProceduralStreetLamps='Enabled'),lambda a:a['Roads'][0].update(Material=r'a3\synthetic\wrong.paa'),lambda a:a.update(Buildings={'generic':{}}),lambda a:a.update(Sidewalks=[1]),lambda a:a.update(Ponds={'Size5':1}),lambda a:a.update(Dependencies=[{}])]
        for i,f in enumerate(mutations):
            with self.subTest(i=i):
                a=copy.deepcopy(self.a);f(a);self.assertRaises(ValueError,self.report,a)
    def test_resource_path_normalization(self):
        self.assertEqual(c.resource_path(r'\A3/Synthetic/X.P3D'),r'a3\synthetic\x.p3d')
        for p in [r'C:\test\x.p3d',r'a3\..\x.p3d',r'a3\synthetic\..paa',r'\\server\a3\x.p3d','a3/x.p3d ']:
            with self.subTest(p=p):self.assertRaises(ValueError,c.resource_path,p)
    def test_missing_and_external_never_approved(self):
        a=copy.deepcopy(self.a);a['Objects']['Synthetic']+=[{'Model':r'a3\synthetic\missing.p3d'},{'Model':r'z\external\models\test.p3d'}];r=self.report(a);self.assertEqual(r['resource_counts']['stock_unverified'],1);self.assertEqual(r['resource_counts']['external'],1);self.assertIn('EXTERNAL_RESOURCE_PATHS',r['blockers']);self.assertEqual(r['resource_counts']['runtime_approved'],0)
    def test_absent_surface_is_blocker(self):
        a=copy.deepcopy(self.a);a['Materials']['Definitions'][9].pop('Surface');self.assertEqual(self.report(a)['missing_surfaces'],['LakeGround','RiverGround'])
    def test_inventory_conflicts(self):
        p=self.inv['references'][0]['virtual_path'];co=next(x['virtual_path'] for x in self.inv['references'] if x['virtual_path'].endswith('_co.paa'))
        for f in [lambda i:i['references'].append(copy.deepcopy(i['references'][0])),lambda i:i.update(errors=['error']),lambda i:i['ground_texture_candidates'].append({'color':co,'normal_candidates':[r'a3\synthetic\bad_nopx.paa']})]:
            inv=copy.deepcopy(self.inv);f(inv);self.assertRaises(ValueError,self.report,None,inv)
        inv=copy.deepcopy(self.inv);next(x for x in inv['references'] if x['virtual_path']==co)['exists_as_loose_file']=False;inv['ground_texture_candidates']=[{'color':co,'normal_candidates':[co[:-7]+'_nopx.paa']}];self.assertRaises(ValueError,self.report,None,inv)
    def test_dependency_graph(self):
        rows=[{'name':n,'requires':deps,'approved':True,'scope':'SYNTHETIC_ONLY'} for n,deps in [('A',['B','C']),('B',['C']),('C',[])]]
        self.assertEqual(c.synthetic_dependency_closure(rows,['A']),['a','b','c'])
        for f in [lambda r:r.pop(),lambda r:r[2].update(requires=['A']),lambda r:r[2].update(approved=False),lambda r:r.append(dict(r[0],name='a'))]:
            with self.subTest():
                x=copy.deepcopy(rows);f(x);self.assertRaises(ValueError,c.synthetic_dependency_closure,x,['A'])
    def test_zpb_never_selectable(self):
        m=zpb_fixture();self.assertEqual(c.zpb_review(m)['selectable_count'],0);m['assets'][0]['status']='MODEL_READY';self.assertEqual(c.zpb_review(m)['selectable_count'],0)
        for f in [lambda x:x['assets'].append(copy.deepcopy(x['assets'][0])),lambda x:x['assets'][0].update(p3d_path=r'a3\synthetic\test.p3d'),lambda x:x['assets'][0].update(pbo_filename='other.pbo')]:
            x=copy.deepcopy(m);f(x);self.assertRaises(ValueError,c.zpb_review,x)
    def test_catalog_reference_audit(self):
        row={'approved_for_generation':False,'p3d_path':r'a3\synthetic\x.p3d'};cats={n:{'schema_version':1,'status':'REFERENCE_ONLY','approved_for_generation':False,k:[copy.deepcopy(row)]} for n,k in [('vegetation','assets'),('roads','profiles'),('materials','definitions'),('infrastructure','assets')]};self.assertEqual(c.reference_audit(cats)['count'],1);cats['roads']['profiles'][0]['approved_for_generation']=True;self.assertRaises(ValueError,c.reference_audit,cats)
    def test_module_schema(self):
        m=c.split_config(self.a);m['roads']['Buildings']={};self.assertRaises(ValueError,c.compile_review,m,self.a,self.inv)
    def test_json_invalid(self):
        for b in [b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":1e999}']:
            self.assertRaises(ValueError,c.load_bytes,b)
    def test_cli_modes(self):
        with tempfile.TemporaryDirectory() as td:
            paths=[Path(td)/f'{i}.json' for i in range(3)]
            for p,v in zip(paths,[self.a,self.a,self.inv]):p.write_bytes(c.canonical(v))
            cmd=[sys.executable,str(Path(c.__file__).resolve()),*map(str,paths)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'REVIEW_ONLY_GENERATION_BLOCKED')
            r=subprocess.run(cmd+['--mode','production'],capture_output=True,text=True,timeout=10);self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertEqual(len(list(Path(td).iterdir())),3)

if __name__=='__main__':unittest.main()
