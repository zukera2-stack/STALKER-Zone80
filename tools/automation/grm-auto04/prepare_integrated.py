"""Independent fixed-fixture export QC and local TB handoff. No height synthesis."""
from pathlib import Path
from decimal import Decimal as D
import hashlib,json,math,struct,csv,collections,shutil,zipfile,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent
A=R/"c"; B=R/"d"; T=R/"TBHandoff"
old=R.parent/"GRMAUTO01"/"TBHandoff"
prev=R.parent/"GRMAUTO03"
def need(b,msg):
    if not b: raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def files(p):return {f.relative_to(p).as_posix():sha(f) for f in p.rglob("*") if f.is_file()}
need(not T.exists() and not (R/"GRMAUTO04_TB_IMPORT.zip").exists(),"fresh output")
need(len(files(A))==11 and files(A)==files(B),"repeat")
m=load(A/"result.json")
need(m["inputCount"]==m["exported"]==4562 and m["held"]==0 and m["roads"]==2,"native export counts")
source=load(R/"retained"/"MANIFEST.json")
need(sha(R/"retained"/"MANIFEST.json")=="49cc261ed8fc5da6c17945886a4d0ffe53752b4264efeccf4b1cbb64123a2368","manifest")
rows={}
for s in ("SW","SE","NW","NE"):
    n=s+"_objects.json";p=R/"retained"/n
    need(sha(p)==source["files"][n],"retained hash")
    for o in load(p):need(o["id"] not in rows,"duplicate ID");rows[o["id"]]=o
need(len(rows)==4562 and not load(A/"canonical_holds.json"),"conservation")
ids=load(A/"placement_ids.json")
need(ids==sorted(rows),"ID coverage/order")
csvrows=list(csv.reader((A/"relative_objects.txt").read_text().splitlines(),delimiter=";"))
need(len(csvrows)==4562,"CSV count")
models={x.findtext("Name"):x.findtext("File") for x in ET.parse(A/"templates"/"arma3.tml").getroot().findall("Template")}
need(len(models)==3,"TML")
for v in models.values():
    need(v.startswith("a3\\vegetation_f_enoch\\tree\\t_betula_pendula_") and Path("P:/"+v).is_file(),"model dependency")
maxxy=[0,0];maxpose=0
for id,r in zip(ids,csvrows):
    o=rows[id];need(len(r)==9 and r[-1]=="" and r[0]==o["model"] and r[0] in models,"CSV identity")
    for j,k,shift in [(1,"x",200015),(2,"y",15)]:
        err=abs(float(r[j])-shift-o[k]);maxxy[j-1]=max(maxxy[j-1],err);need(err<=.00051,"coordinate precision")
    for j,k in [(3,"yaw"),(4,"pitch"),(5,"roll"),(6,"scale"),(7,"elevation")]:
        e=abs(float(r[j])-o[k]);maxpose=max(maxpose,e);need(e<=.001,"pose")
need(len({(r[1],r[2]) for r in csvrows})==4562,"duplicate anchors")
# Source native 2 full PolyLineZ records, merge is by native full frame rather than concatenation of clipped pieces.
src=(A/"roads.shp").read_bytes()
need(struct.unpack_from(">i",src,0)[0]==9994 and struct.unpack_from(">i",src,24)[0]*2==len(src) and struct.unpack_from("<i",src,32)[0]==13,"SHP")
o=100;geom=[];idx=[];road_source=[]
while o<len(src):
    rid,n=struct.unpack_from(">ii",src,o);typ,np,nv=struct.unpack_from("<i32xii",src,o+8)
    need(rid==len(geom)+1 and typ==13 and np==1 and nv>=2 and 48+16*nv+2*(16+8*nv)==n*2,"record")
    pts=[struct.unpack_from("<dd",src,o+8+48+16*i) for i in range(nv)]
    xspan=max(x for x,y in pts)-min(x for x,y in pts);yspan=max(y for x,y in pts)-min(y for x,y in pts)
    horiz=xspan>yspan
    need(all(abs((y if horiz else x-200000)-900)<=.05 for x,y in pts),"road line")
    z=[x-200000 if horiz else y for x,y in pts]
    need(abs(min(z)-400)<=.05 and abs(max(z)-1400)<=.05,"road extent")
    road_source.append({"record":rid,"synthetic_way":103 if horiz else 104,"vertices":nv})
    geom.append([(x+15,y+15) for x,y in pts]);idx.append((o//2,n));o+=8+2*n
need(o==len(src) and len(geom)==2 and {r["synthetic_way"] for r in road_source}=={103,104},"road counts")
ix=(A/"roads.shx").read_bytes();need(len(ix)==116 and [struct.unpack_from(">ii",ix,i) for i in (100,108)]==idx,"SHX")
dbf=(A/"roads.dbf").read_bytes();need(struct.unpack_from("<I",dbf,4)[0]==2,"DBF")
def bounds(ps):return min(x for x,y in ps),min(y for x,y in ps),max(x for x,y in ps),max(y for x,y in ps)
def header(n,bb):return struct.pack(">7i",9994,0,0,0,0,0,n//2)+struct.pack("<ii8d",1000,3,*bb,0,0,0,0)
records=[];idx=[];pos=100
for i,ps in enumerate(geom,1):
    rec=struct.pack("<i4diii",3,*bounds(ps),1,len(ps),0)+b"".join(struct.pack("<dd",*q) for q in ps)
    hh=struct.pack(">ii",i,len(rec)//2);records.append(hh+rec);idx.append(struct.pack(">ii",pos//2,len(rec)//2));pos+=len(hh)+len(rec)
bb=bounds([p for ps in geom for p in ps])
shp=header(pos,bb)+b"".join(records);shx=header(100+8*len(idx),bb)+b"".join(idx)
# Common canonical canvas used to derive each block view; compare all common pixels independently.
palette={"6b8e23","664a00","add8e6","000000"}
def bmp(p,w):
    b=p.read_bytes();off=struct.unpack_from("<I",b,10)[0]
    need(b[:2]==b"BM" and struct.unpack_from("<iiHHI",b,18)==(w,w,1,24,0),"BMP")
    stride=(w*3+3)//4*4
    return [b[off+j*stride:off+j*stride+w*3] for j in range(w)]
def pix(rows,i,j):return rows[j][i*3:i*3+3]
base=bmp(A/"mask.bmp",480);tb=bmp(A/"tb_mask.bmp",480)
def hist(rows):
    c=collections.Counter(row[i:i+3][::-1].hex() for row in rows for i in range(0,len(row),3))
    need(set(c)==palette,"palette")
    return dict(c)
h1,h2=hist(base),hist(tb)
need(sum(h1.values())==sum(h2.values())==230400 and sorted(h1.values())==sorted(m["mask_counts"]) and sorted(h2.values())==sorted(m["tb_mask_counts"]),"mask counts")
# Asymmetric control points in source and translated TB canvas; lake away from crossing road.
controls=[(502,502,"664a00"),(702,702,"664a00"),(862,1202,"add8e6"),(902,802,"000000"),(1402,1402,"6b8e23")]
for x,y,c in controls:
    need(pix(base,x//4,y//4)[::-1].hex()==c,"source mask control")
    need(pix(tb,(x+15)//4,(y+15)//4)[::-1].hex()==c,"TB mask control")
blocks={"SW":(180,180),"SE":(780,180),"NW":(180,780),"NE":(780,780)}
oldmask={s:bmp(prev/s/"a"/"mask.bmp",210) for s in blocks}
views={s:[row[ox//4*3:(ox//4+210)*3] for row in base[oy//4:oy//4+210]] for s,(ox,oy) in blocks.items()}
pairqc={}
for i,s in enumerate(sorted(blocks)):
    for t in sorted(blocks)[i+1:]:
        x,y=blocks[s];u,v=blocks[t];raw=0;fixed=0;n=0;trans=collections.Counter()
        for Y in range(max(y,v),min(y,v)+840,4):
            for X in range(max(x,u),min(x,u)+840,4):
                a=pix(oldmask[s],(X-x)//4,(Y-y)//4);b=pix(oldmask[t],(X-u)//4,(Y-v)//4)
                c=pix(views[s],(X-x)//4,(Y-y)//4);d=pix(views[t],(X-u)//4,(Y-v)//4)
                n+=1;raw+=a!=b;fixed+=c!=d
                if a!=b:trans[a[::-1].hex()+"->"+b[::-1].hex()]+=1
        need(fixed==0,"canonical overlap")
        pairqc[s+"-"+t]={"pixels":n,"previous_mismatches":raw,"canonical_mismatches":fixed,"previous_transitions":dict(trans)}
need(sum(v["previous_mismatches"] for v in pairqc.values())==19,"previous mismatch evidence")
# Exact original height values, existing verified GM-local terrain/imagery and world file.
need(sha(old/"MANIFEST.json")=="a219a1037a7a893a6fae323e440089d60acda2d17945e58d824a6fbbd1ea80dc","old handoff manifest")
oldm=load(old/"MANIFEST.json")
for n in ("terrain.asc","imagery.bmp","imagery.bpw","maplegend.png","layers.cfg"):need(sha(old/n)==oldm["files"][n],"prior input "+n)
local=(old/"terrain.asc").read_text().splitlines();orig=(R/"terrain.asc").read_text().splitlines()
need(len(local)==len(orig)==70 and all(list(map(D,a.split()))==list(map(D,b.split())) for a,b in zip(local[6:],orig[6:])),"GM exact heights")
hd={k.lower():D(v) for k,v in (l.split() for l in local[:6])}
need(hd["ncols"]==hd["nrows"]==64 and hd["cellsize"]==30 and hd["xllcorner"]==200000 and hd["yllcorner"]==0,"TB terrain grid")
need(struct.unpack_from("<iiHHI",(old/"imagery.bmp").read_bytes(),18)==(480,480,1,24,0),"imagery")
need([D(x) for x in (old/"imagery.bpw").read_text().split()]==[4,0,0,-4,200002,1918],"world file")
cfg=(old/"layers.cfg").read_text()
import re
for path in re.findall(r'(?:texture|material)="([^"]+)"',cfg):
    need(path.startswith("a3\\") and Path("P:/"+path).is_file(),"material dependency")
    if path.endswith("_co.paa"):need(Path("P:/"+path.replace("_co.paa","_nopx.paa")).is_file(),"normal dependency")
needle=str(old/"maplegend.png");need(cfg.count(needle)==1,"legend path")
cfg=cfg.replace(needle,str(T/"maplegend.png"))
# No mutation of old project or assets; export only our candidate.
T.mkdir()
sources={n:old/n for n in ("terrain.asc","imagery.bmp","imagery.bpw","maplegend.png")}
sources.update({"mask.bmp":A/"tb_mask.bmp","mask.bpw":old/"imagery.bpw","relative_objects.txt":A/"relative_objects.txt","arma3.tml":A/"templates"/"arma3.tml","roads.dbf":A/"roads.dbf","roadslib.cfg":A/"roadslib.cfg","placement_ids.json":A/"placement_ids.json"})
for n,p in sources.items():
    shutil.copyfile(p,T/n);need(sha(p)==sha(T/n),"copy")
(T/"roads.shp").write_bytes(shp);(T/"roads.shx").write_bytes(shx);(T/"layers.cfg").write_text(cfg,encoding="ascii")
# Independent planar readback, verify all vertex coordinates and DBF record order.
b=(T/"roads.shp").read_bytes();o=100
for k,pts in enumerate(geom,1):
    rid,n=struct.unpack_from(">ii",b,o);typ,np,nv=struct.unpack_from("<i32xii",b,o+8)
    need(rid==k and typ==3 and np==1 and nv==len(pts) and 48+16*nv==n*2,"planar record")
    need([struct.unpack_from("<dd",b,o+8+48+16*i) for i in range(nv)]==pts,"planar XY");o+=8+2*n
need(o==len(b) and (T/"roads.shx").read_bytes()==shx and (T/"roads.dbf").read_bytes()==dbf,"road readback")
report={"scope":"SYNTHETIC_TB_IMPORT_CANDIDATE","native_repeat_files":11,"objects":4562,"object_xy_max_error_m":maxxy,"pose_max_rounding":maxpose,"canonical_additional_holds":0,"max_native_height_delta_m":m["max_height_delta_m"],"roads":road_source,"road_format":"planar PolyLine from full-frame native PolyLineZ; Z/M intentionally omitted, DBF unchanged; synthetic distinct way IDs, no junction topology proof","mask_overlap":pairqc,"source_mask_histogram":h1,"tb_mask_histogram":h2,"terrain":{"size_m":1920,"grid":64,"step_m":30,"height_count":4096,"pixel_m":4,"image_px":480,"tb_corner":[200000,0],"grm_to_tb_xy_delta_m":[15,15]},"native_tb_import":"NOT_RUN","full_native_IdMapRender":"NOT_RUN","actual_P3D_collision":"NOT_RUN","files":files(T)}
(T/"MANIFEST.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
zpath=R/"GRMAUTO04_TB_IMPORT.zip"
with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(T.iterdir()):z.write(f,f.name)
with zipfile.ZipFile(zpath) as z:need(set(z.namelist())=={f.name for f in T.iterdir()} and all(hashlib.sha256(z.read(n)).hexdigest()==sha(T/n) for n in z.namelist()),"ZIP")
print(json.dumps({k:v for k,v in report.items() if k!="files"},indent=2))
print("ZIP_SHA256="+sha(zpath)+" BYTES="+str(zpath.stat().st_size)+" FILES="+str(len(list(T.iterdir()))))
