import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import preflight as p

NOW = dt.datetime(2026, 11, 25, tzinfo=dt.timezone.utc)

def job():
    return dict(schema_version=1, scope='synthetic_review_only', fixture=p.FIXTURE, road_state='abandoned', height_delta_m=0, config_sha256=p.CONFIG, cache_sha256=p.CACHE, osm_sha256=p.OSM, export=False)


def envelope(files):
    return dict(schema_version=1, kind='cc05p_native_synthetic', scope='synthetic_review_only', issue=42, reviewed_code_sha='a'*40, approval='unit fixture only', expires_utc=(NOW+dt.timedelta(hours=1)).isoformat(), max_attempts=1, wall_timeout_seconds=30, max_sampled_group_rss_bytes=1024**3, min_available_ram_bytes=1024, min_free_disk_bytes=1024, files=files)


class GateTests(unittest.TestCase):
    def test_job(self):
        p.validate_job(job())
        for change in (dict(scope='production'), dict(export=True), dict(height_delta_m=False), dict(road_state='guess'), dict(config_sha256='0'*64), dict(argv=[])):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.validate_job(dict(job(), **change))

    def test_json(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.parse(raw)

    def test_envelope(self):
        files = dict.fromkeys(p.REQUIRED, 'a'*64)
        files.update({'inputs/config.grma3a':p.CONFIG, 'inputs/modelinfo.json':p.CACHE})
        m = envelope(files)
        p.validate_envelope(m, NOW)
        for change in (dict(issue=True), dict(scope='real'), dict(max_attempts=3), dict(wall_timeout_seconds=31), dict(max_sampled_group_rss_bytes=0), dict(expires_utc=NOW.isoformat()), dict(approval=' '), dict(shell='bad'), dict(files=dict(files, **{'runtime/../escape':'a'*64})), dict(files={})):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.validate_envelope(dict(m, **change), NOW)

    def test_snapshot_and_invalidation(self):
        # Unit fixtures are bytes, not a .NET runtime or actual GRM input.
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            for name in p.REQUIRED:
                f=root/name; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(name.encode())
            with patch.multiple(p, CONFIG=p.sha(root/'inputs/config.grma3a'), CACHE=p.sha(root/'inputs/modelinfo.json')):
                (root/'inputs/job.json').write_text(json.dumps(job()))
                files={name:p.sha(root/name) for name in p.REQUIRED}
                m=envelope(files)
                a=p.prepare(root,m,NOW)
                self.assertFalse(a['launch_authorized'])
                self.assertEqual(a,p.prepare(root,m,NOW))
                self.assertEqual(len(a['argv']),5)
                target=root/'child/Zone80.JobProbe.dll'; target.write_bytes(b'changed')
                with self.assertRaises(ValueError): p.prepare(root,m,NOW)
                updated=dict(files, **{'child/Zone80.JobProbe.dll':p.sha(target)})
                self.assertNotEqual(a['identity'],p.prepare(root,envelope(updated),NOW)['identity'])
                extra=root/'child/unlisted.dll'; extra.write_bytes(b'x')
                with self.assertRaises(ValueError): p.prepare(root,envelope(updated),NOW)
                extra.unlink(); extra.symlink_to(target)
                with self.assertRaises(ValueError): p.prepare(root,envelope(updated),NOW)
                extra.unlink(); target.unlink()
                with self.assertRaises(ValueError): p.prepare(root,envelope(updated),NOW)

    def test_output_routing(self):
        # Spy verifies routing only; NOT a native output or independent GRM acceptance.
        calls=[]
        def verifier(r,j):
            calls.append((r,j))
            if r != {'unit':True}: raise ValueError('unit rejection')
        tail=b'PASS guarded synthetic job; no export/runtime approval\n'
        good=b'RESULT_JSON {"unit":true}\n'+tail
        self.assertEqual(p.output_gate(good,0,job(),verifier),{'unit':True})
        self.assertEqual(calls, [({'unit':True},job())])
        for raw,rc in ((good,1),(tail,0),(good+good,0),(good+b'after',0),(b'RESULT_JSON {"unit":true,"unit":false}\n'+tail,0),(b'RESULT_JSON {"unit":false}\n'+tail,0)):
            with self.subTest(raw=raw,rc=rc), self.assertRaises(ValueError):
                p.output_gate(raw,rc,job(),verifier)

if __name__=='__main__': unittest.main()
