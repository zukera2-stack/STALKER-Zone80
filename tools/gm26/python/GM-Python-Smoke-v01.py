"""Zone80 MAP-003: read-only desktop Python smoke test (v01)."""
import json
import os
import struct
import sys


def probe():
    host = os.path.basename(sys.executable or "").lower()
    bits = struct.calcsize("P") * 8
    result = {"schema": 1, "host": host, "pid": os.getpid(),
              "python": list(sys.version_info[:3]), "bits": bits,
              "status": "BLOCKED"}
    try:
        import globalmapper as gm
        result["sdk"] = gm.GetSDKVersion()
        registered = gm.IsRegistered()
        result["registered"] = registered if type(registered) in (bool, int) else None
        if host != "global_mapper.exe" or os.name != "nt" or bits != 64:
            result["reason"] = "DESKTOP_HOST_NOT_CONFIRMED"
        elif result["sdk"] != 2621:
            result["reason"] = "SDK_VERSION_NOT_CONFIRMED"
        elif type(registered) not in (bool, int) or registered != 1:
            result["reason"] = "REGISTRATION_NOT_CONFIRMED"
        else:
            result["status"] = "SMOKE_PASS"
    except Exception as exc:
        result["reason"] = type(exc).__name__
    return result


print("ZONE80_SMOKE_V01_START", flush=True)
print("ZONE80_SMOKE_V01_RESULT " + json.dumps(probe(), ensure_ascii=True, default=str), flush=True)
