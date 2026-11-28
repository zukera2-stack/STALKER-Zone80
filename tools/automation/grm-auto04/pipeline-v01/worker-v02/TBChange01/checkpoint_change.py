"""Fixed native TB-CHANGE-01 checkpoint. No GUI mutation, never reimports."""
from pathlib import Path
import json, sys
import verify_change as v
from verify_change import R,C,S,g,req,sha
ROOT=R.parent
ORIGINAL=Path(r"D:\Zone80\GRMAUTO04")
PROJECT="Native/source/TerrainBuilder/GRMAUTO04.tv4p"
LAYER="Native/source/TerrainBuilder/GRMAUTO04.Layers/TXT_autonomy_probe_01_001.tv4l"
REOPEN=R/"f74d6ce9eb1d42929fdf13325a24f83e/CHILD.log"
EXPORT=R/"54fd35654d1641a6b479f82a0b6f0a18/CHILD.log"
def nodes(p):
    return [json.loads(s) for s in p.read_text(encoding="utf-8-sig").splitlines() if s.startswith("{")]
def filetree(root):
    out={}
    for d in ("Native","TBHandoff"):
        for p in (root/d).rglob("*"):
            if p.is_file():out[p.relative_to(root).as_posix()]=sha(p)
    return out
def main():
    req(Path(__file__).resolve()==R/"checkpoint_change.py","fixed scope")
    req(not (ROOT/"stop.request").exists(),"stop requested")
    v.verify()
    plan=g.load(R/"change_plan.json")
    save=g.load(R/"save_receipt.json")
    qc=g.load(R/"changed_export_qc.json")
    intent=g.load(R/"import_intent.json")
    req(intent["plan_sha256"]==v.PLAN and intent["pre_count"]==4562 and intent["expected_count"]==4563,"intent identity")
    req(save["plan_sha256"]==v.PLAN and save["object_count"]==4563 and qc["matched_unique"]==4563,"saved/QC identity")
    req(sha(C/PROJECT)==save["project_sha256"].lower()=="de6cdf0d62c9d492dad47491f859cd0bd579d7838f7292fe3e74695cdb58e828","saved project pin")
    req(sha(C/LAYER)==save["layer_sha256"].lower()=="f7445ed9e6d848a9a11f7948738cba85d9ce99b51600b927ee9dc2baba4f08b7","saved layer pin")
    reopen=nodes(REOPEN);export=nodes(EXPORT)
    req(any(n["name"]=="Total object count: 4563" and n["enabled"] for n in reopen),"native reopen count")
    req(any(n["name"]=="Save project" and not n["enabled"] for n in reopen),"native reopen not clean")
    for n in ("terrain.asc","imagery.bmp","mask.bmp"):
        req(any(x["name"]==str(C/"TBHandoff"/n) and x["type"]=="ControlType.Text" for x in reopen),"native reopen root")
    req(any(n["type"]=="ControlType.Text" and n["name"]=='Export objects to txt file - File "'+str(R/"native_objects.txt")+'" succesfully created.' for n in export),"native export success absent")
    old=g.load(S/"relocation_receipt.json")
    new=g.load(C/"relocation_receipt.json")
    req(all(sha(S/n)==x["after"] for n,x in old["files"].items()),"previous candidate modified")
    req(all(sha(ORIGINAL/n)==x for n,x in old["source_before"].items()),"original modified")
    tree=filetree(C)
    changes=[n for n,x in new["files"].items() if tree.get(n)!=x["after"]]
    added=sorted(set(tree)-set(new["files"]))
    req(all(n.startswith("Native/source/TerrainBuilder/") for n in changes),"unexpected original input change")
    req(all(n.startswith("Native/source/TerrainBuilder/") or n=="TBHandoff/autonomy_probe_01.txt" for n in added),"unexpected new file")
    req(all(n in tree for n in new["files"]),"candidate original file missing")
    old_layer="Native/source/TerrainBuilder/GRMAUTO04.Layers/TXT_relative_objects_001.tv4l"
    before=(S/old_layer).read_bytes();after=(C/old_layer).read_bytes()
    req(sha(S/old_layer)=="41609f9ab68adbc478dfcd5eca9df682c3723e7eb62584e034f52cf1b14fbf01" and sha(C/old_layer)=="71bee7b7ade641ccf37c329e68f7f0358f4daf594e807c7dae9830f003d37dfa","measured old layer revision pin")
    req(len(before)==len(after)==3862465 and sum(x!=y for x,y in zip(before,after))==85054,"measured layer diff")
    # Old placement semantics independently verified by full native export; not binary identity.
    req(set(changes)=={PROJECT,old_layer,"Native/source/TerrainBuilder/GRMAUTO04.Layers/default.tv4l","Native/source/TerrainBuilder/GRMAUTO04.Shapes/default area.tv4s","Native/source/TerrainBuilder/GRMAUTO04.Shapes/roads.tv4s","Native/source/TerrainBuilder/TemplateLibs/arma3.tml"},"unexpected native save changes")
    result={"status":"PASS","scope":"synthetic_changed_object_saved_reopened_exported",
        "identity":g.b.digest(g.b.canonical({"plan":v.PLAN,"parent":v.CURRENT})),
        "plan_sha256":v.PLAN,"parent_sha256":v.CURRENT,
        "project_files":tree,"native_export_sha256":qc["export_sha256"],
        "native_reopen_log_sha256":sha(REOPEN),"native_export_log_sha256":sha(EXPORT),
        "original_count":4562,"new_count":4563,"old_layer_bytes_unchanged":False,"old_layer_diff_bytes":85054,"old_placement_semantics_verified":True,"native_shape_geometry":"NOT_RUN","native_template_metadata":"NOT_RUN",
        "original_files_verified":len(old["source_before"]),"previous_copy_files_verified":len(old["files"]),
        "changed_files":changes,"added_files":added,"buldozer":"NOT_RUN","whole_pipeline":"PARTIAL"}
    out=R/"change_checkpoint.json"
    if out.exists():
        req(g.load(out)==result,"checkpoint/artifact mismatch; no reimport")
        print("SKIP verified TB change; no reimport")
    else:
        g.atomic(out,result)
        print("PASS TB changed layer checkpoint; no reimport")
    print(json.dumps({k:x for k,x in result.items() if k!="project_files"},indent=2))
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,g.b.Blocked,KeyError,TypeError) as e:
        print("BLOCKED:",e,file=sys.stderr);raise SystemExit(2)
