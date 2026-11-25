"""CC05Q candidate: closed native snapshot gate, no process execution."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

JOB_KEYS = set('schema_version scope fixture road_state height_delta_m config_sha256 cache_sha256 osm_sha256 export'.split())
ENVELOPE_KEYS = set('schema_version kind scope issue reviewed_code_sha approval expires_utc max_attempts wall_timeout_seconds max_sampled_group_rss_bytes min_available_ram_bytes min_free_disk_bytes files'.split())
FIXTURE = 'cc05o-inline-480m-v1'
OSM = 'd20dbe01972c981946bf17254f94a8180cbbd7c867e9741d88a91301fa0a222c'
CONFIG = '418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e'
CACHE = '1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94'
REQUIRED = {'runtime/dotnet', 'child/Zone80.JobProbe.dll', 'child/Zone80.JobProbe.deps.json', 'child/Zone80.JobProbe.runtimeconfig.json', 'inputs/config.grma3a', 'inputs/modelinfo.json', 'inputs/job.json', 'code/worker.py', 'code/cc01_base.py', 'code/verify_job.py', 'code/preflight.py'}


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def parse(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            check(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda v: check(False, 'nonfinite JSON'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def hexstr(value, n):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{'+str(n)+'}', value) is not None


def validate_job(job):
    check(type(job) is dict and set(job) == JOB_KEYS, 'job fields')
    check(type(job['schema_version']) is int and job['schema_version'] == 1 and job['scope'] == 'synthetic_review_only' and job['fixture'] == FIXTURE and job['export'] is False, 'job scope')
    check(job['road_state'] in ('abandoned', 'operational', 'unknown') and type(job['height_delta_m']) is int and job['height_delta_m'] in (0, 100), 'job values')
    check((job['config_sha256'], job['cache_sha256'], job['osm_sha256']) == (CONFIG, CACHE, OSM), 'fixture pins')


def validate_envelope(m, now):
    check(type(m) is dict and set(m) == ENVELOPE_KEYS, 'envelope fields')
    check(type(m['schema_version']) is int and m['schema_version'] == 1 and m['kind'] == 'cc05p_native_synthetic' and m['scope'] == 'synthetic_review_only' and type(m['issue']) is int and m['issue'] == 42, 'envelope scope')
    check(hexstr(m['reviewed_code_sha'], 40) and isinstance(m['approval'], str) and 0 < len(m['approval'].strip()) <= 200, 'review/approval reference')
    deadline = dt.datetime.fromisoformat(m['expires_utc'])
    check(deadline.tzinfo is not None and now.tzinfo is not None and now < deadline <= now + dt.timedelta(days=7), 'approval expiry')
    for k, upper in [('max_attempts', 2), ('wall_timeout_seconds', 30), ('max_sampled_group_rss_bytes', 2**31), ('min_available_ram_bytes', 2**50), ('min_free_disk_bytes', 2**50)]:
        check(type(m[k]) is int and 0 < m[k] <= upper, 'invalid limit '+k)
    files = m['files']
    check(type(files) is dict and REQUIRED <= set(files) and len(files) <= 20000, 'incomplete snapshot')
    for path, digest in files.items():
        check(isinstance(path, str) and all(re.fullmatch('[A-Za-z0-9_.+-]+', p) and p not in ('.', '..') for p in path.split('/')) and path.split('/')[0] in ('runtime', 'child', 'inputs', 'code') and hexstr(digest, 64), 'unsafe snapshot entry')
    check(files['inputs/config.grma3a'] == CONFIG and files['inputs/modelinfo.json'] == CACHE, 'input pin mismatch')


def prepare(root, m, now):
    """Trusted local snapshot only. Returns review plan, never launch approval."""
    validate_envelope(m, now)
    check(root.is_dir() and root.is_absolute() and root == root.resolve(), 'unsafe root')
    actual = {}
    for path in root.rglob('*'):
        check(not path.is_symlink(), 'symlink refused')
        if path.is_dir():
            continue
        check(path.is_file(), 'special file refused')
        rel = path.relative_to(root).as_posix()
        check(rel in m['files'], 'unlisted snapshot file')
        actual[rel] = sha(path)
    check(actual == m['files'], 'snapshot mismatch')
    jobpath = root / 'inputs/job.json'
    check(jobpath.stat().st_size <= 8192, 'oversized job')
    job = parse(jobpath.read_bytes())
    validate_job(job)
    identity = hashlib.sha256(json.dumps(m, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    argv = [str(root / p) for p in ('runtime/dotnet', 'child/Zone80.JobProbe.dll', 'inputs/config.grma3a', 'inputs/modelinfo.json', 'inputs/job.json')]
    return {'identity': identity, 'argv': argv, 'job': job, 'launch_authorized': False}


def output_gate(stdout, exit_code, job, verifier):
    """Use CC05P verify_job.validate; this gate itself never publishes PASS."""
    validate_job(job)
    check(type(exit_code) is int and exit_code == 0 and len(stdout) <= 16 * 1024 * 1024, 'exit/output limit')
    lines = stdout.decode('utf-8').splitlines()
    results = [line[12:] for line in lines if line.startswith('RESULT_JSON ')]
    check(len(results) == 1 and lines[-1] == 'PASS guarded synthetic job; no export/runtime approval', 'incomplete or multiple results')
    result = parse(results[0])
    verifier(result, job)
    return result
