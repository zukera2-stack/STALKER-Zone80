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

VERSION = 7
LIFETIME = 300.0
MAX_REQUESTS = 5
REQUEST = re.compile(r"request-([0-9a-f]{32})\.json\Z")
OPERATIONS = {"ping", "status", "stop", "export_candidate"}


def emit(kind, value):
    print("ZONE80_BRIDGE_V07_" + kind + " " + json.dumps(value, ensure_ascii=True), flush=True)


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



def export_candidate(gm, host_confirmed, output_parent):
    """Fixed SRTM diagnostic: exact UTM cell centers queried in WGS84."""
    import math
    import hashlib
    import traceback

    source = "SRTM Worldwide Elevation Data (1-arc-second Resolution, SRTM Plus V3)"
    bbox = (30.041, 51.395, 30.074, 51.417)
    controls = [(294688.084, 5699727.108, 30.047580700382, 51.411534691737),
                (294988.084, 5699427.108, 30.052062010081, 51.408949230160),
                (295348.084, 5699067.108, 30.057438915213, 51.405846437886),
                (295708.084, 5698707.108, 30.062815093355, 51.402743385634),
                (295978.084, 5698437.108, 30.066846749945, 51.400415925884)]
    r = {"schema": 8, "source": source, "diagnostic_only": True,
         "vertical_datum": "UNVERIFIED", "source_acceptance": "DIAGNOSTIC_ONLY", "query_epsg": 4326, "grid_epsg": 32636,
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
        if not output_parent or not safe_output_parent(output_parent):
            return "BLOCKED_OUTPUT_PARENT"
        if not callable(getattr(gm, "ExportElevationEx", None)) or not all(hasattr(gm, n) for n in (
                "GM_Export_Arc_ASCII_Grid", "GM_Export_ElevGeoTIFF", "GM_ExportFlags_GenPRJFile",
                "GM_ExportFlags_NoCompression", "GM_ExportFlags_FillSmallGaps", "GM_ElevUnit_Meters", "GM_LoadFlags_NoWebDownload", "GM_LoadFlags_NoProjPrompt")):
            return "BLOCKED_EXPORT_API"
        if not callable(getattr(gm,"LoadLayer",None)):
            return "BLOCKED_LOCAL_LOAD_API"
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
        # Inset one sample from the online extent. Covers all pilot corners plus margin.
        step("WGS84_INTERMEDIATE")
        if not budget() or not safe_output_parent(output_parent):
            return "BLOCKED_EXPORT_GATE"
        folder = Path(tempfile.mkdtemp(prefix="native-export-", dir=str(output_parent)))
        r["output_directory"] = str(folder)
        r["export"] = "PARTIAL"
        r["export_commands"] = []
        bounds = gm.GM_Rectangle_t()
        bounds.mMinX,bounds.mMinY,bounds.mMaxX,bounds.mMaxY = (30.04125,51.39525,30.07375,51.41675)
        # Prove pilot outer corners covered by the intermediate center hull, not just its edges.
        for e in (294373.084,296293.084):
            for n in (5698122.108,5700042.108):
                x,y,code = transform(e,n)
                if code != 0 or x is None or y is None or not (bounds.mMinX < x < bounds.mMaxX and bounds.mMinY < y < bounds.mMaxY):
                    return "BLOCKED_INTERMEDIATE_COVERAGE"
        flags=gm.GM_ExportFlags_GenPRJFile
        file=folder/"SRTM_WGS84_INTERMEDIATE.asc"
        if flags & gm.GM_ExportFlags_FillSmallGaps or file.exists():
            return "BLOCKED_EXPORT_PATH_OR_FLAGS"
        code=gm.ExportElevationEx(str(file),gm.GM_Export_Arc_ASCII_Grid,[owned],bounds,131,87,flags,gm.GM_ElevUnit_Meters,None)
        r["export_commands"].append({"format":"wgs84_asc","code":int(code),"file_exists":file.is_file()})
        if code!=0 or not file.is_file():
            return "BLOCKED_INTERMEDIATE_EXPORT"
        # Read-only validation BEFORE reloading. No raster is produced by Python.
        prj=file.with_suffix(".prj")
        try:
            if not ordinary_file(file) or not ordinary_file(prj) or file.stat().st_size>2_000_000 or prj.stat().st_size>65536:
                return "BLOCKED_INTERMEDIATE_FILE"
            raw=file.read_bytes(); pbytes=prj.read_bytes()
            lines=raw.decode('utf-8-sig').splitlines()
            fields={k.lower():float(v) for k,v in (line.split() for line in lines[:6])}
            if set(fields)!={'ncols','nrows','xllcorner','yllcorner','cellsize','nodata_value'} or len(lines)!=93 or fields['ncols']!=131 or fields['nrows']!=87:
                return "BLOCKED_INTERMEDIATE_GRID"
            if any(not math.isfinite(fields[k]) or abs(fields[k]-v)>1e-8 for k,v in {'xllcorner':30.041125,'yllcorner':51.395125,'cellsize':.00025}.items()):
                return "BLOCKED_INTERMEDIATE_GRID"
            rows=[list(map(float,line.split())) for line in lines[6:]]
            if any(len(row)!=131 for row in rows): return "BLOCKED_INTERMEDIATE_GRID"
            vals=[v for row in rows for v in row]
            if any(not math.isfinite(v) or v==fields['nodata_value'] or not -500<=v<=9000 for v in vals) or min(vals)==max(vals):
                return "BLOCKED_INTERMEDIATE_NODATA"
            wkt=pbytes.decode('utf-8-sig').upper()
            if not wkt.startswith('GEOGCS[') or 'D_WGS84' not in wkt or '6378137' not in wkt or 'PROJCS[' in wkt or 'UNIT["DEGREE"' not in wkt:
                return "BLOCKED_INTERMEDIATE_CRS"
            r['intermediate']={'cols':131,'rows':87,'valid':len(vals),'nodata':0,'min_m':min(vals),'max_m':max(vals),'header':fields,'asc_sha256':hashlib.sha256(raw).hexdigest(),'prj_sha256':hashlib.sha256(pbytes).hexdigest()}
        except (OSError,ValueError,KeyError):
            return "BLOCKED_INTERMEDIATE_QC"
        step("RELOAD_LOCAL")
        old=owned; owned=None
        r['online_close_code']=int(gm.CloseLayer(old))
        if r['online_close_code']!=0 or count_layers(gm.GetLoadedLayerList())!=0:
            return "BLOCKED_ONLINE_CLEANUP"
        # Single ordinary ASC + its verified PRJ. LoadLayer returns one handle, no web downloads.
        code,handle=gm.LoadLayer(str(file),gm.GM_LoadFlags_NoWebDownload|gm.GM_LoadFlags_NoProjPrompt)
        if handle: owned=handle
        r['local_load_code']=int(code)
        if code!=0 or not owned or count_layers(gm.GetLoadedLayerList())!=1:
            return "BLOCKED_LOCAL_LOAD"
        if gm.SetProjection(geo)!=0: return "BLOCKED_LOCAL_GEO_PROJECTION"
        local_info=gm.GetLayerInfo(owned)
        r['local_layer_type']=str(field(local_info,'mTypeName'))[:100]
        if not field(local_info,'mHasRasterData'): return "BLOCKED_LOCAL_LAYER"
        r['local_controls']=[]
        for p in r['controls']:
            code,z=gm.GetLocationElevation(owned,p['lon'],p['lat']); z=num(z)
            if code!=0 or z is None or z==invalid or not -500<=z<=9000:
                return "BLOCKED_LOCAL_CONTROL"
            d=abs(z-p['z_m']); r['local_controls'].append({'index':p['index'],'z_m':z,'source_delta_m':d})
        if max(p['source_delta_m'] for p in r['local_controls'])>1.0:
            return "BLOCKED_LOCAL_CONTROL_DELTA"
        step("EXPORT_PROJECTION")
        if gm.SetProjection(utm)!=0: return "BLOCKED_EXPORT_PROJECTION"
        code,x,y=gm.ProjectPointAtElev(controls[0][2],controls[0][3],geo,None,0.0)
        if code!=0 or num(x) is None or num(y) is None or abs(x-controls[0][0])>.2 or abs(y-controls[0][1])>.2:
            return "BLOCKED_EXPORT_PROJECTION_READBACK"
        bounds=gm.GM_Rectangle_t()
        bounds.mMinX,bounds.mMinY,bounds.mMaxX,bounds.mMaxY=(294388.084,5698137.108,296278.084,5700027.108)
        r['export_bounds']=[294388.084,5698137.108,296278.084,5700027.108]
        r['resampling']='TWO_NATIVE_EXPORTS_DEFAULT_UNVERIFIED'
        for suffix,fmt,flags,extra in (("asc",gm.GM_Export_Arc_ASCII_Grid,gm.GM_ExportFlags_GenPRJFile,None),("tif",gm.GM_Export_ElevGeoTIFF,gm.GM_ExportFlags_NoCompression,"VOID_VALUE=-9999")):
            step("EXPORT_UTM_"+suffix.upper())
            if not budget() or count_layers(gm.GetLoadedLayerList())!=1: return "BLOCKED_EXPORT_GATE"
            target=folder/("MAP003_SRTM."+suffix)
            if target.exists() or flags & gm.GM_ExportFlags_FillSmallGaps: return "BLOCKED_EXPORT_PATH_OR_FLAGS"
            code=gm.ExportElevationEx(str(target),fmt,[owned],bounds,64,64,flags,gm.GM_ElevUnit_Meters,extra)
            r['export_commands'].append({'format':suffix,'code':int(code),'file_exists':target.is_file()})
            if code!=0 or not target.is_file() or not ordinary_file(target) or not target.stat().st_size:
                return "BLOCKED_UTM_EXPORT_"+suffix.upper()
        prj=folder/'MAP003_SRTM.prj'
        if not prj.is_file() or not ordinary_file(prj) or not prj.stat().st_size: return "BLOCKED_PRJ"
        r['export']='FILES_CREATED_QC_NOT_RUN'
        return "CANDIDATE_EXPORTED_QC_REQUIRED"

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
        if not owned:
            r["remaining_layers"]=count_layers(gm.GetLoadedLayerList())
            r["cleanup_ok"]=r["remaining_layers"]==0 and r.get("online_close_code",0)==0
            if not r["cleanup_ok"]:
                r["status_before_cleanup"]=r["status"]; r["status"]="BLOCKED_CLEANUP"
        r["elapsed_seconds"] = round(time.monotonic()-start,3)
    emit("GRID_RESULT", r)
    return r


def safe_output_parent(path):
    # Only a staged script directory under reports/MAP-003, not a configurable remote path.
    try:
        path = Path(path)
        if not path.is_absolute() or path.name != "dc-bridge-v07-20261126" or path.parent.name != "MAP-003" or path.parent.parent.name != "reports":
            return False
        for p in (path, *path.parents):
            info = p.lstat()
            if not stat.S_ISDIR(info.st_mode) or p.is_symlink() or getattr(info,"st_file_attributes",0) & 0x400:
                return False
        return True
    except (OSError, ValueError):
        return False


def host_ok(check):
    return (os.name == "nt" and check["host"] == "global_mapper.exe"
            and check["bits"] == 64 and check["python"][:2] == [3, 9]
            and check["sdk"] == 2621 and check["registered"] and check["layers"] == 0)

def serve(gm, root, lifetime=LIFETIME, max_requests=MAX_REQUESTS, output_parent=None):
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
                    elif op == "export_candidate":
                        if not pinged or not host_ok(status(gm)):
                            raise ValueError("ping and empty registered desktop required")
                        # One fixed diagnostic, then stop even when coverage fails.
                        probe_finished = True
                        response.update(ok=True, result=export_candidate(gm, True, output_parent))
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
        root = Path(tempfile.mkdtemp(prefix="Zone80-GM-Bridge-v07-"))
        source_path = globals().get("__file__")
        output_parent = Path(source_path).absolute().parent if source_path else None
        if not output_parent or not safe_output_parent(output_parent):
            emit("BLOCKED", {"reason":"SCRIPT_LOCATION_NOT_CONFIRMED"})
            return
        serve(gm, root, output_parent=output_parent)
    except Exception as exc:
        emit("BLOCKED", {"reason": type(exc).__name__})


if __name__ == "__main__":
    main()
