"""Candidate v02 entrypoint. GRM worker owns its recovery; handoff unchanged."""
import ctypes
from ctypes import wintypes
import contextlib
import subprocess
import msvcrt
import os
from pathlib import Path
import re
import sys
import uuid
import pipeline_gate as g
import handoff_gate as h
import cc01_base as b

ROOT=g.ROOT

@contextlib.contextmanager
def lock():
    p=g.safe(ROOT/"runner.lock")
    g.need(p.is_file(),"existing runner lock required")
    with p.open("r+b") as f:
        f.seek(0)
        try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise b.Blocked("runner lock held") from None
        try:yield
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)

def main():
    g.need(sys.platform=="win32" and g.safe(Path(__file__).parent)==ROOT,"fixed Windows fixture only")
    # Existing stages retain their own exclusive lock, validation, and stop gates.
    g.run()
    with lock():
        h.main()
        stage=ROOT/"TBChange01"
        pins={"verify_change.py":"b5671bdfb1ef171b080720d523d37ccbe8dac889b5e8f1363d8719878877957f",
              "checkpoint_change.py":"d4edabd79e6fec644aaace23a6c5d69202950cc9808148cb08d3c3eeac6cb105",
              "recover_change.py":"21457a14325e045ffb03e1d160f60af4c028ef7817b59e325c99a9d35c4e6646"}
        for n,digest in pins.items():g.need(g.hashed(stage/n)==digest,"TB recovery code pin")
        sys.path.insert(0,str(stage))
        import recover_change as recovery
        g.need(Path(recovery.__file__).resolve()==stage/"recover_change.py","TB recovery module identity")
        recovery.reconcile(stage)
    print("PASS verified GRM + handoff + reconciled TB saved import; visual/shape gates remain",flush=True)

if __name__=="__main__":
    try:main()
    except (b.Blocked,OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.TimeoutExpired) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
