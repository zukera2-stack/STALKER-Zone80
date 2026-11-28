"""Fixed native GRM candidate: Windows process ownership + journal recovery.
Not a general launcher. Use only in PipelineV01_02 via the pinned candidate worker.
"""
import ctypes as C
from ctypes import wintypes as W
import msvcrt, os, re, subprocess, time, sys
from pathlib import Path
import job_probe as j
from job_probe import H,D,S
ROOT=Path(r"D:\Zone80\PipelineV01_02")
DOTNET=Path(r"C:\Program Files\dotnet\dotnet.exe")
PROTOCOL="win-job-list-v1"
FAULTS=("", "during-child", "before-publish", "after-publish")
open_job=j.bind("OpenJobObjectW",H,D,W.BOOL,W.LPCWSTR)
query=j.bind("QueryInformationJobObject",W.BOOL,H,C.c_int,C.c_void_p,D,C.POINTER(D))
class ACCOUNT(C.Structure):
    _fields_=[(x,C.c_longlong) for x in ("user","kernel","period_user","period_kernel")]+[(x,D) for x in ("faults","total","active","terminated")]
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def owner_gone(pid):
    h=j.open_proc(0x100000,False,pid)
    if not h:return C.get_last_error()==87
    try:return j.wait(h,0)==0
    finally:j.close(h)
def name(attempt):
    require(re.fullmatch("attempt-[0-9a-f]{32}",attempt),"attempt name")
    return "Global\\Zone80_GRM_Job_"+attempt[8:]
def absent(jobname):
    h=open_job(4,False,jobname) # JOB_OBJECT_QUERY only
    if not h:return C.get_last_error()==2
    j.close(h);return False
def wait_absent(jobname):
    until=time.monotonic()+5
    while time.monotonic()<until:
        if absent(jobname):return
        time.sleep(.05)
    require(absent(jobname),"job still exists or query denied; preserve journal")
def active(job):
    acc=ACCOUNT()
    j.checked(query(job,1,C.byref(acc),C.sizeof(acc),None),"QueryInformationJobObject")
    return acc.active
def checkpoint(g,attempt,identity):
    require(g.ROOT==ROOT,"fixed candidate")
    rec={"protocol":PROTOCOL,"attempt":attempt.name,"identity":identity,
         "status":"RUNNING","owner_pid":os.getpid(),"owner_birth":j.birth(j.current()),
         "job":name(attempt.name),"utc":g.b.now()}
    g.atomic(ROOT/"inflight.json",rec)
    return rec
def create_child(job,argv,cwd,handles):
    size=S()
    j.init_attrs(None,2,0,C.byref(size))
    require(size.value>0,"attribute size")
    attrs=C.create_string_buffer(size.value)
    j.checked(j.init_attrs(attrs,2,0,C.byref(size)),"InitializeProcThreadAttributeList")
    try:
        jobs=(H*1)(job)
        std=(H*3)(*handles)
        j.checked(j.update(attrs,0,0x2000D,C.byref(jobs),C.sizeof(jobs),None,None),"JOB_LIST")
        j.checked(j.update(attrs,0,0x20002,C.byref(std),C.sizeof(std),None,None),"HANDLE_LIST")
        sx=j.SX();sx.si.cb=C.sizeof(sx);sx.attrs=C.cast(attrs,C.c_void_p)
        sx.si.flags=0x100; sx.si.stdin,sx.si.stdout,sx.si.stderr=handles
        pi=j.PI()
        cmd=C.create_unicode_buffer(subprocess.list2cmdline(argv))
        j.checked(j.create(str(DOTNET),cmd,None,None,True,0x80000|0x4|0x08000000,None,str(cwd),C.byref(sx),C.byref(pi)),"CreateProcessW")
        return pi
    finally:j.delete(attrs)
def execute(g,attempt,stage,identity,fault):
    require(g.ROOT==ROOT and stage==attempt/"GRMAUTO04" and fault in FAULTS,"fixed scope")
    rec=checkpoint(g,attempt,identity)
    job=None;pi=None
    start=time.monotonic()
    try:
        C.set_last_error(0)
        job=j.create_job(None,rec["job"])
        j.checked(job,"CreateJobObject")
        require(C.get_last_error()!=183,"job name collision")
        lim=j.EXT();lim.basic.flags=0x2000
        j.checked(j.set_job(job,9,C.byref(lim),C.sizeof(lim)),"SetInformationJobObject")
        argv=[str(DOTNET),str(ROOT/"snapshot/child/GrmAuto.dll"),str(stage),"c"]
        with open(os.devnull,"rb") as inp,(attempt/"stdout.log").open("xb") as out,(attempt/"stderr.log").open("xb") as err:
            handles=[msvcrt.get_osfhandle(f.fileno()) for f in (inp,out,err)]
            try:
                for h in handles:os.set_handle_inheritable(h,True)
                pi=create_child(job,argv,stage,handles)
            finally:
                for h in handles:os.set_handle_inheritable(h,False)
            inside=W.BOOL()
            j.checked(j.in_job(pi.process,job,C.byref(inside)),"IsProcessInJob")
            require(inside.value and active(job)==1,"membership before resume")
            rec.update(pid=int(pi.pid),birth=j.birth(pi.process))
            g.atomic(ROOT/"inflight.json",rec)
            require(j.resume(pi.thread)==1,"resume count")
            if fault=="during-child":
                require(j.wait(pi.process,0)==258,"fault child not live")
                print("INJECT abrupt worker exit with live native GRM child",flush=True)
                os._exit(73)
            while True:
                w=j.wait(pi.process,50)
                if w==0:break
                require(w==258,"wait error")
                require(not (ROOT/"stop.request").exists(),"stop during native child")
                require(time.monotonic()-start<45,"native timeout")
            ec=D();j.checked(j.get_exit(pi.process,C.byref(ec)),"GetExitCodeProcess")
            require(active(job)==0,"descendant still running after leader exit")
            rc=ec.value
    finally:
        if job:j.close(job)
        if pi:j.close(pi.thread);j.close(pi.process)
    wait_absent(rec["job"])
    return rc,rec["pid"],time.monotonic()-start
def archive(g,marker,label):
    dest=marker.parent/(label+"-"+g.load(marker)["attempt"]+".json")
    require(not dest.exists(),"journal archive exists")
    os.rename(marker,dest)
def recover(g,m,identity,fault):
    marker=ROOT/"inflight.json"
    if not marker.exists():return
    rec=g.load(marker)
    keys={"protocol","attempt","identity","status","owner_pid","owner_birth","job","utc","pid","birth"}
    # Before child identity is durable, outcome is uncertain; do not auto-retry that gap.
    require(type(rec) is dict and set(rec)==keys and rec["protocol"]==PROTOCOL and rec["identity"]==identity and rec["status"]=="RUNNING","unrecognized/incomplete journal")
    require(rec["job"]==name(rec["attempt"]) and all(type(rec[k]) is int and rec[k]>0 for k in ("owner_pid","owner_birth","pid","birth")),"invalid ownership")
    require(owner_gone(rec["owner_pid"]),"previous owner live or PID reused")
    wait_absent(rec["job"])
    require(owner_gone(rec["pid"]),"previous child live or PID reused")
    attempt=g.safe(ROOT/rec["attempt"])
    current=ROOT/"current.json"
    if (attempt/"execution.json").exists() and (attempt/"report.json").exists():
        e=g.load(attempt/"execution.json")
        require(e["exit_code"]==0 and e["pid"]==rec["pid"],"exit evidence mismatch")
        for rel,digest in m["input_files"].items():
            require(g.hashed(attempt/"GRMAUTO04"/rel)==digest,"staged input changed")
        report=g.verify_export(attempt/"GRMAUTO04/c",m)
        require(g.load(attempt/"report.json")==report,"recovery report mismatch")
        pointer={"identity":identity,"attempt":attempt.name,"report_sha256":g.hashed(attempt/"report.json")}
        require(not (ROOT/"stop.request").exists(),"stop before recovery publish")
        if current.exists():require(g.load(current)==pointer,"different accepted output")
        else:g.atomic(current,pointer)
        if fault=="after-publish":
            print("INJECT abrupt worker exit after recovery publication",flush=True)
            os._exit(73)
        archive(g,marker,"recovered")
        print("RECOVER verified complete native result",attempt.name,flush=True)
    else:
        require(not current.exists(),"accepted output exists; preserve unresolved journal")
        require(not (attempt/"execution.json").exists(),"inconsistent exit evidence")
        require(len(list(ROOT.glob("attempt-*")))<2,"retry budget exhausted")
        archive(g,marker,"interrupted")
        print("RECOVER interrupted owned job; one bounded retry permitted",attempt.name,flush=True)
