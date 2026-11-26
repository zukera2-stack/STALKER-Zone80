"""Read-only QC for native GM diagnostic outputs. No raster writes or dependencies."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import struct

X, Y, N, CELL = 294373.084, 5698122.108, 64, 30
CONTROL = [(10,10),(20,20),(32,32),(44,44),(53,53)]
# Retain v04 acceptance threshold; v05 native ASCII precision is unverified.
# If native rounding exceeds this, stop and report rather than silently relax.
PAIR_TOL = .002
SOURCE_TOL = 1.0  # engineering diagnostic, not accuracy certification


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def read_file(path, limit):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,'NOT_ORDINARY_FILE')
    require(0 < info.st_size <= limit,'FILE_SIZE')
    return path.read_bytes()


def near(a,b,t=.001):
    return math.isfinite(a) and abs(a-b)<=t


def check_values(values, nodata):
    require(len(values)==4096,'VALUE_COUNT')
    require(all(math.isfinite(z) and z!=nodata and -500<=z<=9000 for z in values),'INVALID_HEIGHT')
    require(min(values)!=max(values),'CONSTANT_HEIGHT')


def read_asc(raw):
    lines=raw.decode('utf-8-sig').splitlines()
    require(len(lines)==70,'ASC_ROW_COUNT')
    fields={}
    for line in lines[:6]:
        key,val=line.split(); require(key.lower() not in fields,'ASC_DUPLICATE_HEADER'); fields[key.lower()]=float(val)
    require(set(fields)=={'ncols','nrows','xllcorner','yllcorner','cellsize','nodata_value'},'ASC_HEADER')
    require(fields['ncols']==N and fields['nrows']==N and near(fields['xllcorner'],X) and near(fields['yllcorner'],Y) and near(fields['cellsize'],CELL),'ASC_GRID')
    rows=[list(map(float,line.split())) for line in lines[6:]]
    require(all(len(row)==N for row in rows),'ASC_COLUMN_COUNT')
    values=[z for row in rows for z in row]; check_values(values,fields['nodata_value'])
    return values,fields


def read_tiff(raw):
    # Strict subset: classic uncompressed single-band float32 GeoTIFF, strips or tiles.
    require(raw[:2] in (b'II',b'MM'),'TIFF_BYTE_ORDER')
    endian='<' if raw[:2]==b'II' else '>'
    def unpack(fmt, offset):
        size=struct.calcsize(endian+fmt); require(0<=offset<=len(raw)-size,'TIFF_OFFSET')
        return struct.unpack_from(endian+fmt,raw,offset)
    magic,off=unpack('HI',2); require(magic==42,'TIFF_NOT_CLASSIC')
    count,=unpack('H',off); require(0<count<=256,'TIFF_IFD_COUNT')
    tags={}; types={1:'B',2:'c',3:'H',4:'I',11:'f',12:'d'}
    for i in range(count):
        at=off+2+12*i; tag,typ,n,ptr=unpack('HHII',at)
        require(tag not in tags,'TIFF_DUPLICATE_TAG')
        if typ not in types: continue
        size=struct.calcsize(endian+types[typ])*n
        require(n<=100000,'TIFF_TAG_SIZE')
        where=at+8 if size<=4 else ptr
        tags[tag]=unpack(str(n)+types[typ],where)
    def one(tag,default=None):
        value=tags.get(tag,(default,)); require(len(value)==1,'TIFF_TAG_COUNT'); return value[0]
    require(one(256)==64 and one(257)==64,'TIFF_GRID')
    require(one(258)==32 and one(339)==3 and one(277,1)==1 and one(259,1)==1 and one(284,1)==1 and one(274,1)==1 and one(317,1)==1,'TIFF_UNSUPPORTED_ENCODING')
    require(34264 not in tags,'TIFF_TRANSFORM_UNSUPPORTED')
    scale,tie=tags.get(33550,()),tags.get(33922,())
    require(len(scale)==3 and len(tie)==6 and near(scale[0],30) and near(scale[1],30),'TIFF_PIXEL_SCALE')
    keys=tags.get(34735,()); require(len(keys)>=4 and len(keys)==4+4*keys[3] and keys[0]==1,'TIFF_GEOKEYS')
    geo={}
    for i in range(4,len(keys),4):
        k,loc,c,v=keys[i:i+4]
        if loc==0 and c==1: geo[k]=v
    require(geo.get(1024)==1 and geo.get(3072)==32636,'TIFF_CRS')
    require(geo.get(3076,9001)==9001 and geo.get(4099,9001)==9001,'TIFF_UNITS')
    pixel=geo.get(1025,1); require(pixel in (1,2),'TIFF_PIXEL_TYPE')
    west=tie[3]-tie[0]*scale[0]; north=tie[4]+tie[1]*scale[1]
    if pixel==2: west-=15; north+=15
    require(near(west,X) and near(north,Y+1920),'TIFF_ORIGIN')
    if 324 in tags:
        w,h=one(322),one(323); require(type(w)==int and type(h)==int and 0<w<=256 and 0<h<=256,'TIFF_TILE_SIZE')
        offsets,counts=tags[324],tags.get(325,()); nx=(64+w-1)//w; ny=(64+h-1)//h
        require(len(offsets)==len(counts)==nx*ny,'TIFF_TILE_COUNT'); values=[None]*4096
        for i,(p,c) in enumerate(zip(offsets,counts)):
            require(c==w*h*4,'TIFF_TILE_BYTES'); tile=unpack(str(w*h)+'f',p)
            for rr in range(h):
                for cc in range(w):
                    row,col=i//nx*h+rr,i%nx*w+cc
                    if row<64 and col<64: values[row*64+col]=tile[rr*w+cc]
    else:
        offsets,counts=tags.get(273,()),tags.get(279,()); rows=one(278,64)
        require(type(rows)==int and rows>0 and len(offsets)==len(counts)==(64+rows-1)//rows,'TIFF_STRIP_COUNT')
        values=[]
        for i,(p,c) in enumerate(zip(offsets,counts)):
            n=min(rows,64-i*rows)*64; require(c==n*4,'TIFF_STRIP_BYTES'); values.extend(unpack(str(n)+'f',p))
    nodata=-9999.
    if 42113 in tags: nodata=float(b''.join(tags[42113]).rstrip(b'\x00').decode('ascii'))
    check_values(values,nodata)
    return values,{'epsg':32636,'pixel_is': 'area' if pixel==1 else 'point','west':west,'north':north,'cellsize':30,'nodata':nodata,'vertical_crs_code':geo.get(4096)}


def read_prj(raw):
    text=raw.decode('utf-8-sig').upper()
    # WKT1 expected from GM; reject unknown dialect rather than infer a CRS.
    require('PROJCS[' in text and 'TRANSVERSE_MERCATOR' in text and ('WGS_1984' in text or 'WGS 84' in text),'PRJ_UNRECOGNIZED')
    params={k.lower():float(v) for k,v in re.findall(r'PARAMETER\s*\[\s*"([^"]+)"\s*,\s*([-+0-9.E]+)',text)}
    for k,v in {'central_meridian':33,'latitude_of_origin':0,'scale_factor':.9996,'false_easting':500000,'false_northing':0}.items():
        require(k in params and near(params[k],v,1e-8),'PRJ_PARAMETER_'+k)
    require(re.search(r'UNIT\s*\[\s*"(?:METER|METRE|METERS|METRES)"\s*,\s*1(?:\.0+)?\s*[,\]]',text) is not None,'PRJ_METRE_UNIT')
    return 'WGS84 / UTM 36N parameters matched'


def qc(folder,response):
    files={ext:read_file(folder/('MAP003_SRTM.'+ext),2_000_000) for ext in ('asc','tif','prj')}
    asc,ah=read_asc(files['asc']); tif,th=read_tiff(files['tif']); prj=read_prj(files['prj'])
    delta=max(abs(a-b) for a,b in zip(asc,tif)); require(delta<=PAIR_TOL,'ASC_TIFF_DELTA')
    require(response.get('schema')==7 and response.get('op')=='export_candidate' and response.get('ok') is True,'RESPONSE_IDENTITY')
    r=response['result']; require(r['status']=='CANDIDATE_EXPORTED_QC_REQUIRED' and r.get('cleanup_ok') is True and r['grid']['valid']==4096 and r['grid']['invalid']==0,'NATIVE_GATE')
    require(Path(r['output_directory']).resolve()==folder.resolve(),'OUTPUT_IDENTITY')
    mid=r['intermediate']; require(mid['valid']==11397 and mid['nodata']==0,'INTERMEDIATE_GATE')
    for suffix in ('asc','prj'):
        data=read_file(folder/('SRTM_WGS84_INTERMEDIATE.'+suffix),2_000_000); require(hashlib.sha256(data).hexdigest()==mid[suffix+'_sha256'],'INTERMEDIATE_HASH')
    controls=r['controls']; require(len(controls)==5,'CONTROL_COUNT')
    deltas=[]
    for i,((row,col),p) in enumerate(zip(CONTROL,controls),1):
        require(p['index']==i and p['valid'] is True and near(p['e'],X+15+col*30) and near(p['n'],Y+1920-15-row*30),'CONTROL_ALIGNMENT')
        z=asc[row*64+col]; d=abs(z-p['z_m']); deltas.append({'index':i,'export_m':z,'source_m':p['z_m'],'delta_m':d})
    require(max(p['delta_m'] for p in deltas)<=SOURCE_TOL,'SOURCE_CONTROL_DELTA')
    return {'status':'DIAGNOSTIC_EXPORT_QC_PASS','source_acceptance':'DIAGNOSTIC_ONLY','vertical_datum':'UNVERIFIED','valid':4096,'nodata':0,'min_m':min(asc),'max_m':max(asc),'asc_header':ah,'tiff_metadata':th,'prj':prj,'pair_max_delta_m':delta,'pair_tol_m':PAIR_TOL,'source_control_tol_m':SOURCE_TOL,'controls':deltas,'sha256':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}


def main():
    p=argparse.ArgumentParser(); p.add_argument('folder',type=Path); p.add_argument('response',type=Path); a=p.parse_args()
    try:
        result=qc(a.folder,json.loads(read_file(a.response,65536)))
        print(json.dumps(result,allow_nan=False)); return 0
    except Exception as e:
        print(json.dumps({'status':'BLOCKED_QC','error':str(e),'error_type':type(e).__name__})); return 2


if __name__=='__main__': raise SystemExit(main())
