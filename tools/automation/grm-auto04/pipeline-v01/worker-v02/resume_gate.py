"""Candidate v02 entrypoint. GRM worker owns its recovery; handoff unchanged."""
import ctypes
from ctypes import wintypes
import contextlib
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
    with lock():h.main()
    print("PASS existing GRM + handoff; further TB steps not automated here",flush=True)

if __name__=="__main__":
    try:main()
    except (b.Blocked,OSError,ValueError,TypeError,KeyError,RuntimeError) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
