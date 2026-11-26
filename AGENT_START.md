# ☢️ AGENT_START — единая точка входа STALKER-Zone80

## ЦЕЛЬ И РОЛИ — уточнение владельца 26.11.2026
Готовим **конвейер секторного производства**, а не серию разовых чат-экспортов. ChatGPT — разработчик и проверяющий технологию; Codex/Луна на ПК — исполнитель конечных задач и QC. Global Mapper — высоты и отдельно качественная геопривязанная спутниковая подложка; GameRealisticMap — генерация игровых слоёв по профилям Zone80; Terrain Builder — конечная сборка единого мира. Читать [технологический план и gates](docs/automation/ZONE80_PRODUCTION_PIPELINE.md). Переиспользовать CC02–CC05R, CC06 отложен. Текущий разрешённый MAP-003: v06 geographic diagnostic ASC PASS, v07 полный локальный промежуточный GM raster → UTM QC; источник SRTM не принят для production. Imagery, real GRM layers, two sectors and full queue require respective source/asset/owner gates. Не расширять текущие разрешения; Stage 001 PARTIAL.

## АКТУАЛЬНО — Луна, 26.11.2026: автономный MAP-003
Владелец поручил укрупнить задачу и выполнять её с самопроверкой. **Единственный активный практический маршрут — Issue #42, встроенный Online Data Global Mapper 26.2 → полный рельеф → QC → один безопасный TB terrain-only импорт.** Прочитай [автономный навык](.cursor/skills/zone80-luna-autonomous/SKILL.md) и [профиль GM→TB](.cursor/skills/zone80-map003-gm-tb/SKILL.md), затем [LUNA_HANDOFF](docs/automation/LUNA_HANDOFF.md). Старые указания о внешнем получении тайла и новом Worker/UI/SOAK не исполнять. TB launch PASS по локальному отчёту 26.11; импорт NOT RUN; 629 NoData. Stage 001 PARTIAL. Самостоятельно исправлять безопасные ошибки и проверять результат, не расширяя полномочия. Никаких новых высот вне GM, P:, WRP/PBO, реального GRM placement, merge. 


## АКТУАЛЬНО — после CC-05R (25.11.2026)
**Начни с [RESUME_AFTER_CC05R](docs/automation/RESUME_AFTER_CC05R.md).** Ветка `feat/cc05r-sector-review`, родительский Draft PR #48, измеренный код `7954bd57b9d7ca72404b1841204989f906686459`. CC05R bounded Linux synthetic PASS / overall PARTIAL; 64 review nodes, 112 edges, native fixture only two sectors. Решение владельца: CC06/CC06A DEFERRED до практической проверки на реальной карте. Следующий активный шаг MAP-003, полное покрытие высот в GM26.2. Локальный MAP-003 независим, 629 NoData; Stage 001 PARTIAL. Исторические записи ниже не являются конкурирующими заданиями.

**Для:** Cursor/«Луна», Codex, ChatGPT и любого нового агента.  
**Контрольная точка:** Stage 001 — Foundation / PARTIAL; реальный WRP и запуск Arma 3 не подтверждены.  
**Источник истины:** `main` — только принятый Foundation; **текущая разрешённая работа и её точный SHA находятся в GitHub [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42) и зависимом [Draft PR #47](https://github.com/zukera2-stack/STALKER-Zone80/pull/47)**. Единый навигатор — [`docs/PROJECT_CONTROL.md`](docs/PROJECT_CONTROL.md), реестр результатов — [`docs/VERIFICATION_LEDGER.md`](docs/VERIFICATION_LEDGER.md). Документы аудита находятся в отдельном Draft PR, пока не `main`.  
**Библиотека проектных источников (личная ChatGPT Library):** `/Арма/STALKER-Zone80/`; её структура описана в [docs/LIBRARY_INDEX.md](docs/LIBRARY_INDEX.md).

## Решение владельца 24.11.2026 — переходим от тестов к карте

**Текущий активный шаг — [MAP-003 / Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), эпик — [MAP-001 / Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35).** Владелец прекратил серию TB-UIA/SOAK как самостоятельную работу и разрешил начать реальную карту Припяти: небольшой географически обоснованный участок 1–2 км, рельеф + дороги + отдельный геокаталог контуров зданий (без их размещения), preview и при безопасной изоляции — один пробный импорт в **отдельный пустой** Terrain Builder sandbox. Длинные стресс-тесты, новый SOAK-60 и общие UIA-инвентаризации не проводить без конкретного обнаруженного блокера картографии.

**Последнее решение владельца (24.11.2026): высоты загружает и экспортирует сама локальная Global Mapper 26.2 Pro 64-bit. ChatGPT выдаёт только точные координаты, тайлы и требования к сетке; **не генерировать новые ASC/GeoTIFF через Python/GDAL/GitHub Actions**. Предыдущий [PR #43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) закрыт без merge как отменённый способ. **Основной локальный GIS-инструмент владельца — Global Mapper 26.2 Pro, 64-bit.** Использовать его для DEM/DSM, обрезки участка, проверки CRS, экспорта ASC/GeoTIFF и векторных геоданных (если функции подтверждены именно в 26.2). Старые указания Global Mapper 27 устарели. Установку, лицензию, GUI/Script Builder и фактические операции перепроверить на локальной Windows; не обновлять программу ради задачи. Global Mapper — программа обработки, **не первичный источник** фотографий или геоданных.

**Границы свидетельств:** автономный запуск, read-only UIA 203 элемента и 50/120 циклов подтверждены предыдущими опытами; **60-минутный SOAK не PASS**, первая причина обрыва **CAUSE_UNKNOWN**. Длительная синтетическая 27-минутная проба прошла. Это достаточно для *старта ограниченного картографирования*, но не является доказанной стабильностью финального WRP/Arma 3. **Stage 001 остаётся PARTIAL; Stage 002 формально не повышается.** Не строить весь мир, не утверждать CRS, центр и историческую эпоху без отдельной проверки/одобрения.

**GitHub Issues — обязательный канал задания:** ChatGPT публикует новое задание Cursor/«Луне» непосредственно как GitHub Issue либо дополняет активный Issue; в чате предоставляет ссылку. Прежде чем работать, прочитать текущий Issue, эту инструкцию и `AGENTS.md`; указать base SHA, scope, исходники, ограничения, измеренные результаты и stop conditions. Публикация Issue не отменяет установленные запреты. При недоступности GitHub считать передачу задания блокированной, не требовать ручного переноса длинного текста из чата.

## Дополнение 24.11.2026 — локальный фоновый исполнитель
Владелец запросил подготовку автономной автоматизации. Читать [LUNA_HANDOFF](docs/automation/LUNA_HANDOFF.md), [WORKER_CONTRACT](docs/automation/WORKER_CONTRACT.md), [GRM](.cursor/skills/zone80-grm/SKILL.md), [Worker](.cursor/skills/zone80-worker/SKILL.md), [Sector pipeline](.cursor/skills/zone80-sector-pipeline/SKILL.md). Текущий Draft PR #47 и Issue #42; новый исполнитель ещё не реализован, допустимы синтетические испытания и preflight, реальные операции только по прежним gates. Не регистрировать scheduler/service без отдельного решения. GM-only высоты и Stage 001 PARTIAL неизменны.

## 0. Порядок чтения и приоритет сведений

1. Этот файл `AGENT_START.md` — точка входа; `AGENTS.md` — обязательные ограничения и STOP.
2. [`docs/PROJECT_CONTROL.md`](docs/PROJECT_CONTROL.md) → `docs/PROJECT_STATE.yaml` → `docs/DECISIONS/ADR-0002-owner-pivot-map-and-gm-only.md`: **текущий курс владельца**.
3. **Активная задача:** [Issue #42 / MAP-003](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), `docs/map/MAP_003_GM26_TILES.md`, `docs/GO_NOGO.md`. [Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35) — эпик. `docs/TASK_CURSOR_001.md` — исторический foundation-аудит, не активное задание.
4. `docs/REQUIREMENTS_MATRIX.md`, `docs/VERIFICATION_LEDGER.md`: критерии, **где и когда** тест действительно прошёл.
5. `docs/MASTER_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/ASSET_PROVENANCE.md`, `docs/GIS_PIPELINE.md` — проектная архитектура.
6. `docs/BASELINE_FROM_PRIOR_REPORTS.md` и `docs/research/deep-research-report-2026-11-22.md` — **исторические источники**, не новый тест.

Если документы расходятся, **не исправляй молча**: сравни дату, SHA, результаты измерений, зафиксируй противоречие и запроси решение у владельца/аудитора. Поздний подтверждённый эксперимент важнее старого предположения. Статус из отдельной библиотеки не меняет GitHub автоматически.

## 1. Миссия

Создать **один** мир Arma 3 с географической основой Чернобыльской зоны и игровыми локациями STALKER. Цель: 81 920 × 81 920 м, heightmap 4096² × 20 м, предобработка 8×8 логических секторов по 10 240 м. Это **целевые параметры**, не доказанная работоспособная карта. Нельзя собирать 64 самостоятельных WRP вместо единого мира.

Три независимые сущности: **географические факты → визуальные прокси из разрешённых аддонов → художественный игровой слой**. Footprint реального дома не равен подлинной 3D-модели; положение машин/заборов требует источника или маркируется как процедурное.

## 2. Роли

- **Владелец:** разрешает использование конкретных аддонов, утверждает историческую эпоху, центр/границы карты, локации и переход к следующей стадии.
- **Cursor/Луна:** работает в локальной Windows, запускает программы и тесты, ведёт Git, сдаёт логи/хеши/измерения; оригиналы модов не меняет.
- **ChatGPT/аудитор:** ставит ограниченные задачи, сопоставляет факты, проверяет итоговый отчёт и критерии GO/PARTIAL/NO-GO.
- **Codex:** работает с кодом в отдельной ветке, следует тем же ограничениям; работа в облаке не доказывает локальный запуск Arma или Global Mapper.

## 3. Сначала учти обнаруженное в предыдущих отчётах

Личные отчёты от 21.11.2026 (копии в `/Арма/STALKER-Zone80/03_Отчёты`) указывают:
- ОС при том аудите — **Windows 10 Pro**, не 11 Pro из старого задания; перепроверь на ПК, прежде чем писать новую версию в отчёт.
- Установленная Studio — **GameRealisticMap 0.9**; локальное обновление до 0.11.1 не подтверждено.
- Старые логи показывали ошибку `A task may only be disposed if it is in a completion state` на этапе `RawSatelliteImage` при указанной в логах памяти ~8.3–8.7 ГБ. **Это не доказанный out-of-memory.** Исправление похожей ошибки заявлено в 0.11.1, но маленький повторный тест ещё не выполнялся.
- Полученный раньше `Zona.grma3m` имел тяжёлую конфигурацию: 8192 × 10.875 м, то есть 89 088 м, спутник 1 м/пиксель. Черновик `zone80_proto.grma3m` (512 × 20 м, 4 м/пиксель) существует **только как непроверенный проектный файл**.
- Некоторые предыдущие инструменты не имели полного доступа к WMI/локальной файловой системе; факт неудачной проверки не означает отсутствия установленного ПО.

Это **сведения из сохранённых отчётов**, которые исполнитель должен сопоставить с реальными журналами/файлами. Не пытайся повторно «лечить OOM», не изучив обнаруженный Task-exception.

## Текущий MAP-003 контракт (вместо старого Foundation job)

- **Вход:** одна [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), [таблица координат/тайла](docs/map/MAP_003_GM26_TILES.md), действительный локальный GM26.2. Тайл **N51 E030**, квадрат **64×64×30м EPSG:32636** с `xllcorner 294373.084` и `yllcorner 5698122.108`. Полный CRS мира не утверждён.
- **Действие:** непосредственно в **Global Mapper** выбрать доступный источник высот и экспортировать новый файл; минимум 5 высотных контрольных ячеек и `NoData=0`. Не требовать от владельца вручную делать работу за Луну, если её локальная консоль может выполнить разрешённые действия. Раньше успешно работал локальный batch GMS с `60×62`; это **не** доказательство нового online/64² экспорта.
- **Следующий gate:** только при подтверждении отсутствия риска для пользовательского TB-проекта разрешён один импорт **только высот** в изолированный пустой sandbox; при неуверенности — `BLOCKED`, не запускать повторный SOAK.
- **Отчёт:** [шаблон](docs/AGENT_REPORT_TEMPLATE.md), `PR + Issue`, git SHA, источник/licence, GM версии, реальный log/exit, SHA файлов, высоты/CRS и `PASS/PARTIAL/BLOCKED/NOT RUN` **отдельно** для GIS/TB/Arma. Никаких зданий/3D/WRP/PBO и auto merge.

**Следующая секция — сохранённое историческое задание Foundation, а не чек-лист, который нужно заново выполнить перед MAP-003.**

## 4. Контракт Foundation и специально разрешённого MAP-001

1. Прочитать состояние ветки, `git status` и эту инструкцию; создать отдельную ветку `feat/foundation-audit` от актуального `main` либо продолжить существующую согласованную ветку.
2. Сверить старые отчёты и реальные логи GRM; подтвердить версии ОС, Studio, Arma Tools, Global Mapper **26.2 Pro 64-bit**, .NET, свободное место и исходные файлы.
3. Проверить официальный GRM с закреплённым tag/SHA; без перезаписи установленной версии. Только **малый** контролируемый запуск после фиксации исходников и пути отката.
4. Выполнить безопасный read-only скан выбранного владельцем каталога PBO/P3D; не извлекать/не копировать лицензируемые игровые ресурсы в публичный Git.
5. Протестировать преобразование координат на контрольных точках без утверждения, что EPSG:32636 уже одобрен.
6. Запустить автономные проверки:
   - `python tools/validation/validate_config.py`
   - `python -m unittest discover -s tools/validation -p "test_*.py" -v`
   - `python tools/validation/build_sector_manifests.py --dry-run`
   - `powershell -ExecutionPolicy Bypass -File tools/audit/environment_audit.ps1` (только при понятном локальном пути и доверенном скрипте; предпочти доступный pwsh).
7. Сдать отчёт по шаблону `docs/AGENT_REPORT_TEMPLATE.md`, указать ссылки на GitHub Issues #2–#5.

**Дополнение владельца от 24.11.2026:** разрешён ограниченный реальный пилот MAP-001 по Issue #35: лицензированно допустимые **малые** выборки реальных геоданных, экспорт рельефа/дорог и **отдельный каталог** footprints без размещения строений; один изолированный импорт только рельефа в TB sandbox при доказанной безопасности. Это не разрешение полного мира, Stage 002 GO или изменения оригинальных PBO/P3D/PAA. Не выкачивать крупные данные, не удалять архивы, не принимать лицензии автоматически, не выдавать предварительный GRM-прототип за загруженный в Arma мир.

## 5. Правило завершения

Нужны исходный commit SHA, исполненные команды, версии инструментов, файлы и их хеши, фактические логи и метрики, статусы по каждому критерию. Если доступа к локальному ПК или данным нет, укажи `NOT TESTED` / `PARTIAL`; не выдумывай запуск. **Выполни только разрешённую MAP-003 операцию (Issue #42) до измеренного GIS результата**, затем остановись и предъяви его владельцу; Stage 001/PARTIAL не повышать автоматически.

**Новый агент начинает здесь, а не с генерации всей карты.**


## Cross-project integration
Read [ZONE80–ZPB contract](docs/integration/ZONE80_ZPB_CONTRACT.md) before work on models, catalog bindings, GRM assets or Terrain Builder templates. Example manifest contains reserved candidate only, not a live asset. Current gates unchanged.


## Owner decision — minimal runtime dependencies (2026-11-24)
Read [MINIMAL_DEPENDENCIES](docs/integration/MINIMAL_DEPENDENCIES.md). Base Arma 3 + free Enoch + own project packages only as target. No mandatory external mods/paid DLC; actual compatibility untested. Existing gates unchanged.

## Контрольная точка 25.11.2026 — читать перед продолжением
[MAP_003_CURRENT_CHECKPOINT](docs/map/MAP_003_CURRENT_CHECKPOINT.md) — единый актуальный индекс геокаталога, GRM и фоновой автоматизации. Рабочая ветка Draft PR #47; точный HEAD проверять перед задачей. [v03](docs/map/GRM_CONFIG_PREFLIGHT_V03.md) — editor-only, 179/203 refs covered, 22 stock refs unverified, 2 external ice + external base world; шесть материалов подтверждены сохранением v02 в Studio. Не повторять исходные инвентаризации и ручную настройку. Следующий локальный preflight: новые clutter refs, mud, классы/зависимости, затем gates адаптера GM. A GM diagnostic 629 NoData / D TB BLOCKED, B existing bbox PASS, C PARTIAL. Stage 001 PARTIAL. Все запреты сохраняются.

## План разработки без Луны — 25.11.2026
[Zone80 Control Center / CC-01…07](docs/automation/CONTROL_CENTER_ROADMAP.md) — семиэтапный план автономной разработки программного ядра: Worker → отказоустойчивость → Sector Manager → Config Builder → GM Adapter → Control Center → интеграция с Луной. Следующий программный подэтап CC-01 (синтетика). Это не повышение Stage 001 и не разрешение реальной генерации. Локальный MAP-003 и preflight остаются независимыми; соблюдать WORKER_CONTRACT и все gates. Не считать план выполнением.

## CC-01 checkpoint
Read [CC01_RESULT](docs/automation/CC01_RESULT.md): tested bounded Linux synthetic worker in tools/automation/cc01; next CC-02 fault injection. Windows deliberately blocked; old disabled manifest not executable by this prototype. No actual GIS/native job, no Stage promotion. Existing local MAP-003 gates unchanged.

## CC-02 checkpoint
[CC02_RESULT](docs/automation/CC02_RESULT.md) is the current Worker result: 13 Linux synthetic tests PASS twice; active stop, actual kill/recovery, inherited lock and owned descendant cleanup. CC-01 remains archived; CC-02 has a new synthetic-only schema/root, no automatic state migration. Next CC-03 logical sector manager on synthetic inputs; no production CRS, real heights, native jobs, P: writes, scheduler, merge or stage promotion. Existing local MAP-003 gates unchanged.

## CC-03 checkpoint
[CC03_RESULT](docs/automation/CC03_RESULT.md): tested coordinate-only sector planning in tools/automation/cc03, reuses existing foundation manifests, 64 sectors/112 shared edges, 11 tests PASS twice. Dirty sets only, not executed generation. Next CC-04 Config Builder + Asset Manager; reuse editor v03 evidence, explicit unresolved ice/mud/base/22 refs, no invented approvals or native execution. Stage 001 PARTIAL and GM-only elevation unchanged.

## CC-04 checkpoint
[CC04_RESULT](docs/automation/CC04_RESULT.md): tested six-module review-only GRM Config Builder / Asset Manager, actual v03 input audit and synthetic dependency graph/asset gates. 13 tests PASS twice. 179 inventory-present +22 stock unverified +2 ice; zero runtime-approved, missing mud surface and external base unchanged. No native production output. Next CC-05 read-only GM adapter source review and synthetic fixtures, no RawElevationBuilder/new real heights, native GIS or P: writes. Stage 001 PARTIAL.

## CC-05 checkpoint
[CC05_RESULT](docs/automation/CC05_RESULT.md): 12 synthetic tests PASS twice, actual pinned diagnostic 3467/4096 valid and 629 NoData; 5/5 controls match. GRM source seam identified, but native provider BLOCKED by missing heights, node/center mismatch, mutation and external dependencies. No native patch, no new elevations. Next CC-06 offline Control Center with synthetic integration; separate CC-07 local validation gates. No P: writes, generation or merge; Stage 001 PARTIAL.

## Owner-approved pivot CC-05B
Owner selects direct GM-only elevation injection into GRM; CC-06 UI deferred. Read [CC05B_RESULT](docs/automation/CC05B_RESULT.md) and tools/automation/cc05b/README.md. Python node-compatible input gate tested; C# source candidate NOT compiled or run locally; synthetic-only factory, real context disabled. Next CC-05C compile against pinned GRM net10 and verify native synthetic consumer; no real generation until source/CRS/grid/edge/asset/offline dependency gates. Do not claim recognized upstream source license or distribute modified GRM. Stage 001 PARTIAL, no P: writes, merge or native map output.

## CC-05C environment checkpoint
[CC05C_ENVIRONMENT](docs/automation/CC05C_ENVIRONMENT.md): owner SDK 10.0.404 Linux extracted and dependency-free C# smoke PASS; pinned-name GRM source ZIP CRC PASS. Actual restore blocked by absent NuGet packages / DNS. Collector ZIP delivered to owner; Windows collector NOT RUN. Next verify offline package bundle, restore/build/test actual GRM core and bridge. No native real map run; UI deferred.

## CC-05C measured result
[CC05C_RESULT](docs/automation/CC05C_RESULT.md): owner offline packages received; actual GRM core and existing bridge built, 0 errors/31 upstream warnings, native synthetic smoke PASS twice; 8 Python tests PASS. CC-05D next: missing pinned BIS submodule and Arma3 dependency closure, new collector delivered. Real factory remains disabled; no generation/Stage promotion. CC-06 deferred.

## CC-05D measured result
[CC05D_RESULT](docs/automation/CC05D_RESULT.md): owner 39-package Arma3 bundle verified; pinned native Arma3 assembly compiled offline (0 errors/12 warnings). Original TreesBuilder and TreesGenerator ran on synthetic inline OSM + supplied node grid via GM adapter; 0/1/3 selections, relative Z, repeat and forbidden elevation fallback tests PASS. No real geography/output. Next CC-05E offline input/config/coordinate gates; CC-06 and Vercel deferred. Stage 001 PARTIAL, no P: writes or merge.

## CC-05E measured result and persistent Library
[CC05E_RESULT](docs/automation/CC05E_RESULT.md): actual v03 native parser diagnostic PASS, strict missing metadata refusal, 11 materials/16 usages/10 surfaces/9 roads, 163 unresolved distinct model paths. Four pilot corner checks max absolute UTM residual 0.000933 m, no real grid or placement. Owner toolchain and input archives saved in personal Library [exact locations and SHA256](docs/LIBRARY_INDEX.md); authorized agents retrieve from there, not Git. Next CC-05F reviewed model metadata resolver and per-layer offline source gates, then GM-only complete node-compatible grid. UI deferred; real generation blocked, Stage 001 PARTIAL.

## CC-05F measured result
[CC05F_RESULT](docs/automation/CC05F_RESULT.md): actual owner modelinfo.json saved in Library, 491 records, exact 163/163 v03 P3D metadata coverage, strict native parse PASS twice, missing entry/unknown/changed hash refused. 141 prior loose-file evidence, 22 new clutter paths not inventoried; runtime approval still zero. Next CC-05G per-layer offline dependency closure and synthetic actual-config layer test. GM complete grid and local asset gates still required. No real placement, P: writes or merge; Stage 001 PARTIAL.

## CC-05G measured result
[CC05G_RESULT](docs/automation/CC05G_RESULT.md): actual v03 and owner model cache with native tree layer, seven reviewed native builder types, only elevation preseeded; 26/26 synthetic tree records, +100m Z response, deterministic repeat, unchanged grids, missing dependency refusal. Interior-road clearance FAIL (0m) despite outside-edge 2m PASS. Next CC-05H synthetic post-placement collision validation, no silent relocation; additional forest dependency review. Real GM/OSM/asset gates unchanged. Stage 001 PARTIAL.

## CC-05H owner policy and measured result
Read [VEGETATION_SUCCESSION_POLICY](docs/map/VEGETATION_SUCCESSION_POLICY.md) and [CC05H_RESULT](docs/automation/CC05H_RESULT.md). Owner-approved separate state overlay replaces blanket road exclusion. Synthetic rectangular policy and unchanged native TreesGenerator PASS twice with actual v03/cache: abandoned road retains observed anchor, operational excludes, unknown review; 6/5/5 records. Stock 2m anchor displacement preserved as evidence. No upstream source changes. Next CC-05I native forest closure and synthetic test, then policy polygon/sector integration. Real gates unchanged. Stage 001 PARTIAL.

## CC-05I measured result
[CC05I_RESULT](docs/automation/CC05I_RESULT.md): stock ForestBuilder blocked at ElevationWithLakesData; bounded geometry-only adapter uses actual OSM interpretation and native geometry, original ForestGenerator unchanged. Synthetic forest 2829/2769 records, 46 models, 50/0 on-road for abandoned/protected state, 0 lake/cutline, 3/5 final review points; +100m Z and repeat PASS. Next CC-05J forest edge/radial and scrub closure, polygon policy and final point/seam checks. No real generation, Stage 001 PARTIAL.

## CC-05J measured result
[CC05J_RESULT](docs/automation/CC05J_RESULT.md): all five native vegetation generators exercised on multi-polygon synthetic input; 1616/1692 records, 41/0 on-road, 21/33 final review. Native ForestEdgeBuilder safe on supplied forest geometry; scrub/radial stock builders refused lake elevation dependency. Full-polygon generation then half-open ownership reconciled; clip-first differs (737 vs 738, 216 common). Do not clip natural features before generation assuming equivalence. Next proposed CC-05K native road/rail/infrastructure dependency review and bounded synthetic road layer, GM-only. Cross-layer/halo/general geometry pending. No real generation, Stage 001 PARTIAL.

## Требование к лесу
Владелец требует естественный лес без искусственной рядности, подлесок, валежник и сухостой. [Политика и проверка исходников](docs/map/VEGETATION_SUCCESSION_POLICY.md#требования-владельца-к-естественному-лесу--25112026). Штатный GRM Forest + ForestAdditional в приоритете. Фактический состав, естественность, посадка валежника и визуальная приёмка ещё не доказаны. Следующий CC-05K не изменён.

## CC-05K measured result
[CC05K_RESULT](docs/automation/CC05K_RESULT.md): native RoadsBuilder/RailwaysBuilder, memory-only RoadsCompiler/reader, BridgeGenerator and RailwayGenerator PASS bounded synthetic. 3 roads/2 non-bridge shape records, 9 profiles, 4 rail segments, 4 bridge and 9 rail model records, +100m Z and repeat PASS. Short isolated bridge omitted and disused rail treated as normal; preserve source/state, review before production. No grade/physical fit or runtime proof. Next proposed CC-05L hydrography and surface dependencies, GM-only. No real generation; Stage 001 PARTIAL.

## CC-05L measured result
[CC05L_RESULT](docs/automation/CC05L_RESULT.md): native lakes/watercourses/sand and WatercourseGenerator PASS bounded, 13 records, +100m Z and repeat. Native polygon draw helper produced memory-only 480x480 mask, 16 usage/11 material mapping PASS; full IdMapRender NOT RUN due to ElevationWithLakesData, radial actually refused. River width fixed, canal omitted, StreamTunnel flag false, lake inset clips edge. Next proposed CC-05M GM-only surface geometry contract and priority graph tests. Stage 001 PARTIAL, no real generation.

## CC-05M measured result
[CC05M_RESULT](docs/automation/CC05M_RESULT.md): explicit bounded 18-slot surface plan using native drawing/coordinate helpers, 16 usage mappings, 11 material IDs, 15 visible slots/9 colors, 17 semantic controls and exact all-pixel mapping; two identical runs and unchanged grid. Native AsphaltBuilder excludes forest; candidate retains asphalt under vegetation (2800 pixels changed). Full stock IdMap NOT RUN, Grass/Forest blocked at lake elevation dependency, coast/ice absent in fixture. Next proposed CC-05N remaining native infrastructure placement, then common contracts. Stage 001 PARTIAL, no real generation.

## CC-05N measured result
[CC05N_RESULT](docs/automation/CC05N_RESULT.md): native fences, explicit oriented objects, explicit tree row, disabled sidewalks PASS bounded; 55/5/8/0 = 68 records, +100m Z/repeat, unchanged grid. All nine road profiles disable procedural lamps/sidewalks, explicit lamp survives. Retaining wall/gate/power pole omitted, postbox unconfigured, one fence point on road. No physical or full catalog approval. Next proposed CC-05O common synthetic pipeline and provenance/review contracts. Stage 001 PARTIAL, no real generation.

## CC-05O measured result
[CC05O_RESULT](docs/automation/CC05O_RESULT.md): one shared native context, 13/27 generator instances, memory road roundtrip and bounded surface mask. 1015/1062 records, 21/14 held, 31/0 point-pass road plants, source-tree unknown review separate. +100m Z and identical repeated runs PASS; 530 GRM files unchanged. 14 catalog layers NOT RUN, no generic building or physical proof. Next proposed CC-05P catalog disposition, fail-closed shared job/input and manifest contract, then worker/sector integration. No real generation; Stage 001 PARTIAL.

## CC-05P measured result
[CC05P_RESULT](docs/automation/CC05P_RESULT.md): closed synthetic job and explicit 27-name catalog policy, 12 enabled, 2 disabled (sidewalk zero check, ZPB building), 13 pending. Two identical verification suites (5 native jobs, 20 input refusals and 6 result refusals each); stable logical IDs and height-sensitive content hashes, unknown state distinct. Explicit incomplete per-model lineage. No Worker integration or durable publication. Next proposed CC-05Q guarded synthetic native child integration with CC02 Worker, pinned executables, finite approval/attempts, validation and recovery. Stage 001 PARTIAL, no real generation.
