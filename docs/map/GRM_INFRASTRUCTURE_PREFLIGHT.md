# GRM infrastructure references and generation gates
2026-11-25. MAP-003 #42, Draft PR #47, base a099afd8bc2e6e09ac8b6a5a5c5829c62f3b943e. Upstream jetelain/ArmaRealMap @ 2aef2040836daa11a8a368bb0c7f9ecd8f405d65; inspected CentralEurope.grma3a, Builtin license from prior reference audit, generators and builders listed below. APL reference metadata only, no binaries or copied composition/transform/probability payload. No new GIS snapshot, no local native execution.
## Reference inventory
{
  "infra": 65,
  "stock": 60,
  "external": 5,
  "bySection": {
    "Bridges": 9,
    "Railways": 9,
    "Fences": 6,
    "Sidewalks": 1,
    "Objects": 35,
    "Ponds": 5
  },
  "combinedUnique": 204,
  "combinedStock": 181,
  "combinedExternal": 23,
  "combinedNote": "Main reference arrays only; excludes additional unselected candidates and model dependencies; not installed resource count"
}
Sections are disjoint within this inventory; Objects.Tree duplicates vegetation references, so do not add previous category totals without dedup. All path references remain unverified, no rights/entitlement inferred from a3 prefix. Reference segment lengths in configs/grm/infrastructure.references.json (not field surveys).
{
  "bridges": {
    "TwoLanesMotorway": {
      "Single": 40,
      "Start": 19.8,
      "Middle": 40.3,
      "End": 20
    },
    "TwoLanesPrimaryRoad": {
      "Single": 40,
      "Start": 19.8,
      "Middle": 40.3,
      "End": 20
    },
    "TwoLanesSecondaryRoad": {
      "Single": 42,
      "Start": 28,
      "Middle": 24,
      "End": 28
    },
    "TwoLanesConcreteRoad": {
      "Single": 42,
      "Start": 28,
      "Middle": 24,
      "End": 28
    }
  },
  "rail_straight_m": [
    2,
    4,
    8,
    25,
    40
  ],
  "rail_crossing_reference_m": [
    {
      "length": 75,
      "road_max_width": 14
    },
    {
      "length": 60,
      "road_max_width": 9
    }
  ],
  "fence_straight_m": {
    "Wall": [
      5
    ],
    "Fence": [
      4,
      8
    ],
    "Hedge": [
      2,
      4
    ]
  },
  "sidewalk_straight_m": [
    4
  ],
  "pond_nominal_size_m": [
    5,
    10,
    20,
    40,
    80
  ]
}
## Source-grounded gates
Sources under https://github.com/jetelain/ArmaRealMap/tree/2aef2040836daa11a8a368bb0c7f9ecd8f405d65
- GameRealisticMap.Arma3/ManMade/BridgeGenerator.cs: requests ElevationData and RoadsData even before testing available definitions. Selects single/multipart from road bridge flags, length and endpoint elevations; single samples ends of actual model possibly outside source road segment. Do not generate without complete valid GM heights, grade metadata, support/clearance checks, approach continuity and measured fit. Missing bridge definition skips placement; report omission, never pretend completed bridge. Curves and multipart fit require local QA. No changes to DEM.
- RailwayGenerator.cs: returns empty when assets.Railways null or no Straights. Otherwise follows railways and chooses nearest-length crossing composition. GameRealisticMap/ManMade/Railways/RailwaysBuilder.cs reads railway=rail/disused and railway=level_crossing nodes, uses RoadsData and splits segments. A geometric crossing alone is not a level crossing. Preserve source tags including bridge/tunnel/layer, reject unsupported special sections, validate joins, track spacing, slope, crossing width, gaps/overlap; do not claim complete railway fidelity or no elevation dependency based solely on direct calls. RailwaysData transitive dependency audit still required. Railways are static scenery, no railway simulation promised.
- FenceGenerator.cs and OrientedObjectsGenerator.cs request ConditionEvaluator (previous audit: unconditionally requires ElevationData). Explicitly mapped fences and objects separate from procedural decoration. Do not approximate gates, corners or named landmarks as confirmed. OrientedObjectsGenerator separately generates lamps from ProceduralStreetLampsData if lamp candidates exist; disable road procedural lamp rules initially.
- SidewalksGenerator.cs requires ConditionEvaluator if Sidewalks nonempty. SidewalksBuilder.cs generates paths alongside eligible normal roads in residential polygons, uses roads/fences/railways masks; this is NOT the 32 explicit OSM sidewalk records. Keep explicit sidewalks distinct from optional procedural sidewalks; no double placement. Disable automatic generation in pilot profile. Need curb alignment and model dimension/offset tests.
- LakeSurfaceGenerator.cs requests ElevationWithLakesData BEFORE checking GetMinimalPondSize; removing Ponds alone does not avoid elevation dependency. Five external arm_pond_blue size 5/10/20/40/80 models, not stock. Propose dedicated own water surface tiles or later reviewed stock alternative (none verified); no claim water collision/render behavior from geometry alone. Water levels absolute, no lake reshaping or fake heights. Exclude native layer until adapter and water-specific QA. Grid edge test needed: Process uses x+objSize<=w10 and y+objSize<h10; possible last-row omission, not reproduced.
- Composition.cs and CompositionObject.cs: uses matrix M41/M43 for horizontal coordinates, M42 elevation; relative/absolute branches and transforms multiplication. GRM internal Y-up vs canonical exchange Z-up: adapter must convert and test; do not assume identity or copy transforms. No model paths invented for own props. Unique monuments, authentic Soviet fences/lamps/stops and similar custom models belong to ZPB contract (separate project approval). Generic objects are optional proxies not historical evidence.
## Local preflight and compiler handoff
Luna verify actual P3D, bounds/pivot, CfgPatches, transitive material/texture paths and rights; read-only. For bridges/rails/fences/sidewalks measure effective segment lengths, alignment, contact, rotation, start/end junctions. Ponds all blocked. Keep all native layer jobs disabled until GM adapter/source gate. Prepare own compiler to assemble verified modules using pinned GRM parser and approved source definitions; reject external z/arm paths in final config, but keep them in reference inventory for audit; reject duplicate refs, implicit defaults, missing required enums/usage, mismatched model paths and disabled-feature leakage. Separate reference catalogs from selected assets. No generic building generation or placement; no full-world generation. #42 remains one local task.
## Actual checks
In-memory JS extraction twice identical, 65 unique case-insensitive paths, five external pond refs, segment control lengths. 10/10 negative mutations rejected: case duplicate, traversal, per-entry/global approval, false stock classification, invalid group, false verification, invalid rail size, unsafe sidewalk policy, missing entry. Read-back JSON validation; no persistent test suite or native parser execution. No GM export, P: writes, GIS acquisition, TB, WRP/PBO, scheduler or merge. Stage 001 PARTIAL; 629 diagnostic NoData unchanged.
