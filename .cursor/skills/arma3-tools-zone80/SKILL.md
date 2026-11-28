---
name: arma3-tools-zone80
description: Safe Arma 3 Tools workflows for Cursor in STALKER-Zone80. Use for Terrain Builder, Work Drive, Object Builder, Addon Builder, Binarize, CfgConvert, Terrain Processor, Buldozer, environment inventory, and synthetic TB ASC/CSV validation.
---

# Arma 3 Tools — STALKER-Zone80 / Cursor

**Новое решение владельца 27.11.2026 — штатная среда P: (TB-P-NATIVE-01, [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7226176532)).** Использовать `P:\` как Data Directory Terrain Builder/Buldozer и штатные ресурсы `a3`, `bin`, `core`, без копирования набора ресурсов на D:. Общий `P:\buldozer.cfg` единственный, штатный, read-only; не менять и не создавать альтернативных cfg. Профили, GIS-производство, логи и архивы на D:. Разрешена запись только в собственный новый каталог `P:\zone80` после проверки containment, отсутствия reparse/чужих данных и необходимости. Остальное на P: неприкосновенно; не монтировать/размонтировать диск. Эта узкая оговорка имеет приоритет над прежними абсолютными запретами P: и требованием отдельных cfg/cwd; изоляция профилей, выходов, editor/IPC, принадлежности процесса и контроль хешей обязательны. Для TB использовать штатный Connect, без `-noLand`; чужой Buldozer не закрывать. При конфликте редактора или нехватке ресурсов STOP. Сохраняются запреты WRP/PBO, имитации ввода, merge, stage promotion. Исторические результаты не переписывать. Официальная инструкция: https://community.bistudio.com/wiki/Buldozer_Manual.

**Проверенный маршрут TB-P-NATIVE-03 (28.11.2026) — [результат #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42#issuecomment-7233711770).** Для дальнейших испытаний карты предпочитать установленный `P:\buldozer_x64.exe` (2.22) вместо x86: x64 реально запущен штатным Connect, получен CONN, тогда как предыдущий x86 запуск не наблюдался. Это не доказательство универсальной несовместимости x86.
- Terrain Builder: Data Directory и Working Directory — `P:` , Executable — `P:\buldozer_x64.exe`; общий `P:\buldozer.cfg` только чтение. Временный профиль и журналы в уникальном собственном каталоге на D:.
- Проверенные аргументы карты: `-buldozer -name=Zone80Preview64 -window -exThreads=0 -disableSteam -noAsserts -cfg=P:\buldozer.cfg -profiles=<уникальный каталог на D:> -showScriptErrors` (подставить реальный путь, при пробелах заключить в кавычки). Не добавлять `-noLand` (он для Object Builder), не отключать RPT. Канал `-connect=pipe...` создаёт сам TB; не подставлять вручную.
- До/после проверить процессы, RAM, cfg, проект; после теста закрыть только идентифицированный собственный viewer штатно, проверить выход, восстановить временные настройки TB.
- Фактически: CONN, поверхность видна, RPT при проверке без Cannot load texture / Cannot open object / Bad texture format. Камера (-197475,91,2925) вне синтетического участка; корректное отображение деревьев и материалов НЕ ПОДТВЕРЖДЕНО. Zoom extent не переместил камеру, Goto position через UIA не открылся. Следующий gate — штатная навигация в центр (локально 960,109,960; исходное начало TB E200000/N0; проверить формат координат диалога), снимок и сравнение RPT. Не повторять x86/копирование ресурсов без новой причины. Stage001 PARTIAL; прежние запреты сохраняются.



Read AGENT_START.md, AGENTS.md, docs/PROJECT_STATE.yaml, docs/GO_NOGO.md and current Issue #42. Mandatory: read ../zone80-luna-autonomous/SKILL.md and ../zone80-map003-gm-tb/SKILL.md. Stage 001 / PARTIAL remains; the owner-approved MAP-005 bounded synthetic editor scope supersedes historical TB-01 examples, not the safety limits. Do not merge PRs automatically.

## Use

1. Identify whether this terminal is local Cursor on the owner's Windows machine or Codex/remote. Only real local Windows evidence can prove installed tool access.
2. Reuse verified installation, versions and P: evidence; refresh only changed or task-critical facts. Do not turn preparation into a repeated audit. Start the next authorized production step immediately.
3. For MAP-005, use the existing synthetic ASC/BMP/BPW/SHP/mask handoff. Create the owned mapframe, import layers, save and reopen the project using confirmed supported operations. Check every result. TB-01 remains historical. Preserve input hashes, screenshots and errors; a successful file validation is not a native import.
4. Use references/TOOLCHAIN.md and references/TERRAIN_BUILDER.md for tool-specific procedures. Record evidence using references/PROVENANCE.md.

## Commands (from repository/workspace root)

Read-only Windows tools inventory:

    pwsh -NoProfile -File .cursor/skills/arma3-tools-zone80/scripts/inspect_arma_tools.ps1

For a known root use -ToolsRoot "<verified path>". Do NOT guess the real path or recursively search entire disks.

Synthetic TB format preflight (requires files produced by GRM-01):

    python .cursor/skills/arma3-tools-zone80/scripts/validate_tb_inputs.py --asc reports/grm01-example/world/elevation.asc --absolute reports/grm01-example/world/absolute_fixture.txt --relative reports/grm01-example/world/relative_fixture.txt

Offline tests:

    python -m unittest discover -s .cursor/skills/arma3-tools-zone80/scripts -p "test_*.py" -v

These tests validate input syntax only. They do not prove Terrain Builder import or model availability.

## Tool boundaries

- Terrain Builder: mapframe, terrain ASC, satmap/idmap, object CSV and TML. For Zone80 import absolute and relative layers separately and check XShift=200000.
- Work Drive / P:: inspect only, NEVER mount/unmount or write automatically.
- Object Builder: work only with owner-authorized editable models; do not de-binarize copyrighted P3D.
- Addon Builder / Binarize: packaging and compilation. NOT authorized in Stage 001.
- CfgConvert: inspect location/version, no conversion of original game files.
- Terrain Processor: plan controlled synthetic placement, NOT production WRP.
- Buldozer: MAP-005 permits a bounded visual check of the owned sandbox when supported and safe, without P: writes; requires actual graphical evidence. Do not claim a preview without evidence.
- GRM gentb: upstream may fetch OSM and convert imagery. Do not run blindly or treat a format-contract test as full native gentb.

## Safety rules

Keep original GIS sources and game assets read-only. Never upload PBO/P3D/PAA, satellite rasters, credentials, license keys or personal absolute paths. Stage 001 excludes actual 10.24 km pilot, full 81.92 km map, WRP/PBO, binarization, large downloads or unapproved model extraction. Write only to a new ignored reports/ sandbox, not P: or installed tool directories.

If a dependency is unavailable, follow the autonomy skill: test all materially different applicable authorized routes within budget, fix reversible faults, finish independent outputs, then report a precise BLOCKED/NOT RUN for the affected criterion. Do not stop at an intermediate check or hand back an executable next step. Do not silently use substitute tests as PASS. Return exact branch/SHA, tool versions, commands, sanitized logs, timing/working set if measured, hashes, blockers and a GO/PARTIAL/NO-GO conclusion.

This portable copy is intended for the currently opened Cursor workspace. It does not turn a non-Git folder into a Git clone.

## Terrain Builder command reference

- For researched Terrain Builder menu commands and CLI compatibility, read [Terrain Builder commands](references/TERRAIN_BUILDER_COMMANDS.md).
