# Agent instructions: STALKER Zone80

**First entrypoint: [AGENT_START.md](AGENT_START.md).** Read it before taking any task.\n\nApplies to ChatGPT, Codex, Cursor/Luna and all repository automation. Read README, docs/MASTER_PLAN.md and docs/GO_NOGO.md before modifying code.

## Mandatory limits
- Local user mods, extracted PBO contents and GIS source datasets are **read only**. Never mutate, delete, repack or upload them.
- Never store or push PBO/P3D/PAA, geospatial source rasters, satellite images, proprietary GRM source copies, local absolute paths or credentials.
- Use only project-owned output/cache paths; report any exception before writing.
- Never claim a loaded Arma terrain, valid WRP, solved CRS, accurate buildings, or fixed RAM issue without reproducible evidence.
- Stop at the authorized stage. Stage 001 permits audits and minimal synthetic data tests, not full world generation.
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

Work order: docs/TASK_CURSOR_001.md. Project gate: docs/GO_NOGO.md.
