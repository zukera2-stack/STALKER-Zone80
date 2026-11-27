"""Build a LOCAL, editor-only Zone80 v04 review candidate. Never generate terrain."""
import argparse
import copy
import hashlib
import json
import re
import stat
from pathlib import Path, PureWindowsPath

V02 = "84e0cdee7501b7e9f01cc92b6635c70e8d6503f591e0b1a0ffffef2a2d6bf41a"
V03 = "418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e"
OLD_BASE = ("arm_world_centraleurope", "arm_centraleurope")
NEW_BASE = ("CAWorld", "A3_Map_Data")
OLD_MUD = (r"a3\map_enoch\data\gdt_enmud_co.paa", r"a3\map_enoch\data\gdt_enmud_nopx.paa")
NEW_MUD = (r"a3\map_data\gdt_mud_co.paa", r"a3\map_data\gdt_mud_nopx.paa")
ICE = (r"z\arm\addons\common_v2\data\gdt\arm_ice_co.paa", r"z\arm\addons\common_v2\data\gdt\arm_ice_nopx.paa")
IDS = {"6B8E23FF", "569600FF", "A52A2AFF", "C3E6FFFF", "808080FF", "F4A460FF",
       "0026FFFF", "664A00FF", "805C00FF", "ADD8E6FF", "000000FF"}
USAGES = {"Default", "Meadow", "DefaultUrban", "Grass", "DefaultIndustrial", "IceSurface",
          "ScreeSurface", "RockGround", "Coastline", "Sand", "OceanGround", "ForestGround",
          "FarmLand", "RiverGround", "LakeGround", "Asphalt"}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, "DUPLICATE_JSON_KEY")
            result[k] = v
        return result
    def bad_constant(value):
        raise ValueError("NONFINITE_JSON")
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=bad_constant)

def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")

def references(value):
    out = set()
    def visit(x):
        if isinstance(x, str) and re.search(r"\.(p3d|paa|rvmat)$", x, re.I):
            p = PureWindowsPath(x)
            require(not p.is_absolute() and not p.drive and not p.root
                    and not any(part in ("..", ".") or ":" in part for part in p.parts),
                    "UNSAFE_RESOURCE_PATH")
            out.add(str(p).lower())
        elif isinstance(x, dict):
            for v in x.values():
                visit(v)
        elif isinstance(x, list):
            for v in x:
                visit(v)
    visit(value)
    return out

def pair(row):
    m = row["Material"]
    return m["ColorTexture"], m["NormalTexture"]

def select(defs, usages):
    found = [row for row in defs if set(row["Usages"]) == set(usages)]
    require(len(found) == 1, "MATERIAL_SELECTION")
    return found[0]

def transform(original):
    out = copy.deepcopy(original)
    require((out["BaseWorldName"], out["BaseDependency"]) == OLD_BASE, "BASE")
    defs = out["Materials"]["Definitions"]
    usages = [u for row in defs for u in row["Usages"]]
    require(len(defs) == 11 and len(usages) == 16 and set(usages) == USAGES, "USAGES")
    require({row["Material"]["Id"] for row in defs} == IDS, "MASK_IDS")
    require(len(out["Roads"]) == 9, "ROADS")
    require(out["Buildings"] == {} and out["Sidewalks"] == [] and out["Dependencies"] == []
            and out["Ponds"] == {f"Size{x}": None for x in (5,10,20,40,80)}, "DISABLED_FEATURES")
    mud = select(defs, ("RiverGround", "LakeGround"))
    require(mud["Material"]["Id"] == "ADD8E6FF" and mud.get("Surface") is None
            and pair(mud) in (OLD_MUD, NEW_MUD), "MUD")
    ice = select(defs, ("IceSurface",))
    require(pair(ice) == ICE and ice["Material"]["Id"] == "C3E6FFFF", "ICE")
    before = references(original)
    require(len(before) == 203 and {p for p in before if not p.startswith("a3\\")} == set(ICE),
            "EXTERNAL_REFERENCE_SET")
    mud["Material"]["ColorTexture"], mud["Material"]["NormalTexture"] = NEW_MUD
    out["BaseWorldName"], out["BaseDependency"] = NEW_BASE
    after = references(out)
    require(len(after) == 203 and {p for p in after if not p.startswith("a3\\")} == set(ICE),
            "OUTPUT_REFERENCE_SET")
    reversed_out = copy.deepcopy(out)
    reversed_out["BaseWorldName"], reversed_out["BaseDependency"] = OLD_BASE
    m = select(reversed_out["Materials"]["Definitions"], ("RiverGround", "LakeGround"))["Material"]
    m["ColorTexture"], m["NormalTexture"] = pair(select(original["Materials"]["Definitions"], ("RiverGround","LakeGround")))
    require(reversed_out == original, "UNEXPECTED_MUTATION")
    return out

def self_test(original):
    require(encode(transform(original)) == encode(transform(original)), "NONDETERMINISTIC")
    cases = []
    def test(name, mutate):
        bad = copy.deepcopy(original)
        mutate(bad)
        try:
            transform(bad)
        except (ValueError, KeyError, TypeError):
            cases.append(name)
        else:
            raise ValueError("NEGATIVE_TEST_NOT_REJECTED:" + name)
    test("base", lambda x: x.update(BaseWorldName="Enoch"))
    test("mask", lambda x: select(x["Materials"]["Definitions"], ("RiverGround","LakeGround"))["Material"].update(Id="FFFFFFFF"))
    test("mud", lambda x: select(x["Materials"]["Definitions"], ("RiverGround","LakeGround"))["Material"].update(ColorTexture="a3\\invented.paa"))
    test("ice", lambda x: select(x["Materials"]["Definitions"], ("IceSurface",))["Material"].update(ColorTexture="a3\\map_data\\gdt_white_co.paa"))
    test("buildings", lambda x: x["Buildings"].update(bad=[]))
    test("pond", lambda x: x["Ponds"].update(Size5="fake"))
    test("duplicate usage", lambda x: x["Materials"]["Definitions"][0]["Usages"].__setitem__(0, "Grass"))
    test("duplicate id", lambda x: x["Materials"]["Definitions"][0]["Material"].update(Id=x["Materials"]["Definitions"][1]["Material"]["Id"]))
    test("unsafe path", lambda x: x.update(Unsafe=r"a3\..\bad.p3d"))
    test("external path", lambda x: x.update(Extra=r"z\other\bad.p3d"))
    return cases

def check_chain(path):
    for p in [path, *path.parents]:
        st = p.lstat()
        require(not p.is_symlink() and not (getattr(st, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)), "REPARSE_POINT")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    a = parser.parse_args()
    require(re.fullmatch(r"v04-[0-9a-f]{32}", a.run_id), "RUN_ID")
    require(a.source.is_absolute() and a.reports_root.is_absolute() and a.asset_root.is_absolute(), "ABSOLUTE_PATHS")
    check_chain(a.source)
    check_chain(a.reports_root)
    require(a.reports_root.is_dir() and a.reports_root.name == "MAP-003"
            and a.reports_root.parent.name == "reports", "REPORT_ROOT")
    require(a.reports_root.drive.lower() != a.asset_root.drive.lower(), "ASSET_DRIVE_WRITE")
    raw = a.source.read_bytes()
    source_hash = digest(raw)
    require(source_hash in (V02, V03), "SOURCE_SHA256")
    original = read_json(raw)
    candidate = transform(original)
    tests = self_test(original)
    paths = references(candidate)
    stock = sorted(p for p in paths if p.startswith("a3\\"))
    missing = [p for p in stock if not a.asset_root.joinpath(*PureWindowsPath(p).parts).is_file()]
    require(len(stock) == 201 and not missing, "MISSING_A3:" + ",".join(missing))
    dest = a.reports_root / a.run_id
    dest.mkdir(exist_ok=False)
    data = encode(candidate)
    output = dest / "Zone80_v04_EDITOR_ONLY.grma3a"
    with output.open("xb") as f:
        f.write(data)
    require(read_json(output.read_bytes()) == candidate, "OUTPUT_READBACK")
    require(digest(a.source.read_bytes()) == source_hash, "SOURCE_CHANGED")
    report = {
        "status": "EDITOR_ONLY_BLOCKED_FOR_GENERATION", "approved_for_generation": False,
        "source_sha256": source_hash, "source_unchanged": True, "output_sha256": digest(output.read_bytes()),
        "output_bytes": len(data), "stock_present": len(stock), "stock_missing": 0,
        "external_paths": sorted(paths - set(stock)), "material_definitions": 11, "material_usages": 16,
        "road_types": 9, "tests": {"determinism": "PASS", "reverse_semantics": "PASS",
        "readback": "PASS", "negative_pass": tests}, "gates": {
            "ice": "BLOCKED_EXTERNAL_ICE_PAIR", "stock_surface_collisions": "BLOCKED",
            "requiredAddons": "NOT_CLOSED", "DLC": "NOT_RUN", "native_parser": "NOT_RUN",
            "native_generation": "FORBIDDEN"
        }
    }
    with (dest / "review.json").open("xb") as f:
        f.write(encode(report))
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
