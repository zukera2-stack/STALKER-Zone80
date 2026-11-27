from pathlib import Path
from decimal import Decimal as D
import hashlib,json
r=Path(__file__).resolve().parent
def read(p):
 b=p.read_bytes(); a=b.decode('ascii').splitlines(); h={k.lower():D(v) for k,v in (l.split() for l in a[:6])}
 n=int(h['ncols']);v=[list(map(D,l.split())) for l in a[6:]][::-1]
 assert h['nrows']==n and len(v)==n and all(len(row)==n and all(x.is_finite() and x!=h['nodata_value'] for x in row) for row in v)
 return h,v,hashlib.sha256(b).hexdigest()
h,a,ref=read(r/'REF/terrain.asc')
assert ref=='ed061ad8db76e9341607443114d675afcc63665fdaddc1e1a92818b32e79e324'
out={}
for name,ix,iy in [('W',6,10),('E',26,10)]:
 h2,b,digest=read(r/name/'terrain.asc')
 assert h2['ncols']==h2['nrows']==32 and h2['cellsize']==30
 assert h2['xllcorner']==h['xllcorner']+ix*30 and h2['yllcorner']==h['yllcorner']+iy*30
 err=max(abs(b[y][x]-a[y+iy][x+ix]) for y in range(32) for x in range(32))
 assert err==0,err
 out[name]={'sha256':digest,'origin_index':[ix,iy],'count':1024,'max_delta_m':float(err)}
_,w,_=read(r/'W/terrain.asc');_,e,_=read(r/'E/terrain.asc')
assert all(w[y][x+20]==e[y][x] for y in range(32) for x in range(12))
out['shared_nodes']=384
out['shared_node_max_delta_m']=0
p=r/'gm_qc.json';assert not p.exists();p.write_text(json.dumps(out,indent=2));print(json.dumps(out))
