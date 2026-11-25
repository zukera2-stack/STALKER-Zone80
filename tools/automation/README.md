# Zone80 Worker
Current implementation: [CC-02](cc02/README.md), bounded Linux synthetic recovery prototype. From cc02: `python -m unittest -v test_worker.py`. [Report](../../docs/automation/CC02_RESULT.md), [contract](../../docs/automation/WORKER_CONTRACT.md), [roadmap](../../docs/automation/CONTROL_CENTER_ROADMAP.md). CC-01 remains in cc01/ with original evidence; old state/schema not automatically migrated. Windows/native jobs, hard resource isolation, scheduler, GIS generation NOT enabled. Next CC-03 synthetic sector manager.

## CC-03 sector planner
[cc03/](cc03/README.md) consumes existing foundation manifests without rewriting them. Synthetic integer-mm point/segment plans, shared seam signatures and dirty sector identities; no Worker job submission or actual GIS generation. Run from cc03: `python -m unittest -v test_sector_manager.py`, `python demo.py --repo-root ../../..`. [Report](../../docs/automation/CC03_RESULT.md). Next CC-04.

## CC-04 config/asset review
[cc04/](cc04/README.md) contains review-only six-module assembler, material/road locks, resource inventory reconciliation, synthetic dependency graph checks and ZPB metadata gate. From cc04: `python -m unittest -v test_config_builder.py`. Actual owner v03 reproduction requires separate owner inputs. No native config output, production mode disabled. [Report](../../docs/automation/CC04_RESULT.md). Next CC-05.

## CC-05 GM input review
[cc05/](cc05/README.md): strict read-only ASC review of the pinned historical owner archive, synthetic center sampling and validation; native integration design only. Run `python -m unittest -v test_gm_adapter.py` from cc05. Diagnostic CLI exit 2 is expected (NoData), not a successful native import. No raster output. [Report](../../docs/automation/CC05_RESULT.md). Next CC-06.

## CC-05B GM-only bridge (owner-selected)
[cc05b/](cc05b/README.md): read-only node-compatible input contract, 8 Python tests PASS twice; original C# bridge candidate and synthetic smoke harness for actual GRM APIs, compile NOT RUN locally. No native real-context entrypoint. [Report](../../docs/automation/CC05B_RESULT.md). UI deferred; CC-05C build and native synthetic smoke next.

## CC-05E config and coordinate review
[cc05e/](cc05e/README.md) is native diagnostic-only companion using real v03 and exact pilot example. Requires offline toolchain from [Library index](../../docs/LIBRARY_INDEX.md). No native layer call, strict missing metadata rejection; actual generation blocked. [Report](../../docs/automation/CC05E_RESULT.md). Next CC-05F.

## CC-05F
[cc05f](cc05f/README.md) — strict native model cache review companion, pinned v03 and owner cache; no generation. [Report](../../docs/automation/CC05F_RESULT.md).

## CC-05G
[cc05g](cc05g/README.md) — original GRM native synthetic tree layer using actual v03/model cache, bounded OSM graph and collision defect probe. [Report](../../docs/automation/CC05G_RESULT.md).

## CC-05H
[cc05h](cc05h/README.md): synthetic state overlay and native GRM tree placement companion, no production exporter. [Report](../../docs/automation/CC05H_RESULT.md).

## CC-05I
[cc05i](cc05i/README.md) — native forest geometry adapter and synthetic probe. [Report](../../docs/automation/CC05I_RESULT.md).
