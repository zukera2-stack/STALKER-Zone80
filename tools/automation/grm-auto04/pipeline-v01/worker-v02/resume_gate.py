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
              "checkpoint_change.py":"7342355ffac043ab35c5d4be0b7163a1c22beb842814edc99f8dabb024ace32f"}
        for n,digest in pins.items():g.need(g.hashed(stage/n)==digest,"TB checkpoint code pin")
        g.need((stage/"change_checkpoint.json").is_file(),"TB changed layer checkpoint incomplete; no automatic import")
        result=subprocess.run([sys.executable,"-B",str(stage/"checkpoint_change.py")],cwd=stage,timeout=30)
        g.need(result.returncode==0,"TB changed layer checkpoint refused")
    print("PASS verified GRM + handoff + saved TB object checkpoint; visual/shape gates remain",flush=True)

if __name__=="__main__":
    try:main()
    except (b.Blocked,OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.TimeoutExpired) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
