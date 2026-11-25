# START HERE — передача Zone80 после CC-05P

Дата: 25.11.2026. Документ передачи, не новый тест. Последний измеренный код: `ff84106de719dbb17fd1caa749cf5aa5269b9698`. Этот SHA — **evidence cutoff**, не обещание текущего HEAD. Рабочая ветка `audit/map003-digital-geocatalog`, [Draft PR #47](https://github.com/zukera2-stack/STALKER-Zone80/pull/47), активная [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42). Main не содержит всех результатов. Stage 001 / PARTIAL.

## 1. Первые действия любого нового агента
1. Сверить фактический HEAD PR #47, draft/merge, локальную ветку и git status. Не сбрасывать незакоммиченные изменения владельца. Если PR/HEAD изменён другим агентом, сначала согласовать область и прочитать новые commits; не переписывать старую работу.
2. Прочитать [AGENTS](../../AGENTS.md), [PROJECT_STATE](../PROJECT_STATE.yaml), [VEGETATION_SUCCESSION_POLICY](../map/VEGETATION_SUCCESSION_POLICY.md), [CC05P_RESULT](CC05P_RESULT.md), [WORKER_CONTRACT](WORKER_CONTRACT.md), [CC02 README](../../tools/automation/cc02/README.md), [CC05P README](../../tools/automation/cc05p/README.md). Для локальной Windows — [LUNA_HANDOFF](LUNA_HANDOFF.md). Не требуется читать все исторические логи до начала нового блока.
3. Продолжать только текущую ветку/согласованную отдельную ветку, Issue #42. Сообщить base SHA, scope, stop gate; сохранить отчёт с командами, метриками, exit и hash. Не merge без владельца.
4. Не повторять предыдущие фазы ради галочки. Если нет среды, восстановить закреплённые инструменты из [Library index](../LIBRARY_INDEX.md), проверить hashes и запустить только нужную контрольную проверку. ChatGPT Library не автоматически доступна Cursor. Не требовать заново уже полученные файлы при наличии проверенной копии.

## 2. Что реально сделано и откуда продолжать

| Блок | Измеренный результат | Где код / отчёт |
|---|---|---|
| CC-01/02 Worker | Linux synthetic; 9 тестов CC01, 13 CC02 дважды; lock, stop/resume, аварийное восстановление, потомки в проверенном сценарии | [cc02](../../tools/automation/cc02/README.md), [CC02](CC02_RESULT.md); CC01 исторический |
| CC-03 Sector Manager | 64 логических сектора, 112 общих граней, 11 тестов дважды; dirty sets | [cc03](../../tools/automation/cc03/README.md), [CC03](CC03_RESULT.md) |
| CC-04 Config/Asset | 13 тестов дважды, review-only; production resources BLOCKED | [CC04](CC04_RESULT.md) |
| CC-05/05B–D | Проверка GM ASC, строгий node gate, C# bridge, сборка pinned GRM и native synthetic tree probe | [CC05](CC05_RESULT.md), [bridge](../../tools/automation/cc05b/README.md), [CC05D](CC05D_RESULT.md) |
| CC-05E/F/G | Native v03 parser, 491 cache entries / 163 selected paths, реальные native synthetic tree placements, +100m response | [CC05E](CC05E_RESULT.md), [CC05F](CC05F_RESULT.md), [CC05G](CC05G_RESULT.md) |
| CC-05H–J | Состояние территории, 5 native vegetation layers, полная геометрия до sector assignment | [H](CC05H_RESULT.md), [I](CC05I_RESULT.md), [J](CC05J_RESULT.md) |
| CC-05K | native road SHP/DBF roundtrip in memory, bridge/rail placements | [K](CC05K_RESULT.md) |
| CC-05L/M | native hydrography и bounded semantic/material masks; full IdMapRender NOT RUN | [L](CC05L_RESULT.md), [M](CC05M_RESULT.md) |
| CC-05N | native fence/explicit small objects/tree rows, 68 synthetic records | [N](CC05N_RESULT.md) |
| CC-05O | Один контекст, 13/27 native generators, 1015/1062 records, 21/14 held, 31/0 road plants | [O](CC05O_RESULT.md) |
| CC-05P | Closed job/result schema; 2 identical suites, each 5 native jobs, 20 input refusals, 6 output refusals | [P](CC05P_RESULT.md), [current child and verifier](../../tools/automation/cc05p/README.md) |

Все PASS ограничены измеренными synthetic Linux / review scope; реальная карта не создана. 12 генераторов enabled_synthetic, Sidewalks disabled_verified_empty (проверка нуля), Building disabled_zpb, 13 pending_review. Последние две категории не означают окончательно утверждённый состав игры. Модели ZPB развиваются отдельно. Лес — случайные группы, подлесок, валежник, сухостой; не NaturalRows кроме явных посадок. Состояние покрытия и растительность независимы, заброшенная дорога может зарастать. Unknown не превращать в подтверждённое состояние. GM — единственный источник реальных высот. Не заменять штатный GRM самостоятельным генератором.

## 3. Следующий программный блок CC-05Q — только synthetic Worker integration

Использовать `tools/automation/cc02/worker.py` и `test_worker.py` как проверенный Linux baseline, `tools/automation/cc05p/Program.cs`, `JobContract.cs`, `verify_job.py`, `job.abandoned.json` как актуальный native child. Не переписывать с нуля. Новый изолированный companion/версия схемы, без скрытой миграции старого CC02 state.

- Ввести узкий тип задания для фиксированного CC05P synthetic child; никакого произвольного argv/shell, real GIS job, network acquisition или автоматического remote execution.
- Закрепить конкретный SDK/runtime/child/dependency snapshot, config/cache/job hashes, code SHA, scope, expiry, attempts, finite wall/resource limits и approval reference. Политика не заменяет аутентификацию и OS sandbox. При отсутствии обязательной проверки BLOCKED.
- Запускать штатный child в собственном attempt, отдельно stdout/stderr, проверять ровно один RESULT_JSON независимым verifier; атомарно публиковать review-only manifest и PASS только после exit 0 + validation + hashes.
- Проверить реальный bounded child: успех, повторный запуск skip только валидного результата, invalidation при смене входа/бинарника, неверный/пропущенный/подменённый результат, expiry, lock, stop/cancel/timeout, crash/recovery без второго живого child; сохранить прежние успешные попытки. Не убивать чужие процессы, не удалять живой lock. Если часть не реализована или не проверена — честный PARTIAL.
- Отдельно измерить время и доступные ресурсы, не заявлять hard RSS/private/commit bound по sampled RSS. Windows, arbitrary descendants, detached survival и scheduler остаются отдельными gates.

**Stop:** измеренный synthetic native-child Worker integration, с отчётом и следующей точкой. Никакого real output, P:, WRP/PBO, gentb, genwrp, genmod, автоматического TB/Arma, scheduler, merge или Stage promotion. После CC05Q — предложить общий Worker→Sector Manager contract с full-feature scheduling, затем закрывать нужные pending layers, input/asset/geometry gates. CC06 UI отложен до ядра. Не создавать 64 отдельных WRP. Full polygons до final ownership; clip-first FAIL в CC05J (737 vs 738, только 216 common). Halo и независимые секторные швы ещё не решены.

## 4. Восстановление среды

Канонические исходники и sanitized logs — GitHub, архивы пользователя — private Library. Pinned GRM v0.11.1 `2aef2040836daa11a8a368bb0c7f9ecd8f405d65`, BIS `5e406d5021ba19ced8babcadd89ed26119f71f48`, Linux SDK 10.0.404, offline feeds (39 packages в Arma3 closure; см. CC05D). Exact v03 inner config SHA256 `418a6b1db5493c8b9f89f288024a769522f568483a5e614383d934506e7a941e`, modelinfo SHA256 `1177ec6d4618f198bd40f79880d3434ecbd7e0b8414881e23159c3e2a4cd9e94`. Полные имена архивов, paths и hashes — [LIBRARY_INDEX](../LIBRARY_INDEX.md); не публиковать raw ресурсы. Проверить CRC/manifest/locks и извлекать только в scratch. No online restore. Не предполагать сохранность /mnt/data, установленного GRM, SDK или готовых DLL между сессиями. Использовать команды из [CC05P README](../../tools/automation/cc05p/README.md) с фактическими путями и выходной DLL; `DOTNET_PROCESSOR_COUNT=2`. Worker/sector tests — соответствующие README. Не тратить ресурсы на повтор всех CC05B–O probes.

## 5. Независимый локальный поток, когда Cursor/Луна доступен

Не ждать CC05Q для разрешённых локальных read-only/GM действий, но не дублировать cloud код. Current local MAP-003: 1920m, 64×64×30m, pilot EPSG:32636, N51 E030; 3467 valid / 629 NoData, final blocked. B roads PASS for existing bbox only, C building geocatalog PARTIAL (449 records), D TB BLOCKED / NOT RUN. Нужен новый **реальный** полный источник и GM26.2 export с 0 NoData/5 controls, не cloud heightmap. Существующая cell-centered сетка TB и separate proposed GRM node lattice различны на 15m/axis, см. [CC05B](CC05B_RESULT.md); не перезаписывать TB grid, не синтезировать halo. Только при доказанной изоляции — один terrain-only TB import. Локально проверить права/stock CfgPatches/CfgSurfaces/CfgSurfaceCharacters, 22 новых refs, mud/ice/base-world, runtime closure. 163/163 metadata records не ODOL or rights proof. ZPB no generic substitute. No approved production CRS/extent/epoch. Real grading/fit, actual shore/river width/canal, short bridges, disused rails, gates/poles, full IdMap, naturalness/ground contact, all real collision/seams remain pending.

**При смене этапа:** обновить верхний current pointer в AGENT_START, PROJECT_STATE, этот handoff/его преемника, roadmap, ledger и Issue #42; сохранить старые отчёты как историю. Не обозначать новые работы PASS без реальных логов. На 25.11.2026 сделан только документальный handoff после CC05P; CC05Q ещё NOT RUN.
