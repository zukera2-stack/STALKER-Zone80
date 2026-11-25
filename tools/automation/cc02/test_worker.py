import copy
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import worker as w
b=w.b
BASE='f585327a32849c7c83601a275c4d23a178b54cf0'

def manifest():
    j={'id':'a','kind':'synthetic_probe','requires':[],'payload':'Zone80 CC-02','wall_timeout_seconds':5,'max_address_space_bytes':128*1024**2,'min_available_ram_bytes':1024**2,'min_free_disk_bytes':1024**2,'fault':'ok','delay_ms':0,'max_sampled_group_rss_bytes':256*1024**2}
    return {'schema_version':1,'enabled':True,'issue':42,'scope':'synthetic_worker_acceptance_only','reviewed_code_sha':BASE,'local_approval':'CC-02 synthetic test only','expires_utc':(dt.datetime.now(b.UTC)+dt.timedelta(minutes=10)).isoformat(),'max_parallel_jobs':1,'native_jobs_authorized':False,'worker_sha256':b.file_hash(Path(w.__file__).resolve()),'executable_sha256':b.file_hash(Path(sys.executable).resolve()),'jobs':[j,dict(j,id='b',requires=['a'])]}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'zone80-synthetic-cc02';w.init(self.root);self.m=manifest()
    def state(self,n='a'):return b.load(self.root/(n+'.json'))
    def attempts(self,n='a'):return sorted(p for p in self.root.glob(n+'-*') if p.is_dir())
    def cli(self,*flags):
        mf=Path(self.tmp.name)/'queue.json';mf.write_text(json.dumps(self.m));return [sys.executable,str(Path(w.__file__).resolve()),'run',str(self.root),'--manifest',str(mf),*flags]
    def launch(self,*flags):
        p=subprocess.Popen(self.cli(*flags),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def cleanup():
            if p.poll() is None:p.kill()
            p.communicate(timeout=12)
        self.addCleanup(cleanup);return p
    def ready(self,n='a'):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            for attempt in self.attempts(n):
                if (attempt/'ready').exists():return attempt
            time.sleep(.02)
        self.fail('child readiness not observed')
    def test_pass_resume_corruption_and_invalidation(self):
        self.assertEqual(w.run(self.root,self.m),0);a=self.state();b0=self.state('b')
        self.assertGreater(a['sampled_peak_group_rss_bytes'],0);self.assertEqual(a['exit_code'],0)
        self.assertEqual(w.run(self.root,self.m),0);self.assertEqual(self.state(),a);self.assertEqual(self.state('b'),b0)
        (self.root/a['attempt']/'artifact.json').write_text('bad')
        self.assertEqual(w.run(self.root,self.m),0);self.assertNotEqual(self.state()['attempt'],a['attempt'])
        self.m['jobs'][0]['payload']='changed';self.assertEqual(w.run(self.root,self.m),0);self.assertNotEqual(self.state('b')['attempt'],b0['attempt'])
    def test_actual_nonzero(self):self.failure('nonzero','nonzero')
    def test_actual_false_success_missing(self):self.failure('missing','missing or unsafe file')
    def test_actual_false_success_wrong(self):self.failure('wrong','artifact mismatch')
    def failure(self,mode,reason):
        self.m['jobs'][0]['fault']=mode;self.assertEqual(w.run(self.root,self.m),2);self.assertEqual(self.state()['status'],'FAIL');self.assertIn(reason,self.state()['reason']);self.assertEqual(self.state('b')['status'],'BLOCKED')
        self.assertEqual(len(self.attempts()),1);self.assertEqual(self.attempts('b'),[])
    def test_actual_timeout(self):
        self.m['jobs'][0].update(fault='delay',delay_ms=4000,wall_timeout_seconds=1);self.assertEqual(w.run(self.root,self.m),2);self.assertEqual(self.state()['reason'],'wall timeout');self.assertLess(self.state()['elapsed_s'],4);self.assertEqual(self.state('b')['status'],'BLOCKED')
    def test_active_cancel_descendant_and_unrelated_sentinel(self):
        self.m['jobs'][0].update(fault='descendant',delay_ms=4000)
        sentinel=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])
        try:
            p=self.launch();attempt=self.ready();pgid=int((attempt/'ready').read_text());self.assertTrue((attempt/'descendant.pid').exists());self.assertGreaterEqual(w.group_usage(pgid)[0],2)
            time.sleep(.10);(self.root/'stop.request').touch();out,err=p.communicate(timeout=6);self.assertEqual(p.returncode,2,err);self.assertEqual(self.state()['status'],'CANCELLED');self.assertEqual(w.group_usage(pgid)[0],0);self.assertIsNone(sentinel.poll());self.assertGreaterEqual(self.state()['sampled_max_members'],2);self.assertEqual(self.attempts('b'),[])
        finally:sentinel.terminate();sentinel.wait(timeout=3)
    def test_leader_exit_with_descendant(self):
        self.failure('leader_exit','live descendants');self.assertEqual(w.group_usage(int((self.attempts()[0]/'ready').read_text()))[0],0)
    def test_real_kill_restart_and_explicit_recovery(self):
        # Finish A, then kill runner while B's fixed child is alive.
        self.m['jobs'][1].update(fault='delay',delay_ms=3000);p=self.launch();attempt=self.ready('b');a=self.state();self.assertEqual(a['status'],'PASS');pgid=int((attempt/'ready').read_text())
        p.kill();p.communicate(timeout=3);self.assertLess(p.returncode,0);self.assertGreater(w.group_usage(pgid)[0],0)
        q=subprocess.run(self.cli('--recover'),capture_output=True,text=True,timeout=3);self.assertEqual(q.returncode,2);self.assertIn('inherited child lock held',q.stderr);self.assertEqual(len(self.attempts('b')),1)
        deadline=time.monotonic()+6
        while w.group_usage(pgid)[0] and time.monotonic()<deadline:time.sleep(.05)
        self.assertEqual(w.group_usage(pgid)[0],0)
        self.assertEqual(w.run(self.root,self.m),2);self.assertEqual(self.state('b')['status'],'INTERRUPTED');self.assertEqual(self.state(),a)
        self.assertEqual(w.run(self.root,self.m,recover=True),0);self.assertEqual(self.state(),a);self.assertEqual(len(self.attempts('b')),2);self.assertEqual(self.state('b')['status'],'PASS');self.assertTrue(attempt.exists())
    def test_real_checkpoint_crash_before_after_replace(self):
        path=self.root/'checkpoint.json';script="import os,sys;from pathlib import Path;import cc01_base as b;old=os.replace\ndef crash(a,c):\n if sys.argv[2]=='after':old(a,c)\n os._exit(77)\nos.replace=crash;b.atomic(Path(sys.argv[1]),{'new':1})"
        for phase,expected in [('before',{'old':1}),('after',{'new':1})]:
            b.atomic(path,{'old':1});p=subprocess.run([sys.executable,'-c',script,str(path),phase],cwd=Path(w.__file__).parent,timeout=3);self.assertEqual(p.returncode,77);self.assertEqual(b.load(path),expected)
    def test_bad_manifests_and_resource_gate(self):
        for mutation in [lambda m:m['jobs'][0].update(fault='exec'),lambda m:m['jobs'][0].update(delay_ms=5000),lambda m:m['jobs'][0].update(argv=['echo']),lambda m:m['jobs'][0].update(kind='gm26_export'),lambda m:m.update(native_jobs_authorized=True),lambda m:m.update(worker_sha256='0'*64),lambda m:m.update(expires_utc='2000-01-01T00:00:00+00:00'),lambda m:m['jobs'][0].update(id='../escape'),lambda m:m['jobs'][0].update(requires=['b'])]:
            with self.subTest(mutation=mutation):
                m=copy.deepcopy(self.m);mutation(m)
                with self.assertRaises(b.Blocked):w.run(self.root,m)
        self.assertFalse((self.root/'runner.lock').exists());self.m['jobs'][0]['min_free_disk_bytes']=2**50;self.assertEqual(w.run(self.root,self.m),2);self.assertEqual(self.state()['status'],'BLOCKED');self.assertEqual(self.attempts(),[])
    def test_sampled_rss_limit(self):
        self.m['jobs'][0].update(fault='delay',delay_ms=3000,max_sampled_group_rss_bytes=1)
        self.assertEqual(w.run(self.root,self.m),2);self.assertEqual(self.state()['reason'],'sampled group RSS exceeded');self.assertGreater(self.state()['sampled_peak_group_rss_bytes'],1)
    def test_concurrent_runner(self):
        self.m['jobs'][0].update(fault='delay',delay_ms=2000);p=self.launch();self.ready()
        q=subprocess.run(self.cli(),capture_output=True,text=True,timeout=3);self.assertEqual(q.returncode,2);self.assertIn('inherited child lock held',q.stderr);self.assertEqual(len(self.attempts()),1)
        (self.root/'stop.request').touch();p.communicate(timeout=4);self.assertEqual(p.returncode,2)
    def test_stop_keeps_completed_pass(self):
        self.assertEqual(w.run(self.root,self.m),0);a=self.state();(self.root/'stop.request').touch();self.assertEqual(w.run(self.root,self.m),0);self.assertEqual(self.state(),a)

if __name__=='__main__':unittest.main()
