"""CC05R: deterministic sector review queue, one fixed native fixture, Linux only."""
import fcntl
import json
from decimal import Decimal
import os
from pathlib import Path
import sys
import uuid

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE/'cc03'))
import sector_manager as sm
sys.path.insert(0, str(BASE/'cc05q'))
import native_worker as nw
import preflight as p

b = nw.b
ACTIVE = ('S00_00', 'S01_00')
MARKER = {'scope':'CC05R review only','version':1}


def init(root):
    b.require(root==root.resolve() and not root.exists() and root.name.startswith('zone80-review-'), 'new isolated review root required')
    root.mkdir(mode=0o700)
    b.atomic(root/'marker.json',MARKER)
    (root/'cache').mkdir(mode=0o700)
    nw.init(root/'zone80-native-child')


def owner(grid, x, y):
    # Synthetic translation, not a CRS: 240m fixture seam maps to sector boundary.
    b.require(grid.step_mm>=480000 and x.is_finite() and y.is_finite() and 0<=x<480 and 0<=y<480,'outside fixture')
    lx=Decimal(grid.step_mm-240000)+1000*x
    ly=Decimal(grid.step_mm//2-240000)+1000*y
    for c in (0,1):
        x0,y0,x1,y1=grid.bounds(c,0)
        if x0<=lx<x1 and y0<=ly<y1:return grid.id(c,0)
    raise b.Blocked('no owner')


def partition(grid,result):
    groups={k:[] for k in ACTIVE}; held=[]; ids=set()
    for row in result['records']:
        b.require(row['id'] not in ids,'duplicate native ID');ids.add(row['id'])
        if row['reason']:
            b.require(row['sector']=='held','invalid held record');held.append(row);continue
        x,y=map(Decimal,row['key'].split(';')[2:4]);name=owner(grid,x,y)
        b.require(name==ACTIVE[0 if row['sector']=='left' else 1] and row['sector'] in ('left','right'),'native ownership mismatch')
        groups[name].append(row)
    b.require(len(ids)==result['total'] and [len(groups[k]) for k in ACTIVE]+[len(held)]==[result[k] for k in ('left','right','held')],'native reconciliation')
    return groups,held


def lock(path):
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BaseException:os.close(fd);raise
    return fd


def run(root,snapshot,envelope,grid,features,rule_hash,recover=False):
    b.require(root==root.resolve() and root.name.startswith('zone80-review-') and b.load(b.safe(root,'marker.json'))==MARKER,'invalid root')
    b.require(not snapshot.is_relative_to(root) and not root.is_relative_to(snapshot),'overlapping snapshot')
    fd=lock(b.safe(root,'review.lock'))
    try:
        native=b.safe(root,'zone80-native-child');stop=b.safe(native,'stop.request')
        b.require(not stop.exists(),'stop requested')
        plan=sm.plan(grid,features,rule_hash)
        b.require(not sm.validate_seams(plan),'sector seam review required')
        expected=nw.prepare(snapshot,envelope)
        rc=nw.run(native,snapshot,envelope,recover)
        b.require(rc==0,'native dependency not PASS')
        childfd=lock(b.safe(native,'runner.lock'))
        try:
            matches=[]
            for attempt in sorted(native.glob('attempt-*')):
                b.require(not attempt.is_symlink(),'unsafe attempt')
                rec=b.load(b.safe(attempt,'status.json'))
                if rec.get('status')=='PASS' and rec.get('identity')==expected['identity'] and nw.reusable(attempt,rec,expected):matches.append(attempt)
            b.require(matches,'no validated dependency')
            reviews=[b.load(b.safe(a,'review.json')) for a in matches]
            b.require(all(v==reviews[0] for v in reviews),'conflicting native results')
            result=reviews[0]['result'];groups,held=partition(grid,result)
            native_id=sm.digest(reviews[0]);code=p.sha(Path(__file__).resolve())
            cache=b.safe(root,'cache');nodes={};built=[];reused=[]
            # Full source geometry stays in the native result. CC03 features are
            # separate review metadata only, never fed to the closed CC05P job.
            for name,sector in sorted(plan['sectors'].items()):
                b.require(not stop.exists(),'stop during review queue')
                covered=name in ACTIVE
                payload={'scope':'synthetic_review_only','sector':name,'sector_identity':sector['identity'],'code_sha256':code,'coverage':'partial_fixture_only' if covered else 'NOT_COVERED','native_dependency':native_id if covered else None,'records':groups.get(name,[]),'export_authorized':False}
                key=sm.digest(payload);path=b.safe(cache,key+'.json')
                if path.exists():
                    b.require(b.load(path)==payload,'tampered sector cache; no overwrite');reused.append(name)
                else:b.atomic(path,payload);built.append(name)
                nodes[name]=key
            b.require(not stop.exists(),'stop before publication')
            b.require(nw.prepare(snapshot,envelope)['identity']==expected['identity'],'dependency changed')
            manifest={'scope':'synthetic_review_only','plan_sha256':sm.digest(plan),'native_dependency':native_id,'native_job_identity':expected['identity'],'held':held,'nodes':nodes,'shared_edges':sum(len(v['neighbors']) for v in plan['sectors'].values())//2,'export_authorized':False}
            revision=sm.digest(manifest);revision_path=b.safe(root,'revision-'+revision+'.json')
            if revision_path.exists():b.require(b.load(revision_path)==manifest,'tampered revision')
            else:b.atomic(revision_path,manifest)
            b.require(not stop.exists(),'stop before pointer publication')
            b.atomic(b.safe(root,'current.json'),{'revision':revision,'scope':'synthetic_review_only'})
            return {'revision':revision,'built':built,'reused':reused,'native_counts':[len(groups[k]) for k in ACTIVE]+[len(held)],'nodes':nodes,'shared_edges':manifest['shared_edges']}
        finally:os.close(childfd)
    finally:os.close(fd)
