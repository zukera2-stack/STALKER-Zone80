from pathlib import Path
import hashlib, msvcrt, subprocess, sys
root=Path(__file__).parent
script=root/'pipeline_gate.py'
current=root/'current.json'
old=current.read_bytes()
attempts=set(root.glob('attempt-*'))
def refused(reason):
    p=subprocess.run([sys.executable,'-B',str(script),'run'],capture_output=True,text=True,timeout=30)
    assert p.returncode==2 and reason in p.stderr,(p.returncode,p.stdout,p.stderr)
    assert current.read_bytes()==old and set(root.glob('attempt-*'))==attempts
    print('PASS refusal:',reason,flush=True)
with (root/'runner.lock').open('r+b') as f:
    f.seek(0)
    msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:refused('runner lock held')
    finally:
        f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
marker=root/'stop.request'
with marker.open('xb') as f:f.write(b'test only')
try:refused('stop requested')
finally:marker.unlink()
marker=root/'inflight.json'
with marker.open('xb') as f:f.write(b'{"test":"unresolved marker only; no process"}')
try:refused('prior attempt unresolved')
finally:marker.unlink()
p=subprocess.run([sys.executable,'-B',str(script),'run'],capture_output=True,text=True,timeout=30)
assert p.returncode==0 and 'SKIP verified' in p.stdout
assert current.read_bytes()==old and set(root.glob('attempt-*'))==attempts
print('PASS verified resume; one original attempt')
for p in (script,Path(__file__)):
    raw=p.read_bytes()
    print(p.name,'SHA256',hashlib.sha256(raw).hexdigest(),'GIT_BLOB',hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
