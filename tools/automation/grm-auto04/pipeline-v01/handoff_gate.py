"""Bind current verified GRM output to existing handoff adapter, fixed fixture only."""
from pathlib import Path
import json, shutil, subprocess, sys, os, re, msvcrt
import pipeline_gate as g
import cc01_base as b
ROOT=g.ROOT
SOURCE=g.SOURCE
DEST=ROOT/"Handoff01"
STAGE=DEST/"GRMAUTO04"
ADAPTER="2be62bc392af43ba955088cad3109e22b93ca38e4ab18c52a0fdbb3b805df938"
def need(ok,msg):g.need(ok,msg)
def main():
    m,identity=g.validate_snapshot()
    current=g.load(ROOT/"current.json")
    need(current["identity"]==identity and re.fullmatch("attempt-[0-9a-f]{32}",current["attempt"]),"current identity")
    attempt=ROOT/current["attempt"]
    out=attempt/"GRMAUTO04/c"
    report=g.verify_export(out,m)
    need(g.hashed(attempt/"report.json")==current["report_sha256"] and g.load(attempt/"report.json")==report,"current report")
    marker=ROOT/"stop.request"
    need(not marker.exists() and not (ROOT/"inflight.json").exists(),"stop/unresolved")
    original=g.tree(SOURCE/"TBHandoff")
    script=SOURCE/"prepare_integrated.py"
    need(g.hashed(script)==ADAPTER,"original adapter hash")
    # Only root location of read-only reference artifacts changes; adapter logic untouched.
    text=script.read_text(encoding="utf-8")
    a='old=R.parent/"GRMAUTO01"/"TBHandoff"'
    z='prev=R.parent/"GRMAUTO03"'
    need(text.count(a)==text.count(z)==1,"adapter anchors")
    patched=text.replace(a,r'old=Path(r"D:\Zone80\GRMAUTO01\TBHandoff")').replace(z,r'prev=Path(r"D:\Zone80\GRMAUTO03")')
    # c is the actual current run; d is a previously measured identical run.
    if DEST.exists():
        p=DEST/"receipt.json"
        need(p.is_file(),"unresolved handoff attempt; preserve evidence")
        receipt=g.load(p)
        need(receipt["identity"]==identity and receipt["current_sha256"]==g.hashed(ROOT/"current.json") and receipt["adapter_sha256"]==g.hashed(STAGE/"prepare_integrated.py") and receipt["files"]==g.tree(STAGE/"TBHandoff") and receipt["archive_sha256"]==g.hashed(STAGE/"GRMAUTO04_TB_IMPORT.zip"),"handoff cache mismatch")
        print("SKIP verified handoff",len(receipt["files"]));return
    DEST.mkdir();STAGE.mkdir()
    for rel,digest in m["input_files"].items():g.copy(ROOT/"snapshot/inputs"/rel,STAGE/rel,digest)
    for rel,digest in m["baseline"].items():
        g.copy(out/rel,STAGE/"c"/rel,digest)
        g.copy(SOURCE/"d"/rel,STAGE/"d"/rel,digest)
    dest=STAGE/"prepare_integrated.py"
    with dest.open("x",encoding="utf-8",newline="\n") as f:f.write(patched)
    with (DEST/"stdout.log").open("xb") as o,(DEST/"stderr.log").open("xb") as e:
        proc=subprocess.run([sys.executable,"-B",str(dest)],cwd=STAGE,stdout=o,stderr=e,timeout=60)
    need(proc.returncode==0,"handoff adapter failed")
    handoff=STAGE/"TBHandoff"; new=g.tree(handoff)
    need(set(new)==set(original) and len(new)==15,"handoff file count")
    for rel in original:
        if rel not in ("layers.cfg","MANIFEST.json"):need(new[rel]==original[rel],"handoff byte mismatch: "+rel)
    cfg=(handoff/"layers.cfg").read_text()
    oldcfg=(SOURCE/"TBHandoff/layers.cfg").read_text()
    need(cfg==oldcfg.replace(str(SOURCE/"TBHandoff/maplegend.png"),str(handoff/"maplegend.png")),"legend rebase mismatch")
    newm=g.load(handoff/"MANIFEST.json");oldm=g.load(SOURCE/"TBHandoff/MANIFEST.json")
    need(newm["files"]=={k:v for k,v in new.items() if k!="MANIFEST.json"},"manifest actual mismatch")
    need({k:v for k,v in newm.items() if k!="files"}=={k:v for k,v in oldm.items() if k!="files"},"manifest semantics")
    need(g.tree(SOURCE/"TBHandoff")==original and g.validate_snapshot()[1]==identity and not marker.exists(),"input changed")
    receipt={"status":"PASS","identity":identity,"current_sha256":g.hashed(ROOT/"current.json"),"adapter_sha256":g.hashed(dest),"files":new,"archive_sha256":g.hashed(STAGE/"GRMAUTO04_TB_IMPORT.zip"),"reference_run":"historic d, not a second fresh execution","native_tb":"NOT_RUN"}
    g.atomic(DEST/"receipt.json",receipt)
    print("HANDOFF PASS",len(new),"files; 13 equal, 2 path/manifest changes",receipt["archive_sha256"])
if __name__=="__main__":
    try:
        g.safe(ROOT)
        with (ROOT/"runner.lock").open("r+b") as f:
            f.seek(0)
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            try:main()
            finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
    except (b.Blocked,OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as e:
        print("BLOCKED",e,file=sys.stderr);raise SystemExit(2)
