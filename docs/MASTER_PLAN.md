# Master plan — Stage-gated STALKER Zone80

Source baseline: the owner's deep-research-report.md, 2026-11-22, SHA-256 e28339b70032173e8b50c14592ecc0209c6bba696fa44e47a80f600fc6d3abdf. This document is a **project design**, not a verified implementation result.

## Mission
Build a geographically defensible Chernobyl exclusion-zone map for Arma 3 with realistic footprints, roads and terrain, selected proxy objects from licensed/user-provided addon dependencies and a separate STALKER creative layer. Track source dates, uncertainty, manual overrides and licenses.

## Architectural commitments
- Target 81,920 m, 4096² cells at 20 m; texture layer candidate 80 m. Validate engine practicality by staged tests.
- Split preprocessing into 64 logical sectors of 10,240 m with buffer; final deliverable is **one WRP**. Streaming assembly is a research hypothesis, not achieved.
- Preserve WGS84 source coordinates; defer production CRS until full-world error/residual tests. Avoid silently mixing UTM zones 35N and 36N.
- Treat footprints as measured locations, matched P3D as visual proxies and procedural assets as fiction unless documented otherwise.
- Work within a suggested 18–20 GiB process budget, warn at 20 GiB, abort/checkpoint at 24 GiB; these are test policies, not Windows limits.
- Every object has immutable source_id, source_date, source/license, confidence, historical state and reviewer status.
- Input remains immutable, cache is disposable, overrides are versioned.

## Stage sequence
| Stage | Deliverable | Promotion gate |
|---|---|---|
| 001 Foundation | Hardware/GRM/project/asset inventory and GIS projection experiment | Clear facts, reproducible scripts, licenses and measured bottleneck |
| 002 Pripyat micro-pilot | Real 1–2 km urban area: footprints, model proxies, courtyards, roads, fences | Geographic QC, manual landmark review and measured object placement |
| 003 10.24 km | 512² × 20 m pilot terrain with roads, buildings, surfaces, objects | WRP/Binarize/PBO and **in-game** loading |
| 004 Two adjacent sectors | Stable ownership, overlap checks, buffer and deterministic reruns | No missing seams or duplicate objects |
| 005 Density stress | Q0-Q3 object load and measured runtime | Measured practical FPS/RAM/loading targets approved by owner |
| 006 Full-world dry run | Manifest for all 64 sectors | No full RAM-sized object aggregation |
| 007 Final world | One 81.92 km WRP, mod dependencies, publishable credits | Verified build, runtime, licensing and owner approval |

Only Stage 001 is authorized by this repository initialization.

## Known unknowns
1. True local Windows/CPU/RAM/pagefile/drive configuration, tool versions and paths.
2. Whether Zona.grma3m and selected addon folders are present.
3. Exact and license-compliant sources for historical footprints and suitable models.
4. Correct projected CRS, actual land extent and transformation residuals.
5. Root cause of the past GRM memory exhaustion.
6. Whether final one-WRP assembly can be implemented within measured budgets.

See ARCHITECTURE, GIS_PIPELINE, ASSET_PROVENANCE, PERFORMANCE, GO_NOGO and TASK_CURSOR_001.
