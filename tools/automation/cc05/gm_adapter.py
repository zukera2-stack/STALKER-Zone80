"""CC-05: read-only MAP-003 ASC validation. No native or raster output."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import zipfile
from pathlib import Path

D = Decimal
N = 64
STEP = D('30')
SW = (D('294373.084'), D('5698122.108'))
PRJ_SHA = 'fdab6e893555dc5503ea414374724e48aa547eedf16896329215cfa07a851bfe'
ARCHIVE_SHA = '457f1fdb363d0f586ef3fde82cec4f407784f1ab68af867e099c1bac84e72869'
ASC_SHA = 'a6d85a93956145bb505a49c8d46c098e998ed85bc6cf3477ba93c1b814e77f6e'
SYN_PRJ = b'CC05 synthetic fixture; not a CRS definition'
NUM = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?')

class Rejected(ValueError):
    pass

def check(ok, message):
    if not ok:
        raise Rejected(message)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def number(s):
    check(isinstance(s, str) and len(s) <= 48 and NUM.fullmatch(s), 'invalid numeric token')
    try:
        v = D(s)
    except InvalidOperation as e:
        raise Rejected('invalid decimal') from e
    check(v.is_finite() and abs(v) <= D('1000000000') and v.as_tuple().exponent >= -20, 'number outside parser bounds')
    return v

@dataclass(frozen=True)
class Grid:
    rows_north_first: tuple
    nodata: Decimal
    data_sha: str
    synthetic: bool

    def center(self, col, row_south):
        check(type(col) is int and type(row_south) is int and 0 <= col < N and 0 <= row_south < N, 'index outside grid')
        return (SW[0]+STEP*(D(col)+D('.5')), SW[1]+STEP*(D(row_south)+D('.5')))

    def sample_center(self, east, north):
        check(type(east) is Decimal and type(north) is Decimal and east.is_finite() and north.is_finite(), 'exact decimal coordinates required')
        x,y=(east-SW[0])/STEP-D('.5'),(north-SW[1])/STEP-D('.5')
        check(x==x.to_integral_value() and y==y.to_integral_value() and 0<=x<N and 0<=y<N, 'not an existing cell center; no interpolation')
        check((east,north)==self.center(int(x),int(y)), 'not an exact cell center')
        v=self.rows_north_first[N-1-int(y)][int(x)]
        check(v != self.nodata, 'NoData cell')
        return v

    def report(self):
        values=[v for row in self.rows_north_first for v in row if v!=self.nodata]
        missing=N*N-len(values)
        return {'scope':'SYNTHETIC' if self.synthetic else 'OWNER_DIAGNOSTIC', 'asc_sha256':self.data_sha,
                'shape':[N,N], 'cell_size_m':str(STEP),'valid_cells':len(values),'nodata_cells':missing,
                'min_m':str(min(values)) if values else None,'max_m':str(max(values)) if values else None,
                'grid_validation':'PASS' if not missing else 'BLOCKED_NODATA',
                'native_alignment':'BLOCKED_CELL_CENTER_VS_NODE', 'offset_each_axis_m':'15',
                'native_grm_authorized':False, 'raster_written':False}

def parse(data, prj, meta, *, synthetic=False):
    check(type(data) is bytes and type(prj) is bytes and len(data)<=512000 and len(prj)<=16000,'input size/type')
    expected={'scope':'synthetic' if synthetic else 'owner_diagnostic', 'producer':'fixture' if synthetic else 'Global Mapper Pro 26.2',
              'crs':'EPSG:32636','vertical_datum':'EGM2008','horizontal_unit':'m','vertical_unit':'m','pixel':'area_center',
              'asc_sha256':sha(data),'prj_sha256':sha(prj)}
    check(meta==expected, 'metadata/hash mismatch')
    check(prj==SYN_PRJ if synthetic else sha(prj)==PRJ_SHA, 'projection not pinned for this input')
    # This version accepts only the historical diagnostic in actual mode, not arbitrary caller-declared provenance.
    check(synthetic or sha(data)==ASC_SHA, 'actual ASC not pinned historical diagnostic')
    try:
        lines=data.decode('ascii').splitlines()
    except UnicodeDecodeError as e:
        raise Rejected('non-ASCII ASC') from e
    check(len(lines)==6+N,'unexpected line count')
    header={}
    for line in lines[:6]:
        parts=line.split()
        check(len(parts)==2 and parts[0].lower() not in header,'invalid/duplicate header')
        header[parts[0].lower()]=number(parts[1])
    check(set(header)=={'ncols','nrows','xllcorner','yllcorner','cellsize','nodata_value'}, 'corner header required')
    check((header['ncols'],header['nrows'],header['cellsize'],header['xllcorner'],header['yllcorner'])==(N,N,STEP,*SW), 'wrong pilot geometry')
    check(header['nodata_value']==D('-9999'), 'unexpected NoData marker')
    rows=[]
    for line in lines[6:]:
        fields=line.split(); check(len(fields)==N,'ragged row')
        rows.append(tuple(number(x) for x in fields))
    return Grid(tuple(rows),header['nodata_value'],sha(data),synthetic)

def metadata(data, prj, synthetic=False):
    return {'scope':'synthetic' if synthetic else 'owner_diagnostic','producer':'fixture' if synthetic else 'Global Mapper Pro 26.2',
            'crs':'EPSG:32636','vertical_datum':'EGM2008','horizontal_unit':'m','vertical_unit':'m','pixel':'area_center',
            'asc_sha256':sha(data),'prj_sha256':sha(prj)}

def review_archive(path):
    # Exact known archive from the owner, no extraction, no new GIS data.
    check(path.is_file() and path.stat().st_size<=1000000, 'archive missing or too large')
    raw=path.read_bytes(); check(sha(raw)==ARCHIVE_SHA,'archive hash mismatch')
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        check(z.testzip() is None,'ZIP CRC error')
        data=z.read('relief/coverage-check.asc'); prj=z.read('relief/coverage-check.prj')
    g=parse(data,prj,metadata(data,prj))
    return dict(g.report(),archive_sha256=sha(raw),prj_sha256=sha(prj),source='owner MAP-003 diagnostic only; provenance from existing report')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);a=p.parse_args()
    try:
        report=review_archive(a.archive); print(json.dumps(report,sort_keys=True,indent=2))
    except (Rejected,OSError,zipfile.BadZipFile,KeyError) as e:
        p.exit(2,'BLOCKED: '+str(e)+'\n')
    raise SystemExit(2 if report['grid_validation']!='PASS' else 0)
