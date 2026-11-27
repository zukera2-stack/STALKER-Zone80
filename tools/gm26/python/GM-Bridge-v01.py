"""Zone80 GM bridge experiment: local, bounded, read-only, fixed operations."""
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile
import time

VERSION = 1
LIFETIME = 180.0
MAX_REQUESTS = 5
REQUEST = re.compile(r"request-([0-9a-f]{32})\.json\Z")
OPERATIONS = {"ping", "status", "stop"}


def emit(kind, value):
    print("ZONE80_BRIDGE_V01_" + kind + " " + json.dumps(value, ensure_ascii=True), flush=True)


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


def serve(gm, root, lifetime=LIFETIME, max_requests=MAX_REQUESTS):
    start = time.monotonic()
    seen = set()
    why = "TIME_LIMIT"
    pinged = False
    ready = {"schema": VERSION, "state": "READY", "pid": os.getpid(),
             "created_unix": time.time(), "lifetime_seconds": lifetime,
             "operations": sorted(OPERATIONS), "max_requests": max_requests}
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
                try:
                    op = read_request(path, request_id)
                    response["op"] = op
                    if op == "ping":
                        response.update(ok=True, result="PONG")
                        pinged = True
                    elif op == "status":
                        response.update(ok=True, result=status(gm))
                    elif op == "stop":
                        response.update(ok=True, result="STOPPING")
                        stop = True
                except Exception as exc:
                    response["error_type"] = type(exc).__name__
                write_json(root / ("response-" + request_id + ".json"), response)
                emit("RESPONSE", response)
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
        if (os.name != "nt" or check["host"] != "global_mapper.exe" or check["bits"] != 64
                or check["python"][:2] != [3, 9] or check["sdk"] != 2621
                or not check["registered"] or check["layers"] != 0):
            emit("BLOCKED", {"reason": "HOST_OR_EMPTY_WORKSPACE_NOT_CONFIRMED"})
            return
        # Fresh per-run directory in this Windows user's temporary folder, not GM's own temp files.
        root = Path(tempfile.mkdtemp(prefix="Zone80-GM-Bridge-v01-"))
        serve(gm, root)
    except Exception as exc:
        emit("BLOCKED", {"reason": type(exc).__name__})


if __name__ == "__main__":
    main()
