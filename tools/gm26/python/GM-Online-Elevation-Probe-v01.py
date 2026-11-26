"""MAP-003: read actual GM elevations, never export or fill a grid."""
import json
import math
import os
import struct
import sys
import time

SRTM = "SRTM Worldwide Elevation Data (1-arc-second Resolution, SRTM Plus V3)"
CONTROL = [(294688.084, 5699727.108), (294988.084, 5699427.108),
           (295348.084, 5699067.108), (295708.084, 5698707.108),
           (295978.084, 5698437.108)]
LIMIT_SECONDS = 300


def emit(kind, data):
    print("ZONE80_ELEV_V01_" + kind + " " + json.dumps(data, ensure_ascii=True, allow_nan=False), flush=True)


def field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def source_names(raw):
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
    if (os.name != "nt" or os.path.basename(sys.executable or "").lower() != "global_mapper.exe"
            or struct.calcsize("P") != 8 or gm.GetSDKVersion() != 2621
            or gm.IsRegistered() != 1):
        return "BLOCKED_DESKTOP_HOST"
    _, count = gm.GetLoadedLayerList()
    if count != 0:
        return "BLOCKED_NONEMPTY_WORKSPACE"
    invalid = float(gm.GM_INVALID_ELEV_VALUE)
    names, count, complete = source_names(gm.GetAvailableOnlineSourceList())
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
    code, _ = gm.GetOnlineSourceInfo(source)
    report["source_code"] = int(code)
    if code != 0:
        return "BLOCKED_SOURCE_INFO"
    bounds = gm.GM_Rectangle_t()
    bounds.mMinX, bounds.mMinY, bounds.mMaxX, bounds.mMaxY = 30.041, 51.395, 30.074, 51.417
    handle = None
    try:
        code, handle = gm.LoadOnlineLayer(source, bounds, "BOUNDS_PROJ=EPSG:4326")
        report["load_code"] = int(code)
        if code != 0 or not handle:
            return "BLOCKED_LOAD"
        info = gm.GetLayerInfo(handle)
        if not field(info, "mHasRasterData"):
            return "BLOCKED_NOT_RASTER"
        code, projection = gm.LoadProjectionFromEPSGCode(32636)
        report["projection_load_code"] = int(code)
        if code != 0:
            return "BLOCKED_PROJECTION"
        code = gm.SetProjection(projection)
        report["projection_set_code"] = int(code)
        if code != 0:
            return "BLOCKED_PROJECTION"
        start = time.monotonic()
        controls = []
        for x, y in CONTROL:
            if time.monotonic() - start > LIMIT_SECONDS:
                return "BLOCKED_SAMPLE_BUDGET"
            controls.append(sample(gm, handle, x, y, invalid))
            emit("POINT", controls[-1])
        report["controls"] = controls
        if not all(p["valid"] for p in controls):
            return "BLOCKED_CONTROL_COVERAGE"
        valid, missing, minimum, maximum = 0, 0, None, None
        report["grid"] = {"expected": 4096, "checked": 0, "valid": 0, "invalid": 0}
        for row in range(64):
            for col in range(64):
                if time.monotonic() - start > LIMIT_SECONDS:
                    return "BLOCKED_SAMPLE_BUDGET"
                x = round(294388.084 + col * 30, 3)
                y = round(5700027.108 - row * 30, 3)
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
                gm.CloseLayer(handle)
                report["close_called"] = True
            except Exception as exc:
                report["cleanup_error"] = type(exc).__name__


def main():
    report = {"schema": 1, "status": "BLOCKED", "export": "NOT_RUN"}
    emit("START", report)
    try:
        import globalmapper as gm
        report["status"] = run(gm, report)
    except Exception as exc:
        report.update(status="BLOCKED_EXCEPTION", error_type=type(exc).__name__)
    if "cleanup_error" in report:
        report["status"] = "BLOCKED_CLEANUP"
    emit("RESULT", report)


if __name__ == "__main__":
    main()
