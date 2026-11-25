---
name: zone80-sector-pipeline
description: Plan deterministic sector jobs, coordinate conversion, seams and output validation for one Zone80 world.
---
# Sector pipeline
Read docs/map/MAP_003_GRM_AUTOMATION.md, docs/automation/WORKER_CONTRACT.md, docs/map/MAP_003_GM26_TILES.md, Issue #42 and historical Issue #13. 
- Current real scope: central Pripyat 1920m square, 64x64x30m, EPSG:32636 only pilot. Full-world center/CRS/epoch not approved.
- Future target: 81920m, 4096x20m, 8x8 sectors each 10240m. Do not generate all sectors. Begin with synthetic two-neighbor fixture; real two-sector expansion requires gate. One eventual world not 64 WRP.
- Use canonical projected coordinates, world-local offsets, half-open core ownership (outer boundary explicit), halo for cross-boundary geometry and algorithm radius; canonical IDs and deterministic seeds, no simple coordinate rounding dedup. Road segments clipped with stable IDs; crossing features and placements ownership explicit. Validate north/east axes, grid centers/corners, seams, rotation, scale, relative/absolute height; TB XShift=200000 applied once only where format contract proves it. Never apply to raw UTM twice.
- Pin source snapshot, generator/config hashes, assets and transformation version. If GRM independent sector output not deterministic or seam-safe, BLOCKED; use common-source generation or propose limited adaptation after approval.
- Keep facts, procedural proxies, gameplay layers separate; no building placement. Separate line/polygon/point and material Unknown. GM-only height authority; no NoData filling or seam interpolation.
- Native TB import only per current #42 gate, one terrain-only sandbox after full GM coverage. No WRP/PBO/Stage 002. Produce reports with hashes, boundary tests, measured resources.

## CC-03 implementation checkpoint
Use tools/automation/cc03 (see docs/automation/CC03_RESULT.md) for synthetic logical planning; reuse existing tools/validation/build_sector_manifests.py. The prototype uses exact integer mm translation against a synthetic origin, half-open core including exclusion of maximum world bounds, conservative clipped halo, exact rational segment seam events, collinear review, stable point IDs and dirty-set detection. No native clipping/placement, CRS transformation, actual height seam, seed generation or Worker submission yet. Production halo, origin and CRS still unapproved.
