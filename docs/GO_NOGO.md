# Stage gates: evidence rather than optimism

## Status vocabulary
- **PASS / GO:** measured criteria satisfied by reproducible evidence.
- **PARTIAL:** preparatory work exists but required tests or dependencies are missing.
- **FAIL / NO-GO:** criterion contradicted or safety bound breached.
- **NOT TESTED:** no evidence. This is never PASS.

## Stage 001 foundation acceptance
- Actual Windows build, CPU/cores, physical RAM, pagefile, storage and tool paths/versions recorded.
- Existing local .grma3m/.grma3a, GRM tag/SHA and addon roots located *if they exist*, without mutation.
- Unchanged upstream GRM builds; small memory profile recorded with stage-by-stage peak. If not possible, PARTIAL with reason.
- Asset inventory with hashes and UNKNOWN license handling; no copyrighted binaries committed.
- Candidate CRS roundtrip and distortion measured on boundary control points; no guessed map origin.
- Git diff clean of third-party assets, credentials and source datasets; manifest tooling deterministic.
- Reports include exact commands, SHA, logs, file inventory and unresolved issues.

## Owner-approved mapping pilot (2026-11-24) — NOT a stage promotion

**Issue #35 / MAP-001 may proceed now** despite incomplete Stage 001 inventory. It is a controlled **small real 1–2 km Pripyat data/preview/sandbox** exercise, not Stage 002 GO. The decision explicitly **stops the TB-UIA/SOAK test workstream**: earlier autonomous launch/UIA 203 nodes/50 completed real SOAK cycles suffice for this pilot operationally; a 60-minute SOAK is **NOT PASS** and the old stop cause is **CAUSE_UNKNOWN**. Do not demand another soak or more generic UIA tests as a prerequisite to creating real map data.

MAP-001 uses the owner's existing **Global Mapper 26.2 Pro 64-bit** as its primary GIS processor, subject to local installation/version/license verification; primary DEM/vector data provenance is separate. No buildings or structures are to be placed in Terrain Builder. Google 360 may supply verified source links only, not scraped images or extracted model geometry.

Map-pilot acceptance: documented legally usable DEM/source + actual WGS84 area and sample metadata; a verifiable elevation-and-roads preview plus a *separate* building-footprint GIS catalog (no placement or 3D models); georeferenced coordinate/height control points; and, **only if safely isolated**, a Terrain Builder sandbox import + evidence. If TB cannot be isolated, record GUI import BLOCKED but continue producing the real offline geographic artifact. No bulk data, no copyright-bearing raw assets in Git, no unsaved user project changes. Formal promotion, final CRS/extent/epoch and in-game claims remain separate decisions.

## Promotion
The director audits the evidence; the owner authorizes Stage 002. Do not begin 10.24 km pilot or full world on Stage 001 authorization. For Stage 003 and Stage 007, a successful serializer is not a PASS: **the actual Arma map must load** with RPT/screenshots and package dependency checks.
