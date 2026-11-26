"""Console client for the bounded Zone80 bridge; no executable payloads."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time
import uuid


def read_json(path):
    with path.open("rb") as stream:
        data = stream.read(16385)
    if len(data) > 16384:
        raise ValueError("oversize response")
    return json.loads(data.decode("utf-8"))


def check_root(root):
    root = root.resolve(strict=True)
    temp = Path(tempfile.gettempdir()).resolve(strict=True)
    if root.parent != temp or not root.name.startswith("Zone80-GM-Bridge-v01-"):
        raise ValueError("not a bridge session in this user's temp directory")
    ready = read_json(root / "ready.json")
    if (ready.get("schema") != 1 or ready.get("state") != "READY"
            or type(ready.get("pid")) is not int or (root / "finished.json").exists()
            or not 0 <= time.time() - ready["created_unix"] < ready["lifetime_seconds"]):
        raise ValueError("session not active")
    return root, ready


def request(root, op, timeout=10):
    if op not in ("ping", "status", "stop"):
        raise ValueError("unknown operation")
    root, ready = check_root(root)
    request_id = uuid.uuid4().hex
    path = root / ("request-" + request_id + ".json")
    fd, name = tempfile.mkstemp(prefix=".client-", dir=str(root))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 1, "id": request_id, "op": op}, stream)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)
    response = root / ("response-" + request_id + ".json")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response.exists():
            value = read_json(response)
            if (value.get("schema") != 1 or value.get("id") != request_id
                    or value.get("pid") != ready["pid"] or value.get("op") != op):
                raise ValueError("response identity mismatch")
            return value
        if (root / "finished.json").exists():
            raise RuntimeError("session stopped before response")
        time.sleep(0.1)
    raise TimeoutError("no response; do not retry blindly")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, help="exact READY directory")
    parser.add_argument("operation", choices=("ping", "status", "stop"))
    args = parser.parse_args()
    try:
        value = request(args.directory, args.operation)
        print(json.dumps(value, ensure_ascii=True))
        return 0 if value.get("ok") is True else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
