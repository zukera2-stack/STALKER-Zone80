"""Independent synthetic child-output verifier; no worker integration, no real data."""
import collections, hashlib, json, math, os, pathlib, subprocess, sys, tempfile

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def validate(result, job):
    require(result['schema_version']==1 and result['scope']=='synthetic_review_only' and result['export_authorized'] is False, 'scope')
    for k in ('fixture','road_state','height_delta_m','config_sha256','cache_sha256','osm_sha256'):
        require(result[k]==job[k], 'job binding '+k)
    expected=sha('\n'.join(['cc05p-job-v1',job['scope'],job['fixture'],job['road_state'],str(job['height_delta_m']),job['config_sha256'],job['cache_sha256'],job['osm_sha256'],'false']))
    require(result['job_id']==expected,'job identity')
    catalog=result['catalog']; counts=collections.Counter(e['Status'] for e in catalog)
    require(len(set(e['Name'] for e in catalog))==27 and counts=={'enabled_synthetic':12,'pending_review':13,'disabled_verified_empty':1,'disabled_zpb':1}, 'catalog dispositions')
    layers={e['Name'] for e in catalog if e['Status']=='enabled_synthetic'}
    entries=result['records']; require(len(entries)==result['total'],'count'); ids=[r['id'] for r in entries];require(ids==sorted(set(ids)),'unique sorted identities')
    for r in entries:
        require(r['id']==sha('cc05p-placement-v1\n'+job['fixture']+'\n'+r['key']), 'placement identity')
        require(r['content']==sha(r['payload']) and r['payload'].startswith(r['key']+';'), 'payload hash')
        fields=r['key'].split(';');require(len(fields)==9 and fields[0]==r['layer'] and r['layer'] in layers,'layer/key')
        x,y=map(float,fields[2:4]);require(all(math.isfinite(float(v)) for v in fields[2:8]+r['payload'].split(';')[-2:]),'finite transform')
        expected_sector='held' if r['reason'] else ('left' if x<240 else 'right')
        require(r['sector']==expected_sector and (r['reason'] or (0<=x<480 and 0<=y<480)),'ownership/review')
        require(r['source_feature_id'] is None and r['provenance']=='layer_and_fixture_only','no fabricated lineage')
    counts=collections.Counter(r['sector'] for r in entries)
    require(all(counts[k]==result[k] for k in ('left','right','held')),'reconcile')
    old_digest=sha(result['source_review']+'\n'+'\n'.join(r['key']+'|'+r['reason']+'|'+r['sector'] for r in sorted(entries,key=lambda r:r['key'])))
    require(result['review_sha256']==old_digest,'review digest')
    return entries

def main():
    dotnet,dll,config,cache,jobfile=map(pathlib.Path,sys.argv[1:])
    base=json.loads(jobfile.read_text())
    runs={}
    env=dict(os.environ,DOTNET_PROCESSOR_COUNT='2',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1')
    with tempfile.TemporaryDirectory(prefix='cc05p-') as temp:
        root=pathlib.Path(temp); path=root/'job.json'
        def call(raw, cache_path=cache):
            path.write_bytes(raw)
            return subprocess.run([str(dotnet),str(dll),str(config),str(cache_path),str(path)],capture_output=True,timeout=30,env=env)
        for name,state,delta,reorder in [('abandoned','abandoned',0,False),('repeat','abandoned',0,True),('shift','abandoned',100,False),('operational','operational',0,False),('unknown','unknown',0,False)]:
            j=dict(base,road_state=state,height_delta_m=delta)
            raw=json.dumps(dict(reversed(list(j.items()))) if reorder else j,indent=2 if reorder else None).encode()
            p=call(raw); require(p.returncode==0,p.stderr.decode()[:500]); lines=p.stdout.decode().splitlines(); records=[line[12:] for line in lines if line.startswith('RESULT_JSON ')];require(len(records)==1 and lines[-1]=='PASS guarded synthetic job; no export/runtime approval','complete output')
            r=json.loads(records[0]); entries=validate(r,j); runs[name]=r
            print(f'PASS {name} job={r["job_id"]} records={r["total"]} held={r["held"]} left={r["left"]} right={r["right"]} on_road={r["point_pass_road_plants"]} manifest_sha256={sha(records[0])}')
        a,b,c,d,u=[runs[k] for k in ('abandoned','repeat','shift','operational','unknown')]
        require(a==b,'repeat/order canonicalization');require(a['job_id']!=c['job_id'] and a['grid_sha256']!=c['grid_sha256'] and a['review_sha256']==c['review_sha256'],'shift identity')
        require(a['mask_sha256']==c['mask_sha256'] and a['road_sha256']==c['road_sha256'],'shift geometry')
        for x,y in zip(a['records'],c['records'],strict=True):
            require(x['id']==y['id'] and x['content']!=y['content'] and abs(float(y['payload'].split(';')[-1])-float(x['payload'].split(';')[-1])-100)<.001,'stable identity / height response')
        require(d['records']==u['records'] and d['job_id']!=u['job_id'] and d['review_sha256']!=u['review_sha256'],'unknown state distinct')
        print('PASS canonical repeat, stable logical IDs, +100m payload change, unknown state distinct')
        invalid=[('real_scope',dict(base,scope='production')),('export',dict(base,export=True)),('fixture',dict(base,fixture='real_pripyat')),('version',dict(base,schema_version=2)),('state',dict(base,road_state='guess')),('delta',dict(base,height_delta_m=10)),('float_delta',dict(base,height_delta_m=0.0)),('boolean_delta',dict(base,height_delta_m=False)),('config_hash',dict(base,config_sha256='0'*64)),('cache_hash',dict(base,cache_sha256='0'*64)),('osm_hash',dict(base,osm_sha256='0'*64)),('extra_command',dict(base,command='not allowed')),('extra_layers',dict(base,layers=['BuildingGenerator'])),('missing', {k:v for k,v in base.items() if k!='road_state'}),('wrong_type',dict(base,export='false')),('array',[])]
        invalid_raw=[(n,json.dumps(j).encode()) for n,j in invalid]+[('duplicate_key',json.dumps(base).replace('"export": false','"export": false, "export": false').encode()),('malformed',b'{'),('oversize',b' '*8193)]
        for name,raw in invalid_raw:
            p=call(raw);require(p.returncode==2 and b'RESULT_JSON ' not in p.stdout and b'CATALOG ' not in p.stdout,'bad job accepted '+name);print('REFUSED',name,'exit=2')
        changed=root/'cache.json';changed.write_bytes(cache.read_bytes()+b' ');p=call(json.dumps(base).encode(),changed);require(p.returncode==2 and b'RESULT_JSON ' not in p.stdout,'changed cache');print('REFUSED changed_cache exit=2')
        # Independent validator rejects tampered output; not a signature or hostile-process security boundary.
        import copy
        for name,mutate in [('job',lambda m:m.update(job_id='0'*64)),('missing_record',lambda m:m['records'].pop()),('payload',lambda m:m['records'][0].update(payload='forged')),('held_sector',lambda m:m['records'][0].update(sector='bogus')),('review',lambda m:m.update(review_sha256='0'*64)),('export',lambda m:m.update(export_authorized=True))]:
            fake=copy.deepcopy(a);mutate(fake)
            try: validate(fake,base)
            except ValueError: print('OUTPUT_REFUSED',name)
            else: raise ValueError('tampered output accepted '+name)
    print(f'PASS 5 native jobs, {len(invalid_raw)+1} input refusals, 6 output refusals; synthetic review only')

if __name__=='__main__': main()
