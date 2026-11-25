# Zone80 Worker
Current implementation: [CC-02](cc02/README.md), bounded Linux synthetic recovery prototype. From cc02: `python -m unittest -v test_worker.py`. [Report](../../docs/automation/CC02_RESULT.md), [contract](../../docs/automation/WORKER_CONTRACT.md), [roadmap](../../docs/automation/CONTROL_CENTER_ROADMAP.md). CC-01 remains in cc01/ with original evidence; old state/schema not automatically migrated. Windows/native jobs, hard resource isolation, scheduler, GIS generation NOT enabled. Next CC-03 synthetic sector manager.

## CC-03 sector planner
[cc03/](cc03/README.md) consumes existing foundation manifests without rewriting them. Synthetic integer-mm point/segment plans, shared seam signatures and dirty sector identities; no Worker job submission or actual GIS generation. Run from cc03: `python -m unittest -v test_sector_manager.py`, `python demo.py --repo-root ../../..`. [Report](../../docs/automation/CC03_RESULT.md). Next CC-04.

## CC-04 config/asset review
[cc04/](cc04/README.md) contains review-only six-module assembler, material/road locks, resource inventory reconciliation, synthetic dependency graph checks and ZPB metadata gate. From cc04: `python -m unittest -v test_config_builder.py`. Actual owner v03 reproduction requires separate owner inputs. No native config output, production mode disabled. [Report](../../docs/automation/CC04_RESULT.md). Next CC-05.
