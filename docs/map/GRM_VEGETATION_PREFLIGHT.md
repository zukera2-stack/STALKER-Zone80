# GRM vegetation reference inventory / MAP-003
24.11.2026, PR #47, base ebfb83252da6d6a601d6d681d61c15d7b3940278, upstream jetelain/ArmaRealMap @ 2aef2040836daa11a8a368bb0c7f9ecd8f405d65. Source review only. Read exact CentralEurope.grma3a; upstream Builtin/LICENSE states APL. No copied composition/transform/probability definitions or binaries. Extracted path references + group memberships only in configs/grm/vegetation.references.json. 76 distinct paths case-insensitive, all a3 prefix; NOT proof of installed assets/rights or runtime dependency closure. Includes trees, shrubs, rocks, deadwood, crop and agricultural objects, not 76 tree models. Counts by group overlap.
- BasicCollections.ForestAdditional: 21
- BasicCollections.Rocks: 2
- BasicCollections.RocksAdditional: 7
- BasicCollections.ScrubAdditional: 6
- BasicCollections.SmallOrchard: 2
- BasicCollections.WatercourseAdditional: 5
- ClusterCollections.Forest: 26
- ClusterCollections.ForestEdge: 7
- ClusterCollections.ForestRadial: 7
- ClusterCollections.Scrub: 8
- ClusterCollections.ScrubRadial: 6
- NaturalRows.FarmLandRow: 1
- NaturalRows.OrchardRow: 2
- NaturalRows.TreeRow: 1
- NaturalRows.VineyardRow: 2
- Objects.Tree: 5
## Local verification and own config
Luna: use existing read-only model inventory and actual installed resources, record exact P3D paths, modelinfo bounds/anchor, CfgPatches and transitive dependencies, rights and DLC restrictions. Reject missing/unapproved. No extraction of binaries without owner approval. No invented transforms. Prioritize Enoch birch/pine/spruce and region-appropriate shrubs/deadwood; exact species mix/density not measured. Ficus, vines, crops, orchard trees require region/landuse review. Need raw landcover snapshot; no fabricated forest polygons. Geometry facts separate from procedural vegetation and gameplay aging. Do not copy CentralEurope config as release; remove external world/material/pond dependency through reviewed replacements, not just Dependencies. Native .grma3a not emitted yet; reference inventory is not a GRM config. ModelInfoReferenceConverter rejects unresolved paths in normal parser (allowUnresolvedModel is not acceptance).
## Proven elevation dependency
Source links under https://github.com/jetelain/ArmaRealMap/tree/2aef2040836daa11a8a368bb0c7f9ecd8f405d65
- GameRealisticMap.Arma3/Nature/GeneratorBase.cs Generate calls GetDataAsync<ConditionEvaluator>(); ClusteredGeneratorBase derives from it. ForestGenerator adds ForestAdditional.
- GameRealisticMap.Arma3/Nature/Trees/TreesGenerator.cs explicitly context.GetData<ConditionEvaluator>() before candidate lookup.
- GameRealisticMap/Conditions/ConditionEvaluator.cs constructor unconditionally calls GetData<ElevationData>(); additionally CategoryAreaData, CitiesData, OceanData, RoadsData.
- GameRealisticMap/Nature/BasicBuilderBase.cs GetPriority uses ElevationWithLakesData, BuildingsData, RoadsData, RailwaysData. ForestBuilder adds CutlinesData. Thus removing conditional slope constraints or emptying tree list does not establish height-free forest or tree generation.
- Need audit exact ElevationData/RawElevationData registration and consumers and design GM-input adapter. A separately reviewed adapter must preserve actual GM input grid, north/south row ordering, sampling origin and NoData, units/datum and out-of-bounds; no GRM-created elevation, no smoothing or lake/road reshaping of authoritative heights without owner decision. If algorithm needs expanded coverage or alternate grid convention, STOP and request GM export; do not fabricate halo. Test dependency graph with forbidden elevation network builder throwing, synthetic controls and real GM output only after gate. No production adapter implemented.
## Tests performed
JS extraction against actual pinned source, 76 count, path prefix, deterministic repeat equality; validation of reference manifest and five negative mutations (case duplicate, third-party prefix, per-asset approval, traversal, global approval): 5/5 rejected. These are in-memory static checks, not native tests or committed test suite. No local model verification, parser, native layer, GM/TB, WRP/PBO, scheduler or P: writes. Stage 001 PARTIAL, full GM 0 NoData and existing TB gate unchanged. Real GRM vegetation BLOCKED by dependency/inputs. Continue current Issue #42 only.
