"""Independent QC and deterministic assembly of four fixed native GRM blocks."""
from pathlib import Path
from decimal import Decimal as D
import collections, hashlib, json, math, struct, zipfile, xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent
B={"SW":(180,180),"SE":(780,180),"NW":(180,780),"NE":(780,780)}
ORDER=sorted(B)
def need(b,msg):
    if not b: raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def files(p):return {f.name:sha(f) for f in p.iterdir() if f.is_file()}
def asc(p):
    lines=p.read_text().splitlines();h={k.lower():D(v) for k,v in (s.split() for s in lines[:6])}
    n=int(h["ncols"]);v=[list(map(D,s.split())) for s in lines[6:]][::-1]
    need(len(v)==n and h["nrows"]==n and all(len(row)==n and all(x.is_finite() and x!=h["nodata_value"] for x in row) for row in v),"ASC")
    return h,v
h,whole=asc(R/"terrain.asc")
need(sha(R/"terrain.asc")=="ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324","source")
nodes=collections.defaultdict(list)
for s,(ox,oy) in B.items():
    g,v=asc(R/s/"terrain.asc")
    need(g["ncols"]==28 and g["cellsize"]==30 and g["xllcorner"]==h["xllcorner"]+ox and g["yllcorner"]==h["yllcorner"]+oy,"GM grid")
    for y in range(28):
        for x in range(28):
            i,j=x+ox//30,y+oy//30
            need(v[y][x]==whole[j][i],"GM value")
            nodes[i,j].append(v[y][x])
need(all(len(set(v))==1 for v in nodes.values()),"shared nodes")
repeat={s:len(files(R/s/"a")) for s in B}
for s in B:need(repeat[s]==9 and files(R/s/"a")==files(R/s/"b"),"native repeat "+s)
basehash={sha(R/s/"a"/"fixture.osm") for s in B};newhash={sha(R/s/"changed"/"fixture.osm") for s in B}
need(len(basehash)==len(newhash)==1 and basehash!=newhash,"common OSM")
# Independently verify only node coordinates of feature 105 changed.
def xml(p):
    root=ET.parse(p).getroot()
    return {(e.tag,e.attrib["id"]):ET.tostring(e,encoding="unicode") for e in root}
a,c=xml(R/"SW"/"a"/"fixture.osm"),xml(R/"SW"/"changed"/"fixture.osm")
need(a.keys()==c.keys() and {k for k in a if a[k]!=c[k]}=={("node","16"),("node","17")},"local change")
changed_files={s:sorted(n for n,v in files(R/s/"a").items() if files(R/s/"changed")[n]!=v) for s in B}
need(all(set(changed_files[s])=={"fixture.osm","result.json"} for s in B if s!="SW"),"nonlocal native artifact change")
need("objects.json" in changed_files["SW"] and "mask.bmp" in changed_files["SW"],"local change ineffective")
# Native sample grids independently compared at same world points.
samples={s:load(R/s/"a"/"heights.json") for s in B}
need(all(len(v)==361 for v in samples.values()),"probe count")
for s in B:need([(o["x"],o["y"]) for o in samples[s]]==[(o["x"],o["y"]) for o in samples["SW"]],"probe positions")
delta=max(max(p["z"] for p in row)-min(p["z"] for p in row) for row in zip(*samples.values()))
need(delta<=.0001,"interpolation seam")
# Native road SHP/SHX/DBF and global straight-line geometry.
road_errors=[];road_ranges={}
for s,(ox,oy) in B.items():
    p=R/s/"a";b=(p/"roads.shp").read_bytes()
    need(struct.unpack_from(">i",b,0)[0]==9994 and struct.unpack_from(">i",b,24)[0]*2==len(b) and struct.unpack_from("<i",b,32)[0]==13,"SHP header")
    o=100;idx=[];ranges={}
    while o<len(b):
        rid,n=struct.unpack_from(">ii",b,o);typ,np,nv=struct.unpack_from("<i32xii",b,o+8)
        need(rid==len(idx)+1 and typ==13 and np==1 and nv>=2 and 48+16*nv+2*(16+8*nv)==2*n,"SHP record")
        pts=[(x-200000+ox,y+oy) for x,y in (struct.unpack_from("<dd",b,o+8+48+16*i) for i in range(nv))]
        xr,yr=max(x for x,y in pts)-min(x for x,y in pts),max(y for x,y in pts)-min(y for x,y in pts)
        axis="H" if xr>yr else "V"
        need(axis not in ranges,"road duplicate")
        err=max(abs((y if axis=="H" else x)-900) for x,y in pts)
        road_errors.append(err);need(err<=.05,"road line deviation")
        z=[x if axis=="H" else y for x,y in pts];lo,hi=min(z),max(z)
        expected=(max(400,ox if axis=="H" else oy),min(1400,(ox if axis=="H" else oy)+840))
        need(abs(lo-expected[0])<=.05 and abs(hi-expected[1])<=.05,"road clipping")
        need(lo<=960<=hi and lo<=900<=hi,"road crossing")
        ranges[axis]=[lo,hi];idx.append((o//2,n));o+=8+2*n
    need(o==len(b) and set(ranges)=={"H","V"},"two roads")
    ix=(p/"roads.shx").read_bytes()
    need(len(ix)==116 and [struct.unpack_from(">ii",ix,i) for i in (100,108)]==idx and struct.unpack_from("<I",(p/"roads.dbf").read_bytes(),4)[0]==2,"SHX/DBF")
    road_ranges[s]=ranges
def owner(x,y,lo,mid,hi):
    if not(lo<=x<hi and lo<=y<hi):return None
    return ("N" if y>=mid else "S")+("E" if x>=mid else "W")
need(owner(960,960,480,960,1440)=="NE" and owner(900,900,300,900,1500)=="NE" and owner(1440,960,480,960,1440) is None,"half-open corner")
radius={"t_betula_pendula_2f":.7,"t_betula_pendula_3f":1.0,"t_betula_pendula_3s":2.0}
def key(o):return [o["model"],*(round(o[k],3) for k in ("x","y","yaw","pitch","roll","scale","elevation"))]
def oid(s,f,o):
    return hashlib.sha256(json.dumps(["grmauto03-fixed-world-v1",s,f,key(o)],separators=(",",":")).encode()).hexdigest()
def candidate(attempt):
    cand=[];counts={}
    for s in B:
        raw=load(R/s/attempt/"objects.json");valid=[o for o in raw if not o["reason"]]
        need(len({(round(o["x"],3),round(o["y"],3)) for o in valid})==len(valid),"native duplicate")
        cnt=collections.Counter(o["reason"] for o in raw if o["reason"])
        selected=[]
        for o in valid:
            x,y=o["x"],o["y"];own=owner(x,y,480,960,1440)
            if owner(x,y,300,900,1500)!=s or own is None:continue
            f=101 if 659.98<=x<=1140.02 and 659.98<=y<=1140.02 else 105 if 499.98<=x<=(640.02 if attempt=="changed" else 600.02) and 499.98<=y<=600.02 else None
            need(f is not None,"feature lineage")
            need(o["model"] in radius and all(math.isfinite(o[k]) for k in ("x","y","z","yaw","pitch","roll","scale","elevation")) and 0<radius[o["model"]]*o["scale"]<=2,"transform")
            selected.append(dict(o,source_feature=f,block=s,owner=own,id=oid(s,f,o)))
        counts[s]={"generated":len(raw),"native_accepted":len(valid),"native_holds":dict(cnt),"owned_candidates":len(selected)}
        cand.extend(selected)
    need(len({o["id"] for o in cand})==len(cand),"ID duplicate")
    return cand,counts
def incompatible(p,q):
    # All pairs that cross either generation block or storage-sector boundary.
    return (p["block"]!=q["block"] or p["owner"]!=q["owner"]) and math.hypot(p["x"]-q["x"],p["y"]-q["y"])<radius[p["model"]]*p["scale"]+radius[q["model"]]*q["scale"]
def bucket(o):return math.floor(o["x"]/4),math.floor(o["y"]/4)
def neighbors(b,o):
    x,y=bucket(o)
    for i in range(x-1,x+2):
        for j in range(y-1,y+2):yield from b.get((i,j),())
def arbitrate(cand):
    # Stable block priority, then stable ID; not a physical collision model.
    seen=collections.defaultdict(list);accepted=collections.defaultdict(list);good=[];held=[];pairs=0;diagonal=0
    for o in sorted(cand,key=lambda o:(o["block"],o["id"])):
        hits=[q for q in neighbors(seen,o) if incompatible(o,q)]
        pairs+=len(hits);diagonal+=sum(q["block"][0]!=o["block"][0] and q["block"][1]!=o["block"][1] for q in hits)
        seen[bucket(o)].append(o)
        conflicts=[q["id"] for q in neighbors(accepted,o) if incompatible(o,q)]
        if conflicts:held.append(dict(o,hold_reason="cross_boundary_anchor_proxy",conflicts_with=sorted(conflicts)))
        else:good.append(o);accepted[bucket(o)].append(o)
    need(len(good)+len(held)==len(cand),"candidate conservation")
    check=collections.defaultdict(list)
    for o in good:
        need(not any(incompatible(o,q) for q in neighbors(check,o)),"unresolved proxy collision")
        check[bucket(o)].append(o)
    return {s:sorted((o for o in good if o["owner"]==s),key=lambda o:o["id"]) for s in B},sorted(held,key=lambda o:o["id"]),pairs,diagonal
# Separate fabricated algorithm-only corner probe, never included in native results.
toy=[dict(model="t_betula_pendula_2f",scale=1,x=x,y=y,block=s,owner=s,id=s) for s,x,y in [("SW",959.9,959.9),("SE",960.1,959.9),("NW",959.9,960.1),("NE",960.1,960.1)]]
t,held,pairs,diag=arbitrate(toy)
need(sum(map(len,t.values()))==1 and len(held)==3 and pairs==6 and diag==2 and arbitrate(list(reversed(toy)))==(t,held,pairs,diag),"corner negative test")
cand,counts=candidate("a");parts,held,pairs,diag=arbitrate(cand)
need(arbitrate(list(reversed(cand)))==(parts,held,pairs,diag),"order invariant")
again,_=candidate("b");need(arbitrate(again)==(parts,held,pairs,diag),"repeat assembly")
changed,ccounts=candidate("changed");cp,ch,cpairs,cdiag=arbitrate(changed)
def ids(ps):return {o["id"] for rows in ps.values() for o in rows}
need(all(parts[s]==cp[s] for s in B if s!="SW"),"changed non-SW storage object output")
need(all({o["id"] for o in cand if o["block"]==s}=={o["id"] for o in changed if o["block"]==s} for s in B if s!="SW"),"nonlocal candidates")
# Full storage core mask from single authoritative generation core per world pixel.
PALETTE={"6b8e23","664a00","add8e6","000000"}
def bmp_reader(s,attempt):
    b=(R/s/attempt/"mask.bmp").read_bytes();off=struct.unpack_from("<I",b,10)[0]
    w,h,planes,bpp,comp=struct.unpack_from("<iiHHI",b,18)
    need((w,h,planes,bpp,comp)==(210,210,1,24,0),"BMP")
    stride=(w*3+3)//4*4;ox,oy=B[s]
    def pix(x,y):
        i=(x-ox)//4;j=(y-oy)//4
        need(0<=i<w and 0<=j<h,"pixel extent")
        k=off+j*stride+i*3;v=b[k:k+3];need(v[::-1].hex() in PALETTE,"palette");return v
    return pix
def mask(attempt):
    pix={s:bmp_reader(s,attempt) for s in B}
    def world(x,y):
        s=owner(x,y,300,900,1500);need(s in B,"mask owner")
        return pix[s](x,y)
    result={}
    for s in B:
        x0=960 if s[1]=="E" else 480;y0=960 if s[0]=="N" else 480
        result[s]=[b"".join(world(x,y) for x in range(x0+2,x0+480,4)) for y in range(y0+2,y0+480,4)]
    return result,pix,world
m,pix,world=mask("a");mb,_,_=mask("b");mc,_,_=mask("changed")
need(m==mb and all(m[s]==mc[s] for s in B if s!="SW"),"mask repeat/local")
# Raw independently rendered overlap: exact equality diagnostic, no seam claim if nonzero.
overlap={}
for i,s in enumerate(ORDER):
    for t in ORDER[i+1:]:
        a,b=B[s];c,d=B[t];lo=max(a,c);hi=min(a,c)+840;bot=max(b,d);top=min(b,d)+840
        dif=0;n=0
        for y in range(bot+2,top,4):
            for x in range(lo+2,hi,4):
                n+=1;dif+=pix[s](x,y)!=pix[t](x,y)
        overlap[s+"-"+t]={"pixels":n,"mismatches":dif}
dest=R/"assembled_review";zpath=R/"GRMAUTO03_FOUR_SECTOR_REVIEW.zip"
need(not dest.exists() and not zpath.exists(),"fresh output")
dest.mkdir()
def write_bmp(out,rows):
    w=120;h=120;payload=b"".join(rows);need(len(payload)==w*h*3,"mask dimensions")
    out.write_bytes(struct.pack("<2sIHHI",b"BM",54+len(payload),0,0,54)+struct.pack("<IiiHHIIiiII",40,w,h,1,24,0,len(payload),0,0,0,0)+payload)
for s in B:
    (dest/(s+"_objects.json")).write_text(json.dumps(parts[s],separators=(",",":")),encoding="utf-8")
    write_bmp(dest/(s+"_mask.bmp"),m[s])
(dest/"held.json").write_text(json.dumps(held,separators=(",",":")),encoding="utf-8")
# Independent on-disk readback across entire 960m storage square.
hist=collections.Counter();n=0
for s in B:
    raw=(dest/(s+"_mask.bmp")).read_bytes();need(struct.unpack_from("<iiHHI",raw,18)==(120,120,1,24,0),"written mask")
    x0=960 if s[1]=="E" else 480;y0=960 if s[0]=="N" else 480
    for j in range(120):
        for i in range(120):
            off=54+(j*120+i)*3;v=raw[off:off+3]
            need(v==world(x0+i*4+2,y0+j*4+2),"written pixel")
            hist[v[::-1].hex()]+=1;n+=1
    need(load(dest/(s+"_objects.json"))==parts[s],"objects readback")
need(n==57600 and sum(hist.values())==n and len(ids(parts))==sum(map(len,parts.values())),"coverage")
changed_px=sum(a[i:i+3]!=b[i:i+3] for a,b in zip(m["SW"],mc["SW"]) for i in range(0,len(a),3))
report={"scope":"SYNTHETIC_REVIEW_ONLY","generation_cores_m":600,"halo_m":120,"storage_cores_m":480,"source_node_reads":3136,"unique_nodes":len(nodes),"shared_nodes":sum(len(v)>1 for v in nodes.values()),"four_way_nodes":sum(len(v)==4 for v in nodes.values()),"node_max_delta_m":0,"interpolation_probes":361,"interpolation_max_delta_m":delta,"native_repeat_files":repeat,"road_max_line_error_m":max(road_errors),"road_ranges":road_ranges,"raw_overlap_masks":overlap,"native_counts":counts,"candidate_count":len(cand),"cross_boundary_pairs_before":pairs,"diagonal_block_pairs_before":diag,"held":len(held),"cross_boundary_pairs_after":0,"storage_counts":{s:len(v) for s,v in parts.items()},"unique_ids":len(ids(parts)),"exact_corner_negative_test":{"candidates":4,"conflicts":6,"diagonal":2,"accepted":1,"held":3},"mask_pixels":n,"mask_histogram":dict(hist),"mask_readback_mismatches":0,"changed_native_files":changed_files,"changed_storage_counts":{s:len(v) for s,v in cp.items()},"changed_ids_removed":len(ids(parts)-ids(cp)),"changed_ids_added":len(ids(cp)-ids(parts)),"changed_SW_mask_pixels":changed_px,"changed_non_SW_storage_objects_and_masks_exact":True,"lineage":"synthetic feature rectangle containment, fixed block and quantized pose IDs; not generalized source lineage","native_TB_import":"NOT_RUN","full_road_export":"NOT_RUN","physical_collision":"NOT_RUN","files":files(dest)}
(dest/"MANIFEST.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
with zipfile.ZipFile(zpath,"x",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(dest.iterdir()):z.write(f,f.name)
with zipfile.ZipFile(zpath) as z:need(set(z.namelist())=={f.name for f in dest.iterdir()} and all(hashlib.sha256(z.read(n)).hexdigest()==sha(dest/n) for n in z.namelist()),"archive")
print(json.dumps({k:v for k,v in report.items() if k not in ("files","road_ranges")},indent=2))
print("ZIP_SHA256="+sha(zpath)+" BYTES="+str(zpath.stat().st_size)+" FILES="+str(len(list(dest.iterdir()))))
