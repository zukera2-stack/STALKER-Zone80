# ☢️ AGENT_START — единая точка входа STALKER-Zone80

**Для:** Cursor/«Луна», Codex, ChatGPT и любого нового агента.  
**Контрольная точка:** Stage 001 — Foundation / PARTIAL; реальный WRP и запуск Arma 3 не подтверждены.  
**Источник истины:** `main` — только принятый Foundation; **текущая разрешённая работа и её точный SHA находятся в GitHub [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42) и зависимом [Draft PR #44](https://github.com/zukera2-stack/STALKER-Zone80/pull/44)**. Единый навигатор — [`docs/PROJECT_CONTROL.md`](docs/PROJECT_CONTROL.md), реестр результатов — [`docs/VERIFICATION_LEDGER.md`](docs/VERIFICATION_LEDGER.md). Документы аудита находятся в отдельном Draft PR, пока не `main`.  
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
