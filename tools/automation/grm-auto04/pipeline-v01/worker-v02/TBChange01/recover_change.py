"""TB-RECOVER-01: reconcile a completed native import without replay.

Fixed observed fixture only; a missing/uncertain native readback never permits
automatic import. No GUI mutation or termination. Keep original intent for audit.
"""
from pathlib import Path
import os, sys, json, subprocess
import checkpoint_change as c
from verify_change import R,C,g,req,sha,PLAN,CURRENT,setup,compare
ROOT=R.parent
TEST=R/"Recovery01"
EXPECTED="7d31ba94e0f7fe33b325430f568f653e6d8665ce5b2ae54eae148992c554681f"
PINS={
 "import_intent.json":"028dfbce8408c317e1b7b80da38086f8643d8ac2f91970617ae7aa21c188a120",
 "save_receipt.json":"0aac9b3e2155ef6b2fce7d43be06750b1331fd65a7d7e39ca264ed617099dfc8",
 "changed_export_qc.json":"43badb270492a8aeb7977ce66c1b0b5752bdd2a5b892d1ead69d974fc013684a",
 "native_objects.txt":"4e52b64dc6faf3e823804342c3129def372272ae7768543b48faf02d6c4e51eb",
 "f74d6ce9eb1d42929fdf13325a24f83e/CHILD.log":"79e0314cc5b60cf6cf6307a2d7a55f877b198d4302614741ec80cdd04f91403d",
 "54fd35654d1641a6b479f82a0b6f0a18/CHILD.log":"2cb5d185f417797bca4195e047f932222505ede5dac54a2c0cf2430864b902e2"
}
def encoded(o):return g.b.canonical(o)+b"\n"
def pinned_intent(o):
    req(type(o) is dict and set(o)=={"expected_count","plan_sha256","pre_count","utc","editor_pid","status","editor_ticks"},"unknown intent fields")
    req(o["status"]=="RUNNING" and o["plan_sha256"]==PLAN and o["pre_count"]==4562 and o["expected_count"]==4563,"intent identity")
    req(type(o["editor_pid"]) is int and o["editor_pid"]==9260 and type(o["editor_ticks"]) is int and o["editor_ticks"]==639314571534828805,"intent editor identity")
    req(o["utc"]=="2026-11-28T11:01:47.7671500Z","intent timestamp")
def route(base,probe,actual):
    """Content diagnosis only. Not a permission to replay or save.
    Callers must establish fresh native evidence/owner/clean state separately.
    """
    if actual is None:return "READBACK_REQUIRED"
    for expected,action in ((base+probe,"VERIFY_SAVED_OR_SAVE_ONCE"),(base,"VERIFY_BASE_BEFORE_IMPORT")):
        try:compare(expected,actual)
        except ValueError:continue
        return action
    return "BLOCK_AMBIGUOUS"
def validate():
    req(not (ROOT/"stop.request").exists(),"stop requested")
    for n,h in PINS.items():req(sha(R/n)==h,"evidence pin changed: "+n)
    pinned_intent(g.load(R/"import_intent.json"))
    a,p,_=setup()
    req(route(a,p,g.poses(R/"native_objects.txt"))=="VERIFY_SAVED_OR_SAVE_ONCE","native content mismatch")
    result=c.build()
    req(g.b.digest(encoded(result))==EXPECTED,"reconstructed checkpoint differs from observed accepted revision")
    # No fresh UI claim: historic native logs plus current exact persisted bytes.
    req(len(result["project_files"])==69,"file set mismatch")
    return result
def reconcile(dest,fault=""):
    req(dest in (R,TEST/"before-publication",TEST/"after-publication",TEST/"corrupt"),"fixed destination")
    req(fault in ("","before","after") and (not fault or dest!=R),"fault only in test destination")
    g.safe(dest)
    req(dest.is_dir(),"missing destination")
    out=dest/"change_checkpoint.json";done=dest/"import_resolution.json"
    result=validate()
    if done.exists():req(out.exists(),"resolution without checkpoint; preserve journal")
    if out.exists():
        req(sha(out)==EXPECTED and g.load(out)==result,"checkpoint mismatch; preserve journal")
    else:
        req(not (ROOT/"stop.request").exists(),"stop before publication")
        if fault=="before":
            print("INJECT abrupt recovery worker exit before checkpoint",flush=True);os._exit(73)
        g.atomic(out,result)
        req(sha(out)==EXPECTED,"checkpoint publication mismatch")
        if fault=="after":
            print("INJECT abrupt recovery worker exit after checkpoint",flush=True);os._exit(73)
    receipt={"status":"PASS","scope":"saved_native_object_import_reconciled",
        "identity":result["identity"],"intent_sha256":PINS["import_intent.json"],
        "checkpoint_sha256":EXPECTED,"parent_sha256":CURRENT,
        "native_export_sha256":PINS["native_objects.txt"],"object_count":4563,
        "action":"NO_REIMPORT","native_gui_crash":"NOT_RUN","whole_pipeline":"PARTIAL"}
    req(not (ROOT/"stop.request").exists(),"stop before resolution")
    if done.exists():
        req(g.load(done)==receipt,"resolution mismatch; preserve journal")
        print("SKIP verified resolved native import; no reimport",flush=True)
    else:
        g.atomic(done,receipt)
        print("RECOVER completed native import; no reimport",flush=True)
    return receipt
def tests():
    a,p,native=setup()
    changed=g.poses(R/"native_objects.txt")
    cases=[(None,"READBACK_REQUIRED"),(native,"VERIFY_BASE_BEFORE_IMPORT"),
        (changed,"VERIFY_SAVED_OR_SAVE_ONCE"),(changed+p,"BLOCK_AMBIGUOUS"),
        (changed[1:],"BLOCK_AMBIGUOUS"),(native+p+p,"BLOCK_AMBIGUOUS"),
        (native+[p[0][:-2]+(p[0][-2]*2,p[0][-1])],"BLOCK_AMBIGUOUS")]
    for rows,want in cases:req(route(a,p,rows)==want,"route "+want)
    print("PASS 7 content diagnosis cases; historical/synthetic, not fresh UI",flush=True)
    intent=g.load(R/"import_intent.json")
    for bad in (dict(intent,expected_count=4564),dict(intent,editor_pid=1),dict(intent,plan_sha256="wrong")):
        try:pinned_intent(bad)
        except ValueError:continue
        raise AssertionError("bad intent accepted")
    print("PASS 3 invalid intents refused",flush=True)
    old=sha(R/"change_checkpoint.json");assert old==EXPECTED
    command=[sys.executable,"-B",str(Path(__file__))]
    for case,fault in (("before-publication","before"),("after-publication","after")):
        d=TEST/case;d.mkdir()
        r=subprocess.run(command+["test-child",case,fault],timeout=30)
        req(r.returncode==73,"fault not reached")
        req((d/"change_checkpoint.json").exists()==(fault=="after"),"fault checkpoint state")
        req(not (d/"import_resolution.json").exists(),"premature resolution")
        r=subprocess.run(command+["test-child",case,""],timeout=30);req(r.returncode==0,"restart failed")
        oldr=sha(d/"import_resolution.json")
        r=subprocess.run(command+["test-child",case,""],timeout=30);req(r.returncode==0,"repeat failed")
        req(sha(d/"change_checkpoint.json")==EXPECTED and sha(d/"import_resolution.json")==oldr,"repeat changed receipt")
        print("PASS actual abrupt exit and restart",case,flush=True)
    d=TEST/"corrupt";d.mkdir();g.atomic(d/"change_checkpoint.json",{"status":"PASS"})
    old_bad=sha(d/"change_checkpoint.json")
    r=subprocess.run(command+["test-child","corrupt",""],timeout=30)
    req(r.returncode==2 and sha(d/"change_checkpoint.json")==old_bad and not(d/"import_resolution.json").exists(),"corrupt checkpoint changed")
    req(sha(R/"change_checkpoint.json")==old and sha(R/"import_intent.json")==PINS["import_intent.json"],"historical evidence changed")
    g.atomic(TEST/"tests.json",{"status":"PASS","content_cases":7,"bad_intents":3,"actual_recovery_worker_exits":2,"corrupt_checkpoint_refused":True,"original_checkpoint_unchanged":True,"native_gui_crash":"NOT_RUN"})
    print("PASS recovery suite; prior checkpoint unchanged",flush=True)
if __name__=="__main__":
    try:
        req(Path(__file__).resolve()==R/"recover_change.py","fixed scope")
        if sys.argv[1:]==["test"]:tests()
        elif len(sys.argv)==4 and sys.argv[1]=="test-child":
            req(sys.argv[2] in ("before-publication","after-publication","corrupt"),"fixed test case")
            from resume_gate import lock
            with lock():reconcile(TEST/sys.argv[2],sys.argv[3])
        elif sys.argv[1:]==["recover"]:
            from resume_gate import lock
            with lock():reconcile(R)
        else:raise ValueError("fixed mode")
    except (ValueError,OSError,g.b.Blocked,KeyError,TypeError,subprocess.TimeoutExpired) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
