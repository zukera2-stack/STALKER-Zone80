"""Explicit simulated interruption after commit on the accepted owned fixture.
Never remove a real unresolved marker or change current.json.
"""
import os, hashlib
from pathlib import Path
import resume_gate as r
import pipeline_gate as g
import cc01_base as b
root=r.ROOT
marker=root/"inflight.json"
current=root/"current.json"
with r.lock():
    assert not marker.exists() and not (root/"stop.request").exists()
    old=current.read_bytes()
    m,identity=g.validate_snapshot()
    p=g.load(current)
    attempt=root/p["attempt"]
    e=g.load(attempt/"execution.json")
    assert e["exit_code"]==0 and r.pid_gone(e["pid"])
    assert not r.pid_gone(os.getpid())
    print("PASS live PID guard")
    good={"attempt":p["attempt"],"identity":identity,"status":"RUNNING","pid":e["pid"],"utc":b.now()}
    assert r.marker_valid(good,identity)
    def injected(rec,expected):
        assert not marker.exists()
        g.atomic(marker,rec)
        payload=marker.read_bytes()
        try:
            if expected:
                try:r.recover_locked()
                except b.Blocked as exc:assert expected in str(exc),str(exc)
                else:raise AssertionError("unexpected recovery")
                assert marker.read_bytes()==payload
                print("PASS refusal:",expected)
            else:
                before=set(root.glob("recovered-*.json"))
                assert r.recover_locked()
                after=set(root.glob("recovered-*.json"))-before
                assert len(after)==1 and next(iter(after)).read_bytes()==payload
                assert not marker.exists()
                print("PASS simulated post-commit interruption; journal preserved")
            assert current.read_bytes()==old
        finally:
            if marker.exists():
                assert marker.read_bytes()==payload
                marker.unlink() # only this explicit test marker
    bad=dict(good);bad.pop("pid")
    injected(bad,"unknown or incomplete attempt marker")
    bad=dict(good);bad["pid"]=os.getpid()
    injected(bad,"no matching durable successful exit evidence")
    injected(good,None)
assert not marker.exists()
assert current.read_bytes()==old
print("PASS accepted pointer byte-identical")
for p in (Path(r.__file__),Path(__file__)):
    raw=p.read_bytes()
    print(p.name,"SHA256",hashlib.sha256(raw).hexdigest(),"GIT_BLOB",hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest())
