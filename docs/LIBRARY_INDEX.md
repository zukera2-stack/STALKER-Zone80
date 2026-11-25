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

## Persistent GRM toolchain and input snapshots (owner request, 2026-11-25)
Actual copies saved in personal ChatGPT Library under `/Арма/STALKER-Zone80/`, confirmed by successful uploads and recursive library listing. This supersedes the earlier register-only paragraph for these named files. Do not confuse personal Library with Project attachments or automatic Cursor access. No public binary/GIS redistribution; rights checks still apply.

### 04_Инструменты_GRM
| Exact filename | SHA256 |
|---|---|
| dotnet-sdk-10.0.404-linux-x64.tar.gz | c0610757a818fde4b960d27a0ac421f273068a05dc5ec7abafc01dbf84e9cb4d |
| dotnet-sdk-10.0.403-linux-x64.tar.gz | cd7224fe8e8ba57c15f1601439ff8785a1a72b54ae5c89dd5302a32dcfbddf18 |
| ArmaRealMap-2aef2040836daa11a8a368bb0c7f9ecd8f405d65.zip | 00c0ea9ae0d996df3476cd64117ca1c35de55caaf8554067e469008e03e9e3e0 |
| Zone80_NuGet_Offline_20261125_160739_4fc541e1.zip | 1227f3314680fbd103ea74fbf57c2e4a6c0f840b05d90836c6a7d63929a1b250 |
| Zone80_Arma3_Offline_20261125_164834_94b29532.zip | 87c01ec5ec21650af66eb2c5c5d090420913501ac3295eb9bbc798779161ce69 |

Use SDK 10.0.404; 10.0.403 reserve only. Second package archive includes the pinned BIS source; keep both feeds and validate manifests/lock before offline restore. Also saved Zone80_CC05E_source_transfer.md (original project code/log text, canonical source is Git). [SDK intake](automation/CC05C_ENVIRONMENT.md), [core build](automation/CC05C_RESULT.md), [Arma3 build](automation/CC05D_RESULT.md), [parser review](automation/CC05E_RESULT.md).

### 05_Входные_данные_GRM
| Exact filename | SHA256 |
|---|---|
| Zone80_base.grma3a | df349cf5fa8fec39f85d510c5b3127c533f586208752b3dbf483efa2753e920d |
| Zone80_inventory.json | bced5f4e610ef0c3667f1f91f6dd2016e5f0223fb147f5986664c17d9493668e |
| Zone80_v02.grma3a | 84e0cdee7501b7e9f01cc92b6635c70e8d6503f591e0b1a0ffffef2a2d6bf41a |
| Zone80_Config_Preflight_v03.zip | 5c1acdf80eaa5e0fd61adddd41845946e8df6e994881c16faaaf2a20cdbee90a |
| MAP-003-Pripyat-verification(1).zip | 457f1fdb363d0f586ef3fde82cec4f407784f1ab68af867e099c1bac84e72869 |

These are private review/diagnostic inputs, not approved release assets or full GM coverage. Historical ASC 629 NoData, no repair. Never transfer original Arma binaries into Git.

### Agent retrieval
Start with AGENT_START and current draft PR HEAD. If authorized, browse personal Library at the exact folder above or search exact filename in Library; select matching file snapshot, download/materialize original bytes into isolated scratch, compare SHA256 before extracting. If not accessible, owner attaches the file from Library or downloads it to local Cursor workstation; do not claim a successful attachment or re-download automatically. SDK tarball and source ZIP are large; reuse existing verified extraction rather than unnecessary duplication. Verify safe archive paths, manifests and transitive lock, extract BIS into the matching GRM submodule path only in isolated copy. Never use P: as build target. Actual saved names/sizes confirmed by listing; SHA values measured on original mounted files, not separately re-read stored copies. All canonical code and sanitized logs in Git. No files auto-synced across agents or to external services.
