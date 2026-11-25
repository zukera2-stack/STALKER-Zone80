import copy
import datetime as dt
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import worker as w

BASE='134b07632bfe271a8cc1d3431381e83b26379b83'

def manifest():
    j={'id':'a','kind':'synthetic_probe','requires':[],'payload':'Zone80 test','wall_timeout_seconds':5,'max_address_space_bytes':128*1024**2,'min_available_ram_bytes':1024**2,'min_free_disk_bytes':1024**2}
    b=dict(j,id='b',requires=['a'],payload='dependent')
    return {'schema_version':1,'enabled':True,'issue':42,'scope':'synthetic_worker_acceptance_only','reviewed_code_sha':BASE,'local_approval':'CC-01 synthetic test only','expires_utc':(dt.datetime.now(w.UTC)+dt.timedelta(minutes=10)).isoformat(),'max_parallel_jobs':1,'native_jobs_authorized':False,'worker_sha256':w.file_hash(Path(w.__file__).resolve()),'executable_sha256':w.file_hash(Path(sys.executable).resolve()),'jobs':[b,j]}

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'zone80-synthetic-test'; w.init(self.root)
        self.m=manifest()
    def state(self,n): return w.load(self.root/(n+'.json'))
    def test_success_resume_and_invalidation(self):
        self.assertEqual(w.run(self.root,self.m),0)
        a,b=self.state('a'),self.state('b')
        self.assertEqual([x['status'] for x in a['history']],['QUEUED','PREFLIGHT','RUNNING','VALIDATING','PASS'])
        self.assertEqual(a['artifact_sha256'],w.digest(w.expected(self.m['jobs'][1])))
        self.assertIn('completed',(self.root/a['attempt']/'stdout.log').read_text())
        self.assertIn('stderr marker',(self.root/a['attempt']/'stderr.log').read_text())
        self.assertEqual(w.run(self.root,self.m),0); self.assertEqual(a,self.state('a')); self.assertEqual(b,self.state('b'))
        self.m['jobs'][1]['payload']='changed'; self.assertEqual(w.run(self.root,self.m),0)
        self.assertNotEqual(a['attempt'],self.state('a')['attempt']); self.assertNotEqual(b['attempt'],self.state('b')['attempt'])
        self.assertTrue((self.root/a['attempt']/'artifact.json').exists())
    def test_corrupted_artifact_not_skipped(self):
        self.assertEqual(w.run(self.root,self.m),0); a=self.state('a'); (self.root/a['attempt']/'artifact.json').write_text('bad')
        self.assertEqual(w.run(self.root,self.m),0); self.assertNotEqual(a['attempt'],self.state('a')['attempt'])
    def test_negative_manifests(self):
        mutations=[lambda m:m.update(enabled=False),lambda m:m.update(native_jobs_authorized=True),lambda m:m.update(expires_utc='2000-01-01T00:00:00+00:00'),lambda m:m.update(worker_sha256='0'*64),lambda m:m.update(executable_sha256='0'*64),lambda m:m.update(max_parallel_jobs=2),lambda m:m['jobs'][0].update(kind='gm26_export'),lambda m:m['jobs'][0].update(argv=['echo']),lambda m:m['jobs'][0].update(id='../escape'),lambda m:m['jobs'][0].update(requires=['missing']),lambda m:m['jobs'][1].update(requires=['b']),lambda m:m['jobs'][0].update(wall_timeout_seconds=31),lambda m:m['jobs'][0].update(id='a'),lambda m:m.update(local_approval='')]
        for i,mutation in enumerate(mutations):
            with self.subTest(i=i):
                m=copy.deepcopy(self.m); mutation(m)
                with self.assertRaises(w.Blocked): w.run(self.root,m)
        self.assertFalse((self.root/'runner.lock').exists())
    def test_resource_block_and_dependencies(self):
        self.m['jobs'][1]['min_free_disk_bytes']=2**50
        self.assertEqual(w.run(self.root,self.m),2); self.assertEqual(self.state('a')['status'],'BLOCKED'); self.assertEqual(self.state('b')['status'],'BLOCKED')
    def test_os_lock(self):
        with (self.root/'runner.lock').open('w') as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(w.Blocked): w.run(self.root,self.m)
    def test_interrupt_conservative(self):
        w.atomic(self.root/'a.json',{'status':'RUNNING','id':'a'})
        self.assertEqual(w.run(self.root,self.m),2); self.assertEqual(self.state('a')['status'],'INTERRUPTED'); self.assertEqual(self.state('b')['status'],'BLOCKED')
    def test_stop_and_symlink(self):
        (self.root/'stop.request').touch(); self.assertEqual(w.run(self.root,self.m),2); self.assertEqual(self.state('a')['status'],'CANCELLED')
        (self.root/'stop.request').unlink(); (self.root/'a.json').unlink(); (self.root/'a.json').symlink_to(Path(self.tmp.name)/'outside')
        with self.assertRaises(w.Blocked): w.run(self.root,self.m)
    def test_cli_real_process(self):
        mf=Path(self.tmp.name)/'queue.json'; mf.write_text(json.dumps(self.m))
        for _ in range(2):
            p=subprocess.run([sys.executable,str(Path(w.__file__).resolve()),'run',str(self.root),'--manifest',str(mf)],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('SKIP verified PASS',p.stdout)
    def test_duplicate_json_keys(self):
        p=self.root/'bad.json';p.write_text('{"enabled":false,"enabled":true}')
        with self.assertRaises(w.Blocked): w.load(p)

if __name__=='__main__': unittest.main()
