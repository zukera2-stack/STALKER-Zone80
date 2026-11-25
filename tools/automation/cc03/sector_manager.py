"""CC-03 logical sectors only. No geographic generation or native adapters."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integer_pair(value):
    require(isinstance(value, (list, tuple)) and len(value) == 2 and all(type(x) is int for x in value), 'integer mm pair required')
    return tuple(value)


def overlap(a, b):
    # Conservative closed intersection: boundary context may be shared.
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


@dataclass(frozen=True)
class Grid:
    side: int
    step_mm: int
    origin_mm: tuple
    halo_mm: int

    @classmethod
    def from_foundation(cls, items, origin_mm, halo_mm):
        origin = integer_pair(origin_mm)
        require(type(halo_mm) is int and halo_mm >= 0, 'invalid halo')
        require(isinstance(items, list) and len(items) == 64, '64 foundation manifests required')
        first = items[0]['local_xy_bbox_m']
        require(len(first) == 4 and all(type(x) is int for x in first), 'integer metre bounds required')
        step = first[2] - first[0]
        require(step > 0 and halo_mm <= step * 1000, 'invalid grid/halo')
        expected = {(c, r) for r in range(8) for c in range(8)}
        for item in items:
            c, r = item['column'], item['row']
            require(type(c) is int and type(r) is int and (c, r) in expected, 'duplicate or invalid sector')
            expected.remove((c, r))
            require(item['schema_version'] == 1 and item['sector_id'] == cls.id(c, r) and item['production_crs'] is None and item['generation_status'] == 'manifest-only', 'foundation contract mismatch')
            require(item['ownership'] == 'half-open [min,max), clipped at world boundary', 'ownership mismatch')
            require(item['local_xy_bbox_m'] == [c*step, r*step, (c+1)*step, (r+1)*step], 'gap or overlap')
        require(not expected, 'missing sector')
        return cls(8, step*1000, origin, halo_mm)

    @staticmethod
    def id(c, r):
        return f'S{c:02d}_{r:02d}'

    def sectors(self):
        return [(c, r) for r in range(self.side) for c in range(self.side)]

    def local(self, point):
        x, y = integer_pair(point)
        return x-self.origin_mm[0], y-self.origin_mm[1]

    def projected(self, point):
        x, y = integer_pair(point)
        return x+self.origin_mm[0], y+self.origin_mm[1]

    def owner(self, point):
        x, y = self.local(point)
        extent = self.side*self.step_mm
        require(0 <= x < extent and 0 <= y < extent, 'outside half-open world')
        return self.id(x//self.step_mm, y//self.step_mm)

    def bounds(self, c, r, halo=False):
        s = self.step_mm
        h = self.halo_mm if halo else 0
        extent = self.side*s
        return [max(0,c*s-h), max(0,r*s-h), min(extent,(c+1)*s+h), min(extent,(r+1)*s+h)]

    def neighbors(self, c, r):
        return {label:self.id(x,y) for label,x,y in [('W',c-1,r),('E',c+1,r),('S',c,r-1),('N',c,r+1)] if 0<=x<self.side and 0<=y<self.side}

    def seam(self, c, r, direction):
        require(direction in self.neighbors(c,r), 'not an internal seam')
        s=self.step_mm
        if direction in ('W','E'):
            return ('x', (c+(direction=='E'))*s, r*s, (r+1)*s)
        return ('y', (r+(direction=='N'))*s, c*s, (c+1)*s)


def normalize(grid, features):
    records = {}
    for f in features:
        require(type(f) is dict and set(f)=={'id','kind','points_mm','revision'}, 'invalid feature schema')
        fid=f['id']
        require(isinstance(fid,str) and re.fullmatch(r'[a-z0-9][a-z0-9:._-]{0,127}',fid) and fid not in records, 'duplicate or invalid source ID')
        require(f['kind'] in ('point','segment') and isinstance(f['points_mm'],list) and len(f['points_mm'])==(1 if f['kind']=='point' else 2), 'unsupported geometry')
        require(isinstance(f['revision'],str) and 0<len(f['revision'])<=128, 'invalid revision')
        points=[grid.local(p) for p in f['points_mm']]
        for p in f['points_mm']:
            grid.owner(p)  # Both segment endpoints must lie in world in this synthetic prototype.
        require(len(points)==1 or points[0]!=points[1], 'degenerate segment')
        # Segment ownership is deliberately not assigned: only point anchors are owned.
        owner=grid.owner(f['points_mm'][0]) if f['kind']=='point' else None
        records[fid]={'id':fid,'kind':f['kind'],'local_mm':points,'revision':f['revision'],'owner':owner}
    return records


def crossing(record, seam):
    if record['kind']!='segment':
        return None
    axis, fixed, lo, hi=seam
    a,b=record['local_mm']; i=0 if axis=='x' else 1; j=1-i
    if a[i]==b[i]:
        if a[i]==fixed and max(min(a[j],b[j]),lo)<min(max(a[j],b[j]),hi):
            return {'id':record['id'],'kind':'collinear-review'}
        return None
    t=Fraction(fixed-a[i],b[i]-a[i])
    v=a[j]+t*(b[j]-a[j])
    if 0<=t<=1 and lo<=v<hi:
        return {'id':record['id'],'kind':'crossing','along_mm':[v.numerator,v.denominator]}
    return None


def plan(grid, features, rule_hash):
    require(isinstance(rule_hash,str) and re.fullmatch(r'[0-9a-f]{64}',rule_hash), 'rule SHA256 required')
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    records=normalize(grid,features)
    ordered=[records[k] for k in sorted(records)]
    out={}
    for c,r in grid.sectors():
        name=grid.id(c,r); halo=grid.bounds(c,r,True); context=[]
        for record in ordered:
            xs,ys=zip(*record['local_mm']); box=[min(xs),min(ys),max(xs),max(ys)]
            if overlap(halo,box): context.append(record)
        seams={}
        for direction in grid.neighbors(c,r):
            edge=grid.seam(c,r,direction)
            events=[event for rec in context if (event:=crossing(rec,edge)) is not None]
            seams[direction]={'edge':edge,'events':events,'sha256':digest([edge,events]),'review_required':any(e['kind']=='collinear-review' for e in events)}
        owned=[rec['id'] for rec in context if rec['owner']==name]
        payload={'sector_id':name,'core_mm':grid.bounds(c,r),'halo_mm':halo,'neighbors':grid.neighbors(c,r),'owned_point_ids':owned,'context_ids':[rec['id'] for rec in context],'seams':seams,'production_crs':None,'generation_status':'synthetic-plan-only'}
        payload['identity']=digest([payload,context,rule_hash,generator_sha256,grid.origin_mm,grid.halo_mm])
        out[name]=payload
    return {'schema_version':1,'scope':'synthetic-only','snapshot_sha256':digest(ordered),'rule_sha256':rule_hash,'generator_sha256':generator_sha256,'sectors':out}


def dirty(previous, current):
    require(previous['scope']==current['scope']=='synthetic-only','scope mismatch')
    require(set(previous['sectors'])==set(current['sectors']),'different grid; full replan required')
    return sorted(k for k,v in current['sectors'].items() if v['identity']!=previous['sectors'][k]['identity'])


def validate_seams(snapshot):
    issues=[]; reverse={'W':'E','E':'W','S':'N','N':'S'}
    sectors=snapshot['sectors']
    expected={Grid.id(c,r) for r in range(8) for c in range(8)}
    if set(sectors)!=expected:
        return [('grid','','missing-or-extra-sector')]
    for r in range(8):
        for c in range(8):
            name=Grid.id(c,r); s=sectors[name]
            expected_neighbors={label:Grid.id(x,y) for label,x,y in [('W',c-1,r),('E',c+1,r),('S',c,r-1),('N',c,r+1)] if 0<=x<8 and 0<=y<8}
            if s['neighbors']!=expected_neighbors or set(s['seams'])!=set(expected_neighbors):
                issues.append((name,'','invalid-adjacency')); continue
            for direction,neighbor in expected_neighbors.items():
                peer=sectors[neighbor]; a=s['seams'][direction]; b=peer['seams'].get(reverse[direction])
                x0,y0,x1,y1=s['core_mm']
                edge={'W':('x',x0,y0,y1),'E':('x',x1,y0,y1),'S':('y',y0,x0,x1),'N':('y',y1,x0,x1)}[direction]
                if peer['neighbors'].get(reverse[direction])!=name or a!=b or tuple(a['edge'])!=edge or a['sha256']!=digest([a['edge'],a['events']]):
                    issues.append((name,direction,'mismatch'))
                if a['review_required'] or any(e['kind']=='collinear-review' for e in a['events']):
                    issues.append((name,direction,'collinear-review'))
    return issues
