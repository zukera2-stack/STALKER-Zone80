"""TB-CHANGE-01 fixed additive probe QC. No UI action or production promotion."""
from pathlib import Path
from decimal import Decimal as D
import hashlib, json, os, sys
R=Path(r"D:\Zone80\PipelineV01_02\TBChange01")
C=Path(r"D:\Zone80\TBGEN0002")
S=Path(r"D:\Zone80\TBGEN0001")
sys.path.insert(0,str(R.parent))
import pipeline_gate as g
import cc01_base as b
PLAN="f1372ed1cf6789e0faf73618f0693993bd4510ad50c9269a3f7f608545a6972a"
CURRENT="d678687abb531f76da445d55b5c12ebe512b97df432ce394d429e5d2076a797f"
NATIVE="f314485654d2ab888e2f029e290e6f097cd3708be6b8aa55bec5722038a1cc86"
def req(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    for q in (p,*p.parents):
        if q.exists():req(not q.stat(follow_symlinks=False).st_file_attributes & 0x400,"reparse")
    return hashlib.sha256(p.read_bytes()).hexdigest()
def compare(expected,actual):
    def keyed(rows):
        out={}
        for r in rows:
            k=r[:3]
            req(k not in out,"duplicate anchor")
            req(D(200000)<=r[1]<D(201920) and D(0)<=r[2]<D(1920),"outside map")
            out[k]=r
        return out
    a,z=keyed(expected),keyed(actual)
    req(a.keys()==z.keys(),"missing or extra anchors")
    yaw=D(0)
    for k,s in a.items():
        t=z[k]
        req(s[4:]==t[4:],"pitch/roll/scale/elevation changed")
        delta=abs((abs(s[3]-t[3])+D(180))%D(360)-D(180))
        req(delta<=D(".001"),"yaw mismatch")
        yaw=max(yaw,delta)
    return {"matched_unique":len(a),"max_yaw_delta_deg":str(yaw),"missing":0,"extra":0,"duplicates":0}
def setup():
    p=R/"change_plan.json"
    req(sha(p)==PLAN and sha(R.parent/"current.json")==CURRENT,"plan or parent pin")
    plan=g.load(p)
    req(plan["scope"]=="synthetic_additive_probe" and plan["base_objects"]==4562 and plan["expected_objects"]==4563,"plan scope")
    req(sha(S/"Native/source/TerrainBuilder/GRMAUTO04.tv4p")==plan["last_good_sha256"],"last good changed")
    src=C/"TBHandoff/relative_objects.txt";probe=C/"TBHandoff/autonomy_probe_01.txt"
    req(sha(src)==plan["base_sha256"] and sha(probe)==plan["input_sha256"],"input pin")
    a=g.poses(src);p=g.poses(probe)
    req(len(a)==4562 and len(p)==1,"input count")
    req(p[0]==("t_betula_pendula_2f",D(200240),D(240),D(17),D(0),D(0),D(1),D(0)),"probe mismatch")
    old=S/"QC01/native_objects.txt"
    req(sha(old)==NATIVE,"native reference changed")
    native=g.poses(old);compare(a,native)
    return a,p,native
def tests():
    a,p,native=setup()
    valid=native+p
    result=compare(a+p,valid)
    def refuse(label,rows):
        try:compare(a+p,rows)
        except ValueError as e:print("PASS refused",label,str(e));return
        raise AssertionError(label)
    print("PASS synthetic composition",result)
    refuse("unapplied",native)
    refuse("duplicate probe",valid+p)
    refuse("lost old object",valid[1:])
    refuse("altered scale",valid[:-1]+[p[0][:-2]+(D(2),D(0))])
    refuse("wrong yaw",valid[:-1]+[p[0][:3]+(D(18),)+p[0][4:]])
    refuse("outside",valid[:-1]+[(p[0][0],D(203000),*p[0][2:])])
    g.atomic(R/"change_qc_tests.json",{"status":"PASS","scope":"in_memory_synthetic_composition_not_native_import","tests":7,"result":result,"plan_sha256":PLAN,"parent_sha256":CURRENT})
def verify():
    a,p,native=setup()
    out=R/"native_objects.txt"
    req(out.is_file(),"new full native export required")
    before=sha(out);actual=g.poses(out)
    result=compare(a+p,actual)
    req(sha(out)==before,"export changed during verification")
    # Comparison alone is not evidence that an export is fresh or that save/reopen occurred.
    report={"status":"PASS","scope":"changed_object_export_content_only","plan_sha256":PLAN,"parent_sha256":CURRENT,"export_sha256":before,**result}
    receipt=R/"changed_export_qc.json"
    if receipt.exists():req(g.load(receipt)==report,"prior receipt differs")
    else:g.atomic(receipt,report)
    print(json.dumps(report))
if __name__=="__main__":
    try:
        req(Path(__file__).resolve()==R/"verify_change.py" and len(sys.argv)==2 and sys.argv[1] in ("test","verify"),"fixed scope")
        (tests if sys.argv[1]=="test" else verify)()
    except (ValueError,OSError,b.Blocked,KeyError,TypeError) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
