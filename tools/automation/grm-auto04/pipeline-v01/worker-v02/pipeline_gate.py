"""Fixed Windows GRMAUTO04 integration gate, synthetic only.
Portable CC01/CC03/CC05Q helpers; not a general Windows Worker or GUI runner.
"""
import csv, ctypes, datetime as dt, json, msvcrt, os, re, shutil, stat, subprocess, sys, uuid
from decimal import Decimal
from pathlib import Path
import cc01_base as b
import sector_manager as sm
import preflight as pf
import job_owner as jo

ROOT = Path(r"D:\Zone80\PipelineV01_02")
SOURCE = Path(r"D:\Zone80\GRMAUTO04")
DOTNET = Path(r"C:\Program Files\dotnet\dotnet.exe")
BASE = "faf3a3f34cfe754c9804b47454d705ec6e630035"
PINS = {
    "terrain.asc":"ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324",
    "terrain.prj":"fdab6e893555dc5503ea414374724e48aa547eedf16896329215cfa07a851bfe",
    "synthetic.grma3a":"4321314e74a02638a3c018d829226fdebc0c6fda0468484474d8c904b19fb039",
    "modelinfo.json":"1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94",
    "fixture.osm":"86a6b53a1ff56f992bc8ea7bd590058daba8869e3983dbb332467a85cfb17ce3",
    "retained/MANIFEST.json":"49cc261ed8fc5da6c17945886a4d0ffe53752b4264efeccf4b1cbb64123a2368",
}
EVIDENCE = {
    "TBHandoff/MANIFEST.json":"7af11b276bb5b8ad6a4b056cf5659201e7327abf80a141d5b46eb4e983b1a118",
    "TBHandoff/relative_objects.txt":"e3f9c2bca1b360ab4fbff809f682a1afef996cb19a5c514d860f8ee0a491b56e",
    "TBHandoff/terrain.asc":"dee095c5bb89ab09c4f596b7aec79acf2b13bddaa2cf4ae95e828f2e786674ac",
    "PoseQC01/native_objects.txt":"d4e3a802acb8f27fd83551ce48e11566bf2bab026631445d8400db45ca55524b",
    "PoseQC01/pose_qc.json":"8668403a89dc4639a224ad6b4cb34a61b35783a6dea5d865974f1cfb1ced38a0",
    "PoseQC01/native_terrain.asc":"fcf59e66c2f7afcf32eedb18c049f99b300bab2b13e952811a6e672d2b56262c",
    "PoseQC01/terrain_material_qc.json":"378a02ee755c4ba3b202877b7c920f33e2e3656918bcd2d19f7b41ba7f0c6a9f",
    "StockPPreview01/NoPause01/Before.png":"7c819bb668f9cdb7ff1db97618e8047e22f5692d9e1388013922a3d98f1cf490",
    "StockPPreview01/NoPause01/AfterGoto.png":"cfc3e871165665d72652fb6648d164e552379cf18d135c5eef47be197e8cc02f",
    "Native/source/TerrainBuilder/GRMAUTO04.tv4p":"24792dc28883be888b92c84d3f277477e7829febd86541bcf0bf6393388075e2",
    "GRMAUTO04_NATIVE_INTEGRATION.zip":"a9d2ad3e11f269e96afd93c8ae81ace1eb92fc9883c86c5ee00ca005306ecfc8",
}
DLL = "21abfa0c2a5ce30affaf23bea2172202313770614f6371add923bcdb4d262cfa"
RESULT = "55615e3cd83a38829c4a8d7df6a6549fd00986f49a0eea935a1f5812c471529e"
HELPERS = {
    "cc01_base.py":"7ee6a93a45e61b3ee53776709e2df85effb2d002a1cc2fe232da32ad35a7b547",
    "sector_manager.py":"514072c171cf29128215e8fa4163612f2b3b38ecfb326e307c8d59c14845e66c",
    "preflight.py":"9aa2bbf4138ad61c5086b26039c0552eb3df3e44dbdc6c86f0ff71d00c9fd286",
}
MARKER = {"scope":"synthetic_grmauto04_windows_integration_only","schema_version":1,"base":BASE}

def need(ok,why): b.require(ok,why)

def safe(path):
    path=Path(path)
    need(path.is_absolute() and path==path.resolve(),"noncanonical path: "+str(path))
    for p in (path,*path.parents):
        if p.exists():
            need(not (p.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT),"reparse point")
    return path

def hashed(p):
    p=safe(p)
    need(p.is_file() and p.stat().st_size<=128*1024*1024,"missing/oversized file: "+str(p))
    return pf.sha(p)

def tree(root):
    root=safe(root);need(root.is_dir(),"missing tree")
    out={}
    for p in root.rglob("*"):
        safe(p)
        if p.is_file(): out[p.relative_to(root).as_posix()]=hashed(p)
        else: need(p.is_dir(),"special file")
    need(len(out)<=300,"tree limit")
    return out

def load(p): return pf.parse(safe(p).read_bytes())

def atomic(path,value):
    # CC01 canonical JSON, Windows same-directory atomic replace, no power-loss claim.
    path=safe(path);tmp=path.parent/(".tmp-"+uuid.uuid4().hex)
    with tmp.open("xb") as f:
        f.write(b.canonical(value)+b"\n");f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def copy(src,dst,digest):
    need(hashed(src)==digest and not dst.exists(),"source mismatch or destination exists")
    safe(dst);dst.parent.mkdir(parents=True,exist_ok=True)
    with src.open("rb") as f,dst.open("xb") as g: shutil.copyfileobj(f,g)
    need(hashed(dst)==digest,"copy verification")

def verify_original():
    for rel,digest in {**PINS,**EVIDENCE}.items():
        need(hashed(SOURCE/rel)==digest,"original pin mismatch: "+rel)
    cfg=Path(r"P:\buldozer.cfg")
    need(pf.sha(cfg)=="f03f301f887eb590f12b1f53bfd91564c2778022837d9f44d628f56fa70317cc","shared cfg changed")
    need(bool(cfg.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY),"shared cfg writable")
    handoff=load(SOURCE/"TBHandoff/MANIFEST.json")
    for rel,digest in handoff["files"].items(): need(hashed(SOURCE/"TBHandoff"/rel)==digest,"handoff mismatch: "+rel)

def code_pins():
    for name,digest in HELPERS.items():need(hashed(ROOT/name)==digest,"helper pin changed")
    extra={"job_owner.py":"21252163536bf440ab5f84d7ede26459df1dca8f48a0f3cf235f3d175f40c0bf","job_probe.py":"79c52423cf10add491dfe141e8769cbb46291328667f9fd4ec6a726240ba2025"}
    for name,digest in extra.items():need(hashed(ROOT/name)==digest,"job source pin changed")
    return {**HELPERS,**extra,"pipeline_gate.py":hashed(ROOT/"pipeline_gate.py")}

def host_pins():return {"dotnet":hashed(DOTNET),"python":hashed(Path(sys.executable).resolve())}

def init():
    need(not (ROOT/"snapshot.json").exists() and not (ROOT/"snapshot").exists(),"existing snapshot")
    verify_original()
    baseline=tree(SOURCE/"c")
    need(len(baseline)==11 and baseline==tree(SOURCE/"d") and baseline["result.json"]==RESULT,"historic baseline mismatch")
    runtime=SOURCE/"srcCorrected/bin/Release/net10.0";runtime_files=tree(runtime)
    need(runtime_files["GrmAuto.dll"]==DLL,"native DLL pin")
    src=dict(PINS);retained=load(SOURCE/"retained/MANIFEST.json")["files"]
    for s in ("SW","SE","NW","NE"):
        n=s+"_objects.json";src["retained/"+n]=retained[n]
    snapshot=ROOT/"snapshot";snapshot.mkdir()
    for rel,digest in src.items():copy(SOURCE/rel,snapshot/"inputs"/rel,digest)
    for rel,digest in runtime_files.items():copy(runtime/rel,snapshot/"child"/rel,digest)
    m={"marker":MARKER,"code":code_pins(),"host":host_pins(),"files":tree(snapshot),
       "baseline":baseline,"input_files":src,"evidence":EVIDENCE}
    atomic(ROOT/"snapshot.json",m)
    print("INIT",len(m["files"]),"snapshot files; baseline",len(baseline),flush=True)

def validate_snapshot():
    m=load(ROOT/"snapshot.json")
    need(m["marker"]==MARKER and m["code"]==code_pins(),"code/marker changed")
    need(m["host"]==host_pins(),"host executable changed")
    need(m["evidence"]==EVIDENCE and m["baseline"]==tree(SOURCE/"c")==tree(SOURCE/"d"),"evidence/baseline changed")
    need(m["baseline"]["result.json"]==RESULT and m["files"]["child/GrmAuto.dll"]==DLL,"baseline/DLL mismatch")
    need(tree(ROOT/"snapshot")==m["files"],"snapshot mismatch")
    verify_original()
    return m,b.digest(b.canonical(m))

def poses(p):
    out=[]
    with p.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.reader(f,delimiter=";"):
            if not r:continue
            need(len(r)==9 and r[-1]=="","pose schema")
            vals=tuple(Decimal(v) for v in r[1:8]);need(all(v.is_finite() for v in vals),"nonfinite pose")
            out.append((r[0],*vals))
    return out

def verify_export(output,m):
    need(tree(output)==m["baseline"],"native export differs from verified baseline")
    r=load(output/"result.json")
    need(r["scope"]=="synthetic_canonical_export" and r["inputCount"]==r["exported"]==4562 and r["held"]==0 and r["roads"]==2,"native export counts")
    ids=load(output/"placement_ids.json");rows=poses(output/"relative_objects.txt");old=poses(SOURCE/"PoseQC01/native_objects.txt")
    need(len(ids)==len(rows)==len(old)==4562 and len(set(ids))==4562,"ID/pose count")
    need(ids==sorted(ids) and all(re.fullmatch("[0-9a-f]{64}",v) for v in ids),"ID format")
    native={(v[0],v[1],v[2]):v for v in old}
    need(len(native)==4562 and len({v[:3] for v in rows})==4562,"duplicate anchor")
    features=[];max_yaw=Decimal(0)
    for fid,v in zip(ids,rows):
        n=native.get(v[:3]);need(n is not None,"native pose missing")
        need(v[4:]==n[4:],"pitch/roll/scale/elevation mismatch")
        delta=abs((abs(v[3]-n[3])+Decimal(180))%Decimal(360)-Decimal(180))
        need(delta<=Decimal(".001"),"yaw mismatch");max_yaw=max(max_yaw,delta)
        mm=[int(v[i]*1000) for i in (1,2)]
        need(all(Decimal(mm[j])==v[j+1]*1000 for j in (0,1)),"sub-mm coordinates")
        features.append({"id":fid,"kind":"point","points_mm":[mm],"revision":sm.digest([str(x) for x in v])})
    # Diagnostic 8x8 grid in 1920m fixture, not production grid or CRS.
    grid=sm.Grid(8,240000,(200000000,0),30000)
    plan=sm.plan(grid,features,b.digest(b.canonical(m["baseline"])))
    need(not sm.validate_seams(plan),"CC03 metadata seam mismatch")
    owned=[fid for node in plan["sectors"].values() for fid in node["owned_point_ids"]]
    need(len(owned)==4562 and set(owned)==set(ids),"CC03 ownership mismatch")
    return {"status":"PASS","native_export_files":len(m["baseline"]),"objects":len(rows),
        "native_readback_reused":True,"yaw_delta_deg":str(max_yaw),"logical_nodes":len(plan["sectors"]),
        "nonempty_nodes":sum(bool(v["owned_point_ids"]) for v in plan["sectors"].values()),
        "owned_once":len(owned),"seam_metadata_issues":0,"plan_sha256":sm.digest(plan),
        "stages":{"GM_input":"VERIFIED_EXISTING","GRM_export":"PASS","TB_pose":"VERIFIED_EXISTING",
                  "TB_height_1mm":"FAIL_EXISTING","TB_material_fidelity":"PARTIAL",
                  "Buldozer_navigation_vegetation":"VERIFIED_EXISTING","fresh_TB_assembly":"NOT_RUN",
                  "fresh_Buldozer":"NOT_RUN","whole_pipeline":"PARTIAL"}}

def available_ram():
    class MEM(ctypes.Structure):
        _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ("total","avail","total_page","avail_page","total_virtual","avail_virtual","extended")]
    memory=MEM();memory.length=ctypes.sizeof(memory)
    need(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)),"RAM probe failed")
    return memory.avail

def run(fault=""):
    need(fault in jo.FAULTS,"fixed test fault")
    lock=ROOT/"runner.lock";safe(lock)
    with lock.open("a+b") as f:
        if f.seek(0,2)==0:f.write(b"\0");f.flush()
        f.seek(0)
        try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise b.Blocked("runner lock held") from None
        try:
            need(not (ROOT/"stop.request").exists(),"stop requested")
            m,identity=validate_snapshot();current=ROOT/"current.json"
            jo.recover(sys.modules[__name__],m,identity,fault)
            need(not (ROOT/"inflight.json").exists(),"prior attempt unresolved")
            if current.exists():
                old=load(current)
                need(old["identity"]==identity and re.fullmatch("attempt-[0-9a-f]{32}",old["attempt"]),"cached identity mismatch")
                attempt=ROOT/old["attempt"];report=verify_export(attempt/"GRMAUTO04/c",m)
                need(old["report_sha256"]==hashed(attempt/"report.json") and load(attempt/"report.json")==report,"cached report mismatch")
                print("SKIP verified native export",old["attempt"],"objects",report["objects"],flush=True);return
            need(shutil.disk_usage(ROOT).free>=512*1024**2,"low disk space")
            ram=available_ram();need(ram>=8*1024**3,"low RAM")
            need(len(list(ROOT.glob("attempt-*")))<2,"retry budget exhausted")
            attempt=ROOT/("attempt-"+uuid.uuid4().hex);attempt.mkdir()
            stage=attempt/"GRMAUTO04";stage.mkdir()
            for rel,digest in m["input_files"].items():copy(ROOT/"snapshot/inputs"/rel,stage/rel,digest)
            rc,pid,elapsed=jo.execute(sys.modules[__name__],attempt,stage,identity,fault)
            need(rc==0,"native child nonzero exit")
            need(not (ROOT/"stop.request").exists(),"stop before publication")
            need(validate_snapshot()[1]==identity,"input changed")
            for rel,digest in m["input_files"].items():need(hashed(stage/rel)==digest,"staged input changed")
            report=verify_export(stage/"c",m)
            atomic(attempt/"report.json",report)
            atomic(attempt/"execution.json",{"exit_code":rc,"pid":pid,"wall_seconds":elapsed,"available_ram_bytes":ram})
            if fault=="before-publish":
                print("INJECT abrupt worker exit after QC before publication",flush=True);os._exit(73)
            atomic(current,{"identity":identity,"attempt":attempt.name,"report_sha256":hashed(attempt/"report.json")})
            if fault=="after-publish":
                print("INJECT abrupt worker exit after publication",flush=True);os._exit(73)
            jo.archive(sys.modules[__name__],ROOT/"inflight.json","completed")
            print(json.dumps(report,indent=2),flush=True)
        finally:
            f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

if __name__=="__main__":
    try:
        need(sys.platform=="win32" and len(sys.argv) in (2,3) and sys.argv[1] in ("init","run") and (len(sys.argv)==2 or (sys.argv[1]=="run" and sys.argv[2] in jo.FAULTS[1:])),"Windows init or run only")
        need(safe(Path(__file__).parent)==ROOT,"fixed owned directory")
        if sys.argv[1]=="init":init()
        else:run(sys.argv[2] if len(sys.argv)==3 else "")
    except (b.Blocked,OSError,ValueError,TypeError,KeyError,RuntimeError) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
