"""Read-only small synthetic Terrain Builder ASC/CSV preflight. No Arma invocation."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_GRID_SIDE = 512
MAX_BYTES = 12 * 1024 * 1024


class InputError(ValueError):
    pass


def reports_input(path: str, base: Path | None = None) -> Path:
    """Check a file is inside reports/ even when the path includes symlinks."""
    reports = (base or (REPO_ROOT / 'reports')).resolve()
    file = Path(path).resolve()
    try:
        file.relative_to(reports)
    except ValueError as exc:
        raise InputError('Only synthetic inputs in ignored reports/ are allowed') from exc
    if not file.is_file():
        raise InputError(f'File not found: {file}')
    if file.stat().st_size > MAX_BYTES:
        raise InputError('Input too large for the synthetic test')
    return file


def read_asc(path: Path) -> dict:
    lines = path.read_text(encoding='utf-8').splitlines()
    if len(lines) < 7:
        raise InputError('Missing six-line ASC header or raster')
    h = {}
    for line in lines[:6]:
        parts = line.split()
        if len(parts) != 2 or parts[0].lower() in h:
            raise InputError('Invalid ASC header')
        h[parts[0].lower()] = parts[1]
    try:
        nx, ny = int(h['ncols']), int(h['nrows'])
        step, nodata = float(h['cellsize']), float(h['nodata_value'])
        corner = 'xllcorner' in h and 'yllcorner' in h
        center = 'xllcenter' in h and 'yllcenter' in h
        if corner == center:
            raise InputError('Use matching corner OR center origins')
        x0 = float(h['xllcorner' if corner else 'xllcenter'])
        y0 = float(h['yllcorner' if corner else 'yllcenter'])
    except (KeyError, ValueError, OverflowError) as exc:
        raise InputError('Invalid grid header') from exc
    if not (1 <= nx <= MAX_GRID_SIDE and 1 <= ny <= MAX_GRID_SIDE):
        raise InputError('Grid dimensions outside synthetic limits')
    if step <= 0 or not all(math.isfinite(v) for v in (x0, y0, step, nodata)):
        raise InputError('Invalid or non-finite ASC header values')
    if center:
        x0 -= step / 2
        y0 -= step / 2
    if len(lines[6:]) != ny:
        raise InputError('Wrong number of ASC raster rows')
    count_nodata = 0
    for line in lines[6:]:
        tokens = line.split()
        if len(tokens) != nx:
            raise InputError('ASC raster row width mismatch')
        try:
            values = [float(token) for token in tokens]
        except ValueError as exc:
            raise InputError('Invalid raster number') from exc
        if not all(math.isfinite(v) for v in values):
            raise InputError('Non-finite raster value')
        count_nodata += sum(v == nodata for v in values)
    return {
        'ncols': nx, 'nrows': ny, 'xllcorner': x0, 'yllcorner': y0,
        'cellsize': step, 'nodata': nodata, 'nodata_cells': count_nodata,
        'bbox': (x0, y0, x0 + nx * step, y0 + ny * step)
    }


def read_objects(path: Path, bounds: tuple[float, float, float, float]) -> dict:
    rows = csv.reader(io.StringIO(path.read_text(encoding='utf-8')), delimiter=';')
    count, models = 0, set()
    for row in rows:
        if not row or row == ['']:
            continue
        if len(row) != 9 or row[-1] != '' or not row[0].strip():
            raise InputError('TB row must be model;X;Y;yaw;pitch;roll;scale;elevation;')
        try:
            x, y, yaw, pitch, roll, scale, z = (float(v) for v in row[1:8])
        except ValueError as exc:
            raise InputError('Invalid TB object number') from exc
        if not all(math.isfinite(v) for v in (x, y, yaw, pitch, roll, scale, z)) or scale <= 0:
            raise InputError('Non-finite transform or invalid scale')
        if not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
            raise InputError('TB object outside the small synthetic area')
        count += 1
        models.add(row[0])
    return {'objects': count, 'symbolic_models': sorted(models)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asc', required=True)
    parser.add_argument('--absolute')
    parser.add_argument('--relative')
    args = parser.parse_args(argv)
    try:
        asc = read_asc(reports_input(args.asc))
        result = {'status': 'INPUT_FORMAT_ONLY', 'terrain': asc, 'layers': {}}
        for kind in ('absolute', 'relative'):
            item = getattr(args, kind)
            if item is not None:
                result['layers'][kind] = read_objects(reports_input(item), tuple(asc['bbox']))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (InputError, OSError, UnicodeError) as exc:
        print(json.dumps({'status': 'FAIL', 'reason': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
