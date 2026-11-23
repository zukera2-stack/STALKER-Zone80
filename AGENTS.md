# Agent instructions: STALKER Zone80

**First entrypoint: [AGENT_START.md](AGENT_START.md).** Read it before taking any task.\n\nApplies to ChatGPT, Codex, Cursor/Luna and all repository automation. Read README, docs/MASTER_PLAN.md and docs/GO_NOGO.md before modifying code.

## Current owner directive: map first (2026-11-24)
- Active task is **[MAP-001 / Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35)**: make a small **real** 1–2 km Pripyat geographic pilot (terrain, roads, building footprints, preview), with one *isolated* Terrain Builder sandbox import only when safe.
- Stop further long UIA/SOAK stability experiments. The earlier 50/120 real SOAK cycles are PARTIAL, not PASS; the 27-minute synthetic runtime test passed. More tests are allowed only to unblock a specific mapping operation, not as a separate workstream.
- Stage 001 is still PARTIAL. Owner approved this bounded hands-on map pilot, **not** full-world production, Stage 002 promotion, unresolved CRS or asset licensing.
- **Issue-first rule:** publish every future Cursor/Luna/agent task as a GitHub Issue (or append to active Issue). Chat responses should link it, not require manual copy/paste. Each Issue states base SHA, deliverable, scope, limits, stop gate and evidence; work on an isolated branch/PR, no automatic merge.

## Mandatory limits
- Local user mods, extracted PBO contents and GIS source datasets are **read only**. Never mutate, delete, repack or upload them.
- Never store or push PBO/P3D/PAA, geospatial source rasters, satellite images, proprietary GRM source copies, local absolute paths or credentials.
- Use only project-owned output/cache paths; report any exception before writing.
- Never claim a loaded Arma terrain, valid WRP, solved CRS, accurate buildings, or fixed RAM issue without reproducible evidence.
- Stop at the authorized stage. Stage 001 permits the owner-authorized MAP-001 small real-world pilot as well as audits/synthetic tests, but **not** the full world generation.
- Keep three layers explicitly separate: grounded geography, proxy reconstruction, gameplay fiction.
- Asset license status UNKNOWN implies **no redistribution** and **no automatic approval**. Prefer external dependencies.
- A user-provided path/name is a search hint, not verification that a local file exists.

## Development contract
- Work on a feature branch. Avoid force pushes; do not merge without stage acceptance.
- Each task must report commit SHA, changed files, test commands/results, measurements, missing dependencies, and a GO/PARTIAL/NO-GO judgement.
- Any external acquisition must be recorded with source URL, time, SHA-256, license and coverage before it enters the pipeline.
- Preserve stable source IDs, seeded procedural generation and deterministic tile ownership.
- Keep full-world constants in config; do not hardcode a projection before measured control-point tests.
- Code and tests must run without requiring user-owned Arma tools where possible; platform-specific integration should skip with an explanation.

Active work order: Issue #35 and docs/MAP_001_TASK.md. Historical foundation: docs/TASK_CURSOR_001.md. Project gate: docs/GO_NOGO.md.
