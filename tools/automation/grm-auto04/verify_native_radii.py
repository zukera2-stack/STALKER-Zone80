"""Diagnostic only: native TML bounds against retained exported placements, not P3D collisions."""
from pathlib import Path
import json, csv, hashlib, math, collections, xml.etree.ElementTree as ET, struct
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,msg):
    if not x:raise ValueError(msg)
manifest=json.loads((R/'native_archive_manifest.json').read_text())
need(sha(R/'GRMAUTO04_NATIVE_INTEGRATION.zip')==manifest['archive_sha256'],'archive')
files=list((R/'Native').rglob('arma3.tml'));need(len(files)==1,'native TML')
p=files[0];need(sha(p)==manifest['files'][p.relative_to(R).as_posix()],'TML hash')
models={}
for t in ET.parse(p).getroot().findall('Template'):
    lo=[float(t.find('BoundingMin').attrib[k]) for k in 'XYZ'];hi=[float(t.find('BoundingMax').attrib[k]) for k in 'XYZ']
    radius=float(t.findtext('BBRadius'));need(radius>0 and all(a<b for a,b in zip(lo,hi)),'bounds')
    models[t.findtext('Name')]={'radius':radius,'bbox_min':lo,'bbox_max':hi,'bbox_extent':[b-a for a,b in zip(lo,hi)],'height_field':float(t.findtext('Height'))}
need(len(models)==3,'models')
src=R/'TBHandoff';m=json.loads((src/'MANIFEST.json').read_text())
for n in ('relative_objects.txt','placement_ids.json','roads.shp','roads.shx','roads.dbf'):need(sha(src/n)==m['files'][n],'source '+n)
ids=json.loads((src/'placement_ids.json').read_text());data={}
for f in (R/'retained').glob('*_objects.json'):
    for v in json.loads(f.read_text()):need(v['id'] not in data,'id');data[v['id']]=v
rows=[]
for id,r in zip(ids,csv.reader((src/'relative_objects.txt').read_text().splitlines(),delimiter=';'),strict=True):
    o=data[id];need(r[0]==o['model'] and len(r)==9 and r[-1]=='','identity')
    x,y=float(r[1])-200000,float(r[2]);s=float(r[6]);need(abs(x-o['x']-15)<.00051 and abs(y-o['y']-15)<.00051 and s>0,'pose')
    rows.append((id,r[0],x,y,s,o['block'],o['owner']))
need(len(rows)==4562 and len(set(ids))==4562,'count')
# Native BBRadius is recorded as-is, not assumed exact footprint. Circles centered on exported anchors.
# All pair distances computed once; separate diagnostic comparison to earlier tiny profile proxies.
proxy={'t_betula_pendula_2f':.7,'t_betula_pendula_3f':1.0,'t_betula_pendula_3s':2.0}
pairs=collections.Counter();model_pairs=collections.Counter();involved=set();min_dist=float('inf');nearest=[float('inf')]*len(rows);road_hits=[];samples=[];proxy_involved=set()
for i,a in enumerate(rows):
    for j in range(i+1,len(rows)):
        b=rows[j];d=math.hypot(a[2]-b[2],a[3]-b[3]);min_dist=min(min_dist,d);nearest[i]=min(nearest[i],d);nearest[j]=min(nearest[j],d)
        crossblock=a[5]!=b[5];crosssector=a[6]!=b[6]
        if d<proxy[a[1]]*a[4]+proxy[b[1]]*b[4]:
            pairs['small_proxy']+=1;proxy_involved.update((i,j))
            if crossblock or crosssector:pairs['small_proxy_cross_boundary']+=1
        if d<models[a[1]]['radius']*a[4]+models[b[1]]['radius']*b[4]:
            pairs['native_radius']+=1;involved.update((i,j))
            if crossblock:pairs['native_radius_cross_block']+=1
            if crosssector:pairs['native_radius_cross_storage']+=1
            if crossblock or crosssector:pairs['native_radius_cross_either']+=1
            model_pairs[' + '.join(sorted((a[1],b[1])))]+=1
            if len(samples)<20:samples.append({'ids':[a[0],b[0]],'distance':d})
# road centerlines from exact TB handoff planar SHP.
b=(src/'roads.shp').read_bytes();need(struct.unpack_from('<i',b,32)[0]==3,'SHP')
pos=100;roads=[]
while pos<len(b):
    rid,n=struct.unpack_from('>ii',b,pos);typ,np,nv=struct.unpack_from('<i32xii',b,pos+8);need(typ==3 and np==1 and nv>=2 and n*2==48+nv*16,'road')
    roads.append([(x-200000,y) for x,y in (struct.unpack_from('<dd',b,pos+56+16*i) for i in range(nv))]);pos+=8+2*n
need(pos==len(b) and len(roads)==2 and sum(map(len,roads))==20,'road count')
def segdist(x,y,a,b):
    vx=b[0]-a[0];vy=b[1]-a[1];q=vx*vx+vy*vy
    t=max(0,min(1,((x-a[0])*vx+(y-a[1])*vy)/q)) if q else 0
    return math.hypot(x-a[0]-t*vx,y-a[1]-t*vy)
min_road=float('inf')
for a in rows:
    d=min(segdist(a[2],a[3],u,v) for line in roads for u,v in zip(line,line[1:]));min_road=min(min_road,d)
    if d<models[a[1]]['radius']*a[4]:road_hits.append({'id':a[0],'model':a[1],'centerline_distance_m':d,'radius_m':models[a[1]]['radius']*a[4]})
nearest.sort()
out={'scope':'synthetic diagnostic only; circles based on saved native TML BBRadius around exported anchors; NOT geometry collision, native pose readback, or road surface collision','native_tml_sha256':sha(p),'count':len(rows),'models':models,'model_counts':dict(collections.Counter(a[1] for a in rows)),'pair_tests':len(rows)*(len(rows)-1)//2,'pair_counts':dict(pairs),'involved_in_native_radius_overlap':len(involved),'involved_in_small_proxy_overlap':len(proxy_involved),'native_radius_model_pairs':dict(model_pairs),'min_anchor_distance_m':min_dist,'median_nearest_anchor_distance_m':(nearest[2280]+nearest[2281])/2,'minimum_centerline_distance_m':min_road,'native_radius_reaches_centerline_count':len(road_hits),'road_hits':road_hits,'samples':samples,'actual_geometry_collision':'NOT_RUN','native_pose_export':'NOT_RUN'}
p=R/'spatial_radius_qc.json';need(not p.exists(),'fresh output');p.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ('road_hits','samples')},indent=2));print('REPORT_SHA='+sha(p))
