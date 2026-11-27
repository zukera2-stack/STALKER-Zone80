"""Review-only deterministic global anchor-spacing filter; original TB remains unchanged."""
from pathlib import Path
import collections,csv,hashlib,json,math,zipfile
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,msg):
    if not x:raise ValueError(msg)
src=R/'TBHandoff';m=json.loads((src/'MANIFEST.json').read_text())
for n in ('relative_objects.txt','placement_ids.json'):need(sha(src/n)==m['files'][n],'source hash')
qc=R/'spatial_radius_qc.json';need(sha(qc)=='edccd7271f10902a783098173988ec7df9782d257c174511d6438efa5196aa26','QC hash')
ids=json.loads((src/'placement_ids.json').read_text())
lines=(src/'relative_objects.txt').read_text().splitlines()
radius={'t_betula_pendula_2f':.7,'t_betula_pendula_3f':1.0,'t_betula_pendula_3s':2.0}
rows=[]
for i,line in zip(ids,lines,strict=True):
    r=next(csv.reader([line],delimiter=';'));x,y=float(r[1])-200000,float(r[2]);rad=radius[r[0]]*float(r[6]);need(0<rad<=2,'radius')
    rows.append((i,x,y,rad,r[0],line))
need(len(rows)==len(set(ids))==4562,'count')
def bucket(o):return math.floor(o[1]/4),math.floor(o[2]/4)
def neighbors(o,grid):
    x,y=bucket(o)
    for i in range(x-1,x+2):
        for j in range(y-1,y+2):yield from grid.get((i,j),())
def conflict(a,b):return math.hypot(a[1]-b[1],a[2]-b[2])<a[3]+b[3]
def run(rows):
    grid=collections.defaultdict(list);good=[];held=[]
    for o in sorted(rows,key=lambda a:a[0]):
        conflicts=[q[0] for q in neighbors(o,grid) if conflict(o,q)]
        if conflicts:held.append({'id':o[0],'model':o[4],'conflicts_with':sorted(conflicts),'reason':'existing_small_anchor_radius_proxy'})
        else:good.append(o);grid[bucket(o)].append(o)
    return good,held
good,held=run(rows);need(run(list(reversed(rows)))==(good,held),'order')
grid=collections.defaultdict(list);raw=0;distance_bins=collections.Counter()
for o in rows:
    for q in neighbors(o,grid):
        d=math.hypot(o[1]-q[1],o[2]-q[2])
        for lim in (.1,.25,.5,1,2):
            if d<lim:distance_bins[str(lim)]+=1
        raw+=conflict(o,q)
    grid[bucket(o)].append(o)
need(raw==562,'baseline proxy count')
grid=collections.defaultdict(list)
for o in good:
    need(not any(conflict(o,q) for q in neighbors(o,grid)),'remaining proxy conflict')
    grid[bucket(o)].append(o)
need(len(good)+len(held)==4562 and {o[0] for o in good}|{h['id'] for h in held}==set(ids),'conservation')
dest=R/'SpacingReview';z=R/'SPACING_REVIEW.zip';need(not dest.exists() and not z.exists(),'fresh')
dest.mkdir()
(dest/'relative_objects_candidate.txt').write_text('\n'.join(o[5] for o in good)+'\n',encoding='ascii')
(dest/'placement_ids.json').write_text(json.dumps([o[0] for o in good]),encoding='ascii')
(dest/'held.json').write_text(json.dumps(held,indent=2),encoding='ascii')
need((dest/'relative_objects_candidate.txt').read_text().splitlines()==[o[5] for o in good],'readback')
report={'scope':'synthetic review only; existing small radii are unverified proxies, not actual trunk collision; no native import','input_count':len(rows),'original_conflict_pairs':raw,'retained':len(good),'held':len(held),'remaining_proxy_conflicts':0,'raw_distance_bins_cumulative_m':dict(distance_bins),'model_retained':dict(collections.Counter(o[4] for o in good)),'model_held':dict(collections.Counter(o['model'] for o in held)),'reverse_order_identical':True,'files':{p.name:sha(p) for p in dest.iterdir()}}
(dest/'MANIFEST.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(z,'x',compression=zipfile.ZIP_DEFLATED) as a:
    for p in sorted(dest.iterdir()):a.write(p,p.name)
with zipfile.ZipFile(z) as a:need(set(a.namelist())=={p.name for p in dest.iterdir()} and all(hashlib.sha256(a.read(n)).hexdigest()==sha(dest/n) for n in a.namelist()),'ZIP')
print(json.dumps(report,indent=2));print('ZIP_SHA='+sha(z)+' BYTES='+str(z.stat().st_size))
