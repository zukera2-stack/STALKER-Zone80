from pathlib import Path
import csv, hashlib, json, math, os, struct
R=Path(r"D:\Zone80\PipelineV01_02\TBChange01")
C=Path(r"D:\Zone80\TBGEN0002")
S=Path(r"D:\Zone80\TBGEN0001")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:
        return [r for r in csv.reader(f,delimiter=";") if r]
src=C/"TBHandoff/relative_objects.txt"
assert sha(src)=="e3f9c2bca1b360ab4fbff809f682a1afef996cb19a5c514d860f8ee0a491b56e"
base=rows(src);assert len(base)==4562
xy=[(float(r[1]),float(r[2])) for r in base]
# Diagnostic location: choose clearance from existing anchors and both source road polylines.
b=(C/"TBHandoff/roads.shp").read_bytes()
off=100;segments=[]
while off<len(b):
    _,words=struct.unpack_from(">2i",b,off);q=b[off+8:off+8+2*words];off+=8+2*words
    typ=struct.unpack_from("<i",q)[0];assert typ==3
    np,nv=struct.unpack_from("<2i",q,36)
    parts=list(struct.unpack_from("<"+"i"*np,q,44))+[nv]
    pts=[struct.unpack_from("<2d",q,44+4*np+16*i) for i in range(nv)]
    for a,z in zip(parts,parts[1:]):segments+=list(zip(pts[a:z],pts[a+1:z]))
assert len(segments)>0
def dist(x,y,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
chosen=None
for y in range(240,1681,120):
    for x in range(200240,201681,120):
        clear=min(math.hypot(x-a,y-b) for a,b in xy)
        road=min(dist(x,y,a,b) for a,b in segments)
        if clear>=30 and road>=30:
            chosen=(x,y,clear,road);break
    if chosen:break
assert chosen
x,y,clear,road=chosen
out=C/"TBHandoff"/"autonomy_probe_01.txt"
with out.open("x",encoding="ascii",newline="\n") as f:f.write(f'"t_betula_pendula_2f";{x:.3f};{y:.3f};17.000;0.000;0.000;1.000;0.000;\n')
r={"scope":"synthetic_additive_probe","base_sha256":sha(src),"input_sha256":sha(out),"base_objects":4562,"expected_objects":4563,"probe":[ "t_betula_pendula_2f",x,y,17,0,0,1,0],"anchor_clearance_m":clear,"road_centerline_clearance_m":road,"project_sha256":sha(C/"Native/source/TerrainBuilder/GRMAUTO04.tv4p"),"last_good_sha256":sha(S/"Native/source/TerrainBuilder/GRMAUTO04.tv4p")}
with (R/"change_plan.json").open("x",encoding="ascii") as f:json.dump(r,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps(r))
