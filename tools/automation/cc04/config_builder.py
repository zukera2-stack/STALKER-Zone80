"""CC-04: deterministic configuration review. Never emits a native executable config."""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

GROUPS = {
    'vegetation': ('BasicCollections', 'ClusterCollections', 'NaturalRows'),
    'roads': ('Roads', 'Bridges'),
    'materials': ('Materials',),
    'infrastructure': ('Objects', 'Ponds', 'Fences', 'Railways', 'Sidewalks'),
    'buildings': ('Buildings',),
    'dependencies': ('BaseWorldName', 'BaseDependency', 'Dependencies'),
}
USAGES = set('Default DefaultUrban DefaultIndustrial IceSurface ScreeSurface Coastline OceanGround ForestGround Sand Grass Meadow FarmLand RiverGround LakeGround RockGround Asphalt'.split())
CLASS = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load_bytes(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            need(k not in out, 'duplicate JSON key: ' + k)
            out[k] = v
        return out
    def bad(s):
        raise ValueError('nonfinite constant: ' + s)
    result = json.loads(raw, object_pairs_hook=unique, parse_constant=bad)
    canonical(result)  # also rejects exponent overflow
    return result


def load(path):
    return load_bytes(Path(path).read_bytes())


def resource_path(s):
    need(isinstance(s, str), 'resource path must be string')
    s = s.replace('/', '\\').lower()
    if s.startswith('\\'):
        s = s[1:]
    need(re.fullmatch(r'(?:a3|z)\\(?:[a-z0-9_-]+\\)+[a-z0-9_-][a-z0-9_.-]*\.(?:p3d|paa|rvmat)', s) is not None, 'invalid virtual resource path: ' + s)
    return s


def references(value):
    if isinstance(value, str) and re.search(r'\.(p3d|paa|rvmat)$', value, re.I):
        yield resource_path(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from references(v)
    elif isinstance(value, list):
        for v in value:
            yield from references(v)


def minimal_namespace(p):
    return p.startswith(('a3\\', 'z\\stalker_pripyat_buildings\\addons\\', 'z\\stalker_zone80\\addons\\'))


def split_config(config):
    need(type(config) is dict and set(config) == {k for keys in GROUPS.values() for k in keys}, 'unexpected top-level config schema')
    canonical(config)
    return {g: {k: copy.deepcopy(config[k]) for k in keys} for g, keys in GROUPS.items()}


def material_lock(config):
    defs = config['Materials']['Definitions']
    need(type(defs) is list and len(defs) == 11, 'expected 11 material definitions')
    result = {}
    ids = set()
    for d in defs:
        usages = d['Usages']
        need(type(usages) is list and usages and all(isinstance(u, str) and u in USAGES for u in usages), 'unknown material usage')
        color = d['Material']['Id']
        need(isinstance(color, str) and re.fullmatch('[0-9A-Fa-f]{8}', color) and color[-2:].upper() == 'FF', 'invalid opaque RGBA material ID')
        color = color.upper()
        need(color[:6] not in ids, 'duplicate RGB material ID')
        ids.add(color[:6])
        for u in usages:
            need(u not in result, 'duplicate usage: ' + u)
            result[u] = color
    need(set(result) == USAGES, 'missing material usage')
    return result


def surface_matches(pattern, path):
    # Pinned GRM SurfaceConfig.Match: trailing * prefix, else exact; filename without extension.
    need(isinstance(pattern, str) and bool(pattern) and pattern != '*', 'invalid surface file mask')
    stem = path.rsplit('\\', 1)[-1].rsplit('.', 1)[0].lower()
    pattern = pattern.lower()
    return stem.startswith(pattern[:-1]) if pattern.endswith('*') else stem == pattern


def validate_config(config, lock, road_ids):
    split_config(config)
    need(material_lock(config) == lock, 'usage-to-RGB lock changed')
    need(config['Buildings'] == {} and config['Sidewalks'] == [] and type(config['Ponds']) is dict and all(v is None for v in config['Ponds'].values()), 'disabled feature enabled')
    need(config['Dependencies'] == [], 'external dependency list not empty')
    for k in ('BaseWorldName', 'BaseDependency'):
        need(isinstance(config[k], str) and CLASS.fullmatch(config[k]), 'invalid base class')
    roads = config['Roads']
    need(type(roads) is list and len(roads) == 9 and len({r['Id'] for r in roads}) == 9 and set(r['Id'] for r in roads) == set(road_ids), 'road ID lock changed')
    for r in roads:
        need(r['ProceduralStreetLamps'] == 'None' and r['HasSideWalks'] is False and r['DistanceBetweenStreetLamps'] is None and r['DistanceBetweenStreetLampsMax'] is None, 'automatic road objects enabled')
        need(all(type(r[k]) in (float,int) and math.isfinite(r[k]) and r[k] > 0 for k in ('Width','TextureWidth','ClearWidth')), 'invalid road widths')
        for k, ext in [('Texture','.paa'),('TextureEnd','.paa'),('Material','.rvmat')]:
            need(resource_path(r[k]).endswith(ext), 'wrong road resource kind')
    missing_surfaces = []
    surface_names = set()
    for d in config['Materials']['Definitions']:
        m = d['Material']
        co, no = resource_path(m['ColorTexture']), resource_path(m['NormalTexture'])
        need(co.endswith('_co.paa') and no == co[:-7]+'_nopx.paa', 'color/normal stem mismatch')
        s = d.get('Surface')
        if s is None:
            need(d.get('Data') is None, 'material data without surface')
            missing_surfaces.extend(d['Usages'])
        else:
            name = s['Name']
            need(isinstance(name,str) and CLASS.fullmatch(name) and name.lower() not in surface_names, 'duplicate or invalid surface name')
            surface_names.add(name.lower())
            need(surface_matches(s['Files'], co), 'surface file mask mismatch: '+name)
            need(type(s['Character']) is list, 'invalid clutter list')
            for cl in s['Character']:
                need(resource_path(cl['Model']).endswith('.p3d'), 'invalid clutter model')
                need(type(cl['Probability']) in (int,float) and 0 <= cl['Probability'] <= 1, 'invalid clutter probability')
    return sorted(missing_surfaces)


def inventory_index(inv):
    need(inv['schema_version'] == 1 and inv['status'] == 'READ_ONLY_LOOSE_FILE_INVENTORY' and inv['errors'] == [], 'inventory rejected')
    known, pairs = {}, {}
    for r in inv['references']:
        p = resource_path(r['virtual_path'])
        need(p not in known and type(r['exists_as_loose_file']) is bool, 'duplicate or invalid inventory entry')
        known[p] = r['exists_as_loose_file']
    for r in inv['ground_texture_candidates']:
        c = resource_path(r['color'])
        need(c not in pairs and c.endswith('_co.paa'), 'duplicate or invalid texture pair')
        n = [resource_path(x) for x in r['normal_candidates']]
        need(len(set(n)) == len(n) and all(x == c[:-7]+'_nopx.paa' for x in n), 'normal texture mismatch')
        pairs[c] = n
    # Preserve contradictory evidence instead of turning explicit absent into present.
    for c, normals in pairs.items():
        if normals:
            for p in [c,*normals]:
                need(known.get(p) is not False, 'conflicting inventory evidence: '+p)
                known[p] = True
    return known


def reference_audit(catalogs):
    """The four main arrays only; do not add additional_reference_candidates."""
    need(set(catalogs)=={'vegetation','roads','materials','infrastructure'}, 'missing reference catalog')
    sections={}
    for name, key in [('vegetation','assets'),('roads','profiles'),('materials','definitions'),('infrastructure','assets')]:
        c=catalogs[name]
        need(c['schema_version']==1 and c['status']=='REFERENCE_ONLY' and c['approved_for_generation'] is False, 'catalog is not reference only')
        need(all(r['approved_for_generation'] is False for r in c[key]), 'reference item marked approved')
        sections[name]=set(references(c[key]))
    paths=set().union(*sections.values())
    return {'count':len(paths),'stock_candidates':sum(p.startswith('a3\\') for p in paths),'external':sum(not p.startswith('a3\\') for p in paths),'sections':{k:len(v) for k,v in sections.items()},'paths':sorted(paths)}


def compile_review(modules, baseline, inventory):
    """Assemble in memory; produce audit/lock only, not .grma3a. Baseline is trusted owner input."""
    need(set(modules)==set(GROUPS), 'module set changed')
    config={}
    for g, keys in GROUPS.items():
        need(type(modules[g]) is dict and set(modules[g])==set(keys), 'module field mismatch: '+g)
        config.update(copy.deepcopy(modules[g]))
    lock=material_lock(baseline)
    road_ids=[r['Id'] for r in baseline['Roads']]
    missing_surfaces=validate_config(config,lock,road_ids)
    known=inventory_index(inventory)
    refs=sorted(set(references(config)))
    records=[]
    for p in refs:
        presence='PRESENT_IN_INVENTORY' if known.get(p) is True else 'ABSENT_LOOSE' if known.get(p) is False else 'UNVERIFIED'
        records.append({'path':p,'presence':presence,'namespace_candidate':minimal_namespace(p),'runtime_approved':False})
    blockers=['NATIVE_GENERATION_NOT_AUTHORIZED','LOCAL_DEPENDENCY_AND_ENTITLEMENT_CLOSURE_NOT_VERIFIED','BASE_WORLD_CLASS_NOT_VERIFIED','NATIVE_PARSER_NOT_RUN','GM_ADAPTER_AND_COMPLETE_HEIGHTS_NOT_VERIFIED','ICE_POLICY_NOT_APPROVED']
    if any(not r['namespace_candidate'] for r in records): blockers.append('EXTERNAL_RESOURCE_PATHS')
    if any(r['presence']!='PRESENT_IN_INVENTORY' for r in records): blockers.append('UNVERIFIED_OR_MISSING_PATHS')
    if missing_surfaces: blockers.append('MISSING_SURFACE_METADATA')
    if config['BaseDependency'].lower().startswith('arm_'): blockers.append('EXTERNAL_BASE_DEPENDENCY')
    report={'status':'REVIEW_ONLY_GENERATION_BLOCKED','native_generation_authorized':False,'config_sha256_canonical':digest(config),'baseline_sha256_canonical':digest(baseline),'inventory_sha256_canonical':digest(inventory),'module_hashes':{g:digest(modules[g]) for g in GROUPS},'material_lock':lock,'missing_surfaces':missing_surfaces,'resource_counts':{'total':len(records),'inventory_present':sum(r['presence']=='PRESENT_IN_INVENTORY' for r in records),'stock_unverified':sum(r['namespace_candidate'] and r['presence']!='PRESENT_IN_INVENTORY' for r in records),'external':sum(not r['namespace_candidate'] for r in records),'runtime_approved':0},'records':records,'blockers':sorted(blockers)}
    return report


def synthetic_dependency_closure(patches, roots):
    """Graph validation only. Every row explicitly synthetic; never proves actual engine closure."""
    index={}
    for row in patches:
        need(set(row)=={'name','requires','approved','scope'} and row['scope']=='SYNTHETIC_ONLY' and row['approved'] is True,'unapproved synthetic dependency')
        name=row['name']; need(isinstance(name,str) and CLASS.fullmatch(name) and name.lower() not in index,'duplicate dependency class')
        req=row['requires'];need(type(req) is list and all(isinstance(x,str) and CLASS.fullmatch(x) for x in req) and len(set(x.lower() for x in req))==len(req),'invalid dependency references')
        index[name.lower()]=[x.lower() for x in req]
    done=set();active=set()
    def visit(n):
        need(n in index,'missing dependency '+n);need(n not in active,'dependency cycle '+n)
        if n in done:return
        active.add(n)
        for r in index[n]:visit(r)
        active.remove(n);done.add(n)
    for root in roots:
        need(isinstance(root,str) and CLASS.fullmatch(root),'invalid root');visit(root.lower())
    return sorted(done)


def zpb_review(manifest):
    """No model is selectable in CC-04; reserved candidate metadata cannot become runtime approval."""
    need(set(manifest)=={'schema_version','addon_release','source_commit','assets'} and manifest['schema_version']==1,'invalid ZPB manifest')
    ids=set();paths=set();classes=set();rows=[]
    for a in manifest['assets']:
        mid=a['model_id'];p=resource_path(a['p3d_path']);cls=a['classname']
        need(isinstance(mid,str) and re.fullmatch(r'zpb\.[a-z0-9_.]+',mid) and mid not in ids,'duplicate or invalid model ID')
        package=a['package'];need(isinstance(package,str) and re.fullmatch('[a-z0-9_]+',package),'invalid package')
        need(p.startswith('z\\stalker_pripyat_buildings\\addons\\'+package+'\\') and p.endswith('.p3d') and p not in paths,'invalid or duplicate model path')
        need(cls is None or isinstance(cls,str) and CLASS.fullmatch(cls) and cls.lower() not in classes,'duplicate or invalid classname')
        need(a['status'] in ('CANDIDATE','MODEL_READY','RETIRED'),'invalid model status')
        need(a['pbo_filename']=='zpb_'+package+'.pbo' and isinstance(a['cfgpatches'],str) and CLASS.fullmatch(a['cfgpatches']),'invalid package metadata')
        ids.add(mid);paths.add(p)
        if cls:classes.add(cls.lower())
        rows.append({'model_id':mid,'path':p,'status':a['status'],'selectable':False,'reason':'NOT_MODEL_READY' if a['status']!='MODEL_READY' else 'LOCAL_MODEL_QA_AND_PLACEMENT_GATE_NOT_VERIFIED'})
    return {'manifest_sha256_canonical':digest(manifest),'models':sorted(rows,key=lambda x:x['model_id']),'selectable_count':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline');p.add_argument('candidate');p.add_argument('inventory');p.add_argument('--mode',choices=['review','production'],default='review');a=p.parse_args()
    if a.mode=='production':p.error('production output is disabled at Stage 001')
    try:
        report=compile_review(split_config(load(a.candidate)),load(a.baseline),load(a.inventory))
        print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    except (ValueError,TypeError,KeyError,OSError,AttributeError,OverflowError) as e:
        p.exit(2,'BLOCKED: '+str(e)+'\n')
    return 0  # review completed, not native PASS

if __name__=='__main__':raise SystemExit(main())
