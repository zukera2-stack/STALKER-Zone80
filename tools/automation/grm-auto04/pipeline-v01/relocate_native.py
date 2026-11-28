"""Fixed synthetic native template relocation test. Not a general TV4P serializer."""
from pathlib import Path, PureWindowsPath, PurePosixPath
import hashlib, json, os, re, stat, struct, zipfile
SRC=Path(r"D:\Zone80\GRMAUTO04")
DST=Path(r"D:\Zone80\TBGEN0001")
ARCH=SRC/"GRMAUTO04_NATIVE_INTEGRATION.zip"
PIN="a9d2ad3e11f269e96afd93c8ae81ace1eb92fc9883c86c5ee00ca005306ecfc8"
TV="Native/source/TerrainBuilder/GRMAUTO04.tv4p"
GRID="Native/source/TerrainBuilder/GRMAUTO04.grid.000.v4w"
OLD=str(SRC).encode("ascii")
NEW=str(DST).encode("ascii")
OFFSETS=[3061,3092,3137,3850,3896,4069,4115,4288,4331]
def req(test,msg):
    if not test:raise RuntimeError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def scan(b):return [m.start() for m in re.finditer(re.escape(OLD.lower()),b.lower())]
def path_safe(p):
    for x in (p,*p.parents):
        if x.exists():req(not x.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT,"reparse "+str(x))
def source_digest():
    return {str(p.relative_to(SRC)):sha(p.read_bytes()) for base in (SRC/"Native",SRC/"TBHandoff") for p in base.rglob("*") if p.is_file()}
def rebase(data,starts):
    b=bytearray(data)
    for off in starts:
        original=data[off:off+len(OLD)]
        req(original.lower()==OLD.lower(),"root not exact")
        new=NEW.lower() if original==OLD.lower() else NEW
        req(original in (OLD,OLD.lower()),"unexpected casing")
        b[off:off+len(OLD)]=new
    req(len(b)==len(data) and not scan(b),"relocation length/root")
    return bytes(b)
def main():
    req(len(OLD)==len(NEW)==19,"root lengths")
    req(not DST.exists(),"destination exists")
    path_safe(SRC);path_safe(DST)
    req(sha(ARCH.read_bytes())==PIN,"archive pin")
    baseline=source_digest()
    with zipfile.ZipFile(ARCH) as z:
        names=z.namelist()
        req(len(names)==len(set(n.lower() for n in names))==67,"archive entries")
        raw={}
        for n in names:
            p=PurePosixPath(n)
            req(not p.is_absolute() and ".." not in p.parts and ":" not in n and "\\" not in n and n.startswith(("Native/","TBHandoff/")),"archive path")
            req(z.getinfo(n).file_size<16*1024**2,"archive size")
            raw[n]=z.read(n)
        req(sha(raw[TV])=="24792dc28883be888b92c84d3f277477e7829febd86541bcf0bf6393388075e2","tv4p pin")
        req(sha(raw[GRID])=="3f77fced9d7e45057259cb83f1e67bc2ac3fd4046624b8233699ba75e435ba61","grid pin")
    # Verify all 9 exact ALB1 length-prefixed path fields and all 26 NUL-terminated grid paths.
    tb=raw[TV];req(tb[:4]==b"ALB1" and scan(tb)==OFFSETS,"ALB1 layout")
    expected=[b"\\native",b"\\TBHandoff\\layers.cfg",b"\\native\\source\\terrainbuilder\\\\GRMAUTO04.grid.000.v4w",b"\\TBHandoff\\terrain.asc",b"\\TBHandoff\\terrain.asc",b"\\TBHandoff\\imagery.bmp",b"\\TBHandoff\\imagery.bmp",b"\\TBHandoff\\mask.bmp",b"\\TBHandoff\\mask.bmp"]
    for off,suffix in zip(OFFSETS,expected):
        n=struct.unpack_from("<H",tb,off-2)[0]
        req(tb[off-3]==11 and n==len(OLD)+len(suffix) and tb[off+len(OLD):off+n]==suffix,"ALB1 path field")
    grid=raw[GRID];starts=scan(grid)
    req(grid.startswith(b"_B_GRID\0") and len(starts)==26,"grid layout")
    rv={n.lower() for n in raw if n.endswith(".rvmat")}
    paths=set()
    for off in starts:
        n=struct.unpack_from("<I",grid,off-4)[0]
        s=grid[off:off+n]
        req(s.endswith(b".rvmat") and grid[off+n]==0 and s[:19]==OLD.lower(),"grid path field")
        paths.add(s[20:].decode().replace("\\","/").lower())
    req(paths==rv,"grid material set")
    manifest={}
    output={}
    for n,b in raw.items():
        req(OLD.lower().decode().encode("utf-16le") not in b.lower(),"unexpected wide reference")
        st=scan(b)
        if n.endswith("Dialogs_new.vdat"):continue # dialog history, not project data
        if n==TV:req(st==OFFSETS,"tv offsets")
        elif n==GRID:req(len(st)==26,"grid offsets")
        elif n.endswith(".rvmat"):
            req(len(st)==2,"material paths")
            for off in st:
                s=b[off:b.index(b'"',off)].decode("ascii")
                rel=s[20:].replace("\\","/").lower()
                req(rel in {k.lower() for k in raw} and rel.endswith(".png"),"material texture ref")
        elif n=="TBHandoff/layers.cfg":req(len(st)==1 and (OLD+b"\\TBHandoff\\maplegend.png") in b,"legend")
        else:req(not st,"unexpected root in "+n)
        output[n]=rebase(b,st) if st else b
        manifest[n]={"before":sha(b),"after":sha(output[n]),"root_replacements":len(st)}
    handoff=json.loads(output["TBHandoff/MANIFEST.json"])
    handoff["files"]["layers.cfg"]=sha(output["TBHandoff/layers.cfg"])
    output["TBHandoff/MANIFEST.json"]=(json.dumps(handoff,ensure_ascii=True,indent=2)+"\n").encode()
    manifest["TBHandoff/MANIFEST.json"]["after"]=sha(output["TBHandoff/MANIFEST.json"])
    req(all(sha(output["TBHandoff/"+n])==h for n,h in handoff["files"].items()),"handoff manifest")
    DST.mkdir()
    for n,b in output.items():
        p=DST.joinpath(*PurePosixPath(n).parts);path_safe(p);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("xb") as f:f.write(b)
        req(sha(p.read_bytes())==manifest[n]["after"],"copy readback")
    req(source_digest()==baseline and sha(ARCH.read_bytes())==PIN,"source changed")
    receipt={"status":"CANDIDATE_ONLY","archive_sha256":PIN,"root_replacements":sum(x["root_replacements"] for x in manifest.values()),"files":manifest,"excluded":"Dialogs_new.vdat: optional dialog history","source_before":baseline}
    (DST/"relocation_receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
    print("CANDIDATE",len(output),"files",receipt["root_replacements"],"verified root substitutions")
if __name__=="__main__":main()
