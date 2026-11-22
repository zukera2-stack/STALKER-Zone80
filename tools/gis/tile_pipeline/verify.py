import collections, ctypes as c, json, os, pathlib
from ownership import assign_parts
r=pathlib.Path(os.environ['GIS_TILE_ROOT'])
p=pathlib.Path(os.environ['GIS_MAPPER_HOME'])
dll=os.add_dll_directory(str(p))
g=c.CDLL(str(p/'gdal.dll'))
P,I,D,S=c.c_void_p,c.c_int,c.c_double,c.c_char_p
def call(n,t,args,*v):
    f=getattr(g,n); f.argtypes=args; f.restype=t
    return f(*v)
call('GDALAllRegister',None,[])
def raster(path):
    ds=call('GDALOpen',P,[S,I],os.fsencode(path),0)
    assert ds,path
    try:
        size=tuple(call('GDALGetRaster'+axis+'Size',I,[P],ds) for axis in 'XY')
        assert size==(32,32),size
        tr=(D*6)()
        assert call('GDALGetGeoTransform',I,[P,c.POINTER(D)],ds,tr)==0
        sr=call('GDALGetSpatialRef',P,[P],ds)
        epsg=call('OSRGetAuthorityCode',S,[P,S],sr,None) if sr else None
        b=call('GDALGetRasterBand',P,[P,I],ds,1)
        has=I()
        nd=call('GDALGetRasterNoDataValue',D,[P,c.POINTER(I)],b,c.byref(has))
        assert has.value
        a=(D*1024)()
        assert call('GDALRasterIO',I,[P,I,I,I,I,I,P,I,I,I,I,I],b,0,0,0,32,32,a,32,32,7,0,0)==0
        return tuple(tr),epsg,nd,[None if v==nd else v for v in a],call('GDALGetRasterDataType',I,[P],b)
    finally: call('GDALClose',None,[P],ds)
results={}
print('GDAL:', call('GDALVersionInfo', S, [S], b'--version').decode())
source=json.loads((r/'features.geojson').read_text())
src={f['properties']['source_id']:f['geometry'] for f in source['features']}
seams={}
raw_ids=collections.Counter()
final_ids=collections.Counter()
for tile,left in [('W',400000),('E',400256)]:
    d=r/tile
    a=raster(d/'dem.asc')
    expected=(left,8,0,5700256,0,-8)
    assert a[0]==expected
    results[tile]={}
    for suffix in ('asc','tif'):
        b=raster(d/f'out.{suffix}')
        assert b[0]==expected
        if suffix=='tif': assert b[1]==b'32636' and b[4]==6, (b[1],b[4])
        assert b[3]==a[3],(tile,suffix,[(i,x,y) for i,(x,y) in enumerate(zip(a[3],b[3])) if x!=y][:10])
        results[tile][suffix]={'transform':b[0],'epsg':b[1].decode() if b[1] else None,'nodata':b[2],'masked':b[3].count(None)}
        seams[tile,suffix]=b[3][31::32] if tile=='W' else b[3][::32]
    raw=json.loads((d/'out.geojson').read_text())
    assert raw['crs']['properties']['name'].endswith('::32636')
    items={f['properties']['source_id']:f for f in raw['features']}
    assert len(items)==len(raw['features']) and set(items)=={tile,'S','R','B'}
    raw_ids.update(items.keys())
    assert items[tile]['geometry']==src[tile] and items['S']['geometry']==src['S']
    right=left+256
    for fid in ('R','B'):
        geom=items[fid]['geometry']
        pts=geom['coordinates'] if fid=='R' else geom['coordinates'][0]
        full=src[fid]['coordinates'] if fid=='R' else src[fid]['coordinates'][0]
        assert geom['type']==src[fid]['type']
        assert pts==[[min(right,max(left,x)),y] for x,y in full],(tile,fid,pts)
    final=assign_parts(items.values(), tile)
    final_ids.update(f['properties']['source_id'] for f in final)
    raw['features']=final
    raw.pop('name',None)
    (d/'owned.geojson').write_text(json.dumps(raw,sort_keys=True,indent=2)+'\n')
    results[tile]['raw_ids']=sorted(items)
    results[tile]['owned_ids']=[f['properties']['part_id'] for f in final]
for suffix in ('asc','tif'): assert seams['W',suffix]==seams['E',suffix] and seams['W',suffix].count(None)==1
assert raw_ids=={'W':1,'E':1,'S':2,'R':2,'B':2}
assert final_ids=={'W':1,'E':1,'S':1,'R':2,'B':2}
for name in ('dem.asc','crop.geojson','tile.gms','out.tif','out.asc','out.geojson'):
    runs=[next(f['sha256'] for f in json.loads((r/f'run-{k}.json').read_text())['files'] if f['name']==name) for k in (1,3)]
    assert runs[0]==runs[1],(name,runs)
results['west_outputs_identical']=True
results['east_unchanged']= (r/'east-unchanged.json').exists()
assert results['east_unchanged']
(r/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
