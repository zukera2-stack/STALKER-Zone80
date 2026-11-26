"""Console client for the bounded Zone80 bridge; no executable payloads."""
import argparse
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid


def read_json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("not an ordinary JSON file")
    with path.open("rb") as stream:
        data = stream.read(65537)
    if len(data) > 65536:
        raise ValueError("oversize response")
    return json.loads(data.decode("utf-8"))


def check_root(root):
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("not an ordinary session directory")
    root = root.resolve(strict=True)
    temp = Path(tempfile.gettempdir()).resolve(strict=True)
    if root.parent != temp or not root.name.startswith("Zone80-GM-Bridge-v04-"):
        raise ValueError("not a bridge session in this user's temp directory")
    ready = read_json(root / "ready.json")
    if (ready.get("schema") != 4 or ready.get("state") != "READY"
            or type(ready.get("pid")) is not int or (root / "finished.json").exists()
            or not 0 <= time.time() - ready["created_unix"] < ready["lifetime_seconds"]):
        raise ValueError("session not active")
    return root, ready


def request(root, op, timeout=None):
    if timeout is None:
        timeout = 330 if op == "export_candidate" else 10
    if op not in ("ping", "status", "stop", "export_candidate"):
        raise ValueError("unknown operation")
    root, ready = check_root(root)
    request_id = uuid.uuid4().hex
    path = root / ("request-" + request_id + ".json")
    fd, name = tempfile.mkstemp(prefix=".client-", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 4, "id": request_id, "op": op}, stream)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)
    response = root / ("response-" + request_id + ".json")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response.exists():
            value = read_json(response)
            if (value.get("schema") != 4 or value.get("id") != request_id
                    or value.get("pid") != ready["pid"] or value.get("op") != op):
                raise ValueError("response identity mismatch")
            return value
        if (root / "finished.json").exists() and not response.exists():
            raise RuntimeError("session stopped before response")
        time.sleep(0.1)
    raise TimeoutError("no response; do not retry blindly")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, help="exact READY directory")
    parser.add_argument("operation", choices=("ping", "status", "stop", "export_candidate"))
    args = parser.parse_args()
    try:
        value = request(args.directory, args.operation)
        print(json.dumps(value, ensure_ascii=True))
        if value.get("ok") is not True:
            return 1
        if args.operation == "export_candidate":
            result = value.get("result")
            if not isinstance(result, dict) or result.get("status") != "CANDIDATE_EXPORTED_QC_REQUIRED":
                return 2
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
