"""Resume the existing fixed Windows fixture; no new scheduler or native permissions.

Recover only an already completed GRM child with durable exit-0 and independently
verified outputs. Unknown/live child, unfinished handoff, or changed pins STOP.
"""
import ctypes
from ctypes import wintypes
import contextlib
import msvcrt
import os
from pathlib import Path
import re
import sys
import uuid
import pipeline_gate as g
import handoff_gate as h
import cc01_base as b

ROOT=g.ROOT

@contextlib.contextmanager
def lock():
    p=g.safe(ROOT/"runner.lock")
    g.need(p.is_file(),"existing runner lock required")
    with p.open("r+b") as f:
        f.seek(0)
        try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise b.Blocked("runner lock held") from None
        try:yield
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def pid_gone(pid):
    # No kill, no inference from PID age. Reused/live PID or access denied => refuse.
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    k.WaitForSingleObject.restype=wintypes.DWORD
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.CloseHandle.restype=wintypes.BOOL
    handle=k.OpenProcess(0x100000,False,pid) # SYNCHRONIZE
    if not handle:return ctypes.get_last_error()==87 # nonexistent PID
    try:return k.WaitForSingleObject(handle,0)==0 # signalled/exited
    finally:k.CloseHandle(handle)

def marker_valid(rec,identity):
    return (type(rec) is dict and set(rec)=={"attempt","identity","status","pid","utc"}
            and rec["identity"]==identity and rec["status"]=="RUNNING"
            and type(rec["pid"]) is int and 0<rec["pid"]<2**32
            and isinstance(rec["utc"],str) and bool(rec["utc"])
            and isinstance(rec["attempt"],str)
            and bool(re.fullmatch("attempt-[0-9a-f]{32}",rec["attempt"])))

def recover_locked():
    g.need(not (ROOT/"stop.request").exists(),"stop requested")
    marker=g.safe(ROOT/"inflight.json")
    if not marker.exists():return False
    m,identity=g.validate_snapshot()
    rec=g.load(marker)
    g.need(marker_valid(rec,identity),"unknown or incomplete attempt marker")
    attempt=g.safe(ROOT/rec["attempt"])
    execution=g.load(attempt/"execution.json")
    g.need(type(execution) is dict and type(execution.get("exit_code")) is int
           and execution["exit_code"]==0 and execution.get("pid")==rec["pid"],
           "no matching durable successful exit evidence")
    g.need(pid_gone(rec["pid"]),"child live, PID reused, or ownership uncertain")
    for rel,digest in m["input_files"].items():
        g.need(g.hashed(attempt/"GRMAUTO04"/rel)==digest,"staged input changed")
    report=g.verify_export(attempt/"GRMAUTO04/c",m)
    g.need(g.load(attempt/"report.json")==report,"report differs from independent QC")
    current=g.safe(ROOT/"current.json")
    pointer={"identity":identity,"attempt":rec["attempt"],
             "report_sha256":g.hashed(attempt/"report.json")}
    if current.exists():
        g.need(g.load(current)==pointer,"different accepted output; preserve it")
    g.need(not (ROOT/"stop.request").exists(),"stop before recovery")
    if not current.exists():g.atomic(current,pointer)
    # A crash after publication but before rename remains recoverable.
    archive=g.safe(ROOT/("recovered-"+uuid.uuid4().hex+".json"))
    os.rename(marker,archive)
    print("RECOVER verified completed GRM",rec["attempt"],archive.name,flush=True)
    return True

def main():
    g.need(sys.platform=="win32" and g.safe(Path(__file__).parent)==ROOT,"fixed Windows fixture only")
    with lock():recover_locked()
    # Existing stages retain their own exclusive lock, validation, and stop gates.
    g.run()
    with lock():h.main()
    print("PASS existing GRM + handoff; further TB steps not automated here",flush=True)

if __name__=="__main__":
    try:main()
    except (b.Blocked,OSError,ValueError,TypeError,KeyError) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
