"""MAP-003: read actual GM elevations, never export or fill a grid."""
import json
import math
import os
import struct
import sys
import time
import traceback

SRTM = "SRTM Worldwide Elevation Data (1-arc-second Resolution, SRTM Plus V3)"
CONTROL = [(294688.084, 5699727.108), (294988.084, 5699427.108),
           (295348.084, 5699067.108), (295708.084, 5698707.108),
           (295978.084, 5698437.108)]
LIMIT_SECONDS = 300


def emit(kind, data):
    print("ZONE80_ELEV_V02_" + kind + " " + json.dumps(data, ensure_ascii=True, allow_nan=False), flush=True)


def field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def step(report, name):
    report["stage"] = name
    emit("STEP", {"stage": name})


def shape(raw):
    # Types/counts only: never stringify handles, provider data or credentials.
    result = {"type": type(raw).__name__}
    if type(raw) is int:
        result["integer"] = raw
    elif isinstance(raw, (tuple, list)):
        result["length"] = len(raw)
        result["item_types"] = [type(x).__name__ for x in raw[:4]]
        if len(raw) == 2 and type(raw[1]) is int:
            result["count"] = raw[1]
    return result


def layer_count(raw):
    if type(raw) is int and raw == 0:
        return 0
    if (isinstance(raw, (tuple, list)) and len(raw) == 2
            and type(raw[1]) is int and raw[1] >= 0):
        return raw[1]
    return None


def error_details(exc, stage):
    frames = traceback.extract_tb(exc.__traceback__)
    last = frames[-1] if frames else None
    # No exception message or absolute filename: either can contain secrets.
    return {"error_type": type(exc).__name__, "failed_stage": stage,
            "error_line": last.lineno if last else None,
            "error_function": last.name if last else None}


def source_names(raw):
    if (not isinstance(raw, (tuple, list)) or len(raw) != 2
            or type(raw[1]) is not int or raw[1] < 0):
        raise TypeError("Unexpected catalog return shape")
    entries, count = raw
    # The v26.2 wrapper has returned just the first dict. Never cast it to a pointer.
    entries = [entries] if isinstance(entries, dict) else entries
    if not isinstance(entries, (list, tuple)):
        return [], int(count), False
    names = [field(e, "mName") for e in entries]
    names = [n for n in names if isinstance(n, str) and n]
    return names, int(count), len(names) == count and len(set(names)) == count


def sample(gm, handle, x, y, invalid):
    code, value = gm.GetLocationElevation(handle, x, y)
    code = int(code)
    z = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    valid = (code == 0 and z is not None and math.isfinite(z)
             and z != invalid and -500.0 <= z <= 9000.0)
    return {"e": x, "n": y, "code": code, "z_m": z if valid else None, "valid": valid}


def run(gm, report):
    step(report, "DESKTOP_HOST")
    if (os.name != "nt" or os.path.basename(sys.executable or "").lower() != "global_mapper.exe"
            or struct.calcsize("P") != 8 or gm.GetSDKVersion() != 2621
            or gm.IsRegistered() != 1):
        return "BLOCKED_DESKTOP_HOST"
    step(report, "GET_LOADED_LAYER_LIST")
    raw = gm.GetLoadedLayerList()
    report["workspace_shape"] = shape(raw)
    count = layer_count(raw)
    if count is None:
        return "BLOCKED_WORKSPACE_SHAPE"
    report["workspace_count"] = count
    if count != 0:
        return "BLOCKED_NONEMPTY_WORKSPACE"
    step(report, "INVALID_ELEVATION_CONSTANT")
    invalid = float(gm.GM_INVALID_ELEV_VALUE)
    if not math.isfinite(invalid):
        return "BLOCKED_INVALID_CONSTANT"
    step(report, "GET_AVAILABLE_ONLINE_SOURCE_LIST")
    raw = gm.GetAvailableOnlineSourceList()
    report["catalog_shape"] = shape(raw)
    names, count, complete = source_names(raw)
    report.update(catalog_count=count, names_returned=len(names), catalog_complete=complete)
    candidates = sorted({n for n in names if "copernicus" in n.casefold()
                         and ("dem" in n.casefold() or "elevation" in n.casefold())
                         and ("30" in n.casefold() or "glo-30" in n.casefold())})
    report["copernicus_candidates"] = candidates
    if len(candidates) > 1:
        return "BLOCKED_AMBIGUOUS_SOURCE"
    source = candidates[0] if candidates else SRTM
    report.update(source=source, diagnostic_only=source == SRTM,
                  vertical_datum="UNVERIFIED", epsg=32636)
    emit("SOURCE", report)
    step(report, "GET_ONLINE_SOURCE_INFO")
    code, _ = gm.GetOnlineSourceInfo(source)
    report["source_code"] = int(code)
    if code != 0:
        return "BLOCKED_SOURCE_INFO"
    step(report, "CREATE_BOUNDS")
    bounds = gm.GM_Rectangle_t()
    bounds.mMinX, bounds.mMinY, bounds.mMaxX, bounds.mMaxY = 30.041, 51.395, 30.074, 51.417
    handle = None
    try:
        step(report, "LOAD_ONLINE_LAYER")
        raw = gm.LoadOnlineLayer(source, bounds, "BOUNDS_PROJ=EPSG:4326")
        report["load_shape"] = shape(raw)
        code, handle = raw
        report["load_code"] = int(code)
        if code != 0 or not handle:
            return "BLOCKED_LOAD"
        step(report, "GET_LAYER_INFO")
        info = gm.GetLayerInfo(handle)
        if not field(info, "mHasRasterData"):
            return "BLOCKED_NOT_RASTER"
        step(report, "LOAD_PROJECTION")
        raw = gm.LoadProjectionFromEPSGCode(32636)
        report["projection_shape"] = shape(raw)
        code, projection = raw
        report["projection_load_code"] = int(code)
        if code != 0:
            return "BLOCKED_PROJECTION"
        step(report, "SET_PROJECTION")
        code = gm.SetProjection(projection)
        report["projection_set_code"] = int(code)
        if code != 0:
            return "BLOCKED_PROJECTION"
        start = time.monotonic()
        step(report, "CONTROL_SAMPLING")
        controls = []
        report["controls"] = controls
        for i, (x, y) in enumerate(CONTROL, 1):
            report["sample_position"] = {"control": i}
            if time.monotonic() - start > LIMIT_SECONDS:
                return "BLOCKED_SAMPLE_BUDGET"
            controls.append(sample(gm, handle, x, y, invalid))
            emit("POINT", controls[-1])
        report["controls"] = controls
        if not all(p["valid"] for p in controls):
            return "BLOCKED_CONTROL_COVERAGE"
        step(report, "GRID_SAMPLING")
        valid, missing, minimum, maximum = 0, 0, None, None
        report["grid"] = {"expected": 4096, "checked": 0, "valid": 0, "invalid": 0}
        for row in range(64):
            for col in range(64):
                if time.monotonic() - start > LIMIT_SECONDS:
                    return "BLOCKED_SAMPLE_BUDGET"
                x = round(294388.084 + col * 30, 3)
                y = round(5700027.108 - row * 30, 3)
                report["sample_position"] = {"row": row, "col": col}
                p = sample(gm, handle, x, y, invalid)
                if p["valid"]:
                    z = p["z_m"]
                    valid += 1
                    minimum = z if minimum is None else min(minimum, z)
                    maximum = z if maximum is None else max(maximum, z)
                else:
                    missing += 1
                report["grid"].update(checked=valid + missing, valid=valid, invalid=missing,
                                      min_m=minimum, max_m=maximum)
            if (row + 1) % 8 == 0:
                emit("GRID_PROGRESS", report["grid"])
        if missing:
            return "BLOCKED_GRID_COVERAGE"
        if minimum == maximum:
            return "BLOCKED_CONSTANT_GRID"
        return "DIAGNOSTIC_COVERAGE_PASS" if source == SRTM else "COVERAGE_PASS_NEEDS_PROVENANCE"
    finally:
        if handle:
            try:
                emit("STEP", {"stage": "CLOSE_OWNED_LAYER"})
                gm.CloseLayer(handle)
                report["close_called"] = True
            except Exception as exc:
                report["cleanup_error"] = error_details(exc, "CLOSE_OWNED_LAYER")


def main():
    report = {"schema": 2, "status": "BLOCKED", "export": "NOT_RUN", "stage": "IMPORT_API"}
    emit("START", report)
    try:
        import globalmapper as gm
        report["status"] = run(gm, report)
    except Exception as exc:
        report.update(error_details(exc, report["stage"]))
        report["status"] = "BLOCKED_EXCEPTION"
    if "cleanup_error" in report:
        report["status_before_cleanup"] = report["status"]
        report["status"] = "BLOCKED_CLEANUP"
    emit("RESULT", report)


if __name__ == "__main__":
    main()
