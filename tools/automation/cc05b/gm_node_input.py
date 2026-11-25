"""Read-only GM node-compatible input contract. Never generates a geographic grid."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib, json, re, struct
from pathlib import Path

class Blocked(ValueError): pass

def check(ok, why):
    if not ok: raise Blocked(why)

def number(s):
    check(isinstance(s,str) and len(s)<=40 and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?',s), 'invalid number')
    try: n=Decimal(s)
    except InvalidOperation: raise Blocked('invalid decimal') from None
    check(n.is_finite() and abs(n)<=Decimal('100000000') and (n==0 or abs(n)>=Decimal('0.000000000001')), 'numeric range')
    return n

@dataclass(frozen=True)
class Contract:
    size:int; step:Decimal; east:Decimal; north:Decimal
    crs:str; datum:str; units:str; asc_sha256:str; prj_sha256:str
    source_evidence:str; grid_semantics:str='pixel_center_on_grm_node'

def inspect(asc:bytes, prj:bytes, c:Contract):
    check(type(c.size) is int and 2<=c.size<=64 and c.step>0 and c.step<=100 and c.step==c.step.to_integral_value(), 'bounded pilot only')
    check(c.crs=='EPSG:32636' and c.datum=='EGM2008' and c.units=='m', 'unsupported metadata')
    check(c.grid_semantics=='pixel_center_on_grm_node' and bool(c.source_evidence.strip()), 'missing reviewed source contract')
    check(len(asc)<=1024*1024 and len(prj)<=65536, 'oversize input')
    check(hashlib.sha256(asc).hexdigest()==c.asc_sha256 and hashlib.sha256(prj).hexdigest()==c.prj_sha256, 'hash mismatch')
    # Pin reviewed PRJ bytes; metadata is a trusted review statement, not a WKT parser.
    try: lines=asc.decode('ascii').splitlines()
    except UnicodeError: raise Blocked('non-ASCII ASC') from None
    check(len(lines)==6+c.size, 'row count')
    h={}
    for line in lines[:6]:
        fields=line.split(); check(len(fields)==2,'header format')
        key=fields[0].lower(); check(key not in h,'duplicate header'); h[key]=number(fields[1])
    check(set(h)=={'ncols','nrows','xllcorner','yllcorner','cellsize','nodata_value'}, 'unsupported header')
    check(h['ncols']==h['nrows']==c.size and h['cellsize']==c.step and h['nodata_value']==-9999, 'grid mismatch')
    check(h['xllcorner']+c.step/2==c.east and h['yllcorner']+c.step/2==c.north, 'sample centers do not coincide with GRM nodes')
    north_rows=[]; missing=0; quantization=Decimal(0)
    for line in lines[6:]:
        fields=line.split(); check(len(fields)==c.size,'column count')
        row=[]
        for token in fields:
            v=number(token)
            if v==-9999: missing+=1; row.append(None); continue
            check(-12000<=v<=12000,'elevation range')
            f=struct.unpack('<f',struct.pack('<f',float(v)))[0]
            quantization=max(quantization,abs(Decimal.from_float(f)-v)); row.append(f)
        north_rows.append(tuple(row))
    check(not missing, f'NoData={missing}; stop')
    south_rows=tuple(reversed(north_rows))
    # Float32 is GRM's native representation. Hash south-first rows, x varies fastest.
    data=b''.join(struct.pack('<f',v) for row in south_rows for v in row)
    return {'status':'VALIDATED_INPUT_ONLY','size':c.size,'nodes':c.size*c.size,'nodata':0,'asc_sha256':c.asc_sha256,'prj_sha256':c.prj_sha256,'float32_sha256':hashlib.sha256(data).hexdigest(),'max_float32_rounding_m':str(quantization),'node_origin_m':[str(c.east),str(c.north)],'cell_m':str(c.step),'outer_edge_policy':'UNRESOLVED_NATIVE_CLAMP','native_generation_authorized':False},south_rows

# No command to write height data, generate new raster or run GRM.
