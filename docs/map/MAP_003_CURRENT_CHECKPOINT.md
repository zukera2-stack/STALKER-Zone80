# MAP-003 / GRM — актуальная контрольная точка 2026-11-25

Scope: consolidated documentation, not a new execution report. Evidence cutoff bbbd43916c712830de26f9779a3ab010788b70fb, Draft PR #47, active Issue #42. Stage 001 PARTIAL. Earlier documents remain historical; this index resolves their outdated NOT RUN statements only within the measured scope. No stage promotion, no new native execution.

## Decisions and architecture
- One world 81920 m, 4096² × 20 m, 64 logical 10240 m sectors; production extent/CRS/epoch not approved. Current pilot only 1920 m, 64² × 30 m, EPSG:32636.
- Global Mapper 26.2 Pro alone acquires/exports real elevations. GRM supplies future geographic layers/procedural scenery, not independent elevation. TB only one safe terrain-only import after NoData=0. [GRM design](MAP_003_GRM_AUTOMATION.md).
- Minimal dependencies: stock Arma 3 + free platform Enoch + own packages, no mandatory CUP/CBA/other STALKER/DLC purchase. No clean runtime proof. [Policy](../integration/MINIMAL_DEPENDENCIES.md).
- ZPB independently owns models and manifest; map owns source geometry, matching and placement. Shared [contract](../integration/ZONE80_ZPB_CONTRACT.md), reserved IDs not ready assets. No placement.
- Local finite queue worker design and synthetic-first tests; no installed worker/scheduler evidence. [Handoff](../automation/LUNA_HANDOFF.md), [contract](../automation/WORKER_CONTRACT.md).

## Existing geography (do not repeat without new inputs)
| Stream | Current evidence and limits |
|---|---|
| A GM | Diagnostic exact grid: 3467 valid / 629 NoData; full N51E030 and online source not confirmed. BLOCKED for final export. [Integrated report](MAP_003_INTEGRATED_RESULT.md) |
| B roads | 446 IDs, 453 parts, 69862.807 m summed source lines. PASS for existing bbox only. 45 truncated DBF tag fields, 784 geometric contact candidates not verified junctions, 45 pedestrian area boundaries not road axes. [Road audit](MAP_003_ROAD_AUDIT.md) |
| C buildings | 449 records = 438 ways + 11 multipolygons; not confirmed independent physical buildings; 28 candidate groups/96 records, unresolved relation roles and historical identities. [Geocatalog](PRIPYAT_DIGITAL_GEOCATALOG.md), [typology](PRIPYAT_ARCHITECTURAL_TYPOLOGY.md) |
| Coverage | 444/449 building records and 427/446 road IDs fully within valid diagnostic cells. [Coverage audit](MAP_003_COVERAGE_AUDIT.md) |
| Surfaces | 45 valid closed pedestrian area polygons, 32994.114 m²; 32 overlap building contours; 0/45 material specified. 92.3782% outside union of footprints and pedestrian areas; no full landcover. [Surface audit](MAP_003_SURFACE_AUDIT.md) |
| D TB | BLOCKED, import NOT RUN; no WRP/PBO or playable world. |

## GRM configuration development
Pinned upstream jetelain/ArmaRealMap v0.11.1 / 2aef2040836daa11a8a368bb0c7f9ecd8f405d65; local installed version not established by config save. Source audit: 76 nature P3D refs, 9 road profiles, 11 material definitions/16 usages, 65 infrastructure models. Combined reference arrays 204 distinct paths (181 a3 / 23 external), exclude Buildings and additional candidates. [Vegetation](GRM_VEGETATION_PREFLIGHT.md), [roads/materials](GRM_ROADS_MATERIALS_PREFLIGHT.md), [infrastructure](GRM_INFRASTRUCTURE_PREFLIGHT.md). Source review and in-memory negative checks only.
Owner's actual CentralEurope export Zone80_base.grma3a: 344 refs incl Buildings, 321 a3 present as loose files, 23 external absent as loose files (not proof PBO absence). 55 color candidates, 54 paired normals, zero scan errors. [Inventory](GRM_LOCAL_INVENTORY_RESULT.md). Counts differ from source reference arrays by scope, not regression.
Editor copy removed generic building definitions, pond models, automatic sidewalks/lamps; seven ground texture candidates substituted without changing 11 color IDs or 16 usages. Owner opened/saved Zone80_v02.grma3a in Studio. Six of seven substitutions restored stock Surface/FakeSatPngImage: GdtKLGrass2, GdtKLGrass1, GdtKLDirt, GdtCliff, GdtBeach, GdtKLForestDec. Mud unresolved. [Roundtrip](GRM_STUDIO_ROUNDTRIP.md).
v03 bounded Python editor-only transformer changes mud to a3/map_data/gdt_mud pair. 203 distinct refs: 179 covered by prior inventory or texture-pair candidates, 22 new stock Surface/clutter refs unverified, 2 external ice refs. Retains CentralEurope base dependency/world; no native parser test of v03. Two unittest methods PASS incl 12 negative subcases in cloud, not native Windows. [v03 report with hashes](GRM_CONFIG_PREFLIGHT_V03.md). Owner ZIP Zone80_Config_Preflight_v03.zip delivered in chat; scripts/config not committed or guaranteed available to Luna; retrieve owner copy and verify hashes rather than assume local path. Not production compiler.
## Next work, ordered by dependency (same Issue #42)
1. Reuse owner artifacts and re-inventory v03 for 22 new refs. Verify local CfgSurfaces/CfgSurfaceCharacters, mud class, full CfgPatches/dependency closure, base-world inheritance and actual resource entitlement. Editor open/save only if needed, no repetitive manual clicks. Do not change base world or ice by guessing. Ice requires full raw source/tag check and explicit unused policy or real replacement; unknown geography remains unknown.
2. Implement reproducible compiler and synthetic tests in project-owned sandbox; reuse verified v03 algorithm if owner artifact accessible. No executable production config until all gates. Do not treat empty Dependencies as proof. Maintain manifest lock and ZPB model eligibility rules.
3. Audit GRM transitive elevation dependencies; forest/trees require ConditionEvaluator/ElevationData; bridge/fence/objects/sidewalks/ponds have elevation dependencies, rail transitive chain unverified. Design reviewed GM-input adapter; no RawElevationBuilder or generated substitute heights, no unauthorized smoothing/halo.
4. Independently complete authorized GM full N51E030 and exact grid NoData=0; only then one isolated terrain-only TB import. Existing GIS audits need no repeat unless source changes.
5. Worker synthetic process tests, restart/stop/checkpoint and resource limits under existing contract. Native layer and scheduler remain gated. No full-world generation, gentb/genwrp/genmod, placement, P: writes, power changes, or automatic merge. Report actual results in existing Issue #42.

## План автономного инструментария — 25.11.2026
[Control Center roadmap](../automation/CONTROL_CENTER_ROADMAP.md) закрепляет семь подэтапов CC-01…07 без смены текущего Stage 001. Следующий предлагаемый программный шаг — CC-01 synthetic Worker core; локальный read-only preflight и GM full coverage остаются независимыми. Статусы ранее проверенных артефактов неизменны; новых тестов нет.
