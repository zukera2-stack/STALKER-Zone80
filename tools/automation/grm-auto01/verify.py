"""Independent QC for bounded native GRM runs. No source modification."""
import collections, csv, hashlib, json, math, pathlib, struct, xml.etree.ElementTree as ET
from decimal import Decimal
R=pathlib.Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def need(x,msg):
    if not x: raise ValueError(msg)
A=R/"run1"; B=R/"run2"
files={str(p.relative_to(A)).replace("\\","/"):sha(p) for p in A.rglob("*") if p.is_file()}
need(len(files)==10 and files=={str(p.relative_to(B)).replace("\\","/"):sha(p) for p in B.rglob("*") if p.is_file()},"repeat mismatch")
m=json.loads((A/"result.json").read_text())
p=json.loads((A/"synthetic.grma3a").read_text())
palette={bytes.fromhex(x["Material"]["Id"])[:3]:x["Usages"] for x in p["Materials"]["Definitions"]}
need(len(palette)==4,"palette")
# Read native CSV and exact TML identities, no GRM code.
tml=ET.parse(A/"templates"/"arma3.tml").getroot()
models={x.findtext("Name"):x.findtext("File") for x in tml.findall("Template")}
need(len(models)==3 and all(v.startswith("a3\\vegetation_f_enoch\\tree\\t_betula_pendula_") for v in models.values()),"model identity")
rows=list(csv.reader((A/"relative_objects.txt").read_text().splitlines(),delimiter=";"))
need(len(rows)==2103 and all(len(r)==9 and r[-1]=="" and r[0] in models for r in rows),"CSV identity/count")
coords=[]; counts=collections.Counter()
for r in rows:
    a=list(map(float,r[1:8])); need(all(math.isfinite(v) for v in a),"nonfinite placement")
    x,y=a[0]-200000,a[1]
    need(99.98<=x<=420.02 and 119.98<=y<=460.02 and abs(y-290)>=3.49 and a[5]>0,"forest/road bounds")
    coords.append((round(x,3),round(y,3)));counts[r[0]]+=1
need(len(set(coords))==len(coords),"duplicate XY")
# Native SHP and SHX: both big-endian record headers and little-endian geometry.
def read_shape(path):
    b=path.read_bytes();need(len(b)>=100 and struct.unpack_from(">i",b,0)[0]==9994 and struct.unpack_from(">i",b,24)[0]*2==len(b),"shp header")
    need(struct.unpack_from("<i",b,32)[0]==13,"not PolyLineZ")
    off=100; rr=[]
    while off<len(b):
        rid,n=struct.unpack_from(">ii",b,off);end=off+8+2*n
        need(rid==len(rr)+1 and end<=len(b),"record framing")
        typ,np,nv=struct.unpack_from("<i32xii",b,off+8)
        need(typ==13 and np==1 and nv>=2 and 44+np*4+nv*16+2*(16+nv*8)==2*n,"PolyLineZ record")
        pts=[struct.unpack_from("<dd",b,off+8+44+np*4+16*i) for i in range(nv)]
        need(all(math.isfinite(x) and math.isfinite(y) and 200000<=x<201920 and 0<=y<1920 for x,y in pts),"road bounds")
        rr.append((off//2,n,pts));off=end
    need(off==len(b),"trailing shape data");return rr
rr=read_shape(A/"roads.shp")
need(len(rr)==2,"road count")
ix=(A/"roads.shx").read_bytes()
need(len(ix)==116 and [struct.unpack_from(">ii",ix,i) for i in (100,108)]==[(x[0],x[1]) for x in rr],"SHX mismatch")
expected=[[(200050,290),(200480,290)],[(201000,620),(201510,960)]]
for target in expected:
    need(any(all(math.dist(a,b)<0.2 for a,b in zip([r[2][0],r[2][-1]],q)) for r in rr for q in (target,target[::-1])),"road endpoint")
dbf=(A/"roads.dbf").read_bytes();need(struct.unpack_from("<I",dbf,4)[0]==2,"DBF count")
# 24-bit BMP, north-up from bottom-up DIB.
b=(A/"mask.bmp").read_bytes();off=struct.unpack_from("<I",b,10)[0]
w,h,planes,bpp,comp=struct.unpack_from("<iiHHI",b,18)
need(b[:2]==b"BM" and (w,h,planes,bpp,comp)==(480,480,1,24,0),"BMP format")
stride=((w*3+3)//4)*4
def rgb(x,y):
    i=off+(h-1-y)*stride+x*3;return b[i:i+3][::-1]
hist=collections.Counter(rgb(x,y) for y in range(h) for x in range(w))
need(set(hist)==set(palette) and sum(hist.values())==230400 and sorted(hist.values())==sorted(m["mask_counts"]),"mask palette/count")
need(rgb(50,430)==bytes.fromhex("664A00") and rgb(200,230)==bytes.fromhex("ADD8E6") and rgb(460,20)==bytes.fromhex("6B8E23"),"mask controls")
# Source ASC remains byte-for-byte unchanged; no vertical-datum assertion.
lines=(R/"terrain.asc").read_text().splitlines()
need(sha(R/"terrain.asc")==m["source_asc"] and len(lines)==70,"source ASC")
vals=[list(map(float,x.split())) for x in lines[6:]]
need(len(vals)==64 and all(len(row)==64 and all(math.isfinite(v) and v!=-9999 for v in row) for row in vals),"heights")
need([vals[0][0],vals[0][63],vals[31][31],vals[63][0],vals[63][63]]==[90,101.8125,108,113.625,125.9375],"height controls")
report={"scope":"synthetic_review_only","repeat_files":len(files),"files":files,"object_count":len(rows),"unique_xy":len(set(coords)),"per_model":dict(counts),"xy_range_grm":[min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords)],"road_count":len(rr),"road_vertex_counts":[len(r[2]) for r in rr],"road_endpoints":[[r[2][0],r[2][-1]] for r in rr],"mask_counts":{k.hex():v for k,v in hist.items()},"height_controls":[90,101.8125,108,113.625,125.9375],"height_count":4096,"nodata":0,"tb_alignment":"GRM node origin +15m east/north relative to source TB corner; full original footprint mask and TB transfer not yet verified"}
out=R/"independent_qc.json"
need(not out.exists(),"QC already exists")
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
print("INDEPENDENT_QC_PASS")
