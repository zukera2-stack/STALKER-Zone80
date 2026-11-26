"""Read-only bounded G2 raster QC; no GIS downloads or raster generation.
Strict classic TIFF RGBA8, uncompressed contiguous strips, one image. Unsupported
encodings fail closed. Raster geometry/alpha is not source or license acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import struct

W, S, E, N = 294373.084, 5698122.108, 296293.084, 5700042.108
D, P, EPSG = 480, 4.0, 32636
LIMIT = 16 * 1024 * 1024
TOL = 0.001


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def near(a, b):
    return math.isfinite(a) and abs(a-b) <= TOL


def read_file(path):
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode) and not path.is_symlink() and not getattr(s, 'st_file_attributes', 0) & 0x400, 'NOT_ORDINARY')
    need(0 < s.st_size <= LIMIT, 'FILE_LIMIT')
    raw = path.read_bytes()
    need(len(raw) == s.st_size, 'FILE_CHANGED')
    return raw


def inspect(raw):
    need(len(raw) <= LIMIT and raw[:2] in (b'II', b'MM'), 'TIFF_HEADER')
    bo = '<' if raw[:2] == b'II' else '>'
    def get(fmt, offset):
        n = struct.calcsize(bo+fmt)
        need(0 <= offset <= len(raw)-n, 'OFFSET')
        return struct.unpack_from(bo+fmt, raw, offset)
    magic, ifd = get('HI', 2)
    need(magic == 42 and ifd >= 8, 'CLASSIC_TIFF_REQUIRED')
    count, = get('H', ifd)
    need(0 < count <= 256, 'IFD_COUNT')
    need(get('I', ifd+2+12*count)[0] == 0, 'MULTIPLE_IFDS_UNSUPPORTED')
    tags, seen = {}, set()
    types = {1:'B',2:'c',3:'H',4:'I',11:'f',12:'d'}
    for i in range(count):
        at = ifd+2+12*i
        k, typ, c, ptr = get('HHII', at)
        need(k not in seen, 'DUPLICATE_TAG'); seen.add(k)
        if typ not in types:
            continue
        need(0 < c <= 100000, 'TAG_COUNT')
        fmt = str(c)+types[typ]
        tags[k] = get(fmt, at+8 if struct.calcsize(bo+fmt) <= 4 else ptr)
    def one(k, default=None):
        v = tags.get(k, (default,))
        need(len(v)==1, 'TAG_CARDINALITY')
        return v[0]
    need(one(256)==D and one(257)==D, 'DIMENSIONS')
    need(one(259,1)==1 and one(262)==2 and one(277)==4 and one(284,1)==1 and one(274,1)==1 and one(317,1)==1, 'RGBA_STRICT_ENCODING')
    need(tags.get(258)==(8,8,8,8) and tags.get(338) in ((1,),(2,)) and tags.get(339,(1,1,1,1))==(1,1,1,1), 'SAMPLES_ALPHA')
    need(not ({34264,324,325,42113,330} & seen), 'UNSUPPORTED_TRANSFORM_TILE_NODATA_OR_SUBIFD')
    scale, tie = tags.get(33550,()), tags.get(33922,())
    need(len(scale)==3 and len(tie)==6 and all(math.isfinite(x) for x in scale+tie) and near(scale[0],P) and near(scale[1],P), 'PIXEL_SCALE')
    keys=tags.get(34735,())
    need(len(keys)>=4 and keys[0]==1 and len(keys)==4+4*keys[3], 'GEOKEYS')
    geo={}; gseen=set()
    for i in range(4,len(keys),4):
        k,loc,c,v=keys[i:i+4]; need(k not in gseen,'DUPLICATE_GEOKEY'); gseen.add(k)
        if loc==0 and c==1: geo[k]=v
    need(geo.get(1024)==1 and geo.get(3072)==EPSG and geo.get(3076,9001)==9001, 'CRS')
    need(geo.get(1025)==1, 'PIXEL_IS_AREA_REQUIRED')
    west=tie[3]-tie[0]*scale[0]; north=tie[4]+tie[1]*scale[1]
    need(near(west,W) and near(north,N) and near(west+D*scale[0],E) and near(north-D*scale[1],S), 'BOUNDS')
    rows=one(278); offsets=tags.get(273,()); sizes=tags.get(279,())
    need(type(rows)==int and 0<rows<=D and len(offsets)==len(sizes)==(D+rows-1)//rows, 'STRIP_COUNT')
    intervals=[]; invalid=0; black=0; rgb_min=[255]*3; rgb_max=[0]*3
    for i,(off,size) in enumerate(zip(offsets,sizes)):
        h=min(rows,D-i*rows)
        need(type(off)==int and type(size)==int and off>=8 and size==h*D*4 and off+size<=len(raw), 'STRIP_BYTES')
        intervals.append((off,off+size))
        px=raw[off:off+size]
        invalid+=sum(a!=255 for a in px[3::4])
        for c in range(3):
            v=px[c::4]; rgb_min[c]=min(rgb_min[c],min(v)); rgb_max[c]=max(rgb_max[c],max(v))
        black+=sum(px[j:j+3]==b'\0\0\0' for j in range(0,len(px),4))
    intervals.sort(); need(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])), 'STRIP_OVERLAP')
    need(invalid==0,'ALPHA_GAP'); need(rgb_min!=rgb_max,'CONSTANT_RGB')
    return {'status':'RASTER_GEOMETRY_ALPHA_PASS_SOURCE_REVIEW_REQUIRED','epsg':EPSG,'dimensions':[D,D],'pixel_m':P,'outer_bounds':[west,north-D*scale[1],west+D*scale[0],north],'opaque':D*D-invalid,'nonopaque':invalid,'black_pixels_review_only':black,'rgb_min':rgb_min,'rgb_max':rgb_max,'sha256':hashlib.sha256(raw).hexdigest(),'source_acceptance':'NOT_ESTABLISHED','native_detail':'NOT_ESTABLISHED','grm_alignment':'NOT_RUN'}


def grm_sample(col,row):
    """Pinned RawSatelliteImageBuilder's local node coordinates, not image centers.
    Valid only if native GRM SW and UTM basis are independently verified.
    """
    need(type(col)==int and type(row)==int and 0<=col<D and 0<=row<D,'GRM_INDEX')
    return W+col*P, S+(D-row-1)*P


def main():
    p=argparse.ArgumentParser();p.add_argument('tif',type=Path);a=p.parse_args()
    try:
        print(json.dumps(inspect(read_file(a.tif)),allow_nan=False));return 0
    except (OSError,ValueError,struct.error) as e:
        print(json.dumps({'status':'BLOCKED_QC','reason':str(e)}));return 2


if __name__=='__main__':raise SystemExit(main())
