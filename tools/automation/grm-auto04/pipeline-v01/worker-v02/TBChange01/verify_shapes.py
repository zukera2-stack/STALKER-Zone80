"""Read-only QC for paired native 2D shapefile exports, not an ALB1 parser.
Requires pyshp and pyproj. Exact parsed geometry/attributes; feature order ignored.
Ring/part/vertex order is deliberately strict (a difference requires review).
"""
import argparse
from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import struct

import shapefile
from pyproj import CRS
from pyproj.exceptions import CRSError


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_export(path, encoding):
    path = Path(path)
    require(path.suffix.lower() == '.shp', 'expected .shp path')
    files = [path.with_suffix(ext) for ext in ('.shp', '.shx', '.dbf', '.prj')]
    require(all(p.is_file() for p in files), 'missing SHP/SHX/DBF/PRJ')
    hashes = lambda: {p.suffix: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before = hashes()
    crs = CRS.from_wkt(files[3].read_text(encoding='utf-8-sig'))
    require(crs.is_projected, 'expected explicit projected CRS')
    with shapefile.Reader(str(path), encoding=encoding, encodingErrors='strict') as reader:
        require(reader.shapeType in (1, 3, 5, 8), 'unsupported non-2D shape type')
        fields = tuple(tuple(f) for f in reader.fields[1:])
        require(len({f[0] for f in fields}) == len(fields), 'duplicate DBF fields')
        shapes = reader.shapes()
        require(len(shapes) == reader.numRecords, 'shape/DBF count mismatch')
        require(bool(shapes), 'empty export requires separate review')
        features = Counter()
        for i, shape in enumerate(shapes):
            record = reader.record(i)
            require(record is not None, 'deleted or missing DBF record')
            require(shape.shapeType == reader.shapeType, 'null/mixed shape type')
            points = tuple(tuple(p) for p in shape.points)
            require(points and all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in points), 'invalid coordinates')
            parts = tuple(shape.parts)
            if shape.shapeType in (3, 5):
                require(parts and parts[0] == 0 and all(a < b for a,b in zip(parts,parts[1:])) and parts[-1] < len(points), 'invalid parts')
                for a,b in zip(parts, parts[1:] + (len(points),)):
                    require(b-a >= (4 if shape.shapeType == 5 else 2), 'short part')
                    if shape.shapeType == 5:
                        require(points[a] == points[b-1], 'unclosed polygon ring')
            attrs = tuple(record)
            require(all(not isinstance(v, float) or math.isfinite(v) for v in attrs), 'nonfinite attribute')
            features[(shape.shapeType, parts, points, attrs)] += 1
    require(hashes() == before, 'input changed during read')
    return crs, fields, reader.shapeType, features, before


def compare_exports(before, after, encoding):
    a, b = read_export(before, encoding), read_export(after, encoding)
    require(a[0].equals(b[0], ignore_axis_order=False), 'CRS mismatch')
    require(a[1] == b[1], 'DBF schema mismatch')
    require(a[2] == b[2], 'shape type mismatch')
    missing, extra = sum((a[3]-b[3]).values()), sum((b[3]-a[3]).values())
    return {'status': 'PASS' if not (missing or extra) else 'DIFFERENT',
            'scope': 'parsed_2d_shp_geometry_attributes_only_not_native_freshness',
            'before_count': sum(a[3].values()), 'after_count': sum(b[3].values()),
            'missing_or_changed': missing, 'extra_or_changed': extra,
            'before_sha256': a[4], 'after_sha256': b[4]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before'); parser.add_argument('after')
    parser.add_argument('--encoding', required=True, help='verified DBF encoding')
    args = parser.parse_args()
    try:
        report = compare_exports(args.before, args.after, args.encoding)
    except (ValueError, OSError, UnicodeError, shapefile.ShapefileException, CRSError, struct.error, LookupError, TypeError) as exc:
        report = {'status': 'BLOCKED', 'reason': str(exc)}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
