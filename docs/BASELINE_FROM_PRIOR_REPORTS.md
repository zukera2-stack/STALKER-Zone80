# Baseline from earlier Zone80 audit — *source reports*, not new engine tests

> **Исторический контекст 21.11.2026, НЕ текущая конфигурация.** Упоминания `Global Mapper v27`, Windows 10 и исходного GRM относятся к конкретным прежним отчётам, **не** перечёркивают более поздний локальный результат GM Pro **26.2** с двумя batch export exit 0 ([PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41)). Host/VM ОС надо отдельно проверять, не смешивать разные машины. Актуальное задание высот — [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), [PROJECT_CONTROL](PROJECT_CONTROL.md).

This is a **sanitized summary** of personal-library source reports dated 2026-11-21, preserved privately under `/Арма/STALKER-Zone80/03_Отчёты/`. Their contents have not been independently reproduced by a new local test in the current GitHub repository.

| Item | Reported finding | Confidence / follow-up |
|---|---|---|
| OS | Windows 10 Pro on audited machine | Reconfirm on same PC; earlier specification said Windows 11 Pro |
| Global Mapper | v27.0 64-bit present | Installed, not yet used for verified GMS export |
| Arma 3/Tools | Arma 3 and Terrain Builder located | No generated world launched |
| GRM Studio | UI/About showed v0.9 | Upgrade/test v0.11.1 only with separate installation, verified package hash |
| Prior failure | `A task may only be disposed if it is in a completion state` during RawSatelliteImage | Measured/logged failure was an exception, **not confirmed OOM** |
| Old logs memory | ~8.3–8.7 GB at failure; system 32 GB reported | May not equal Private Bytes; preserve original logs and instrument new run |
| Upstream source | ArmaRealMap v0.11.1 tag associated with commit `2aef2040836daa11a8a368bb0c7f9ecd8f405d65` | Pin and verify local clone; reported release fix matches prior exception |
| Original Zona.grma3m | 8192 × 10.875 m = 89,088 m world; 1 m/px satellite | Very heavy setup; do **not** rerun as original |
| Small prototype | Draft 512 × 20 m = 10,240 m; satellite 4 m/px | Draft exists in private Library; **NOT TESTED** |

## Operational impact

Previous directive to find the reason for "32 GB exhaustion" must now be **reframed**: first verify the logged exception and determine whether a fixed GRM version resolves it on the small draft configuration. Separately profile memory to establish capacity for the eventual 81.92 km world. No root cause for future large-map scaling has been proven.

## Boundaries
This file intentionally omits private user drive paths and personally identifying account details. Original private reports and the earlier Task001 archive were copied to the personal ChatGPT Library; originals were not moved. Cursor cannot automatically read that library from GitHub and needs an authorized local copy or an evidence-based independent audit.

Source of truth for implementation policy: [AGENT_START.md](../AGENT_START.md), [docs/TASK_CURSOR_001.md](TASK_CURSOR_001.md), [docs/GO_NOGO.md](GO_NOGO.md).
