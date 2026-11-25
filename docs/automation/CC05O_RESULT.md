# CC-05O — integrated synthetic GRM pipeline
Issue #42, Draft PR #47, base 077d76e4d5a7811c641a13906a001782554a99dc. Stage 001 PARTIAL. Isolated Linux SDK 10.0.404, pinned GRM/BIS, CC05B bridge and offline feed, DOTNET_PROCESSOR_COUNT=2. No real geography/elevations, no map output.

## Integration scope
One shared native BuildContext per run, one synthetic 480x480m map centered at 9N/33E, 16x16 30m final node grid with independent dummy origin, strict pinned owner v03/cache hashes and 163-path resolver. Actual source inventory checked: 21 tagged ways (101–121), seven tagged nodes (73–79), zero relations. Native road/rail/building/lake/watercourse/category/sand/cutline/ocean geometry. Shared explicit synthetic feature selection and native polygon subtraction for forest, scrub, radial and other landcover inputs; ForestEdgeBuilder native. Observed tree anchors now extracted from actual synthetic OSM node coordinates, with ID and explicit exclusion/review decision. Road 115 state is external scenario parameter; unknown conservative geometry same as operational, but distinct provenance and source tree review. Original OSM unchanged. No generalized OSM feature-to-placement lineage, no serialized overlay or complete priority graph.
13 selected native generator instances from catalog of 27, with 14 explicitly NOT RUN. Sidewalks returns empty under v03. Native road compiler/reader via four allowlisted in-memory streams, nine road profiles/one non-bridge shape record; normalized decoded geometry/profile digest unchanged across states and height shifts. CC05M SurfacePlan reused unchanged, 18 slots with explicit fixture-only absences, native polygon draw/coordinate helpers, preserved asphalt candidate. Both semantic controls and all 230400 pixel mappings per run checked. Full IdMapRender NOT RUN. No generic building output; footprint remains for ZPB pending. No actual water-plane export.
Final point checks across layers: extent, duplicate exact rounded CSV, selected vegetation polygon, protected vegetation geometry, building footprint and fence-road overlap. Half-open x=240 ownership after generation, no lost reviewed records; no independent sector generation or halo proof. Review manifest is an in-memory fingerprint of non-height placement keys, reasons, source inventory/state and ownership, not production manifest nor exact source ID for each model. Counts are records, not physically verified objects.

## Measurements
| Native generator | Abandoned | Operational / unknown |
|---|---:|---:|
| OrientedObjects | 2 | 2 |
| Bridge | 5 | 5 |
| Fence | 8 | 8 |
| Railway | 4 | 4 |
| Sidewalks | 0 | 0 |
| ForestEdge | 245 | 330 |
| Forest | 504 | 478 |
| ForestRadial | 176 | 171 |
| Scrub | 42 | 37 |
| ScrubRadial | 14 | 13 |
| Trees | 2 | 1 |
| TreeRows | 8 | 8 |
| Watercourse | 5 | 5 |
| Total | 1015 | 1062 |
| Held for point review | 21 | 14 |
| Point-pass records | 994 | 1048 |
| Point-pass left/right | 917/77 | 977/71 |
| Point-pass vegetation on road | 31 | 0 |

Abandoned review reasons: outside selected domain 20, fence-road point 1. Operational/unknown: outside selected domain 13, fence-road point 1, protected vegetation 2 (reasons can overlap). No exact duplicate CSV groups in this fixture across layers. Unknown road retains distinct source record and tree 73 review_unknown instead of protected_exclusion. Power pole/gate unsupported and postbox unconfigured marked in source review; building ZPB pending. No hidden relocation/deletion. Raw generated name heuristics (abandoned): fallen 8, stump 12, stem 5, bush directory 357; operational/unknown 8/8/3/436. These count filename candidates, NOT validated species, visual quality, terrain contact or physical deadwood category. No naturalness or collision proof. 

Two baseline runs per process and +100m synthetic grid: all non-height keys and review digest unchanged, each absolute world Z shifts +100m within 0.001m. All grid fingerprints, exact config/cache and XML hashes unchanged. Relative/absolute mixed transform comparison, no WRP file. Mask digest abandoned 9765495897e209dafc4d5719460a5a894d20ac315faa7f78f9bc8601d20bf7f3; protected 9fbcee62493fbecb9bf3abb7a5ebaf162aca77766f46d539a51f2e032ca9f167. Normalized road digest cd78d7a35d2e75e9fd6e1830451057f5ce193e8263d313c91708394f71617466. Unknown and operational share geometry, distinct manifest fingerprints. Missing RoadsData and unseeded ElevationData refused in separate negative context; RawElevationData/ElevationWithLakesData/ElevationOutOfBoundsData refused per actual run. Mutated cache copy rejected exit 2.

## Build and evidence
Offline restore exit 0 (all projects up-to-date); initial incremental build exit 0, 0 warnings/errors 3.89s and initial run exit 0. Initial source review lacked distinct unknown-state provenance and read hardcoded fixture anchors; corrected to native OSM coordinates and separate source decisions. Final incremental build exit 0, 0 warnings/errors 3.59s. Two separate final runs exit 0, byte-identical stdout SHA256 c95ec62abee1431ffd9627652d4c8f6e7996f21ec786982a6b868ea924b3d8fc. All 530 original archived GRM core/Arma3 files compared unchanged; no new BIS comparison claimed. Program.cs SHA256 7015f925191a6fddb24b3b5d29c9d5715fda4859ab670153e9185f39322d0cce; SurfacePlan.cs SHA256 acae3263b89c13fc85c9bf1e66fa0055b0ca00233898de63906098b009d0733f. Ten actual local Git blob hashes matched transfer. Owner ZIP Zone80_CC05O_PipelineProbe.zip 17138 bytes SHA256 13776386fd73ae18a8f34368ebf6363a4b6791ffca21a3dea292c9f919627893 CRC PASS. Source transfer saved in personal Library /Арма/STALKER-Zone80/02_Агент/Zone80_CC05O_source_transfer.md. [Companion and reproducible commands](../../tools/automation/cc05o/README.md).

## Remaining scope and next
PASS bounded integrated synthetic pipeline, NOT production compiler. 14 unrun layers: BuildingGenerator (ZPB), six default man-made area layers plus DefaultAreasGenerator, LakeSurfaceGenerator, OrchardGenerator, RocksGenerator, ScreeGenerator, VineyardsGenerator, WatercourseRadialGenerator. Next proposed CC-05P catalog disposition and fail-closed input/job contract: classify each remaining layer (enabled/tested, explicitly disabled with reason, or pending), complete shared fixture provenance, stable output/review identities, and input/manifest validation; connect bounded common pipeline to existing worker/sector manager only after clear contract. Avoid indefinite independent probes; work toward reproducible pilot readiness. Still no general feature/sector/halo scheduling, production mask, runtime assets, real OSM completeness, physical fit or local TB/Arma acceptance. GM-only complete real 0 NoData node-compatible grid and asset gates remain. No real map, P: writes, WRP/PBO, scheduler, merge or Stage promotion. UI deferred.
