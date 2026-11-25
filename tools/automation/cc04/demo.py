"""Read-only reproduction of the owner v03 review; stdout is report, not game config."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import config_builder as c


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--v03-zip',type=Path,required=True)
    p.add_argument('--repo-root',type=Path)
    a=p.parse_args()
    with zipfile.ZipFile(a.v03_zip) as z:
        raw=z.read('Zone80_v03_EDITOR_ONLY.grma3a')
    b=a.baseline.read_bytes();i=a.inventory.read_bytes();cfg=c.load_bytes(raw)
    r=c.compile_review(c.split_config(cfg),c.load_bytes(b),c.load_bytes(i))
    result={'status':r['status'],'input_sha256':{'baseline':hashlib.sha256(b).hexdigest(),'inventory':hashlib.sha256(i).hexdigest(),'v03_config':hashlib.sha256(raw).hexdigest(),'v03_zip':hashlib.sha256(a.v03_zip.read_bytes()).hexdigest()},'resource_counts':r['resource_counts'],'material_definitions':len(cfg['Materials']['Definitions']),'material_usages':len(r['material_lock']),'road_profiles':len(cfg['Roads']),'module_hashes':r['module_hashes'],'config_sha256_canonical':r['config_sha256_canonical'],'missing_surfaces':r['missing_surfaces'],'blockers':r['blockers'],'native_generation_authorized':False}
    if a.repo_root:
        cats={n:c.load(a.repo_root/'configs/grm'/f'{n}.references.json') for n in ('vegetation','roads','materials','infrastructure')}
        audit=c.reference_audit(cats);audit.pop('paths');result['reference_catalogs']=audit
        result['zpb_review']=c.zpb_review(c.load(a.repo_root/'docs/integration/assets.manifest.json.example'))
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=='__main__':main()
