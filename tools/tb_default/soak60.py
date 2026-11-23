#!/usr/bin/env python3
"""TB-UIA-02: bounded read-only Windows UIA soak; never starts Terrain Builder.

Offline mode is platform-independent. Windows mode runs only the *existing*
read-only DefaultLauncher(status) and UiaInventory(uia-inventory) programs,
under a private kill-on-close Windows Job Object. No input/UIA actions.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import statistics
import sys
import time
import uuid
from ctypes import wintypes
from pathlib import Path

# Unit tests load this file by path, so the sibling module needs an explicit path.
_THIS_DIR = str(Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
from soak_evidence import EvidenceSession, recover_run

EXPECTED_HASH = '69470C7FB029C5D63F849FDDB197DCE715ED219F7AE08BEC132472FF333A7AC7'
PARENT_DESKTOP = r'WinSta0\Default'
CYCLES, PERIOD, INVENTORY_EVERY = 120, 30, 10
ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / 'reports' / 'TB-UIA-03'
EDITOR_RE = re.compile(r'editorWindow=True; dialogObserved=False; uia=True; responding=True')
RUNTIME_ID_RE = re.compile(r'^-?[0-9]+(?:\.-?[0-9]+)*$')
METRIC_RE = re.compile(r'WS=(\d+); private=(\d+); responding=(True|False)')
HWND_RE = re.compile(
    r'^HWND=0x([0-9A-Fa-f]+); class=wxWindowClassNR; visible=True; enabled=True; '
    r'minimized=(?:True|False); title=Terrain Builder(?: - [^\r\n]+)?$', re.MULTILINE)

class Blocked(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def under_reports(path: Path, base: Path = REPORTS) -> Path:
    out = path.resolve()
    # Use only the old data root or the new evidence-hardening sandbox.
    roots=(base.resolve(),(ROOT/'reports'/'TB-UIA-06').resolve())
    if not any(out==root or root in out.parents for root in roots):
        raise Blocked('output outside approved TB-UIA reports roots')
    return out


def unique_dir(base: Path) -> Path:
    root = under_reports(base)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / uuid.uuid4().hex
    dest.mkdir(exist_ok=False)
    return dest


def canonical_candidate(node: dict, pid: int) -> bool:
    return (node.get('pid') == pid and node.get('name') == 'Import terrain...'
            and node.get('type') == 'ControlType.Button'
            and node.get('enabled') is True
            and 'InvokePatternIdentifiers.Pattern' in node.get('patterns', [])
            and bool(node.get('hwnd')))


def validate_inventory(nodes: list[dict], pid: int, main_hwnd: int | None = None) -> dict:
    if not nodes or any(n.get('pid') != pid for n in nodes):
        raise Blocked('UIA cross-process node or empty inventory')
    if main_hwnd is not None and any(n.get('hwnd') != main_hwnd for n in nodes):
        raise Blocked('UIA HWND mismatch')
    if any(n.get('name') == 'TerrainBuilder Error' or n.get('type') == 'ControlType.Window'
           and 'Error' in str(n.get('name', '')) for n in nodes):
        raise Blocked('unexpected UIA error dialog')
    candidates = [n for n in nodes if n.get('name') == 'Import terrain...']
    if len(candidates) != 1:
        raise Blocked('Import terrain selector not unique')
    if not canonical_candidate(candidates[0], pid):
        raise Blocked('Import terrain not enabled/invokable/owned')
    if not any(n.get('name') == 'Ready' for n in nodes):
        raise Blocked('Ready absent in UIA inventory')
    return {'candidate': {'name': candidates[0]['name'],
                          'type': candidates[0]['type'],
                          'automationId': candidates[0].get('automationId', ''),
                          'patterns': candidates[0]['patterns']},
            'nodes': len(nodes)}


def parse_inventory(text: str) -> list[dict]:
    nodes = []
    for line in text.splitlines():
        if not line.startswith('{'):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Blocked('corrupt UIA JSONL') from exc
        if {'pid', 'hwnd', 'id', 'patterns', 'type'}.issubset(obj):
            if not RUNTIME_ID_RE.fullmatch(str(obj['id'])):
                raise Blocked('unexpected runtime id serialization')
            nodes.append(obj)
    return nodes


def status_metrics(text: str) -> dict:
    match = METRIC_RE.search(text)
    if not match:
        raise Blocked('memory/response metrics absent from status log')
    if match.group(3) != 'True':
        raise Blocked('Terrain Builder not responding')
    return {'workingSetBytes':int(match.group(1)), 'privateBytes':int(match.group(2))}


def status_hwnd(text: str) -> int:
    matches = HWND_RE.findall(text)
    if len(matches) != 1:
        raise Blocked('main Terrain Builder HWND absent/ambiguous')
    return int(matches[0], 16)


def sample_plan(cycles: int = CYCLES, every: int = INVENTORY_EVERY) -> list[tuple[int, bool]]:
    if cycles <= 0 or every <= 0 or cycles % every:
        raise ValueError('invalid monitoring schedule')
    return [(i, i % every == 0) for i in range(1, cycles+1)]


def validate_status(text: str, pid: int) -> None:
    if f'verified pid={pid};' not in text:
        raise Blocked('status lacks verified PID')
    if not EDITOR_RE.search(text):
        raise Blocked('status missing responsive editor/no-dialog evidence')
    if 'name=Ready' not in text or 'Application initialization finished.' not in text:
        raise Blocked('status missing initialisation evidence')


def make_fixture(base: Path) -> dict:
    """Reproduce documented GRM-01 synthetic contract, not an Arma/TB import."""
    root = under_reports(base)
    root.mkdir(parents=True, exist_ok=False)
    def heights(col_offset):
        return [[-9999 if r == 4 and col_offset+c in (31, 32)
                 else 100 + 2*r + abs(col_offset+c-31.5)*.5
                 for c in range(32)] for r in range(32)]
    west, east = heights(0), heights(32)
    merged = [w+e for w,e in zip(west,east)]
    def write_asc(path, rows):
        content = (f'ncols {len(rows[0])}\nnrows {len(rows)}\nxllcorner 200000\n'
                   'yllcorner 0\ncellsize 8\nNODATA_value -9999\n')
        content += ''.join(' '.join(str(v) for v in row)+'\n' for row in rows)
        path.write_text(content, encoding='ascii', newline='\n')
    for name, rows in [('W.asc',west), ('E.asc',east), ('merged.asc',merged)]:
        write_asc(root/name, rows)
    control = [{'id':'west','x':32,'y':48,'mode':'absolute'},
               {'id':'east','x':480,'y':72,'mode':'relative'},
               {'id':'seam','x':256,'y':80,'mode':'relative'},
               {'id':'outer','x':512,'y':256,'mode':'absolute'}]
    (root/'objects.json').write_text(json.dumps(control,indent=2)+'\n',encoding='utf-8')
    return verify_fixture(root)


def verify_fixture(root: Path) -> dict:
    def read(name: str, columns: int) -> list[list[float]]:
        lines = (root/name).read_text(encoding='ascii').splitlines()
        expected = [f'ncols {columns}', 'nrows 32','xllcorner 200000',
                    'yllcorner 0','cellsize 8','NODATA_value -9999']
        if lines[:6] != expected or len(lines) != 38:
            raise Blocked('ASC header or dimensions differ')
        import math
        grid = [list(map(float,l.split())) for l in lines[6:]]
        if any(len(row)!=columns or not all(math.isfinite(v) for v in row) for row in grid):
            raise Blocked('ASC values invalid')
        return grid
    w,e,combined=read('W.asc',32),read('E.asc',32),read('merged.asc',64)
    if any(w[r]+e[r]!=combined[r] for r in range(32)):
        raise Blocked('ASC merged values mismatch')
    if any(w[r][31]!=e[r][0] for r in range(32)):
        raise Blocked('ASC sector seam mismatch')
    nodata={(r,c) for r,row in enumerate(combined) for c,val in enumerate(row) if val == -9999}
    if nodata != {(4,31),(4,32)}:
        raise Blocked('ASC NoData mask mismatch')
    controls=json.loads((root/'objects.json').read_text(encoding='utf-8'))
    truth={'west':(32,48,'absolute'),'east':(480,72,'relative'),
           'seam':(256,80,'relative'),'outer':(512,256,'absolute')}
    if len(controls)!=4 or len({o['id'] for o in controls})!=4:
        raise Blocked('duplicate or missing fixture objects')
    if {o['id']:(o['x'],o['y'],o['mode']) for o in controls}!=truth:
        raise Blocked('invalid control coordinates/modes')
    if [200000+4+8*c for c in (31,32)]!=[200252,200260]:
        raise Blocked('invalid cell center convention')
    return {'rows':32,'columns':64,'cell_m':8,'shift_x_m':200000,
            'nodata_cells':sorted([list(v) for v in nodata]),
            'control_points':len(controls),
            'sha256':{p.name:sha256(p) for p in sorted(root.iterdir()) if p.is_file()}}


# Minimal Windows process isolation. CreateProcessW is suspended until it is
# assigned to our own kill-on-close Job Object. The ONLY executables launched
# here are the two approved diagnostic helpers (and a bounded built-in whoami.exe
# job-smoke), never TerrainBuilder.exe.
def run_in_job(exe: Path, args: list[str], timeout_ms: int, *, protected_pid=None, emit=print) -> int:
    if os.name != 'nt':
        raise Blocked('Windows runtime unavailable: NOT RUN')
    import subprocess
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    class STARTUPINFO(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('lpReserved',wintypes.LPWSTR),
                 ('lpDesktop',wintypes.LPWSTR),('lpTitle',wintypes.LPWSTR),
                 ('dwX',wintypes.DWORD),('dwY',wintypes.DWORD),('dwXSize',wintypes.DWORD),
                 ('dwYSize',wintypes.DWORD),('dwXCountChars',wintypes.DWORD),
                 ('dwYCountChars',wintypes.DWORD),('dwFillAttribute',wintypes.DWORD),
                 ('dwFlags',wintypes.DWORD),('wShowWindow',wintypes.WORD),
                 ('cbReserved2',wintypes.WORD),('lpReserved2',ctypes.c_void_p),
                 ('hStdInput',wintypes.HANDLE),('hStdOutput',wintypes.HANDLE),
                 ('hStdError',wintypes.HANDLE)]
    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_=[('hProcess',wintypes.HANDLE),('hThread',wintypes.HANDLE),
                  ('dwProcessId',wintypes.DWORD),('dwThreadId',wintypes.DWORD)]
    class IO_COUNTERS(ctypes.Structure):
        _fields_=[(n,ctypes.c_ulonglong) for n in ('ReadOperationCount','WriteOperationCount',
                 'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
    class BASIC_LIMIT(ctypes.Structure):
        _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
                  ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
                  ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
                  ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),
                  ('SchedulingClass',wintypes.DWORD)]
    class EXTENDED_LIMIT(ctypes.Structure):
        _fields_=[('BasicLimitInformation',BASIC_LIMIT),('IoInfo',IO_COUNTERS),
                  ('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),
                  ('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
    k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
    k.CreateJobObjectW.restype=wintypes.HANDLE
    k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    k.SetInformationJobObject.restype=wintypes.BOOL
    k.CreateProcessW.argtypes=[wintypes.LPCWSTR,wintypes.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,
                               wintypes.BOOL,wintypes.DWORD,ctypes.c_void_p,wintypes.LPCWSTR,
                               ctypes.POINTER(STARTUPINFO),ctypes.POINTER(PROCESS_INFORMATION)]
    k.CreateProcessW.restype=wintypes.BOOL
    k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    k.AssignProcessToJobObject.restype=wintypes.BOOL
    k.ResumeThread.argtypes=[wintypes.HANDLE];k.ResumeThread.restype=wintypes.DWORD
    k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    k.WaitForSingleObject.restype=wintypes.DWORD
    k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    k.GetExitCodeProcess.restype=wintypes.BOOL
    k.TerminateJobObject.argtypes=[wintypes.HANDLE,wintypes.UINT]
    k.TerminateJobObject.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
    k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
    k.TerminateProcess.restype=wintypes.BOOL
    k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.c_void_p]*4
    k.GetProcessTimes.restype=wintypes.BOOL
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
    k.IsProcessInJob.restype=wintypes.BOOL
    p=PROCESS_INFORMATION()
    limit=EXTENDED_LIMIT()
    limit.BasicLimitInformation.LimitFlags=0x2000
    si=STARTUPINFO()
    si.cb=ctypes.sizeof(si)
    command=ctypes.create_unicode_buffer(subprocess.list2cmdline([str(exe),*args]))

    def require(ok, api):
        if not ok:
            raise Blocked(f'{api} Win32={ctypes.get_last_error()}')

    def job_create():
        job=k.CreateJobObjectW(None,None)
        require(job,'CreateJobObjectW')
        return job

    def setup(job):
        require(k.SetInformationJobObject(job,9,ctypes.byref(limit),ctypes.sizeof(limit)),
                'SetInformationJobObject')
        if protected_pid is not None:
            target=k.OpenProcess(0x1000,False,protected_pid)
            require(target,'OpenProcess(Terrain Builder, query only)')
            try:
                member=wintypes.BOOL()
                require(k.IsProcessInJob(target,job,ctypes.byref(member)),'IsProcessInJob(Terrain Builder)')
                if member.value:
                    raise Blocked('Terrain Builder belongs to diagnostic job')
                emit(f'protectedPid={protected_pid} inDiagnosticJob=false')
            finally:
                k.CloseHandle(target)

    def create():
        require(k.CreateProcessW(str(exe),command,None,None,False,0x4|0x08000000,None,
                                 str(exe.parent),ctypes.byref(si),ctypes.byref(p)), 'CreateProcessW')

    def identity():
        timestamps=[ctypes.c_ulonglong() for _ in range(4)]
        require(k.GetProcessTimes(p.hProcess,*(ctypes.byref(t) for t in timestamps)), 'GetProcessTimes')
        return f'pid={p.dwProcessId} startUtcTicks={timestamps[0].value+504911232000000000}'

    def exit_code():
        code=wintypes.DWORD()
        require(k.GetExitCodeProcess(p.hProcess,ctypes.byref(code)),'GetExitCodeProcess')
        return code.value

    def wait(ms):
        result=k.WaitForSingleObject(p.hProcess,ms)
        require(result!=0xffffffff,'WaitForSingleObject')
        return result

    def close_job(job):
        require(k.CloseHandle(job),'CloseHandle(job)')

    return job_lifecycle(job_create, setup, create, identity,
        lambda job: require(k.AssignProcessToJobObject(job,p.hProcess),'AssignProcessToJobObject'),
        lambda: require(k.ResumeThread(p.hThread)==1,'ResumeThread'),
        wait, exit_code, close_job,
        lambda: require(k.TerminateProcess(p.hProcess,0xE2),'TerminateProcess(owned suspended child)'),
        lambda: (k.CloseHandle(p.hThread), k.CloseHandle(p.hProcess)),
        timeout_ms, emit)


def job_lifecycle(new_job, setup, create, identity, assign, resume, wait, exit_code,
                  close_job, terminate_suspended, close_child, timeout_ms, emit):
    """Own handles by construction; never terminate a process obtained by PID."""
    job = new_job()
    created = assigned = resumed = finished = False
    child = 'identity unavailable'
    try:
        setup(job)
        create()
        created = True
        child = identity()
        emit(f'{child} created=true assigned=false resumed=false')
        assign(job)
        assigned = True
        emit(f'{child} assigned=true')
        resume()
        resumed = True
        emit(f'{child} resumed=true')
        outcome = wait(timeout_ms)
        if outcome != 0:
            raise Blocked(f'diagnostic wait outcome={outcome}')
        code = exit_code()
        finished = True
        emit(f'{child} exit={code}')
        return code
    finally:
        try:
            if created and not finished:
                try:
                    if assigned:
                        close_job(job)
                        job = None
                    else:
                        try:
                            terminate_suspended()
                        except Blocked:
                            if wait(0) != 0:
                                raise
                    if wait(3000) != 0:
                        raise Blocked('owned child did not signal exit')
                    code = exit_code()
                except Exception as exc:
                    raise Blocked(f'UNCONFIRMED CLEANUP {child}: {exc}') from exc
                emit(f'{child} cleanup=confirmed exit={code} assigned={assigned} resumed={resumed}')
        finally:
            try:
                if job is not None:
                    close_job(job)
            finally:
                if created:
                    close_child()


def process_identity(pid: int, exe: Path, sha: str, ticks: int) -> dict:
    if os.name != 'nt': raise Blocked('no Windows process access: NOT RUN')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    k.CloseHandle.argtypes=[wintypes.HANDLE];k.CloseHandle.restype=wintypes.BOOL
    k.GetProcessTimes.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
    k.GetProcessTimes.restype=wintypes.BOOL
    k.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype=wintypes.BOOL
    h=k.OpenProcess(0x1000,False,pid)
    if not h: raise Blocked(f'Terrain Builder PID absent/access denied Win32={ctypes.get_last_error()}')
    try:
        created=ctypes.c_ulonglong(0);exit_time=ctypes.c_ulonglong(0)
        kernel=ctypes.c_ulonglong(0);user=ctypes.c_ulonglong(0)
        if not k.GetProcessTimes(h,ctypes.byref(created),ctypes.byref(exit_time),ctypes.byref(kernel),ctypes.byref(user)):
            raise Blocked('GetProcessTimes failed')
        actual=created.value+504911232000000000
        if actual!=ticks: raise Blocked(f'PID reuse/start ticks mismatch actual={actual}')
        buf=ctypes.create_unicode_buffer(32768);n=wintypes.DWORD(len(buf))
        if not k.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(n)):
            raise Blocked('QueryFullProcessImageNameW failed')
        path=Path(buf.value)
        if os.path.normcase(str(path.resolve()))!=os.path.normcase(str(exe.resolve())):
            raise Blocked('Terrain Builder executable path mismatch')
        if sha256(path)!=sha: raise Blocked('Terrain Builder executable SHA mismatch')
        handles=wintypes.DWORD(0)
        k.GetProcessHandleCount.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        k.GetProcessHandleCount.restype=wintypes.BOOL
        if not k.GetProcessHandleCount(h,ctypes.byref(handles)):
            raise Blocked('GetProcessHandleCount failed')
        return {'pid':pid,'utcTicks':actual,'handles':handles.value,
                'cpu100ns':int(kernel.value+user.value)}
    finally: k.CloseHandle(h)


def diagnostic(exe: Path, args: list[str], runroot: Path, limit_ms: int) -> tuple[int,str,str]:
    existing={p.name for p in exe.parent.iterdir() if p.is_dir()}
    code=run_in_job(exe,args,limit_ms,protected_pid=int(args[1]))
    newer=[p for p in exe.parent.iterdir() if p.is_dir() and p.name not in existing]
    if len(newer)!=1 or not newer[0].parent==runroot:
        raise Blocked('diagnostic evidence directory missing or ambiguous')
    parent=(newer[0]/'PARENT.log').read_text(encoding='utf-8',errors='replace')
    child=(newer[0]/'CHILD.log').read_text(encoding='utf-8',errors='replace')
    return code,parent,child


def soak(pid:int,ticks:int,exe:Path,launcher:Path,inventory:Path,outbase:Path,
         launcher_sha:str,inventory_sha:str,
         cycles:int=CYCLES,period:int=PERIOD,snapshot_every:int=INVENTORY_EVERY) -> Path:
    """One continuous read-only attempt; every completed cycle is checkpointed."""
    if os.name!='nt': raise Blocked('real SOAK requires Windows Default desktop: NOT RUN')
    if pid<=0 or ticks<=0 or cycles!=120 or period!=30 or snapshot_every!=10:
        raise Blocked('SOAK-60 parameters must remain 120x30sec, 12 UIA snapshots')
    if not exe.is_file() or sha256(exe)!=EXPECTED_HASH:
        raise Blocked('Terrain Builder executable not verified')
    if any(not x.is_file() for x in (launcher,inventory)):
        raise Blocked('required compiled diagnostic helper absent')
    if launcher.name.lower() != 'defaultlauncher.exe' or inventory.name.lower() != 'uiainventory.exe':
        raise Blocked('non-allowlisted diagnostic helper name')
    if sha256(launcher) != launcher_sha.upper() or sha256(inventory) != inventory_sha.upper():
        raise Blocked('diagnostic helper hash mismatch')

    runroot=unique_dir(outbase)
    runtime=runroot/'runtime';runtime.mkdir()
    copy_launcher=runtime/'DefaultLauncher.exe';copy_uia=runtime/'UiaInventory.exe'
    shutil.copy2(launcher,copy_launcher);shutil.copy2(inventory,copy_uia)

    # SUMMARY exists before cycle 1; every cycle is fsynced before its checkpoint.
    session=EvidenceSession(runroot, {
        'tbLaunched':False, 'uiActions':False, 'pid':pid, 'startTicks':ticks,
        'tbSha256':EXPECTED_HASH, 'launcherSha256':launcher_sha.upper(),
        'inventorySha256':inventory_sha.upper(),
        'scheduledCycles':120, 'scheduledInventories':12,
    })
    start=time.monotonic();latencies=[];memory=[];handles=[];cpu=[]

    def result_metrics():
        resources=None
        if memory:
            resources={'first':memory[0], 'last':memory[-1],
                'deltaWorkingSetBytes':memory[-1]['workingSetBytes']-memory[0]['workingSetBytes'],
                'deltaPrivateBytes':memory[-1]['privateBytes']-memory[0]['privateBytes'],
                'deltaHandles':handles[-1]-handles[0],
                'deltaCpuSeconds':round((cpu[-1]-cpu[0])/10000000,3)}
        timing=None
        if latencies:
            ordered=sorted(latencies)
            timing={'p50':statistics.median(ordered),
                    'p95':ordered[min(len(ordered)-1,int(.95*len(ordered)))],
                    'max':max(ordered)}
        return resources,timing

    try:
        for i, take_inventory in sample_plan(cycles,snapshot_every):
            remaining=start+(i-1)*period-time.monotonic()
            if remaining>0: time.sleep(remaining)
            if time.monotonic()-start>3600+30: raise Blocked('global soak hard cap exceeded')
            ident=process_identity(pid,exe,EXPECTED_HASH,ticks)
            before=time.monotonic()
            statuscode,parent,child=diagnostic(copy_launcher,['status',str(pid),str(ticks)],runtime,12000)
            if statuscode!=0: raise Blocked(f'status returned {statuscode}')
            validate_status(child,pid)
            main_hwnd=status_hwnd(child)
            metrics=status_metrics(child)
            item={'cycle':i,'elapsedSec':round(time.monotonic()-start,3),
                  'statusCode':statuscode,'identity':ident,'metrics':metrics,
                  'statusMs':round((time.monotonic()-before)*1000,2)}
            if take_inventory:
                code,p,c=diagnostic(copy_uia,['uia-inventory',str(pid),str(ticks)],runtime,12000)
                if code!=0: raise Blocked(f'UIA inventory returned {code}')
                nodes=parse_inventory(c)
                item['inventory']=validate_inventory(nodes,pid,main_hwnd)
                item['inventoryMs']=round((time.monotonic()-before)*1000,2)
            # Commit both the cycle and snapshot before updating in-memory metrics.
            session.commit(item)
            memory.append(metrics);handles.append(ident['handles']);cpu.append(ident['cpu100ns'])
            latencies.append(item['statusMs'])
        time.sleep(max(0,start+3600-time.monotonic()))
        resources,timing=result_metrics()
        session.finish('PASS',time.monotonic()-start,resources=resources,timing=timing)
    except BaseException as exc:
        # External TerminateProcess, hard timeout and lost session bypass Python
        # entirely. Their last durable RUNNING/PARTIAL checkpoint remains useful.
        resources,timing=result_metrics()
        try:
            session.finish('PARTIAL / BLOCKED',time.monotonic()-start,
                reason=f'{type(exc).__name__}: {exc}',resources=resources,timing=timing)
        except Exception:
            # Do not hide original failure; the already-fsynced cycles survive.
            raise
    return runroot


def lifetime_probe(outbase:Path, duration_sec:float=1620, period_sec:float=30)->Path:
    """No-TB runtime longevity test, deliberately exceeds prior ~24.5 min stop.

    Does not create a service/task/daemon and does not escape the agent's Job.
    A lost process leaves atomic RUNNING/PARTIAL and committed cycle evidence.
    """
    if duration_sec < 0 or duration_sec > 1800 or period_sec < .005:
        raise Blocked('lifetime probe duration/period outside allowed bounds')
    count=int(duration_sec//period_sec)+1
    if count>200:
        raise Blocked('lifetime probe would create too many samples')
    root=unique_dir(outbase)
    session=EvidenceSession(root, {
        'probeType':'synthetic-lived-process', 'tbLaunched':False, 'uiActions':False,
        'scheduledSeconds':duration_sec,'samplePeriodSec':period_sec,
        'notTerrainBuilderEvidence':True,
    })
    start=time.monotonic()
    try:
        for i in range(1,count+1):
            pause=start+(i-1)*period_sec-time.monotonic()
            if pause>0: time.sleep(pause)
            snapshot=i%10==0
            row={'cycle':i,'elapsedSec':round(time.monotonic()-start,3),
                 'statusCode':0,'identity':{'synthetic':True}}
            if snapshot: row['inventory']={'nodes':1,'synthetic':True}
            session.commit(row)
        pause=start+duration_sec-time.monotonic()
        if pause>0: time.sleep(pause)
        session.finish('PROBE_COMPLETE',time.monotonic()-start,
                       reason='synthetic only; no Terrain Builder')
    except BaseException as exc:
        session.finish('PARTIAL / BLOCKED',time.monotonic()-start,
                       reason=f'{type(exc).__name__}: {exc}')
    return root


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['offline','job-smoke','soak','recover','lifetime-probe'])
    parser.add_argument('--pid',type=int,default=3856)
    parser.add_argument('--run-dir',type=Path,help='existing local reports run for read-only recovery')
    parser.add_argument('--probe-seconds',type=float,default=1620)
    parser.add_argument('--probe-period',type=float,default=30)
    parser.add_argument('--start-ticks',type=int)
    parser.add_argument('--tb-exe',type=Path)
    parser.add_argument('--launcher-bin',type=Path)
    parser.add_argument('--inventory-bin',type=Path)
    parser.add_argument('--launcher-sha',type=str)
    parser.add_argument('--inventory-sha',type=str)
    parser.add_argument('--out',type=Path,default=REPORTS)
    args=parser.parse_args(argv)
    try:
        root=under_reports(args.out)
        if args.mode=='recover':
            if args.run_dir is None:
                raise Blocked('recover requires --run-dir')
            run_dir=args.run_dir.resolve()
            reports_root=(ROOT/'reports').resolve()
            if reports_root not in run_dir.parents:
                raise Blocked('recovery input must be inside project reports')
            if not run_dir.is_dir():
                raise Blocked('run directory missing')
            recovery=recover_run(run_dir,write=True)
            print(f"RECOVERY: cycles={recovery['cycles']} inventories={recovery['inventories']} "
                  f"status={recovery['status']} cause={recovery['cause']}")
            return 0 if not recovery['evidenceProblems'] else 2
        if args.mode=='lifetime-probe':
            result=lifetime_probe(root,args.probe_seconds,args.probe_period)
            print(f"SYNTHETIC ONLY: evidence={result} (not a TB SOAK)")
            return 0 if json.loads((result/'SUMMARY.json').read_text())['status']=='PROBE_COMPLETE' else 2
        if args.mode=='offline':
            dest=unique_dir(root)
            fixture=make_fixture(dest/'fixture')
            (dest/'OFFLINE.json').write_text(json.dumps(fixture,indent=2)+'\n',encoding='utf-8')
            print(f'PASS offline synthetic fixture: {dest}')
            return 0
        if args.mode=='job-smoke':
            if os.name != 'nt': raise Blocked('Windows job smoke requires Windows: NOT RUN')
            tool=Path(os.environ['WINDIR'])/'System32'/'whoami.exe'
            if not tool.is_file() or tool.name.lower()!='whoami.exe':
                raise Blocked('known Windows diagnostic executable missing')
            code=run_in_job(tool,[],5000,protected_pid=args.pid)
            if code: raise Blocked(f'job-smoke process failed: {code}')
            print('PASS: Windows Job Object owned child completed')
            return 0
        if args.start_ticks is None or not all([args.tb_exe,args.launcher_bin,args.inventory_bin,args.launcher_sha,args.inventory_sha]):
            raise Blocked('soak requires start ticks, TB EXE, and pinned diagnostic helper paths/hashes')
        result=soak(args.pid,args.start_ticks,args.tb_exe,args.launcher_bin,args.inventory_bin,root,
                    args.launcher_sha,args.inventory_sha)
        status=json.loads((result/'SUMMARY.json').read_text(encoding='utf-8'))
        print(f"{status['status']}: cycles={status['cycles']} inventories={status['inventories']} report={result}")
        return 0 if status['status']=='PASS' else 2
    except (Blocked, OSError, ValueError) as exc:
        print(f'BLOCKED: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
