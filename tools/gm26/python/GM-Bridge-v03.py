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

VERSION = 3
LIFETIME = 300.0
MAX_REQUESTS = 5
REQUEST = re.compile(r"request-([0-9a-f]{32})\.json\Z")
OPERATIONS = {"ping", "status", "stop", "elevation_grid"}


def emit(kind, value):
    print("ZONE80_BRIDGE_V03_" + kind + " " + json.dumps(value, ensure_ascii=True), flush=True)


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



def elevation_grid(gm, host_confirmed):
    """Fixed SRTM diagnostic: exact UTM cell centers queried in WGS84."""
    import math
    import traceback

    source = "SRTM Worldwide Elevation Data (1-arc-second Resolution, SRTM Plus V3)"
    bbox = (30.041, 51.395, 30.074, 51.417)
    controls = [(294688.084, 5699727.108, 30.047580700382, 51.411534691737),
                (294988.084, 5699427.108, 30.052062010081, 51.408949230160),
                (295348.084, 5699067.108, 30.057438915213, 51.405846437886),
                (295708.084, 5698707.108, 30.062815093355, 51.402743385634),
                (295978.084, 5698437.108, 30.066846749945, 51.400415925884)]
    r = {"schema": 4, "source": source, "diagnostic_only": True,
         "vertical_datum": "UNVERIFIED", "query_epsg": 4326, "grid_epsg": 32636,
         "bbox": bbox, "stage": "HOST", "status": "BLOCKED", "export": "NOT_RUN",
         "grid": {"expected": 4096, "checked": 0, "valid": 0, "invalid": 0,
                  "min_m": None, "max_m": None, "rows": [], "codes": {},
                  "first_invalid": [], "cell_m": 30, "xllcorner": 294373.084,
                  "yllcorner": 5698122.108, "order": "north_first"}, "controls": []}
    grid = r["grid"]
    owned = None
    start = time.monotonic()

    def step(name):
        r["stage"] = name
        emit("GRID_STEP", {"stage": name, "utc_epoch": time.time()})

    def field(obj, name):
        return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)

    def num(value):
        return float(value) if type(value) in (float, int) and math.isfinite(value) else None

    def budget():
        return time.monotonic() - start < 300

    def details(exc):
        tb = traceback.extract_tb(exc.__traceback__)
        return {"type": type(exc).__name__, "line": tb[-1].lineno if tb else None,
                "function": tb[-1].name if tb else None}

    def run():
        nonlocal owned
        if not host_confirmed or gm.GetSDKVersion() != 2621 or gm.IsRegistered() != 1:
            return "BLOCKED_HOST"
        if count_layers(gm.GetLoadedLayerList()) != 0:
            return "BLOCKED_WORKSPACE"
        step("PROJECTIONS")
        invalid = num(gm.GM_INVALID_ELEV_VALUE)
        if invalid is None:
            return "BLOCKED_INVALID_CONSTANT"
        code, geo = gm.LoadProjectionFromEPSGCode(4326)
        if code != 0:
            return "BLOCKED_GEO_PROJECTION"
        code, utm = gm.LoadProjectionFromEPSGCode(32636)
        if code != 0 or gm.SetProjection(geo) != 0:
            return "BLOCKED_PROJECTION"
        step("LOAD_SOURCE")
        code, _ = gm.GetOnlineSourceInfo(source)
        r["source_code"] = int(code)
        if code != 0:
            return "BLOCKED_SOURCE_INFO"
        bounds = gm.GM_Rectangle_t()
        bounds.mMinX, bounds.mMinY, bounds.mMaxX, bounds.mMaxY = bbox
        code, handle = gm.LoadOnlineLayer(source, bounds, "BOUNDS_PROJ=EPSG:4326")
        r["load_code"] = int(code)
        if code != 0 or not handle:
            return "BLOCKED_LOAD"
        owned = handle
        if count_layers(gm.GetLoadedLayerList()) != 1:
            return "BLOCKED_LAYER_ISOLATION"
        step("GEOGRAPHIC_BOUNDS")
        info = gm.GetLayerInfo(owned)
        rect = field(info, "mGlobalRect")
        b = [num(field(rect, k)) for k in ("mMinX", "mMinY", "mMaxX", "mMaxY")]
        r["global_rect"] = b
        if (not field(info, "mHasRasterData") or None in b
                or not (-180 <= b[0] < b[2] <= 180 and -90 <= b[1] < b[3] <= 90)):
            return "BLOCKED_LAYER_BOUNDS"

        def transform(e, n):
            # None = current projection; tested against independent coordinates below.
            code, x, y = gm.ProjectPointAtElev(e, n, utm, None, 0.0)
            x, y = num(x), num(y)
            if code != 0 or x is None or y is None:
                return None, None, int(code)
            return x, y, int(code)

        def sample(e, n, expected=None):
            x, y, code = transform(e, n)
            p = {"e": e, "n": n, "lon": x, "lat": y, "projection_code": code,
                 "valid": False, "z_m": None}
            if x is None or y is None:
                p["reason"] = "TRANSFORM"
            elif expected and (abs(x-expected[0]) > 1e-6 or abs(y-expected[1]) > 1e-6):
                p["reason"] = "PROJECTION_READBACK"
            elif not (b[0] <= x <= b[2] and b[1] <= y <= b[3]):
                p["reason"] = "OUTSIDE_BOUNDS"
            elif not budget():
                p["reason"] = "BUDGET"
            else:
                code, z = gm.GetLocationElevation(owned, x, y)
                z = num(z)
                p["code"] = int(code)
                if code == 0 and z is not None and z != invalid and -500 <= z <= 9000:
                    p.update(valid=True, z_m=z)
                else:
                    p["reason"] = "ELEVATION"
            return p

        step("CONTROL_POINTS")
        for i, (e,n,x,y) in enumerate(controls, 1):
            if not budget():
                return "BLOCKED_BUDGET"
            p = sample(e,n,(x,y)); p["index"] = i
            r["controls"].append(p)
            emit("GRID_CONTROL", p)
            if p.get("reason") in ("TRANSFORM", "PROJECTION_READBACK", "OUTSIDE_BOUNDS", "BUDGET"):
                return "BLOCKED_CONTROL_" + p["reason"]
        if not all(p["valid"] for p in r["controls"]):
            return "BLOCKED_CONTROL_COVERAGE"
        # Track the exact same locations when visited on the lattice, without saving a raster.
        lookup = {(p["e"], p["n"]):p for p in r["controls"]}
        r["control_grid_readback"] = []
        step("GRID_SAMPLING")
        for row in range(64):
            if count_layers(gm.GetLoadedLayerList()) != 1:
                return "BLOCKED_LAYER_ISOLATION"
            rr = {"row":row, "checked":0, "valid":0, "invalid":0}
            grid["rows"].append(rr)
            for col in range(64):
                if not budget():
                    return "BLOCKED_BUDGET"
                e = round(294388.084 + 30*col, 3)
                n = round(5700027.108 - 30*row, 3)
                r["last_cell"] = [row,col]
                p = sample(e,n)
                if p.get("reason") == "BUDGET":
                    return "BLOCKED_BUDGET"
                grid["checked"] += 1; rr["checked"] += 1
                key = str(p.get("code", p.get("reason", "UNKNOWN")))
                grid["codes"][key] = grid["codes"].get(key,0)+1
                if p["valid"]:
                    z = p["z_m"]
                    grid["valid"] += 1; rr["valid"] += 1
                    grid["min_m"] = z if grid["min_m"] is None else min(grid["min_m"],z)
                    grid["max_m"] = z if grid["max_m"] is None else max(grid["max_m"],z)
                    if (e,n) in lookup:
                        old = lookup[e,n]
                        r["control_grid_readback"].append({"index":old["index"], "row":row,"col":col,"delta_m":z-old["z_m"]})
                else:
                    grid["invalid"] += 1; rr["invalid"] += 1
                    if len(grid["first_invalid"]) < 16:
                        grid["first_invalid"].append(dict(p,row=row,col=col))
                    if p.get("reason") in ("TRANSFORM", "OUTSIDE_BOUNDS"):
                        return "BLOCKED_GRID_" + p["reason"]
            if (row+1)%8 == 0:
                emit("GRID_PROGRESS", {k:grid[k] for k in ("checked","valid","invalid","min_m","max_m")})
        if count_layers(gm.GetLoadedLayerList()) != 1:
            return "BLOCKED_LAYER_ISOLATION"
        if grid["checked"] != 4096 or grid["invalid"] or grid["valid"] != 4096:
            return "BLOCKED_GRID_COVERAGE"
        if grid["min_m"] == grid["max_m"]:
            return "BLOCKED_CONSTANT_GRID"
        if len(r["control_grid_readback"]) != 5:
            return "BLOCKED_CONTROL_GRID_ALIGNMENT"
        return "DIAGNOSTIC_GRID_PASS"

    try:
        r["status"] = run()
    except Exception as exc:
        r["status"] = "BLOCKED_EXCEPTION"
        r["error"] = details(exc)
    finally:
        if owned:
            try:
                code = gm.CloseLayer(owned)
                r["close_return"] = code if type(code) in (int,bool) or code is None else type(code).__name__
                r["remaining_layers"] = count_layers(gm.GetLoadedLayerList())
                r["cleanup_ok"] = code == 0 and r["remaining_layers"] == 0
            except Exception as exc:
                r["cleanup_ok"] = False
                r["cleanup_error"] = details(exc)
            if not r["cleanup_ok"]:
                r["status_before_cleanup"] = r["status"]
                r["status"] = "BLOCKED_CLEANUP"
        r["elapsed_seconds"] = round(time.monotonic()-start,3)
    emit("GRID_RESULT", r)
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
                    elif op == "elevation_grid":
                        if not pinged or not host_ok(status(gm)):
                            raise ValueError("ping and empty registered desktop required")
                        # One fixed diagnostic, then stop even when coverage fails.
                        probe_finished = True
                        response.update(ok=True, result=elevation_grid(gm, True))
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
        root = Path(tempfile.mkdtemp(prefix="Zone80-GM-Bridge-v03-"))
        serve(gm, root)
    except Exception as exc:
        emit("BLOCKED", {"reason": type(exc).__name__})


if __name__ == "__main__":
    main()
