import copy
import unittest
from sector_manager import Grid, plan, dirty, validate_seams, digest

# Exact output contract of existing build_sector_manifests.manifests (not a second writer).
def fixture():
    return [dict(schema_version=1, sector_id=f'S{c:02d}_{r:02d}', column=c,row=r,local_xy_bbox_m=[c*10240,r*10240,(c+1)*10240,(r+1)*10240],ownership='half-open [min,max), clipped at world boundary',production_crs=None,source_features=0,generation_status='manifest-only') for r in range(8) for c in range(8)]

class Tests(unittest.TestCase):
    def setUp(self):
        self.g=Grid.from_foundation(fixture(),(-3000000,5000000),100000)
        self.s=self.g.step_mm; self.h=digest('rules-v1')
    def p(self,x,y): return self.g.projected((x,y))
    def feature(self,id,pts,revision='1'):
        return dict(id=id,kind='point' if len(pts)==1 else 'segment',points_mm=[self.p(*p) for p in pts],revision=revision)
    def test_grid_coverage(self):
        bounds=[self.g.bounds(*cr) for cr in self.g.sectors()]
        self.assertEqual(len(set(map(tuple,bounds))),64)
        self.assertEqual(sum((b[2]-b[0])*(b[3]-b[1]) for b in bounds),(8*self.s)**2)
        for i,a in enumerate(bounds):
            for b in bounds[i+1:]: self.assertFalse(max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]))
        self.assertEqual(sum(len(self.g.neighbors(*cr)) for cr in self.g.sectors()),224)
    def test_ownership_roundtrip(self):
        for c,r in self.g.sectors():
            for x,y in [(c*self.s,r*self.s),((c+1)*self.s-1,(r+1)*self.s-1)]:
                p=self.p(x,y); self.assertEqual(self.g.local(p),(x,y)); self.assertEqual(self.g.owner(p),self.g.id(c,r))
        for p in [(-1,0),(8*self.s,0),(0,8*self.s),(0,-1)]:
            with self.assertRaises(ValueError): self.g.owner(self.p(*p))
    def test_seam_and_halo(self):
        s=self.s; features=[self.feature('anchor',[(s,s//2)]),self.feature('cross',[(s-101,s//2),(s+102,s//2+1)])]
        snap=plan(self.g,features,self.h); a,b=[snap['sectors'][n] for n in ('S00_00','S01_00')]
        self.assertEqual(a['owned_point_ids'],[]); self.assertEqual(b['owned_point_ids'],['anchor'])
        self.assertEqual(a['context_ids'],b['context_ids']); self.assertEqual(a['seams']['E'],b['seams']['W']); self.assertEqual(validate_seams(snap),[])
        self.assertEqual(a['seams']['E']['events'][0]['along_mm'],[s//2*203+101,203])
    def test_corner(self):
        s=self.s; snap=plan(self.g,[self.feature('corner',[(s,s)])],self.h)
        self.assertEqual([k for k,v in snap['sectors'].items() if v['owned_point_ids']],['S01_01'])
        self.assertEqual(sum('corner' in v['context_ids'] for v in snap['sectors'].values()),4)
    def test_dirty_local_boundary_removal(self):
        s=self.s; f=self.feature('one',[(s//2,s//2)]); a=plan(self.g,[f],self.h)
        b=plan(self.g,[dict(f,revision='2')],self.h); self.assertEqual(dirty(a,b),['S00_00'])
        edge=self.feature('one',[(s,s//2)]); c=plan(self.g,[edge],self.h)
        self.assertEqual(dirty(b,c),['S00_00','S01_00']); self.assertEqual(dirty(c,plan(self.g,[],self.h)),['S00_00','S01_00'])
        self.assertEqual(len(dirty(a,plan(self.g,[f],digest('rules-v2')))),64)
    def test_determinism(self):
        f=[self.feature('a',[(2,2)]),self.feature('b',[(3,3)])]
        self.assertEqual(plan(self.g,f,self.h),plan(self.g,list(reversed(f)),self.h))
        self.assertEqual(dirty(plan(self.g,f,self.h),plan(self.g,f,self.h)),[])
    def test_collinear_and_tamper(self):
        s=self.s; snap=plan(self.g,[self.feature('edge',[(s,1),(s,s-1)])],self.h)
        self.assertTrue(any(i[2]=='collinear-review' for i in validate_seams(snap)))
        snap['sectors']['S00_00']['seams']['E']['sha256']='bad'
        self.assertTrue(any(i[2]=='mismatch' for i in validate_seams(snap)))
    def test_missing_seam_rejected(self):
        snap=plan(self.g,[],self.h)
        for name,direction in [('S00_00','E'),('S01_00','W')]:
            del snap['sectors'][name]['seams'][direction]; del snap['sectors'][name]['neighbors'][direction]
        self.assertTrue(any(i[2]=='invalid-adjacency' for i in validate_seams(snap)))
        del snap['sectors']['S00_00']
        self.assertEqual(validate_seams(snap),[('grid','','missing-or-extra-sector')])
    def test_snapshot_json_roundtrip(self):
        import json
        snap=plan(self.g,[self.feature('cross',[(self.s-1,1),(self.s+1,2)])],self.h)
        loaded=json.loads(json.dumps(snap)); self.assertEqual(validate_seams(loaded),[]); self.assertEqual(dirty(snap,loaded),[])
    def test_invalid_foundation(self):
        for field,value in [('sector_id','bad'),('production_crs','EPSG:32636'),('column',1),('local_xy_bbox_m',[0,0,10241,10240]),('generation_status','ready')]:
            items=fixture(); items[0][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): Grid.from_foundation(items,(0,0),0)
        with self.assertRaises(ValueError): Grid.from_foundation(fixture()[:-1],(0,0),0)
    def test_invalid_features(self):
        a=self.feature('a',[(1,1)])
        for features in [[a,a],[dict(a,id='../bad')],[dict(a,kind='polygon')],[dict(a,points_mm=[[0.1,0]])],[self.feature('bad',[(1,1),(1,1)])],[self.feature('bad',[(8*self.s,0)])]]:
            with self.subTest(features=features), self.assertRaises(ValueError): plan(self.g,features,self.h)
        with self.assertRaises(ValueError): plan(self.g,[a],'bad')

if __name__=='__main__': unittest.main()
