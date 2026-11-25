"""Read the existing foundation manifest generator and print a synthetic report."""
import argparse
import json
from pathlib import Path
import sys
from sector_manager import Grid, plan, dirty, validate_seams, digest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,required=True)
    args=parser.parse_args()
    root=args.repo_root.resolve()
    sys.path.insert(0,str(root/'tools'/'validation'))
    from build_sector_manifests import manifests
    items=manifests(root)
    grid=Grid.from_foundation(items,(-3000000,5000000),100000)
    s=grid.step_mm; h=digest('synthetic-demo-rules-v1')
    def feature(name,kind,points,revision='1'):
        return {'id':name,'kind':kind,'points_mm':[grid.projected(p) for p in points],'revision':revision}
    f=[feature('anchor','point',[(s,s//2)]),feature('line','segment',[(s-101,s//2),(s+102,s//2+1)]),feature('inside','point',[(s//2,s//2)])]
    baseline=plan(grid,f,h)
    changed=[dict(x,revision='2') if x['id']=='inside' else x for x in f]
    after=plan(grid,changed,h)
    report={'scope':'synthetic-only','sector_count':len(items),'shared_edges':sum(len(v['neighbors']) for v in baseline['sectors'].values())//2,'seam_issues':validate_seams(baseline),'anchor_owner':grid.owner(f[0]['points_mm'][0]),'dirty_after_interior_edit':dirty(baseline,after),'baseline_sha256':digest(baseline),'reordered_sha256':digest(plan(grid,list(reversed(f)),h)),'production_crs':None,'native_generation':False}
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0 if not report['seam_issues'] and report['baseline_sha256']==report['reordered_sha256'] else 2

if __name__=='__main__': raise SystemExit(main())
