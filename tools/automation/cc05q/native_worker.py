"""CC05Q Linux native synthetic companion; trusted snapshot, no production jobs."""
import argparse
import ctypes
import datetime as dt
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import preflight as p
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'cc02'))
import worker as cc02
import cc01_base as b
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'cc05p'))
import verify_job

MARKER = {'scope':'CC05Q native synthetic review only','version':1}
BOOT = Path('/proc/sys/kernel/random/boot_id')
MAX_LOG = 16*1024**2


def require(ok, reason):
    b.require(ok, reason)


def init(root):
    require(sys.platform=='linux' and root==root.resolve() and not root.exists() and root.name.startswith('zone80-native-'), 'new isolated Linux root required')
    root.mkdir(mode=0o700)
    b.atomic(root/'marker.json', MARKER)


def prepare(snapshot, envelope):
    plan=p.prepare(snapshot,envelope,dt.datetime.now(dt.timezone.utc))
    sources={'worker.py':cc02.__file__,'cc01_base.py':b.__file__,'verify_job.py':verify_job.__file__,'preflight.py':p.__file__,'native_worker.py':__file__,'python':sys.executable}
    for name,path in sources.items():
        require(envelope['files'].get('code/'+name)==p.sha(Path(path).resolve()), 'running code mismatch '+name)
    require(p.sha(Path(b.__file__).resolve())==cc02.BASE_HASH,'CC02 base mismatch')
    require(sorted(x.name for x in (snapshot/'runtime/shared/Microsoft.NETCore.App').iterdir())==['10.0.15'], 'unexpected runtime')
    require((snapshot/'runtime/host/fxr/10.0.15/libhostfxr.so').is_file(), 'missing hostfxr')
    return plan


def parent_guard(parent, seconds):
    # Trusted, single-threaded Linux CLI. Set parent-death signal before exec;
    # recheck parent to close the fork/prctl race. No arbitrary descendants approved.
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(1,signal.SIGKILL,0,0,0)!=0 or os.getppid()!=parent:
        os._exit(125)
    signal.alarm(seconds+1)


def execute(root, attempt, plan, envelope, fd, update):
    start=time.monotonic(); peak=members=0; status='FAIL'; reason='unknown'
    (attempt/'tmp').mkdir(mode=0o700); (attempt/'home').mkdir(mode=0o700)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(attempt/'home'),'TMPDIR':str(attempt/'tmp'),'XDG_RUNTIME_DIR':str(attempt/'tmp'),'DOTNET_ROOT':str(Path(plan['argv'][0]).parent),'DOTNET_PROCESSOR_COUNT':'2','DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'}
    parent=os.getpid()
    with (attempt/'stdout.log').open('xb') as out,(attempt/'stderr.log').open('xb') as err:
        child=subprocess.Popen(plan['argv'],cwd=attempt,stdout=out,stderr=err,env=env,start_new_session=True,pass_fds=(fd,),preexec_fn=lambda:parent_guard(parent,envelope['wall_timeout_seconds']))
        try:
            update('RUNNING','native child started',pid=child.pid,boot_id=BOOT.read_text().strip())
            while True:
                n,r=cc02.group_usage(child.pid);peak=max(peak,r);members=max(members,n)
                if b.safe(root,'stop.request').exists():status,reason='CANCELLED','stop during native child';break
                if r>envelope['max_sampled_group_rss_bytes']:reason='sampled RSS exceeded';break
                if max(os.fstat(out.fileno()).st_size,os.fstat(err.fileno()).st_size)>MAX_LOG:reason='log limit exceeded';break
                if time.monotonic()-start>=envelope['wall_timeout_seconds']:reason='wall timeout';break
                exited=os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                if exited is not None:
                    if cc02.group_usage(child.pid)[0]:reason='leader exited with live descendants'
                    elif exited.si_code==os.CLD_EXITED and exited.si_status==0:status,reason='VALIDATING','native exit 0'
                    else:reason='native nonzero or signalled exit'
                    break
                time.sleep(.02)
        finally:
            rc=cc02.terminate_group(child)
            for f in (out,err):f.flush();os.fsync(f.fileno())
    return status,reason,{'exit_code':rc,'elapsed_s':round(time.monotonic()-start,4),'sampled_peak_group_rss_bytes':peak,'sampled_max_members':members}


def read_result(attempt, plan):
    out=b.safe(attempt,'stdout.log'); require(out.stat().st_size<=MAX_LOG,'stdout too large')
    return p.output_gate(out.read_bytes(),0,plan['job'],verify_job.validate)


def reusable(attempt, record, plan):
    try:
        result=read_result(attempt,plan)
        manifest=b.load(b.safe(attempt,'review.json'))
        return record['exit_code']==0 and record['review_sha256']==p.sha(attempt/'review.json') and record['stdout_sha256']==p.sha(attempt/'stdout.log') and record['stderr_sha256']==p.sha(b.safe(attempt,'stderr.log')) and manifest=={'scope':'synthetic_review_only','identity':plan['identity'],'result':result}
    except (OSError,ValueError,KeyError,TypeError,b.Blocked):return False


def run(root,snapshot,envelope,recover=False):
    require(sys.platform=='linux' and root==root.resolve() and root.name.startswith('zone80-native-') and root.is_dir(),'unsafe root')
    require(not snapshot.is_relative_to(root) and not root.is_relative_to(snapshot),'overlapping state and snapshot')
    require(b.load(b.safe(root,'marker.json'))==MARKER,'wrong state schema')
    fd=os.open(b.safe(root,'runner.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise b.Blocked('runner or child lock held') from None
        plan=prepare(snapshot,envelope); ident=plan['identity']; matches=[]
        for attempt in sorted(root.glob('attempt-*')):
            require(attempt.is_dir() and not attempt.is_symlink(),'unsafe attempt')
            state=b.safe(attempt,'status.json'); record=b.load(state)
            if record['status'] in ('RUNNING','VALIDATING','INTERRUPTED') and not record.get('reconciled'):
                require(recover and type(record.get('pid')) is int and record['pid']>1 and record.get('boot_id')==BOOT.read_text().strip() and cc02.group_usage(record['pid'])[0]==0,'previous process ownership unresolved; explicit recovery with empty group required')
                record.update(status='INTERRUPTED',reconciled=True,reason='explicit recovery; lock free and saved group empty',updated_utc=b.now());b.atomic(state,record)
            if record['identity']==ident:matches.append((attempt,record))
        for attempt,record in matches:
            if record['status']=='PASS' and reusable(attempt,record,plan):
                print('SKIP verified PASS',attempt.name,flush=True);return 0
        require(not b.safe(root,'stop.request').exists(),'stop before start')
        require(len(matches)<envelope['max_attempts'],'attempt budget exhausted')
        b.resources(root,envelope)
        attempt=b.safe(root,'attempt-'+uuid.uuid4().hex);attempt.mkdir(mode=0o700)
        record={'identity':ident,'history':[],'scope':'synthetic_review_only'}
        def update(status,reason,**extra):
            record.update(status=status,reason=reason,updated_utc=b.now(),**extra)
            record['history'].append({'status':status,'reason':reason,'utc':record['updated_utc']});b.atomic(attempt/'status.json',record)
        update('RUNNING','launch pending; unresolved if interrupted before pid recorded')
        try:
            status,reason,metrics=execute(root,attempt,plan,envelope,fd,update)
            update(status,reason,**metrics)
            if status!='VALIDATING':print(status,reason,flush=True);return 2
            require(metrics['exit_code']==0,'nonzero exit')
            result=read_result(attempt,plan)
            require(prepare(snapshot,envelope)['identity']==ident,'snapshot changed after execution')
            require(not b.safe(root,'stop.request').exists(),'stop before publication')
            b.atomic(attempt/'review.json',{'scope':'synthetic_review_only','identity':ident,'result':result})
            update('PASS','verified native synthetic result',review_sha256=p.sha(attempt/'review.json'),stdout_sha256=p.sha(attempt/'stdout.log'),stderr_sha256=p.sha(attempt/'stderr.log'),records=result['total'])
            print('PASS',attempt.name,'records',result['total'],flush=True);return 0
        except (OSError,ValueError,KeyError,TypeError,b.Blocked,subprocess.SubprocessError) as e:
            update('INTERRUPTED' if record['status']=='RUNNING' else 'FAIL',str(e));return 2
    finally:os.close(fd)


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('command',choices=['init','run']);cli.add_argument('root',type=Path);cli.add_argument('--snapshot',type=Path);cli.add_argument('--envelope',type=Path);cli.add_argument('--recover',action='store_true');cli.add_argument('--execute-synthetic',action='store_true');a=cli.parse_args()
    try:
        if a.command=='init':init(a.root.absolute());return 0
        require(a.execute_synthetic and a.snapshot is not None and a.envelope is not None,'explicit synthetic execution and envelope required')
        return run(a.root.absolute(),a.snapshot.absolute(),p.parse(a.envelope.read_bytes()),a.recover)
    except (OSError,ValueError,TypeError,KeyError,b.Blocked) as e:print('BLOCKED:',e,file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
