"""CC-02 Linux-only, fixed synthetic faults; no native adapters."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import cc01_base as b

BASE_HASH = '7ee6a93a45e61b3ee53776709e2df85effb2d002a1cc2fe232da32ad35a7b547'
MODES = {'ok', 'nonzero', 'missing', 'wrong', 'delay', 'descendant', 'leader_exit'}
CHILD = r'''import hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path
cap,fd,mode,delay,payload=sys.argv[1:]
cap=int(cap);fd=int(fd);delay=int(delay)/1000
resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
# Independent finite lifetime even if the runner dies. No setsid or arbitrary argv.
signal.alarm(10)
if mode in ('descendant','leader_exit'):
    p=subprocess.Popen([sys.executable,'-I','-S','-c','import signal,time; signal.alarm(8); time.sleep(6)'],pass_fds=(fd,))
    Path('descendant.pid').write_text(str(p.pid))
Path('ready').write_text(str(os.getpid()))
print('probe started',flush=True);print('probe stderr',file=sys.stderr,flush=True)
if mode=='nonzero':sys.exit(7)
if mode=='missing':sys.exit(0)
if mode=='wrong':Path('artifact.json').write_text('wrong');sys.exit(0)
if mode!='leader_exit':time.sleep(delay)
Path('artifact.json').write_bytes(json.dumps({'sha256':hashlib.sha256(payload.encode()).hexdigest()},sort_keys=True).encode()+b'\n')
'''


def validate(m):
    b.require(b.file_hash(Path(b.__file__).resolve()) == BASE_HASH, 'base source mismatch')
    b.require(m.get('worker_sha256') == b.file_hash(Path(__file__).resolve()), 'worker hash mismatch')
    q=copy.deepcopy(m); q['worker_sha256']=BASE_HASH
    b.require(type(q.get('jobs')) is list, 'jobs required')
    for j in q['jobs']:
        b.require(type(j) is dict, 'job object required')
        mode=j.pop('fault',None); delay=j.pop('delay_ms',None); rss=j.pop('max_sampled_group_rss_bytes',None)
        b.require(b.positive(rss,512*1024**2),'invalid sampled RSS limit')
        b.require(isinstance(mode,str) and mode in MODES, 'unknown synthetic fault')
        b.require(type(delay) is int and 0<=delay<=4000, 'invalid bounded delay')
    order=b.validate(q)
    by_id={j['id']:j for j in m['jobs']}
    return [by_id[j['id']] for j in order]


def init(root):
    b.require(sys.platform=='linux','Linux only')
    b.require(root==root.resolve() and not root.exists() and root.name.startswith('zone80-synthetic-'),'new synthetic root required')
    root.mkdir(mode=0o700)
    b.atomic(root/'marker.json',{'scope':'CC-02 synthetic only'})


def group_usage(pgid):
    """Sample live members of our fixed session; no claim of hard RSS cap."""
    count=rss=0
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])!=pgid or fields[0] in ('Z','X'):continue
            count+=1;rss+=max(0,int(fields[21]))*os.sysconf('SC_PAGE_SIZE')
        except (FileNotFoundError,ProcessLookupError):continue
    return count,rss


def terminate_group(child):
    # The direct child remains unreaped, pinning the group leader PID until signals finish.
    for sig in (signal.SIGTERM,signal.SIGKILL):
        try:os.killpg(child.pid,sig)
        except ProcessLookupError:pass
        if sig==signal.SIGTERM:time.sleep(.10)
    rc=child.wait(timeout=3)
    deadline=time.monotonic()+2
    while group_usage(child.pid)[0] and time.monotonic()<deadline:time.sleep(.02)
    b.require(group_usage(child.pid)[0]==0,'group cleanup uncertain')
    return rc


def execute(root,attempt,j,fd):
    start=time.monotonic();peak=0;members=0;outcome='FAIL';reason='unknown';rc=None
    with (attempt/'stdout.log').open('xb') as out,(attempt/'stderr.log').open('xb') as err:
        child=subprocess.Popen([str(Path(sys.executable).resolve()),'-I','-S','-c',CHILD,str(j['max_address_space_bytes']),str(fd),j['fault'],str(j['delay_ms']),j['payload']],cwd=attempt,stdout=out,stderr=err,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},start_new_session=True,pass_fds=(fd,))
        try:
            while True:
                n,r=group_usage(child.pid);peak=max(peak,r);members=max(members,n)
                if b.safe(root,'stop.request').exists():outcome,reason='CANCELLED','stop during child';break
                if r>j['max_sampled_group_rss_bytes']:reason='sampled group RSS exceeded';break
                if time.monotonic()-start>=j['wall_timeout_seconds']:reason='wall timeout';break
                exited=os.waitid(os.P_PID,child.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                if exited is not None:
                    if group_usage(child.pid)[0]:reason='leader exited with live descendants'
                    elif exited.si_code==os.CLD_EXITED and exited.si_status==0:outcome,reason='VALIDATING','child exit 0'
                    else:reason='nonzero or signalled exit'
                    break
                time.sleep(.02)
        finally:
            rc=terminate_group(child)
    return outcome,reason,{'exit_code':rc,'elapsed_s':round(time.monotonic()-start,4),'sampled_peak_group_rss_bytes':peak,'sampled_max_members':members}


def run(root,m,recover=False):
    b.require(sys.platform=='linux','Linux only; Windows BLOCKED')
    jobs=validate(m)
    b.require(root==root.resolve() and root.is_dir() and root.name.startswith('zone80-synthetic-'),'unsafe root')
    b.require(b.load(b.safe(root,'marker.json'))=={'scope':'CC-02 synthetic only'},'wrong sandbox version')
    fd=os.open(b.safe(root,'runner.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise b.Blocked('runner or inherited child lock held') from None
        results={}
        for j in jobs:
            name=j['id'];state=b.safe(root,name+'.json');prev=b.load(state) if state.exists() else None
            if prev and prev.get('status') in ('RUNNING','VALIDATING','INTERRUPTED'):
                # Lock inheritance is guaranteed only for this trusted CC-02 sandbox/code.
                prev.update(status='INTERRUPTED',reason='previous attempt interrupted; explicit recovery required',updated_utc=b.now())
                b.atomic(state,prev)
                if not recover or prev.get('protocol')!='cc02-inherited-lock-v1':results[name]=prev;continue
            deps={p:results[p].get('identity') for p in j['requires']}
            identity=b.digest(b.canonical({'job':j,'deps':deps,'worker':m['worker_sha256'],'base':BASE_HASH,'exe':m['executable_sha256'],'review':m['reviewed_code_sha']}))
            rec={'id':name,'identity':identity,'history':[],'protocol':'cc02-inherited-lock-v1'}
            def transition(status,reason):
                rec.update(status=status,reason=reason,updated_utc=b.now());rec['history'].append({'status':status,'reason':reason,'utc':rec['updated_utc']});b.atomic(state,rec)
            results[name]=rec
            if any(results[p]['status']!='PASS' for p in j['requires']):transition('BLOCKED','dependency not PASS');continue
            if b.safe(root,'stop.request').exists():
                if prev and prev.get('status')=='PASS' and prev.get('identity')==identity:
                    try:
                        if b.file_hash(b.safe(root,prev['attempt'],'artifact.json'))==prev['artifact_sha256']==b.digest(b.expected(j)):results[name]=prev;continue
                    except (OSError,b.Blocked,KeyError,TypeError):pass
                transition('CANCELLED','stop before job');continue
            b.expiry(m)
            if prev and prev.get('status')=='PASS' and prev.get('identity')==identity:
                try:
                    if b.file_hash(b.safe(root,prev['attempt'],'artifact.json'))==prev['artifact_sha256']==b.digest(b.expected(j)):
                        results[name]=prev;print(name,'SKIP verified PASS',flush=True);continue
                except (OSError,b.Blocked,KeyError,TypeError):pass
            transition('QUEUED','new attempt');transition('PREFLIGHT','host limits')
            try:b.resources(root,j)
            except (OSError,ValueError,b.Blocked) as e:transition('BLOCKED',str(e));continue
            attempt=b.safe(root,name+'-'+uuid.uuid4().hex);attempt.mkdir(mode=0o700);rec['attempt']=attempt.name
            transition('RUNNING','fixed child with inherited runner lock')
            try:
                status,reason,metrics=execute(root,attempt,j,fd);rec.update(metrics)
                transition(status,reason)
                if status=='VALIDATING':
                    artifact=b.safe(root,attempt.name,'artifact.json');h=b.file_hash(artifact);b.require(h==b.digest(b.expected(j)),'artifact mismatch')
                    with artifact.open('rb') as f:os.fsync(f.fileno())
                    d=os.open(attempt,os.O_RDONLY|os.O_DIRECTORY)
                    try:os.fsync(d)
                    finally:os.close(d)
                    rec['artifact_sha256']=h;transition('PASS','validated exact output')
            except (OSError,b.Blocked,subprocess.SubprocessError) as e:
                uncertain=rec['status']=='RUNNING'
                transition('INTERRUPTED' if uncertain else 'FAIL',type(e).__name__+': '+str(e))
                if uncertain:return 2
            print(name,rec['status'],flush=True)
        return 0 if all(r['status']=='PASS' for r in results.values()) else 2
    finally:os.close(fd)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','run']);p.add_argument('root',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--recover',action='store_true');a=p.parse_args()
    try:
        root=a.root.absolute();b.require(root==root.resolve(),'unsafe root')
        if a.command=='init':init(root);return 0
        b.require(a.manifest is not None,'manifest required');return run(root,b.load(a.manifest),a.recover)
    except (b.Blocked,OSError,ValueError,KeyError,TypeError) as e:print('BLOCKED:',e,file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
