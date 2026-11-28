"""Verify fixed shared 720m GRM block and partition into two adjacent cores.
Synthetic review only; the anchor-radius proxy is not a model collision test."""
from pathlib import Path
from decimal import Decimal
import collections, hashlib, json, math, struct, zipfile
R=Path(__file__).resolve().parent
def need(b,msg):
    if not b: raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def files(p):return {f.name:sha(f) for f in p.iterdir() if f.is_file()}
a,b=R/"C"/"a",R/"C"/"b"
need(files(a)==files(b) and len(files(a))==9,"canonical native repeat")
need(sha(a/"fixture.osm")==sha(R/"REF"/"a"/"fixture.osm"),"shared source")
# Verify every GM-exported node against the original native GM raster.
def asc(p):
    lines=p.read_text().splitlines();h={k.lower():Decimal(v) for k,v in (s.split() for s in lines[:6])}
    n=int(h["ncols"]);v=[list(map(Decimal,s.split())) for s in lines[6:]][::-1]
    need(len(v)==n and h["nrows"]==n and all(len(row)==n and all(x.is_finite() and x!=h["nodata_value"] for x in row) for row in v),"ASC")
    return h,v
h,whole=asc(R/"REF"/"terrain.asc")
g,grid=asc(R/"C"/"terrain.asc")
need(g["ncols"]==24 and g["cellsize"]==30 and g["xllcorner"]==h["xllcorner"]+600 and g["yllcorner"]==h["yllcorner"]+420,"canonical grid")
need(all(grid[y][x]==whole[y+14][x+20] for y in range(24) for x in range(24)),"GM values")
probe=load(a/"heights.json")
ref=load(R/"REF"/"a"/"heights.json")
need(len(probe)==len(ref)==231 and all((p["x"],p["y"])==(q["x"],q["y"]) for p,q in zip(probe,ref)),"height samples")
dz=max(abs(p["z"]-q["z"]) for p,q in zip(probe,ref));need(dz<=0.0001,"interpolation")
def key(o):return (o["model"],*(round(o[k],3) for k in ("x","y","yaw","pitch","roll","scale","elevation")))
def oid(o):return hashlib.sha256(("grmauto02-canonical-block-v1\n"+json.dumps(key(o),separators=(",",":"))).encode()).hexdigest()
def owner(o):
    if not(360<=o["x"]<1560 and 480<=o["y"]<1080):return None
    return "W" if o["x"]<960 else "E"
radius={"t_betula_pendula_2f":0.7,"t_betula_pendula_3f":1.0,"t_betula_pendula_3s":2.0}
def build(p,reverse=False):
    source=load(p/"objects.json");valid=[o for o in source if not o["reason"]]
    need(len(valid)==2331 and all(owner(o) for o in valid),"canonical object scope")
    need(len({(round(o["x"],3),round(o["y"],3)) for o in valid})==len(valid),"duplicate XY")
    need(all(o["model"] in radius and all(math.isfinite(o[k]) for k in ("x","y","z","yaw","pitch","roll","scale","elevation")) and o["scale"]>0 for o in valid),"invalid transform")
    # Keep a canonical ordering independent of sector request order or input iteration.
    ordered=sorted((dict(o,id=oid(o),owner=owner(o)) for o in (list(reversed(valid)) if reverse else valid)),key=lambda o:o["id"])
    need(len({o["id"] for o in ordered})==len(ordered),"duplicate ID")
    def clash(p,q):
        return p["owner"]!=q["owner"] and math.hypot(p["x"]-q["x"],p["y"]-q["y"])<radius[p["model"]]*p["scale"]+radius[q["model"]]*q["scale"]
    # Bounded deterministic cross-seam hold only. Does not certify intra-sector footprints.
    cand=[o for o in ordered if abs(o["x"]-960)<4.0]
    need(all(radius[o["model"]]*o["scale"]<=2 for o in ordered),"radius range")
    raw_pairs=sum(clash(p,q) for i,p in enumerate(cand) for q in cand[i+1:])
    good=[];near=[];held=[]
    for o in ordered:
        conflicts=[q["id"] for q in near if clash(o,q)] if abs(o["x"]-960)<4 else []
        if conflicts:held.append(dict(o,hold_reason="cross_seam_anchor_proxy",conflicts_with=conflicts))
        else:
            good.append(o)
            if abs(o["x"]-960)<4:near.append(o)
    need(not any(clash(p,q) for i,p in enumerate(near) for q in near[i+1:]),"proxy conflict after hold")
    need(len(good)+len(held)==len(valid),"ownership count")
    return {"W":[o for o in good if o["owner"]=="W"],"E":[o for o in good if o["owner"]=="E"],"held":held},raw_pairs
parts,pairs=build(a)
other,pairs2=build(b,True)
need(parts==other and pairs==pairs2,"canonical assignment not repeatable")
# Crop both core intersections from ONE native-geometry companion mask grid.
# These cover the shared block intersection only (not the whole 600m cores).
def pixels(p):
    data=p.read_bytes();off=struct.unpack_from("<I",data,10)[0]
    w,h,planes,bpp,comp=struct.unpack_from("<iiHHI",data,18)
    need((w,h,planes,bpp,comp)==(180,180,1,24,0),"BMP")
    stride=(w*3+3)//4*4
    return [data[off+j*stride:off+j*stride+w*3] for j in range(h)]
rows=pixels(a/"mask.bmp")
band=rows[15:165] # y=480..1080, bottom-up; common block origin (600,420)
left=[row[:270] for row in band];right=[row[270:] for row in band]
need(len(left)==len(right)==150 and all(l+r==s for l,r,s in zip(left,right,band)),"mask assembly")
def bmp(out,rows):
    w=90;h=len(rows);stride=(w*3+3)//4*4
    payload=b"".join(row+b"\0"*(stride-w*3) for row in rows)
    out.write_bytes(struct.pack("<2sIHHI",b"BM",54+len(payload),0,0,54)+struct.pack("<IiiHHIIiiII",40,w,h,1,24,0,len(payload),0,0,0,0)+payload)
dest=R/"canonical_review";zpath=R/"GRMAUTO02_CANONICAL_REVIEW.zip"
need(not dest.exists() and not zpath.exists(),"fresh output")
dest.mkdir()
for name,rows2 in parts.items():(dest/(name+".json")).write_text(json.dumps(rows2,separators=(",",":")),encoding="utf-8")
bmp(dest/"W_mask.bmp",left);bmp(dest/"E_mask.bmp",right)
# Verify actual serialized cropped masks including row padding and reassembly.
def raw(p):
    data=p.read_bytes();off=struct.unpack_from("<I",data,10)[0]
    need(struct.unpack_from("<iiHHI",data,18)==(90,150,1,24,0),"crop header")
    return [data[off+j*272:off+j*272+270] for j in range(150)]
need(all(l+r==s for l,r,s in zip(raw(dest/"W_mask.bmp"),raw(dest/"E_mask.bmp"),band)),"serialized reassembly")
report={"scope":"SYNTHETIC_REVIEW_ONLY","canonical_block_m":[720,720],"world_offset_m":[600,420],"height_nodes":576,"height_max_delta_m":0,"height_probe_count":231,"probe_max_delta_m":dz,"native_repeated_files":9,"source_files":files(a),"generated":2343,"native_accepted":2331,"native_held":12,"cross_seam_proxy_pairs_before":pairs,"extra_held":len(parts["held"]),"owned_W":len(parts["W"]),"owned_E":len(parts["E"]),"cross_seam_proxy_pairs_after":0,"unique_assigned_ids":len({o["id"] for s in ("W","E") for o in parts[s]}),"reverse_order_repeat_exact":True,"mask_intersection_pixels":27000,"mask_reassembly_mismatches":0,"mask_crop_scope":"intersection of common 720m block and 600m cores, not full core mask","full_world_scalability":"NOT_PROVEN","physical_model_collisions":"NOT_RUN","native_TB_import":"NOT_RUN","files":files(dest)}
(dest/"MANIFEST.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(dest.iterdir()):z.write(f,f.name)
with zipfile.ZipFile(zpath) as z:
    need(set(z.namelist())=={f.name for f in dest.iterdir()} and all(hashlib.sha256(z.read(n)).hexdigest()==sha(dest/n) for n in z.namelist()),"archive verification")
print(json.dumps({k:v for k,v in report.items() if k not in ("source_files","files")},indent=2))
print("ZIP_SHA256="+sha(zpath)+" BYTES="+str(zpath.stat().st_size)+" FILES="+str(len(list(dest.iterdir()))))
