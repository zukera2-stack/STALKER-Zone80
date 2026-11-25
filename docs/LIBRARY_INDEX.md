# Project reference library

Two distinct locations serve different purposes:

- **GitHub repository:** `zukera2-stack/STALKER-Zone80` is the canonical, version-controlled source for code, tasks, agent instructions, approved schemas and sanitized documentation.
- **Personal ChatGPT Library:** `/Арма/STALKER-Zone80/` contains snapshots of the owner's reports, research and draft model configurations. It is **not automatically synchronized** to GitHub or automatically available to Cursor.

## Library folders

| Folder | Contents | Sensitivity |
|---|---|---|
| `01_Исследование` | Deep Research 2026-11-22, original project plan | Research, not in-game test evidence |
| `02_Агент` | Historical project skill, copy of AGENT_START and navigation index | If conflicting, prefer current GitHub entrypoint |
| `03_Отчёты` | Environment and GRM memory audits from 2026-11-21, Task001 ZIP, prototype config and draft GRM project | Local machine paths and unverified drafts; **do not upload publicly without review** |

## Retrieval order for a new engineer

1. Start [AGENT_START.md](../AGENT_START.md) and read [AGENTS.md](../AGENTS.md).
2. Check [docs/BASELINE_FROM_PRIOR_REPORTS.md](BASELINE_FROM_PRIOR_REPORTS.md) rather than treating prior "OOM" as established.
3. If access to personal Library is authorized, read `03_Отчёты/GRM_MEMORY_AUDIT.md` and `ENVIRONMENT_AUDIT.md`; do not assert local read if access is absent.
4. Keep important new public, sanitized conclusions in GitHub, raw evidence in local ignored reports or private Library, and link to relevant issue/pr with SHA.

## Document authority

A historical report proves what that report observed, not the current installed state. A passing CI validates config and small scripts only; it does not prove the WRP generation, model permissions, or game loading. When uncertain, label claims PROVISIONAL / NOT TESTED. Agent workflow described by root AGENT_START.md.

## Owner artifact register — 2026-11-25
Files delivered in conversation (not claimed copied to personal Library or local Cursor): Zone80_base.grma3a, Zone80_inventory.json, Zone80_v02.grma3a, Zone80_Config_Preflight_v03.zip and prior editor-only copies. Exact hashes and scope in [owner preflight](map/GRM_OWNER_CONFIG_PREFLIGHT.md), [inventory](map/GRM_LOCAL_INVENTORY_RESULT.md), [roundtrip](map/GRM_STUDIO_ROUNDTRIP.md), [v03](map/GRM_CONFIG_PREFLIGHT_V03.md). If unavailable request owner copy; no blind download or public upload. GIS audit ZIP names and hashes in [checkpoint](map/MAP_003_CURRENT_CHECKPOINT.md) linked reports. This is a register, not a file transfer.
