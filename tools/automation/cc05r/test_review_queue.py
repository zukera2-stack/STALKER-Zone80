"""Actual CC05P/CC05Q integration acceptance; no production inputs."""
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import tempfile

import review_queue as q


def need(ok,label):
    if not ok:raise AssertionError(label)


def main():
    src,envfile=map(lambda v:Path(v).resolve(),sys.argv[1:]);base=q.p.parse(envfile.read_bytes())
    base=dict(base,expires_utc=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),approval='Issue 42 owner continuation CC05R synthetic only')
    items=[dict(schema_version=1,sector_id=q.sm.Grid.id(c,r),column=c,row=r,local_xy_bbox_m=[c*10240,r*10240,(c+1)*10240,(r+1)*10240],ownership='half-open [min,max), clipped at world boundary',production_crs=None,generation_status='manifest-only') for r in range(8) for c in range(8)]
    grid=q.sm.Grid.from_foundation(items,(0,0),100000);s=grid.step_mm;rules=q.sm.digest('review-rules-v1')
    def feature(name,points,rev='1'):return dict(id=name,kind='point' if len(points)==1 else 'segment',points_mm=points,revision=rev)
    f=[feature('interior',[(s//2,s//2)]),feature('cross',[(s-101,s//2),(s+102,s//2+1)])]
    need(q.owner(grid,Decimal('239.999999'),Decimal(240))=='S00_00' and q.owner(grid,Decimal(240),Decimal(240))=='S01_00','half-open boundary')
    with tempfile.TemporaryDirectory(prefix='cc05r-') as td:
        t=Path(td);snap=t/'snapshot';shutil.copytree(src,snap);root=t/'zone80-review-test';q.init(root);native=root/'zone80-native-child'
        def attempts():return len(list(native.glob('attempt-*')))
        def run(features=f,env=base,rule=rules):return q.run(root,snap,env,grid,features,rule)
        def blocked(call):
            before=(root/'current.json').read_bytes()
            try:call()
            except (ValueError,q.b.Blocked,OSError):pass
            else:raise AssertionError('expected refusal')
            need((root/'current.json').read_bytes()==before,'previous pointer changed')
        a=run();need(len(a['built'])==64 and a['shared_edges']==112 and a['native_counts']==[917,77,21] and attempts()==1,'baseline')
        print('PASS baseline 64 nodes 112 edges 917/77/21 native records',flush=True)
        b=run(list(reversed(f)));need(b['revision']==a['revision'] and len(b['reused'])==64 and attempts()==1,'repeat')
        print('PASS deterministic repeat, 64 reused, no new native child',flush=True)
        changed=[dict(f[0],revision='2'),f[1]];c=run(changed);need(c['built']==['S00_00'] and len(c['reused'])==63 and attempts()==1,'interior')
        print('PASS interior review edit: one rebuilt, 63 reused, no native launch',flush=True)
        seam=[changed[0],dict(f[1],revision='2')];d=run(seam);need(d['built']==list(q.ACTIVE) and attempts()==1,'seam edit')
        print('PASS cross-border metadata edit: two rebuilt, 62 reused',flush=True)
        e=run(seam,rule=q.sm.digest('review-rules-v2'));need(len(e['built'])==64 and attempts()==1,'rule change')
        print('PASS global review rule change: 64 rebuilt, native unchanged',flush=True)
        job=snap/'inputs/job.json';old=job.read_bytes();j=q.p.parse(old);j['road_state']='operational';job.write_text(json.dumps(j));new=dict(base,files=dict(base['files'],**{'inputs/job.json':q.p.sha(job)}))
        g=run(seam,new,q.sm.digest('review-rules-v2'));need(g['built']==list(q.ACTIVE) and sum(g['native_counts'])==1062 and attempts()==2,'native invalidation')
        print('PASS native changed input: actual 1062 records, two dependent nodes rebuilt',flush=True)
        job.write_bytes(old);blocked(lambda:run(seam,new));need(attempts()==2,'invalid input launched')
        print('PASS invalid native dependency blocks publication',flush=True)
        expired=dict(base,expires_utc=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=1)).isoformat());blocked(lambda:run(seam,expired));need(attempts()==2,'expired')
        print('PASS expired dependency blocks publication',flush=True)
        stop=native/'stop.request';stop.touch();blocked(lambda:run(seam));stop.unlink();need(attempts()==2,'stop')
        print('PASS stop and explicit resume preserve previous evidence',flush=True)
        h=run(seam);need(h['revision']==d['revision'] and not h['built'] and attempts()==2,'resume')
        target=root/'cache'/(h['nodes']['S00_00']+'.json');saved=target.read_bytes();target.write_text('{}');blocked(lambda:run(seam));need(target.read_text()=='{}','tamper overwritten');target.write_bytes(saved)
        print('PASS corrupted cache rejected, old evidence not overwritten',flush=True)
        fd=q.lock(root/'review.lock')
        try:blocked(lambda:run(seam))
        finally:q.os.close(fd)
        print('PASS concurrent review lock refused',flush=True)
        bad=[feature('along',[(s,1),(s,s-1)])];blocked(lambda:run(bad));need(attempts()==2,'seam review')
        print('PASS unresolved collinear seam blocks publication',flush=True)
        print('PASS bounded CC05R; two actual native starts, 64 logical nodes only',flush=True)

if __name__=='__main__':main()
