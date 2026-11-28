"""Build the separate synthetic TB handoff from reviewed native GRM outputs.
No height generation, no raster resampling, no modifications to prior MAP005."""
import pathlib, hashlib, json, shutil, struct, csv, math, collections, zipfile, re
from decimal import Decimal
R=pathlib.Path(__file__).resolve().parent
A=R/"run1"; C=R/"run3"; T=R/"TBHandoff"
old=R.parent/"MAP005"/"source"/"Import"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(b,msg):
    if not b: raise ValueError(msg)
def pinned(p,h):
    need(p.is_file() and sha(p)==h.lower(),"input digest "+p.name);return p
need(not T.exists() and not (R/"GRMAUTO01_TB_IMPORT.zip").exists(),"output exists")
qc=json.loads((R/"independent_qc.json").read_text())
need(qc["object_count"]==qc["unique_xy"]==2103,"QC")
for n,h in qc["files"].items():pinned(C/n,h)
items={
 "terrain.asc":pinned(old/"terrain.asc","DEE095C5BB89AB09C4F596B7AEC79ACF2B13BDDAA2CF4AE95E828F2E786674AC"),
 "imagery.bmp":pinned(old/"imagery.bmp","8E5F6C9E2A5B4F0DF697490F8AE1EE532BE47DE110B75413EAFD46019B27AB0E"),
 "imagery.bpw":pinned(old/"imagery.bpw","313B51EE5C1784C7EC4B3A478405BD7F82732E4F9139B864F0063D1F11E0B82D"),
 "mask.bpw":old/"imagery.bpw",
 "maplegend.png":pinned(old/"maplegend.png","5981632A0BE6ACADC912D395A500C907A9A102AC8EC9987AF8BC29D911642CC3"),
 "mask.bmp":pinned(C/"tb_mask.bmp","55EF82A4520A256A6CE0722A89D9C8DAFCDA49A52A6B204913D65B09EF1002E8"),
 "relative_objects.txt":pinned(C/"tb_relative_objects.txt","C805E052734D14DF6D71A0CEDF5540DD0076D9EB320C0C1E908FEECFAECE4272"),
 "arma3.tml":C/"templates"/"arma3.tml",
 "roads.dbf":C/"roads.dbf",
 "roadslib.cfg":C/"roadslib.cfg",
}
# Validate the sole translation of the serialized objects; preserve all non-position fields.
read=lambda f:list(csv.reader(f.read_text().splitlines(),delimiter=";"))
before=read(A/"relative_objects.txt");after=read(items["relative_objects.txt"])
need(len(before)==len(after)==2103,"object count")
for a,b in zip(before,after):
    need(a[0]==b[0] and a[3:]==b[3:],"transform other than XY changed")
    need(all(abs(Decimal(b[i])-Decimal(a[i])-15)<=Decimal("0.001") for i in [1,2]),"XY transform")
need(len({(r[1],r[2]) for r in after})==2103,"duplicate translated XY")
# Source PolyLineZ -> compatible planar PolyLine records, preserving DBF row order.
src=(C/"roads.shp").read_bytes()
need(struct.unpack_from("<i",src,32)[0]==13,"unexpected source SHP type")
o=100; geom=[]
while o<len(src):
    rid,n=struct.unpack_from(">ii",src,o)
    typ,np,nv=struct.unpack_from("<i32xii",src,o+8)
    need(rid==len(geom)+1 and typ==13 and np==1 and 44+np*4+nv*16+2*(16+nv*8)==n*2,"source geometry")
    pts=[struct.unpack_from("<dd",src,o+8+48+16*i) for i in range(nv)]
    geom.append([(x+15,y+15) for x,y in pts]);o+=8+2*n
need(o==len(src) and len(geom)==2 and sum(map(len,geom))==12,"road count")
def bounds(ps):
    return min(x for x,y in ps),min(y for x,y in ps),max(x for x,y in ps),max(y for x,y in ps)
allpts=[p for ps in geom for p in ps]
need(all(200000<=x<201920 and 0<=y<1920 for x,y in allpts),"shifted road extent")
def header(n,bb):
    return struct.pack(">7i",9994,0,0,0,0,0,n//2)+struct.pack("<ii8d",1000,3,*bb,0,0,0,0)
records=[];idx=[];pos=100
for i,ps in enumerate(geom,1):
    rec=struct.pack("<i4diii",3,*bounds(ps),1,len(ps),0)+b"".join(struct.pack("<dd",*q) for q in ps)
    h=struct.pack(">ii",i,len(rec)//2)
    records.append(h+rec);idx.append(struct.pack(">ii",pos//2,len(rec)//2));pos+=len(h)+len(rec)
shp=header(pos,bounds(allpts))+b"".join(records)
shx=header(100+8*len(idx),bounds(allpts))+b"".join(idx)
need(len(shp)==pos and len(shx)==116 and struct.unpack_from("<I",items["roads.dbf"].read_bytes(),4)[0]==2,"SHP/SHX/DBF")
# The TB mask was re-rendered from native geometry at +15,+15, not shifted by whole pixels.
b=items["mask.bmp"].read_bytes();off=struct.unpack_from("<I",b,10)[0]
w,h,planes,bpp,comp=struct.unpack_from("<iiHHI",b,18)
need((w,h,planes,bpp,comp)==(480,480,1,24,0),"BMP")
def rgb(x,y):return b[off+(h-1-y)*w*3+x*3:off+(h-1-y)*w*3+x*3+3][::-1].hex()
hist=collections.Counter(rgb(x,y) for y in range(h) for x in range(w))
need(hist=={"6b8e23":217758,"664a00":6639,"add8e6":5400,"000000":603},"TB aligned mask")
need(rgb(54,426)=="664a00" and rgb(204,226)=="add8e6" and rgb(460,20)=="6b8e23","TB controls")
# Terrain bytes are unchanged except the earlier verified source-to-TB corner translation.
orig=(R/"terrain.asc").read_text().splitlines()
local=items["terrain.asc"].read_text().splitlines()
need(len(orig)==len(local)==70 and all(list(map(Decimal,a.split()))==list(map(Decimal,b.split())) for a,b in zip(orig[6:],local[6:])),"terrain values")
head={k.lower():Decimal(v) for k,v in (l.split() for l in local[:6])}
need(head["xllcorner"]==200000 and head["yllcorner"]==0 and head["cellsize"]==30 and head["ncols"]==head["nrows"]==64,"TB grid")
# All four selected material definitions were checked by reference on the installed P drive.
# Synthetic TB-only mud binding differs explicitly from GRM's v04-derived profile.
mats=[
 ("grass","a3\\map_enoch\\data\\gdt_engrass2",(107,142,35)),
 ("forest","a3\\map_enoch\\data\\gdt_enforestdec",(102,74,0)),
 ("mud","a3\\map_enoch\\data\\gdt_enmud",(173,216,230)),
 ("asphalt","a3\\map_data_exp\\gdt_asphalt",(0,0,0))]
for _,prefix,_ in mats:
    for s in ("_co.paa","_nopx.paa",".rvmat"):
        need(pathlib.Path("P:/"+prefix+s).is_file(),"material missing "+prefix+s)
T.mkdir()
for name,source in items.items():
    shutil.copyfile(source,T/name);need(sha(source)==sha(T/name),"copy mismatch")
(T/"roads.shp").write_bytes(shp);(T/"roads.shx").write_bytes(shx)
cfg="class Layers {\n"+"".join(' class '+n+' { texture="'+p+'_co.paa"; material="'+p+'.rvmat"; }\n' for n,p,c in mats)+"};\nclass Legend {\n picture=\""+str(T/"maplegend.png")+"\";\n class Colors {\n"+"".join("  "+n+"[]={{"+",".join(map(str,c))+"}};\n" for n,p,c in mats)+" };\n};\n"
(T/"layers.cfg").write_text(cfg,encoding="ascii")
manifest={"scope":"SYNTHETIC_TB_IMPORT_CANDIDATE","source_native_review":qc["files"],"grid":{"size_m":1920,"terrain_cells":64,"cell_m":30,"imagery_mask_px":480,"pixel_m":4,"tb_corner":[200000,0],"source_utm36_corner":[294373.084,5698122.108],"grm_node_origin":[294388.084,5698137.108],"grm_to_tb_xy_delta_m":[15,15],"synthetic_default_outside_node_footprint":True},"object_count":2103,"relative_mode":True,"road_count":2,"road_vertices":12,"road_format":"2D PolyLine converted from native PolyLineZ, XY +15m, DBF unchanged; Z/M intentionally not used for shape editor","mask_histogram":dict(hist),"material_mapping":[{"name":n,"prefix":p,"rgb":c} for n,p,c in mats],"mud_note":"TB-only Enoch mud stock pair substituted for unavailable map_data base RVMAT; original native profile unchanged; no game material approval","native_tb_import":"NOT_RUN","files":{f.name:sha(f) for f in T.iterdir() if f.is_file()}}
(T/"MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
zpath=R/"GRMAUTO01_TB_IMPORT.zip"
with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(T.iterdir()):z.write(f,f.name)
with zipfile.ZipFile(zpath) as z:
    need(set(z.namelist())=={f.name for f in T.iterdir()},"archive files")
    need(all(hashlib.sha256(z.read(n)).hexdigest()==sha(T/n) for n in z.namelist()),"archive digest")
print(json.dumps({"status":"FILE_LEVEL_TB_HANDOFF_PASS","files":len(list(T.iterdir())),"zip_bytes":zpath.stat().st_size,"zip_sha256":sha(zpath),"manifest_sha256":sha(T/"MANIFEST.json"),"roads":[[ps[0],ps[-1]] for ps in geom],"objects":len(after),"mask_histogram":dict(hist)},indent=2))
