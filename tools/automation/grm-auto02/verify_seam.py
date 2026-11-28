"""Independent fixed-fixture QC; outputs are synthetic review only."""
from pathlib import Path
import collections, hashlib, json, math, struct
R=Path(__file__).resolve().parent
def need(b,msg):
    if not b: raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def files(p):return {f.name:sha(f) for f in p.iterdir() if f.is_file()}
dirs={s:R/s/"a" for s in ("W","E","REF")}
repeat={s:len(files(dirs[s])) for s in ("W","E")}
for s in repeat:need(files(dirs[s])==files(R/s/"b"),"repeat "+s)
need(len({sha(p/"fixture.osm") for p in dirs.values()})==1,"shared OSM")
heights={s:load(p/"heights.json") for s,p in dirs.items()}
keys=lambda xs:[(r["x"],r["y"]) for r in xs]
need(len(heights["W"])==231 and all(keys(v)==keys(heights["REF"]) for v in heights.values()),"height samples")
dz=max(abs(a["z"]-b["z"]) for a,b in zip(heights["W"],heights["E"]))
dr=max(abs(a["z"]-b["z"]) for s in ("W","E") for a,b in zip(heights[s],heights["REF"]))
need(dz<=0.0001 and dr<=0.0001,"interpolated height mismatch")
offset={"W":(180,300),"E":(780,300),"REF":(0,0)}
# Native PolyLineZ independently decoded and SHX/DBF row count checked.
def roads(s):
 p=dirs[s];b=(p/"roads.shp").read_bytes()
 need(struct.unpack_from(">i",b,0)[0]==9994 and struct.unpack_from(">i",b,24)[0]*2==len(b) and struct.unpack_from("<i",b,32)[0]==13,"SHP header")
 x0,y0=offset[s];out=[];ind=[];o=100
 while o<len(b):
    rid,n=struct.unpack_from(">ii",b,o);typ,np,nv=struct.unpack_from("<i32xii",b,o+8)
    need(rid==len(out)+1 and typ==13 and np==1 and nv>=2 and 48+16*nv+2*(16+8*nv)==2*n,"SHP record")
    pts=[struct.unpack_from("<dd",b,o+8+48+16*i) for i in range(nv)]
    out.append([(x-200000+x0,y+y0) for x,y in pts]);ind.append((o//2,n));o+=8+2*n
 need(o==len(b) and len(out)==2,"road count")
 ix=(p/"roads.shx").read_bytes();need(len(ix)==116 and [struct.unpack_from(">ii",ix,i) for i in (100,108)]==ind,"SHX")
 need(struct.unpack_from("<I",(p/"roads.dbf").read_bytes(),4)[0]==2,"DBF count")
 return out
lines={s:roads(s) for s in dirs}
def at_x(line,x):
 vals=[]
 for (a,b),(c,d) in zip(line,line[1:]):
    if min(a,c)<=x<=max(a,c) and a!=c:vals.append(b+(d-b)*(x-a)/(c-a))
 need(vals and max(vals)-min(vals)<0.001,"ambiguous crossing")
 return sum(vals)/len(vals)
cross={s:[sorted(at_x(l,x) for l in ls) for x in (900,960,1020)] for s,ls in lines.items()}
roaderr=max(abs(a-b) for s in ("W","E") for pair,ref in zip(cross[s],cross["REF"]) for a,b in zip(pair,ref))
need(roaderr<=0.05 and max(abs(a-b) for a,b in zip(cross["REF"][1],[600,760]))<=0.05,"road seam")
# BMP global grid: center at x+2,y+2, compare same physical pixels.
def bmp(s):
 b=(dirs[s]/"mask.bmp").read_bytes();o=struct.unpack_from("<I",b,10)[0]
 w,h,planes,bpp,comp=struct.unpack_from("<iiHHI",b,18)
 need((w,h,planes,bpp,comp)==((480 if s=="REF" else 240),)*2+(1,24,0),"BMP")
 stride=(w*3+3)//4*4;ox,oy=offset[s]
 def pix(x,y):
    i=(x-ox)//4;j=(y-oy)//4
    need(0<=i<w and 0<=j<h,"pixel extent")
    off=o+j*stride+i*3;return b[off:off+3][::-1].hex()
 return pix
px={s:bmp(s) for s in dirs}
palette={"6b8e23","664a00","add8e6","000000"}
def compare(a,b,xlo,xhi,ylo,yhi):
 pairs=collections.Counter()
 for y in range(ylo+2,yhi,4):
    for x in range(xlo+2,xhi,4):
      p,q=px[a](x,y),px[b](x,y);need(p in palette and q in palette,"palette")
      if p!=q:pairs[p+"->"+q]+=1
 return {"pixels":((xhi-xlo)//4)*((yhi-ylo)//4),"mismatches":sum(pairs.values()),"transitions":dict(pairs)}
mask={"overlap":compare("W","E",840,1080,480,1080),"seam_band":compare("W","E",940,980,480,1080),"W_core_ref":compare("W","REF",360,960,480,1080),"E_core_ref":compare("E","REF",960,1560,480,1080)}
# Raw native objects: exact position/pose identity at 1mm precision in common world frame.
objs={s:load(p/"objects.json") for s,p in dirs.items()}
accepted={s:[o for o in rows if not o["reason"]] for s,rows in objs.items()}
for s,rows in accepted.items():
 need(rows and all(all(math.isfinite(o[k]) for k in ("x","y","z","yaw","pitch","roll","scale","elevation")) and o["scale"]>0 for o in rows),"finite")
 need(len({(round(o["x"],3),round(o["y"],3)) for o in rows})==len(rows),"duplicate XY "+s)
def key(o):return (o["model"],*(round(o[k],3) for k in ("x","y","yaw","pitch","roll","scale","elevation")))
def owned(o,s):return 480<=o["y"]<1080 and (360<=o["x"]<960 if s=="W" else 960<=o["x"]<1560)
def overlap(o):return 840<=o["x"]<1080 and 480<=o["y"]<1080
raw_overlap={s:{key(o) for o in rows if overlap(o)} for s,rows in accepted.items()}
shared=len(raw_overlap["W"]&raw_overlap["E"])
raw={s:[o for o in accepted[s] if owned(o,s)] for s in ("W","E")}
ref={s:[o for o in accepted["REF"] if owned(o,s)] for s in ("W","E")}
# Radius is only a conservative anchor spacing proxy, not a model geometry collision test.
radius={"t_betula_pendula_2f":0.7,"t_betula_pendula_3f":1.0,"t_betula_pendula_3s":2.0}
def conflicts(parts):
 left=[o for o in parts["W"] if o["x"]>=956]
 right=[o for o in parts["E"] if o["x"]<964]
 pairs=[]
 for a in left:
    for b in right:
      d=math.hypot(a["x"]-b["x"],a["y"]-b["y"])
      if d<radius[a["model"]]*a["scale"]+radius[b["model"]]*b["scale"]:
        pairs.append(d)
 return {"pairs":len(pairs),"min_distance_m":min(pairs,default=None),"west_band":len(left),"east_band":len(right)}
rawc=conflicts(raw);refc=conflicts(ref)
need(len({key(o) for s in raw for o in raw[s]})==sum(map(len,raw.values())),"raw ownership duplicate")
# Canonical fallback: generate one bounded native reference in fixed frame, partition by half-open cores.
# Deterministic identity for this fixture only, no source feature IDs or scalable independent seam proof.
def ident(o):
 return hashlib.sha256(("grmauto02-fixed-world-v1\n"+json.dumps(key(o),separators=(",",":"))).encode()).hexdigest()
refall=[o for o in accepted["REF"] if owned(o,"W") or owned(o,"E")]
parts={s:[dict(o,id=ident(o),owner=s) for o in ref[s]] for s in ("W","E")}
ids=[o["id"] for s in parts for o in parts[s]]
need(len(ids)==len(set(ids))==len(refall) and set(ids)=={ident(o) for o in refall},"partition coverage")
# Rebuild identical assignment in reverse sector order, independent of order of processing.
reverse={s:sorted(ident(o) for o in reversed(refall) if owned(o,s)) for s in ("E","W")}
need(all(sorted(o["id"] for o in parts[s])==reverse[s] for s in parts),"order invariant")
stats={"scope":"SYNTHETIC_REVIEW_ONLY","repeat_identical_files":repeat,"fixture_sha256":sha(dirs["REF"]/"fixture.osm"),"shared_nodes":384,"shared_interpolation_samples":231,"interpolation_max_delta_m":dz,"interpolation_vs_ref_max_delta_m":dr,"road_crossings_at_x_900_960_1020":cross,"road_max_delta_m":roaderr,"mask":mask,"native_counts":{s:{"generated":len(objs[s]),"accepted":len(accepted[s]),"held":dict(collections.Counter(o["reason"] for o in objs[s] if o["reason"]))} for s in dirs},"raw_overlap_counts":{s:len(v) for s,v in raw_overlap.items()},"raw_overlap_matching_keys":shared,"raw_overlap_exact_equal":raw_overlap["W"]==raw_overlap["E"],"raw_core_counts":{s:len(v) for s,v in raw.items()},"raw_cross_seam_anchor_conflicts":rawc,"ref_core_counts":{s:len(v) for s,v in ref.items()},"ref_cross_seam_anchor_conflicts":refc,"canonical_partition_count":len(ids),"canonical_partition_order_invariant":True,"native_independent_vegetation_seam":"PASS" if raw_overlap["W"]==raw_overlap["E"] else "FAIL","native_independent_mask_seam":"PASS" if not mask["overlap"]["mismatches"] else "FAIL","canonical_partition":"PASS_REVIEW_ONLY","radius_note":"profile anchor radius proxy; not actual collision detection","files":{s:files(p) for s,p in dirs.items()}}
out=R/"seam_qc.json";dest=R/"canonical_partition";need(not out.exists() and not dest.exists(),"fresh output")
dest.mkdir()
for s in parts:
 (dest/(s+".json")).write_text(json.dumps(sorted(parts[s],key=lambda o:o["id"]),separators=(",",":")),encoding="utf-8")
stats["canonical_partition_hashes"]=files(dest)
out.write_text(json.dumps(stats,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in stats.items() if k!="files"},indent=2))
