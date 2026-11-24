# STALKER Zone80 — Arma 3 exclusion-zone terrain

**Status: Stage 001 / PARTIAL — real GIS progress, NOT a playable map.** This repository is the source-controlled coordination and processing layer for a large, geographically grounded Chernobyl exclusion-zone terrain for Arma 3, enriched with separate S.T.A.L.K.E.R.-style gameplay layers.

## Target, not a demonstrated build

| Parameter | Target |
|---|---|
| One Arma 3 world | 81,920 × 81,920 m |
| Heightmap | 4096 × 4096 cells |
| Terrain cell | 20 m |
| Texture layer candidate | 80 m |
| Processing | 8 × 8 sectors, each 10,240 m |
| Final output | **one WRP**, not 64 independently merged WRP files |
| Pilot sequence | 1–2 km Pripyat → 10.24 km → adjacent sectors → full world |
| Development workstation | Windows 11 Pro / 32 GB RAM as reported, **not locally verified** |

**Crucial distinction:** confirmed physical geographic features, visual proxies reconstructed using licensed Arma assets, and fictional gameplay additions are separate layers. A geographic footprint is not evidence that the matched 3D model is historically authentic.

## Agent entrypoint

**Start every agent session at [AGENT_START.md](AGENT_START.md).** The project reference Library is indexed in [docs/LIBRARY_INDEX.md](docs/LIBRARY_INDEX.md).

## Start here

1. Read [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md), [docs/GO_NOGO.md](docs/GO_NOGO.md) and [AGENTS.md](AGENTS.md).
2. Cursor/Luna: follow active [Issue #42 / MAP-003](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), not the historical [Stage 001 foundation task](docs/TASK_CURSOR_001.md). **Local Global Mapper Pro 26.2** obtains and exports heights; ChatGPT gives only tile/coordinates. No full world or buildings.
3. Review the unresolved projection in [config/terrain_extent.json](config/terrain_extent.json). CRS and exact extent must be experimentally approved.
4. Run local standard-library checks: `python tools/validation/validate_config.py`; generate dry-run sector manifests with `python tools/validation/build_sector_manifests.py`.
5. Import no copyrighted addon models or large source data into Git; read [docs/ASSET_PROVENANCE.md](docs/ASSET_PROVENANCE.md).

## Pipeline

Geographic sources (OSM / DEM / historical) → normalized GIS → source-confidence records → sectorized placement records → licensed asset matching → one final WRP/PBO → in-game acceptance tests.

GameRealisticMap / ArmaRealMap is a candidate processing engine and requires a measured baseline; it is **not** a verified Zone80 81.92 km generator. The prior out-of-memory failure is unresolved.

## Roles

- **Owner / art director:** permits individual mod dependencies and decides historical canon and STALKER deviations.
- **Cursor (“Luna”) / engineer:** local read-only inventory, source audit, scripts, instrumented experiments and evidence.
- **ChatGPT / director and auditor:** stage planning, critical review of evidence, acceptance gates.

Work through feature branches and pull requests. Do not rewrite existing user mods, force-push or assume local files exist. See [docs/HANDOFF.md](docs/HANDOFF.md).

## Source material and licensing

The project roadmap was adapted from a 2026-11-22 deep research report (SHA-256: `e28339b70032173e8b50c14592ecc0209c6bba696fa44e47a80f600fc6d3abdf`). The [complete research report](docs/research/deep-research-report-2026-11-22.md) is archived verbatim for Cursor; its external claims are not independently verified by local engine tests. Primary links and claims are recorded in [docs/RESEARCH_SOURCES.md](docs/RESEARCH_SOURCES.md).

**No redistribution license is presumed for this repository's code/assets or third-party mods.** License review is pending; data sources have separate obligations. No user-provided PBO, P3D, PAA, WRP or other binaries are stored here.
