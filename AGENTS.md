# Agent instructions: STALKER Zone80

**Superpowers:** [проектный инженерный регламент](docs/SUPERPOWERS_WORKFLOW.md). Использовать актуальный профильный skill при наличии плагина, иначе локальный регламент. Технические допуски, нативные guards и полномочия неизменны; Desktop Commander запрещён, согласования только по действующим воротам.


**Действующий регламент владельца 28.11.2026 — AI_WORKSPACE / Google Drive.** ChatGPT — ведущий разработчик и аналитик, выполняет доступные расчёты, код, тесты и независимую приёмку; Cursor/Codex — локальный исполнитель через PowerShell и разрешённые нативные инструменты. GitHub — код, задания, статусы и документация; Google Drive — разрешённые файловые комплекты INPUT/OUTPUT/QA/ARCHIVE, уникальное имя, манифест, SHA256, проверка получателем. Library — исторический источник, не основной канал. Desktop Commander не использовать. При недоступности Drive сохранять локально и продолжать независимые работы. Технические допуски неизменны. [Полный регламент](docs/AI_WORKSPACE.md). Активный TB-RECOVER-02, Issue #42 / PR #52, Stage001 PARTIAL.


**Новое решение владельца 27.11.2026 — штатная среда P: (TB-P-NATIVE-01, [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7226176532)).** Использовать `P:\` как Data Directory Terrain Builder/Buldozer и штатные ресурсы `a3`, `bin`, `core`, без копирования набора ресурсов на D:. Общий `P:\buldozer.cfg` единственный, штатный, read-only; не менять и не создавать альтернативных cfg. Профили, GIS-производство, логи и архивы на D:. Разрешена запись только в собственный новый каталог `P:\zone80` после проверки containment, отсутствия reparse/чужих данных и необходимости. Остальное на P: неприкосновенно; не монтировать/размонтировать диск. Эта узкая оговорка имеет приоритет над прежними абсолютными запретами P: и требованием отдельных cfg/cwd; изоляция профилей, выходов, editor/IPC, принадлежности процесса и контроль хешей обязательны. Для TB использовать штатный Connect, без `-noLand`; чужой Buldozer не закрывать. При конфликте редактора или нехватке ресурсов STOP. Сохраняются запреты WRP/PBO, имитации ввода, merge, stage promotion. Исторические результаты не переписывать. Официальная инструкция: https://community.bistudio.com/wiki/Buldozer_Manual.


**Historical execution channel — superseded by owner decision 2026-11-28 (do not use):** Luna primarily operates from ChatGPT using the connected Desktop Commander Remote plugin on the authorized Windows PC. Read [zone80-desktop-commander](.cursor/skills/zone80-desktop-commander/SKILL.md) with the mandatory autonomy v2.1 skill. Cursor/Codex are optional supporting channels; no need to launch Cursor, no alternative-channel circumvention of denied operations. Verify device, tool availability and native outputs. Existing scope and safety rules remain binding.

**Решение владельца (27.11.2026) — параллельный Buldozer:** разрешено запускать собственный экземпляр Buldozer одновременно с экземпляром другого агента. Само наличие чужого Buldozer больше не является блокером. Перед запуском зафиксировать список уже работающих экземпляров; после штатного Connect идентифицировать новый собственный процесс по PID, времени старта, пути exe, родительскому редактору и фактическим аргументам/каналу подключения. Не требовать единственного Buldozer в системе; требовать единственного однозначно идентифицированного нового собственного экземпляра. Раздельные рабочие каталоги, cfg, profiles, журналы и выходные файлы обязательны. Не изменять общие настройки или тот же экземпляр редактора при конкурирующем доступе; не угадывать IPC, не трогать чужие процессы. Сохранять ограничения P: read-only, запрет имитации ввода, WRP/PBO, merge и stage promotion. После теста штатно закрыть только свой просмотрщик и проверить его завершение, даже если чужие продолжают работать. При неоднозначной принадлежности, конфликте файлов/настроек/каналов или нехватке ресурсов остановить конкретное действие. Это разрешение относится к Buldozer; не расширяет допуск к чужим игровым процессам или иным проектам. Старые требования свободной сессии из исторических отчётов в части наличия другого Buldozer заменены этим правилом.

## Mandatory execution priority — owner decision 2026-11-27
Read AGENT_START.md, latest authorized [Issue #42 / MAP-005](https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7203582618) and **[zone80-luna-autonomous v2.1](.cursor/skills/zone80-luna-autonomous/SKILL.md)** before planning or executing any Luna task. The [alwaysApply rule](.cursor/rules/zone80-autonomous.mdc) makes this workflow persistent within Cursor. Specialist skills follow it. Execute, independently verify, fix, continue; exhaust applicable permitted routes within budget and finish independent branches. Do not stop at an intermediate PASS or return a runnable next step as a report. No new permissions arise from the skill. Mandatory limits below and explicit owner scope prevail. MAP-005 permits bounded synthetic native GRM and test placement in an owned isolated editor project, not real placement without gates, WRP/PBO, P: writes, input emulation, full world or merge. Earlier MAP-003 and CC handoffs below are historical where conflicting. Stage001 PARTIAL.

**Historical handoff (25.11):** [RESUME_AFTER_CC05R](docs/automation/RESUME_AFTER_CC05R.md). Branch feat/cc05r-sector-review, measured code 7954bd57b9d7ca72404b1841204989f906686459. CC05R bounded Linux synthetic PASS / overall PARTIAL; CC06/CC06A DEFERRED by owner until real-map validation; next active MAP-003 GM26.2 coverage. Reuse prior components. Local MAP-003 and all STOP rules unchanged.

**First entrypoint: [AGENT_START.md](AGENT_START.md).** Read it before taking any task.

Applies to ChatGPT, Codex, Cursor/Luna and all repository automation. Read README, docs/MASTER_PLAN.md and docs/GO_NOGO.md before modifying code.

## Historical owner directive: map first (2026-11-24)
- Active EXECUTION task is **[MAP-003 / Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42)** (Issue #35 is the MAP-001 umbrella): make a small **real** 1–2 km Pripyat geographic pilot (terrain and roads, plus a separate geospatial building-footprint catalog (no building placement or 3D models)), with one *isolated* Terrain Builder sandbox import only when safe.
- **Newest owner rule (2026-11-24):** ChatGPT only supplies coordinates and correct geographic tiles; actual elevation acquisition and ASC/GeoTIFF export occur inside the owner's local **Global Mapper 26.2 Pro**. **No NEW Python/GDAL/GitHub Actions heightmap generation**; PR #43 is closed/superseded. Exact tile and 64×64×30 m UTM36 pilot: docs/map/MAP_003_GM26_TILES.md; this is NOT the 4096² world grid.
- **Authoritative current navigation:** docs/PROJECT_CONTROL.md, docs/PROJECT_STATE.yaml, docs/REQUIREMENTS_MATRIX.md, docs/VERIFICATION_LEDGER.md, docs/DECISIONS/ADR-0002-owner-pivot-map-and-gm-only.md. Old draft docs and task files cannot override owner decision.
- Stop further long UIA/SOAK stability experiments. The earlier 50/120 real SOAK cycles are PARTIAL, not PASS; the 27-minute synthetic runtime test passed. More tests are allowed only to unblock a specific mapping operation, not as a separate workstream.
- The owner's primary GIS application is **Global Mapper 26.2 Pro, 64-bit**, not v27. Use the existing local v26.2 for elevation/vector inspection and exports; verify installation/license and exact supported scripting commands locally before claiming PASS. The application is a GIS processor, not a geodata/photography source.
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

Active work order: Issue #42 / MAP-005 and the mandatory autonomous skill; MAP_003_GM26_TILES.md is a reference for the earlier real terrain grid. Epic: Issue #35. Historical foundation: docs/TASK_CURSOR_001.md. Project gate: docs/GO_NOGO.md.

## Current GRM checkpoint (2026-11-25)
Read [MAP_003_CURRENT_CHECKPOINT](docs/map/MAP_003_CURRENT_CHECKPOINT.md) and [minimal dependencies](docs/integration/MINIMAL_DEPENDENCIES.md). Owner v02 Studio save is real evidence for six recovered surfaces, not game generation. v03 remains editor/review-only for production; native strict parser and bounded synthetic Linux generation measured through CC-05P. No real native map or runtime approval. Reuse prior audits; actual new checks only. No external mandatory mods, no ice/default or base world guesses. Existing Issue #42 and Draft PR #47; GM-only and STOP rules unchanged.
