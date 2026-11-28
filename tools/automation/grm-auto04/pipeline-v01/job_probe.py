"""AUTONOMY-WIN-01: finite synthetic Windows job-tree fault test, no map work."""
import ctypes as C
from ctypes import wintypes as W
import json, os, pathlib, subprocess, sys, time, hashlib
P=pathlib.Path
ROOT=P(r"D:\Zone80\PipelineV01_01\AutonomyWin01")
SCRIPT=ROOT/"job_probe.py"
K=C.WinDLL("kernel32",use_last_error=True)
H=W.HANDLE
D=W.DWORD
S=C.c_size_t
class BASIC(C.Structure):
    _fields_=[("per_process",C.c_longlong),("per_job",C.c_longlong),("flags",D),
        ("min_ws",S),("max_ws",S),("active_limit",D),("affinity",S),("priority",D),("scheduling",D)]
class IO(C.Structure):
    _fields_=[(x,C.c_ulonglong) for x in ("ro","wo","oo","rb","wb","ob")]
class EXT(C.Structure):
    _fields_=[("basic",BASIC),("io",IO),("process_memory",S),("job_memory",S),("peak_process",S),("peak_job",S)]
class SI(C.Structure):
    _fields_=[("cb",D),("reserved",W.LPWSTR),("desktop",W.LPWSTR),("title",W.LPWSTR)]+[(x,D) for x in ("x","y","xs","ys","xc","yc","fill","flags")]+[("show",W.WORD),("reserved2",W.WORD),("ptr",C.c_void_p),("stdin",H),("stdout",H),("stderr",H)]
class SX(C.Structure):_fields_=[("si",SI),("attrs",C.c_void_p)]
class PI(C.Structure):_fields_=[("process",H),("thread",H),("pid",D),("tid",D)]
def bind(name,restype,*args):
    f=getattr(K,name);f.restype=restype;f.argtypes=args;return f
create_job=bind("CreateJobObjectW",H,C.c_void_p,W.LPCWSTR)
set_job=bind("SetInformationJobObject",W.BOOL,H,C.c_int,C.c_void_p,D)
init_attrs=bind("InitializeProcThreadAttributeList",W.BOOL,C.c_void_p,D,D,C.POINTER(S))
update=bind("UpdateProcThreadAttribute",W.BOOL,C.c_void_p,D,S,C.c_void_p,S,C.c_void_p,C.c_void_p)
delete=bind("DeleteProcThreadAttributeList",None,C.c_void_p)
create=bind("CreateProcessW",W.BOOL,W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,D,C.c_void_p,W.LPCWSTR,C.POINTER(SX),C.POINTER(PI))
in_job=bind("IsProcessInJob",W.BOOL,H,H,C.POINTER(W.BOOL))
resume=bind("ResumeThread",D,H)
close=bind("CloseHandle",W.BOOL,H)
wait=bind("WaitForSingleObject",D,H,D)
open_proc=bind("OpenProcess",H,D,W.BOOL,D)
get_times=bind("GetProcessTimes",W.BOOL,H,*([C.POINTER(W.FILETIME)]*4))
current=bind("GetCurrentProcess",H)
get_exit=bind("GetExitCodeProcess",W.BOOL,H,C.POINTER(D))
def req(ok,msg):
    if not ok:raise RuntimeError(msg)
def checked(ok,name):
    if not ok:raise C.WinError(C.get_last_error(),name)
def birth(h):
    a,b,c,d=[W.FILETIME() for _ in range(4)]
    checked(get_times(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d)),"GetProcessTimes")
    return (a.dwHighDateTime<<32)|a.dwLowDateTime
def record(p,o):
    with p.open("x",encoding="ascii") as f:json.dump(o,f,sort_keys=True);f.flush();os.fsync(f.fileno())
def read(p):return json.loads(p.read_text(encoding="ascii"))
def ready(p,seconds=8):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        try:return read(p)
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.03)
    raise RuntimeError("no durable marker: "+p.name)
def argv(mode,case):return [sys.executable,"-B",str(SCRIPT),mode,case]
def pin(p):
    for x in (p,*p.parents):
        if x.exists():req(not x.stat(follow_symlinks=False).st_file_attributes & 0x400,"reparse")
def own_handle(rec):
    h=open_proc(0x100000|0x1000,False,rec["pid"])
    checked(h,"OpenProcess")
    if birth(h)!=rec["birth"]:close(h);raise RuntimeError("PID reuse")
    return h
def start(job,case):
    size=S()
    init_attrs(None,1,0,C.byref(size))
    req(size.value>0,"attribute size")
    attrs=C.create_string_buffer(size.value)
    checked(init_attrs(attrs,1,0,C.byref(size)),"InitializeProcThreadAttributeList")
    try:
        jobs=(H*1)(job)
        checked(update(attrs,0,0x2000D,C.byref(jobs),C.sizeof(jobs),None,None),"JOB_LIST")
        sx=SX();sx.si.cb=C.sizeof(sx);sx.attrs=C.cast(attrs,C.c_void_p)
        pi=PI()
        cmd=C.create_unicode_buffer(subprocess.list2cmdline(argv("child",case)))
        checked(create(sys.executable,cmd,None,None,False,0x80000|0x4|0x08000000,None,str(ROOT/case),C.byref(sx),C.byref(pi)),"CreateProcessW")
        return pi
    finally:delete(attrs)
def supervisor(case):
    r=ROOT/case
    if case=="before-spawn":
        record(r/"before.json",{"pid":os.getpid()});os._exit(73)
    job=create_job(None,None);checked(job,"CreateJobObject")
    pi=None
    try:
        limits=EXT();limits.basic.flags=0x2000 # KILL_ON_JOB_CLOSE, no breakaway
        checked(set_job(job,9,C.byref(limits),C.sizeof(limits)),"SetInformationJobObject")
        pi=start(job,case)
        inside=W.BOOL()
        checked(in_job(pi.process,job,C.byref(inside)),"IsProcessInJob")
        req(inside.value,"child outside own job")
        record(r/"ownership.json",{"pid":pi.pid,"birth":birth(pi.process),"member_before_resume":True})
        if case!="before-resume":
            req(resume(pi.thread)==1,"unexpected suspend count")
            if case=="success":
                req(wait(pi.process,8000)==0,"success child timeout")
                ec=D();checked(get_exit(pi.process,C.byref(ec)),"GetExitCodeProcess")
                req(ec.value==0,"child exit")
                record(r/"exit.json",{"exit_code":0})
                return
            descendant=ready(r/"descendant.json")
            h=own_handle(descendant)
            try:
                checked(in_job(h,job,C.byref(inside)),"descendant membership")
                req(inside.value,"descendant outside job")
                record(r/"tree.json",{"member":True})
            finally:close(h)
        # Parent pins exact process handles before allowing injected fault.
        ready(r/"release.json")
        if case=="timeout":
            # Simulated bounded timeout policy on exclusively owned synthetic job.
            req(wait(pi.process,200)==258,"expected timeout")
            record(r/"timeout.json",{"wait":"WAIT_TIMEOUT"})
            return
        os._exit(73) # actual abrupt exit: OS closes sole noninherited job handle
    finally:
        close(job)
        if pi:
            close(pi.thread);close(pi.process)
def child(case):
    r=ROOT/case
    record(r/"child.json",{"pid":os.getpid(),"birth":birth(current())})
    if case=="success":
        record(r/"artifact.json",{"fixture":"ok"});return
    subprocess.Popen(argv("descendant",case),cwd=r,close_fds=True)
    time.sleep(12) # bounded independent lifetime, even if job semantics fail
def descendant(case):
    record(ROOT/case/"descendant.json",{"pid":os.getpid(),"birth":birth(current())})
    time.sleep(12)
def test():
    accepted=ROOT.parent/"current.json";before=accepted.read_bytes()
    cfg=P(r"P:\buldozer.cfg");cfg_before=hashlib.sha256(cfg.read_bytes()).hexdigest()
    results={}
    for case in ("before-spawn","before-resume","during-child","timeout","success"):
        r=ROOT/case;r.mkdir()
        handles=[]
        with (r/"supervisor.log").open("xb") as log:
            p=subprocess.Popen(argv("supervisor",case),cwd=r,stdout=log,stderr=log)
            try:
                if case in ("before-resume","during-child","timeout"):
                    rec=ready(r/"ownership.json");req(rec["member_before_resume"],"pre-resume proof")
                    handles.append(own_handle(rec))
                    if case!="before-resume":
                        req(ready(r/"tree.json")["member"],"tree proof")
                        handles.append(own_handle(ready(r/"descendant.json")))
                    req(all(wait(h,0)==258 for h in handles),"child not live at injection")
                    record(r/"release.json",{"inject":True})
                code=p.wait(timeout=20)
                req(code==(73 if case.startswith("before-") or case=="during-child" else 0),"unexpected supervisor code "+str(code))
                req(all(wait(h,5000)==0 for h in handles),"owned child still live")
                if case=="before-spawn":req(not (r/"ownership.json").exists(),"unexpected spawn")
                if case=="before-resume":req(not (r/"child.json").exists(),"suspended code ran")
                if case=="timeout":req(read(r/"timeout.json")["wait"]=="WAIT_TIMEOUT","timeout proof")
                if case=="success":req(read(r/"exit.json")["exit_code"]==0 and read(r/"artifact.json")=={"fixture":"ok"},"output QC")
                req(accepted.read_bytes()==before,"accepted pointer changed")
                results[case]={"exit":code,"verified_exited_handles":len(handles),"pass":True}
                print("PASS",case,results[case],flush=True)
            finally:
                for h in handles:close(h)
                # No external termination: fixed supervisor and children have bounded waits.
    req(hashlib.sha256(cfg.read_bytes()).hexdigest()==cfg_before,"shared cfg changed")
    record(ROOT/"result.json",{"scope":"synthetic_only","results":results,"accepted_unchanged":True})
if __name__=="__main__":
    req(sys.platform=="win32" and C.sizeof(H)==8 and P(__file__).resolve()==SCRIPT,"fixed x64 Windows fixture")
    pin(ROOT)
    if len(sys.argv)==1:test()
    else:
        req(len(sys.argv)==3 and sys.argv[1] in ("supervisor","child","descendant") and sys.argv[2] in ("before-spawn","before-resume","during-child","timeout","success"),"fixed test mode")
        {"supervisor":supervisor,"child":child,"descendant":descendant}[sys.argv[1]](sys.argv[2])
