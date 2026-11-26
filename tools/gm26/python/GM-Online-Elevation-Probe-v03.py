"""MAP-003: diagnose online elevation NoData; no export, no raster generation."""
import json
import math
import os
import struct
import sys
import time
import traceback

SOURCE = "SRTM Worldwide Elevation Data (1-arc-second Resolution, SRTM Plus V3)"
BBOX = (30.041, 51.395, 30.074, 51.417)
# Existing UTM controls and independent WGS84 coordinate conversions, not heights.
CONTROL = [(294688.084, 5699727.108, 30.047580700382, 51.411534691737),
           (294988.084, 5699427.108, 30.052062010081, 51.408949230160),
           (295348.084, 5699067.108, 30.057438915213, 51.405846437886),
           (295708.084, 5698707.108, 30.062815093355, 51.402743385634),
           (295978.084, 5698437.108, 30.066846749945, 51.400415925884)]
LIMIT = 300


def emit(kind, obj):
    print("ZONE80_ELEV_V03_" + kind + " " + json.dumps(obj, allow_nan=False, ensure_ascii=True), flush=True)


def step(r, name):
    r['stage'] = name
    emit('STEP', {'stage': name, 'utc_epoch': time.time()})


def field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def number(v):
    return float(v) if type(v) in (float, int) and math.isfinite(v) else None


def count(raw):
    if type(raw) is int and raw == 0:
        return 0
    if isinstance(raw, (list, tuple)) and len(raw) == 2 and type(raw[1]) is int and raw[1] >= 0:
        return raw[1]
    return None


def rect(obj):
    vals = [number(field(obj, f)) for f in ('mMinX', 'mMinY', 'mMaxX', 'mMaxY')]
    if None in vals or vals[0] >= vals[2] or vals[1] >= vals[3]:
        return None
    return vals


def inside(b, x, y):
    return b is not None and b[0] <= x <= b[2] and b[1] <= y <= b[3]


def elevation(gm, handle, x, y, invalid):
    code, z = gm.GetLocationElevation(handle, x, y)
    z = number(z)
    valid = code == 0 and z is not None and z != invalid and -500 <= z <= 9000
    return {'code': int(code), 'z_m': z if valid else None, 'valid': valid}


def error(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    return {'type': type(exc).__name__, 'line': tb[-1].lineno if tb else None,
            'function': tb[-1].name if tb else None}


def run(gm, r, host_ok):
    if not host_ok or gm.GetSDKVersion() != 2621 or gm.IsRegistered() != 1:
        return 'BLOCKED_HOST'
    step(r, 'EMPTY_WORKSPACE')
    if count(gm.GetLoadedLayerList()) != 0:
        return 'BLOCKED_WORKSPACE'
    missing = [n for n in ('ProjectPointAtElev', 'LoadProjectionFromEPSGCode', 'SetProjection',
                           'GetLayerInfo', 'LoadOnlineLayer', 'GetOnlineSourceInfo',
                           'GetLocationElevation', 'CloseLayer') if not callable(getattr(gm, n, None))]
    if missing:
        r['missing_functions'] = missing
        return 'BLOCKED_API'
    invalid = number(gm.GM_INVALID_ELEV_VALUE)
    if invalid is None:
        return 'BLOCKED_INVALID_CONSTANT'
    step(r, 'LOAD_PROJECTIONS')
    code, geo = gm.LoadProjectionFromEPSGCode(4326)
    if code != 0:
        return 'BLOCKED_GEO_PROJECTION'
    code, utm = gm.LoadProjectionFromEPSGCode(32636)
    if code != 0:
        return 'BLOCKED_UTM_PROJECTION'
    step(r, 'SET_INITIAL_WGS84')
    if gm.SetProjection(geo) != 0:
        return 'BLOCKED_SET_PROJECTION'
    step(r, 'SOURCE_INFO')
    code, _ = gm.GetOnlineSourceInfo(SOURCE)
    r['source_code'] = int(code)
    if code != 0:
        return 'BLOCKED_SOURCE_INFO'
    bounds = gm.GM_Rectangle_t()
    bounds.mMinX, bounds.mMinY, bounds.mMaxX, bounds.mMaxY = BBOX
    owned = None
    start = time.monotonic()
    try:
        step(r, 'LOAD_ONLINE_LAYER')
        code, handle = gm.LoadOnlineLayer(SOURCE, bounds, 'BOUNDS_PROJ=EPSG:4326')
        r['load_code'] = int(code)
        if code != 0 or not handle:
            return 'BLOCKED_LOAD'
        owned = handle
        r['loaded_count'] = count(gm.GetLoadedLayerList())
        if r['loaded_count'] != 1:
            return 'BLOCKED_LAYER_ISOLATION'
        r['passes'] = []
        for epsg, projection in ((4326, geo), (32636, utm)):
            step(r, 'SET_AND_READBACK_' + str(epsg))
            code = gm.SetProjection(projection)
            if code != 0:
                return 'BLOCKED_SET_PROJECTION'
            info = gm.GetLayerInfo(owned)
            g = rect(field(info, 'mGlobalRect'))
            n = rect(field(info, 'mNativeRect'))
            p = {'epsg_requested': epsg, 'global_rect': g, 'native_rect': n,
                 'raster': bool(field(info, 'mHasRasterData')), 'points': []}
            r['passes'].append(p)
            emit('LAYER', p)
            if not p['raster'] or g is None:
                return 'BLOCKED_LAYER_BOUNDS'
            step(r, 'SAMPLE_' + str(epsg))
            for i, (e, north, lon, lat) in enumerate(CONTROL, 1):
                if time.monotonic() - start > LIMIT:
                    return 'BLOCKED_BUDGET'
                # None is documented as CURRENT projection. Verify independently
                # against fixed coordinates; do not assume SetProjection(0) succeeded.
                code, x, y = gm.ProjectPointAtElev(lon, lat, geo, None, 0.0)
                x, y = number(x), number(y)
                expected = (lon, lat) if epsg == 4326 else (e, north)
                tol = 1e-6 if epsg == 4326 else 0.2
                match = (code == 0 and x is not None and y is not None
                         and abs(x - expected[0]) <= tol and abs(y - expected[1]) <= tol)
                point = {'index': i, 'epsg': epsg, 'x': x, 'y': y,
                         'projection_code': int(code), 'projection_match': match,
                         'inside_global_rect': inside(g, x, y) if match else False}
                p['points'].append(point)
                if not match:
                    emit('POINT', point)
                    return 'BLOCKED_PROJECTION_READBACK'
                if point['inside_global_rect']:
                    point['handle'] = elevation(gm, owned, x, y, invalid)
                    if count(gm.GetLoadedLayerList()) != 1:
                        emit('POINT', point)
                        return 'BLOCKED_LAYER_ISOLATION'
                    # Null means the topmost elevation layer; only one layer allowed.
                    point['topmost'] = elevation(gm, gm.NULL, x, y, invalid)
                emit('POINT', point)
        if any(not q['inside_global_rect'] for p in r['passes'] for q in p['points']):
            return 'BLOCKED_EXTENT_MISMATCH'
        totals = [{'epsg': p['epsg_requested'], 'handle_valid': sum(q['handle']['valid'] for q in p['points']),
                   'topmost_valid': sum(q['topmost']['valid'] for q in p['points'])} for p in r['passes']]
        r['totals'] = totals
        if all(t['handle_valid'] == 5 and t['topmost_valid'] == 5 for t in totals):
            return 'DIAGNOSTIC_CONTROLS_PASS_GRID_NOT_RUN'
        if not any(t['handle_valid'] or t['topmost_valid'] for t in totals):
            return 'BLOCKED_NODATA_BOTH_PROJECTIONS'
        return 'BLOCKED_INCONSISTENT_OR_PARTIAL_READBACK'
    finally:
        if owned:
            try:
                ret = gm.CloseLayer(owned)
                r['close_return'] = ret if type(ret) in (int, bool) or ret is None else type(ret).__name__
                r['remaining_layers'] = count(gm.GetLoadedLayerList())
                r['cleanup_ok'] = r['remaining_layers'] == 0
            except Exception as exc:
                r['cleanup_ok'] = False
                r['cleanup_error'] = error(exc)


def main():
    r = {'schema': 3, 'source': SOURCE, 'diagnostic_only': True, 'bbox': BBOX,
         'stage': 'IMPORT', 'status': 'BLOCKED', 'grid': 'NOT_RUN', 'export': 'NOT_RUN'}
    emit('START', r)
    try:
        import globalmapper as gm
        host_ok = (os.name == 'nt' and os.path.basename(sys.executable or '').lower() == 'global_mapper.exe'
                   and struct.calcsize('P') == 8)
        r['status'] = run(gm, r, host_ok)
    except Exception as exc:
        r['error'] = error(exc)
        r['status'] = 'BLOCKED_EXCEPTION'
    if r.get('cleanup_ok') is False:
        r['status_before_cleanup'] = r['status']
        r['status'] = 'BLOCKED_CLEANUP'
    emit('RESULT', r)


if __name__ == '__main__':
    main()
