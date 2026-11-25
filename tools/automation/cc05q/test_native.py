"""Bounded Linux acceptance test; requires a real pinned CC05P snapshot and envelope."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import native_worker as w
import preflight as p


def need(ok, label):
    if not ok:raise AssertionError(label)


def main():
    source, envpath=map(lambda x:Path(x).resolve(),sys.argv[1:])
    base=p.parse(envpath.read_bytes())
    with tempfile.TemporaryDirectory(prefix='cc05q-accept-') as td:
        work=Path(td); snapshot=work/'snapshot';shutil.copytree(source,snapshot)
        env=work/'envelope.json'
        def setenv(m):env.write_text(json.dumps(m));return m
        setenv(base)
        def root(name):
            r=work/('zone80-native-'+name);w.init(r);return r
        def argv(r,*extra):return [sys.executable,str(Path(w.__file__).resolve()),'run',str(r),'--snapshot',str(snapshot),'--envelope',str(env),'--execute-synthetic',*extra]
        def invoke(r,*extra):return subprocess.run(argv(r,*extra),capture_output=True,text=True,timeout=40)
        def records(r):return [(a,json.loads((a/'status.json').read_text())) for a in r.glob('attempt-*')]
        def state(r,status):return [(a,s) for a,s in records(r) if s['status']==status]
        def active(r,proc):
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                for a in r.glob('attempt-*'):
                    try:s=json.loads((a/'status.json').read_text())
                    except FileNotFoundError:continue
                    if s['status']=='RUNNING' and s.get('pid'):return a,s
                need(proc.poll() is None,'child ended before active observation');time.sleep(.005)
            raise AssertionError('active observation timeout')
        def start(r):return subprocess.Popen(argv(r),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def stopproc(proc):
            if proc.poll() is None:proc.kill()
            proc.communicate(timeout=10)
        def empty_group(pid):
            deadline=time.monotonic()+5
            while w.cc02.group_usage(pid)[0] and time.monotonic()<deadline:time.sleep(.02)
            need(w.cc02.group_usage(pid)[0]==0,'live old group')
        r=root('success');q=invoke(r);need(q.returncode==0,q.stderr);a,s=state(r,'PASS')[0];need(s['records']==1015 and s['sampled_max_members']==1,'native result')
        print('PASS real native baseline',s['records'],s['elapsed_s'],s['sampled_peak_group_rss_bytes'],flush=True)
        q=invoke(r);need(q.returncode==0 and 'SKIP verified PASS' in q.stdout and len(records(r))==1,'skip');print('PASS validated resume skip',flush=True)
        original=(a/'review.json').read_bytes();(a/'review.json').write_bytes(original+b' ')
        q=invoke(r);need(q.returncode==0 and len(state(r,'PASS'))==2,'tamper invalidation');need((a/'review.json').read_bytes()==original+b' ','old evidence overwritten');print('PASS altered review rejected; new native attempt, old evidence preserved',flush=True)
        # Corrupt the actual child binary without repinning: must refuse before start.
        dll=snapshot/'child/Zone80.JobProbe.dll';raw=dll.read_bytes();dll.write_bytes(raw+b' ')
        q=invoke(r);need(q.returncode==2 and len(records(r))==2,'changed binary accepted');dll.write_bytes(raw);print('PASS changed binary refused',flush=True)
        # Different valid job input and explicit new envelope: cached result cannot be reused.
        jobpath=snapshot/'inputs/job.json';old=jobpath.read_bytes();job=p.parse(old);job['road_state']='operational';jobpath.write_text(json.dumps(job));new=dict(base,files=dict(base['files'],**{'inputs/job.json':p.sha(jobpath)}));setenv(new)
        q=invoke(r);need(q.returncode==0 and len(records(r))==3 and any(s['records']==1062 for _,s in state(r,'PASS')),'job invalidation');print('PASS changed valid input; actual 1062-record native attempt',flush=True)
        jobpath.write_bytes(old);setenv(base)
        expired=dict(base,expires_utc=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=1)).isoformat());setenv(expired);q=invoke(r);need(q.returncode==2 and len(records(r))==3,'expired cached success');setenv(base);print('PASS expiry refused even for cached result',flush=True)
        r=root('stop-before');(r/'stop.request').touch();q=invoke(r);need(q.returncode==2 and not records(r),'stop before');print('PASS stop before start',flush=True)
        r=root('cancel');proc=start(r)
        try:
            _,s=active(r,proc);(r/'stop.request').touch();proc.communicate(timeout=10);need(proc.returncode==2 and len(state(r,'CANCELLED'))==1,'cancel');empty_group(s['pid']);need(not list(r.glob('attempt-*/review.json')),'cancel published result')
        finally:stopproc(proc)
        print('PASS actual native cancellation; group empty; no publication',flush=True)
        # Low sampled RSS ceiling is an intentional fault, not a proposed production limit.
        r=root('rss');setenv(dict(base,max_sampled_group_rss_bytes=1));q=invoke(r);need(q.returncode==2 and state(r,'FAIL')[0][1]['reason']=='sampled RSS exceeded','RSS refusal');print('PASS sampled RSS limit',flush=True)
        r=root('timeout');setenv(dict(base,wall_timeout_seconds=1));proc=start(r)
        try:
            _,s=active(r,proc)
            # Freeze only this owned synthetic group to exercise wall timeout deterministically.
            os.killpg(s['pid'],signal.SIGSTOP)
            proc.communicate(timeout=10);need(proc.returncode==2 and state(r,'FAIL')[0][1]['reason']=='wall timeout','timeout');empty_group(s['pid'])
        finally:stopproc(proc)
        print('PASS actual native wall timeout; owned group empty',flush=True)
        setenv(base);r=root('crash');proc=start(r)
        try:
            _,s=active(r,proc)
            q=invoke(r);need(q.returncode==2 and 'lock held' in q.stderr,'concurrent lock');print('PASS concurrent runner refused',flush=True)
            # Kill the owner Worker, not the child. Parent-death guard must end the real child.
            need(proc.poll() is None,'worker already ended');proc.kill();proc.communicate(timeout=10);empty_group(s['pid']);need(len(records(r))==1 and not state(r,'PASS'),'crash state')
        finally:stopproc(proc)
        q=invoke(r);need(q.returncode==2 and len(records(r))==1,'implicit recovery');q=invoke(r,'--recover');need(q.returncode==0 and len(state(r,'PASS'))==1 and len(state(r,'INTERRUPTED'))==1,'explicit recovery');print('PASS worker SIGKILL; no second live child; explicit native recovery',flush=True)
        print('PASS bounded native acceptance; not production or Windows',flush=True)

if __name__=='__main__':main()
