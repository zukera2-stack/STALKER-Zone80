"""CC-01: bounded Linux synthetic worker. No native job adapters."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

UTC = dt.timezone.utc
HEX = re.compile(r'[0-9a-f]{64}')
ID = re.compile(r'[a-z][a-z0-9-]{0,39}')
CHILD = '''import hashlib,json,resource,sys
from pathlib import Path
cap=int(sys.argv[1]); resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
payload=sys.argv[2].encode('utf-8')
Path('artifact.json').write_bytes(json.dumps({'sha256':hashlib.sha256(payload).hexdigest()},sort_keys=True).encode()+b'\\n')
print('synthetic probe completed'); print('synthetic stderr marker',file=sys.stderr)
'''

class Blocked(Exception):
    pass

def require(ok, reason):
    if not ok:
        raise Blocked(reason)

def now():
    return dt.datetime.now(UTC).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def file_hash(path):
    require(path.is_file() and not path.is_symlink(), 'missing or unsafe file')
    return digest(path.read_bytes())

def exact(obj, keys):
    require(type(obj) is dict and set(obj) == set(keys.split()), 'unexpected or missing fields')

def positive(n, upper):
    return type(n) is int and 0 < n <= upper

def expiry(m):
    try:
        deadline = dt.datetime.fromisoformat(m['expires_utc'])
        require(deadline.tzinfo is not None and dt.datetime.now(UTC) < deadline, 'expired approval')
    except (TypeError, ValueError):
        raise Blocked('invalid expiry') from None

def validate(m):
    exact(m, 'schema_version enabled issue scope reviewed_code_sha local_approval expires_utc max_parallel_jobs native_jobs_authorized worker_sha256 executable_sha256 jobs')
    require(type(m['schema_version']) is int and m['schema_version']==1 and m['enabled'] is True and m['issue']==42 and m['scope']=='synthetic_worker_acceptance_only' and type(m['max_parallel_jobs']) is int and m['max_parallel_jobs']==1 and m['native_jobs_authorized'] is False, 'disabled or forbidden scope')
    require(isinstance(m['reviewed_code_sha'],str) and re.fullmatch('[0-9a-f]{40}',m['reviewed_code_sha']) and isinstance(m['local_approval'],str) and 0<len(m['local_approval'])<=200, 'missing review or approval')
    expiry(m)
    require(m['worker_sha256']==file_hash(Path(__file__).resolve()) and m['executable_sha256']==file_hash(Path(sys.executable).resolve()), 'code or executable hash mismatch')
    require(type(m['jobs']) is list and 0<len(m['jobs'])<=64, 'invalid queue size')
    jobs={}
    for j in m['jobs']:
        exact(j,'id kind requires payload wall_timeout_seconds max_address_space_bytes min_available_ram_bytes min_free_disk_bytes')
        name=j['id']
        require(isinstance(name,str) and ID.fullmatch(name) and name not in jobs, 'invalid or duplicate id')
        require(j['kind']=='synthetic_probe','unsupported job kind')
        require(type(j['requires']) is list and all(isinstance(x,str) and ID.fullmatch(x) for x in j['requires']) and len(set(j['requires']))==len(j['requires']), 'invalid predecessors')
        require(isinstance(j['payload'],str) and len(j['payload'].encode())<=4096 and '\x00' not in j['payload'], 'invalid payload')
        require(positive(j['wall_timeout_seconds'],30) and positive(j['max_address_space_bytes'],512*1024**2) and j['max_address_space_bytes']>=64*1024**2 and positive(j['min_available_ram_bytes'],2**50) and positive(j['min_free_disk_bytes'],2**50),'invalid limits')
        jobs[name]=j
    ordered=[]
    while len(ordered)<len(jobs):
        ready=[n for n in jobs if n not in ordered and all(p in ordered for p in jobs[n]['requires'])]
        require(ready,'missing dependency or cycle')
        ordered.extend(ready)
    return [jobs[n] for n in ordered]

def safe(root, *parts):
    p=root
    for part in parts:
        require(isinstance(part,str) and re.fullmatch(r'[A-Za-z0-9_.-]+',part) and part not in ('.','..'), 'unsafe path component')
        p=p/part
        require(not p.is_symlink(), 'symlink refused')
    require(p.resolve().is_relative_to(root), 'path escape')
    return p

def atomic(path, value):
    tmp=path.parent/('.tmp-'+uuid.uuid4().hex)
    with tmp.open('xb') as f:
        f.write(canonical(value)+b'\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def load(path):
    def pairs(entries):
        out={}
        for k,v in entries:
            require(k not in out,'duplicate JSON key'); out[k]=v
        return out
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs)

def init(root):
    require(root.name.startswith('zone80-synthetic-') and not root.exists() and not root.is_symlink(),'new zone80-synthetic-* directory required')
    root.mkdir(mode=0o700)
    atomic(root/'marker.json',{'scope':'CC-01 synthetic only'})

def resources(root,j):
    values=Path('/proc/meminfo').read_text().splitlines()
    available=next((int(s.split()[1])*1024 for s in values if s.startswith('MemAvailable:')),None)
    require(available is not None and available>=j['min_available_ram_bytes'],'host RAM probe blocked')
    require(shutil.disk_usage(root).free>=j['min_free_disk_bytes'],'disk probe blocked')

def expected(j):
    return json.dumps({'sha256':digest(j['payload'].encode())},sort_keys=True).encode()+b'\n'

def run(root,m):
    require(sys.platform=='linux','Linux synthetic prototype only')
    import fcntl
    jobs=validate(m)
    require(root.is_dir() and root.name.startswith('zone80-synthetic-') and not root.is_symlink() and root==root.resolve(), 'unsafe root')
    require(load(safe(root,'marker.json'))=={'scope':'CC-01 synthetic only'},'not a synthetic root')
    lock=safe(root,'runner.lock')
    fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'r+') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise Blocked('runner lock held') from None
        results={}
        for j in jobs:
            name=j['id']; state=safe(root,name+'.json')
            previous=load(state) if state.exists() else None
            # A crashed attempt may still own a live process. Never auto-retry it.
            if previous and previous.get('status') in ('RUNNING','VALIDATING','INTERRUPTED'):
                previous.update(status='INTERRUPTED',reason='prior attempt ownership unresolved',updated_utc=now()); atomic(state,previous)
                results[name]=previous; continue
            deps={p:results[p].get('identity') for p in j['requires']}
            identity=digest(canonical({'job':j,'deps':deps,'worker':m['worker_sha256'],'exe':m['executable_sha256'],'review':m['reviewed_code_sha']}))
            rec={'id':name,'identity':identity,'status':'QUEUED','history':[]}
            def transition(status,reason):
                rec.update(status=status,reason=reason,updated_utc=now())
                rec['history'].append({'status':status,'reason':reason,'utc':rec['updated_utc']}); atomic(state,rec)
            if any(results[p]['status']!='PASS' for p in j['requires']):
                transition('BLOCKED','dependency not PASS'); results[name]=rec; continue
            if safe(root,'stop.request').exists():
                transition('CANCELLED','stop requested before job'); results[name]=rec; continue
            expiry(m)
            if previous and previous.get('status')=='PASS' and previous.get('identity')==identity:
                try:
                    artifact=safe(root,previous['attempt'],'artifact.json')
                    if file_hash(artifact)==previous.get('artifact_sha256')==digest(expected(j)):
                        results[name]=previous; print(name,'SKIP verified PASS'); continue
                except (OSError,Blocked,KeyError,TypeError): pass
            transition('QUEUED','new attempt'); transition('PREFLIGHT','checking host limits')
            try: resources(root,j)
            except (OSError,ValueError,Blocked) as e:
                transition('BLOCKED',str(e)); results[name]=rec; continue
            attempt=safe(root,name+'-'+uuid.uuid4().hex); attempt.mkdir(mode=0o700)
            rec['attempt']=attempt.name
            transition('RUNNING','fixed synthetic child only')
            try:
                with (attempt/'stdout.log').open('xb') as out,(attempt/'stderr.log').open('xb') as err:
                    child=subprocess.run([str(Path(sys.executable).resolve()),'-I','-S','-c',CHILD,str(j['max_address_space_bytes']),j['payload']],cwd=attempt,stdout=out,stderr=err,timeout=j['wall_timeout_seconds'],check=False,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
                rec['exit_code']=child.returncode
                transition('VALIDATING','child exited')
                require(child.returncode==0,'nonzero exit')
                artifact=safe(root,attempt.name,'artifact.json')
                require(file_hash(artifact)==digest(expected(j)),'artifact validation failed')
                with artifact.open('rb') as af: os.fsync(af.fileno())
                afd=os.open(attempt,os.O_RDONLY|os.O_DIRECTORY)
                try: os.fsync(afd)
                finally: os.close(afd)
                rec['artifact_sha256']=file_hash(artifact)
                transition('PASS','verified exact synthetic output')
            except (OSError,Blocked,subprocess.TimeoutExpired) as e:
                transition('FAIL',type(e).__name__+': '+str(e))
            results[name]=rec; print(name,rec['status'])
        return 0 if all(r['status']=='PASS' for r in results.values()) else 2

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('command',choices=['init','run']); p.add_argument('root',type=Path); p.add_argument('--manifest',type=Path); a=p.parse_args()
    try:
        require(sys.platform=='linux','Linux only; Windows BLOCKED')
        root=a.root.absolute(); require(root==root.resolve(),'root symlink or noncanonical path')
        if a.command=='init': init(root); return 0
        require(a.manifest is not None,'manifest required'); return run(root,load(a.manifest))
    except (Blocked,OSError,ValueError,TypeError,KeyError) as e:
        print('BLOCKED:',e,file=sys.stderr); return 2

if __name__=='__main__':
    raise SystemExit(main())
