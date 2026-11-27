"""Zone80 GM bridge experiment: local, bounded, fixed MAP-003 diagnostic operation."""
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile
import time

VERSION = 2
LIFETIME = 300.0
MAX_REQUESTS = 5
REQUEST = re.compile(r"request-([0-9a-f]{32})\.json\Z")
OPERATIONS = {"ping", "status", "stop", "elevation_v03"}


def emit(kind, value):
    print("ZONE80_BRIDGE_V02_" + kind + " " + json.dumps(value, ensure_ascii=True), flush=True)


def count_layers(raw):
    if type(raw) is int and raw == 0:
        return 0
    if isinstance(raw, (list, tuple)) and len(raw) == 2 and type(raw[1]) is int and raw[1] >= 0:
        return raw[1]
    return None


def status(gm):
    registered = gm.IsRegistered()
    return {"pid": os.getpid(), "host": Path(sys.executable or "").name.lower(),
            "python": list(sys.version_info[:3]), "bits": struct.calcsize("P") * 8,
            "sdk": gm.GetSDKVersion(), "registered": registered == 1,
            "layers": count_layers(gm.GetLoadedLayerList())}


def write_json(path, value):
    # Atomic publication within the unique session directory.
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True, allow_nan=False)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def ordinary_file(path):
    info = path.lstat()
    return (stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and not getattr(info, "st_file_attributes", 0) & 0x400)


def read_request(path, request_id):
    if not ordinary_file(path):
        raise ValueError("not a regular file")
    with path.open("rb") as stream:
        raw = stream.read(1025)
    if len(raw) > 1024:
        raise ValueError("oversize request")
    value = json.loads(raw.decode("utf-8"))
    if (type(value) is not dict or set(value) != {"schema", "id", "op"}
            or type(value["schema"]) is not int or value["schema"] != VERSION
            or value["id"] != request_id or type(value["op"]) is not str
            or value["op"] not in OPERATIONS):
        raise ValueError("invalid request")
    return value["op"]



def elevation_v03(gm, host_ok):
    # Embedded from pinned v03 SHA256 3d2c72d4540b7064d59ac3d5921d29b2c14ebdf92e0f52fd3445e21be783b10e.
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
    r = {'schema': 3, 'source': SOURCE, 'diagnostic_only': True, 'bbox': BBOX,
         'stage': 'IMPORT', 'status': 'BLOCKED', 'grid': 'NOT_RUN', 'export': 'NOT_RUN'}
    emit('START', r)
    try:
        r['status'] = run(gm, r, host_ok)
    except Exception as exc:
        r['error'] = error(exc)
        r['status'] = 'BLOCKED_EXCEPTION'
    if r.get('cleanup_ok') is False:
        r['status_before_cleanup'] = r['status']
        r['status'] = 'BLOCKED_CLEANUP'
    emit('RESULT', r)
    return r


def host_ok(check):
    return (os.name == "nt" and check["host"] == "global_mapper.exe"
            and check["bits"] == 64 and check["python"][:2] == [3, 9]
            and check["sdk"] == 2621 and check["registered"] and check["layers"] == 0)

def serve(gm, root, lifetime=LIFETIME, max_requests=MAX_REQUESTS):
    start = time.monotonic()
    seen = set()
    why = "TIME_LIMIT"
    pinged = False
    ready = {"schema": VERSION, "state": "READY", "pid": os.getpid(),
             "created_unix": time.time(), "lifetime_seconds": lifetime,
             "operations": sorted(OPERATIONS), "max_requests": max_requests,
             "probe_auto_stop": True}
    write_json(root / "ready.json", ready)
    emit("READY", dict(ready, directory=str(root)))
    try:
        while time.monotonic() - start < lifetime:
            # Only the fixed request filename pattern is considered; no imports/exec.
            for path in sorted(root.glob("request-*.json")):
                if time.monotonic() - start >= lifetime:
                    break
                match = REQUEST.fullmatch(path.name)
                if not match or match[1] in seen:
                    continue
                request_id = match[1]
                seen.add(request_id)
                response = {"schema": VERSION, "id": request_id, "ok": False,
                            "pid": os.getpid()}
                stop = False
                probe_finished = False
                try:
                    op = read_request(path, request_id)
                    response["op"] = op
                    if op == "ping":
                        response.update(ok=True, result="PONG")
                        pinged = True
                    elif op == "status":
                        response.update(ok=True, result=status(gm))
                    elif op == "elevation_v03":
                        if not pinged or not host_ok(status(gm)):
                            raise ValueError("ping and empty registered desktop required")
                        # One fixed diagnostic, then stop even when coverage fails.
                        probe_finished = True
                        response.update(ok=True, result=elevation_v03(gm, True))
                    elif op == "stop":
                        response.update(ok=True, result="STOPPING")
                        stop = True
                except Exception as exc:
                    response["error_type"] = type(exc).__name__
                write_json(root / ("response-" + request_id + ".json"), response)
                emit("RESPONSE", response)
                if probe_finished:
                    why = "PROBE_COMPLETE"
                    return
                if stop:
                    why = "STOP_REQUEST"
                    return
                if len(seen) >= max_requests:
                    why = "REQUEST_LIMIT"
                    return
            time.sleep(0.2)
    except Exception as exc:
        why = "ERROR_" + type(exc).__name__
        raise
    finally:
        final = {"schema": VERSION, "state": "STOPPED", "reason": why,
                 "processed": len(seen), "ping_received": pinged, "pid": os.getpid()}
        write_json(root / "finished.json", final)
        emit("STOPPED", final)


def main():
    emit("START", {"schema": VERSION})
    try:
        import globalmapper as gm
        check = status(gm)
        emit("HOST", check)
        if not host_ok(check):
            emit("BLOCKED", {"reason": "HOST_OR_EMPTY_WORKSPACE_NOT_CONFIRMED"})
            return
        # Fresh per-run directory in this Windows user's temporary folder, not GM's own temp files.
        root = Path(tempfile.mkdtemp(prefix="Zone80-GM-Bridge-v02-"))
        serve(gm, root)
    except Exception as exc:
        emit("BLOCKED", {"reason": type(exc).__name__})


if __name__ == "__main__":
    main()
