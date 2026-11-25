# REQUIREMENTS MATRIX — проверяемые требования STALKER-Zone80

Актуализация 2026-11-24. **Требование не равно результату.** Значения `PASS` означают, что именно указанный критерий доказан конкретным свидетельством. Статусы `PARTIAL`, `BLOCKED`, `NOT RUN`, `DEFERRED` не дают права объявить весь Stage `GO`.

## Обязательные инварианты владельца

| ID | Требование | Приёмочный критерий / доказательство | Статус | Откуда |
|---|---|---|---|---|
| REQ-001 | **Один** будущий мир Arma 3 размером 81 920 × 81 920 м | Один загружаемый WRP на движке, а не 64 отдельных | **TARGET / NOT RUN** | [ADR-0001](DECISIONS/ADR-0001-staged-single-world.md), `MASTER_PLAN.md` |
| REQ-002 | 4096² × 20м высотная сетка полного мира; 8×8 логических секторов | Реальный, проверенный engine load + границы/стыки, измеренная память | **TARGET / NOT RUN** | `MASTER_PLAN.md` |
| REQ-003 | Stage 001 остаётся PARTIAL; Stage 002 — только с разрешения владельца | Явное решение владельца и закрытые требования Stage gate | **ENFORCED** | [GO_NOGO](GO_NOGO.md), [Issue #6](https://github.com/zukera2-stack/STALKER-Zone80/issues/6) |
| REQ-004 | Не менять оригинальные игровые ресурсы, P:, моды, лицензируемые геоданные | Публикуемый diff без PBO/P3D/PAA/закрытых данных; локальный immutable input | **ONGOING** | `AGENTS.md`, `ASSET_PROVENANCE.md` |
| REQ-005 | Рабочие задачи Cursor/Луны выдавать в GitHub Issue, без ручного копирования из чата | Для каждого шага есть Issue, branch/base SHA, деливерабл, stop conditions | **ONGOING**, текущая [#42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42) | Решение владельца, [PR #24](https://github.com/zukera2-stack/STALKER-Zone80/pull/24) (Draft) |
| REQ-006 | Не проводить бесконечные общие TB SOAK/UIA проверки | По умолчанию тесты отменены; узкая проверка лишь для конкретного картографического блокера | **ENFORCED**, 60-мин SOAK не PASS | [#32](https://github.com/zukera2-stack/STALKER-Zone80/issues/32), [#34](https://github.com/zukera2-stack/STALKER-Zone80/issues/34) |

## Реальный пилот Припяти: разрешённое и недоказанное

| ID | Требование | Конкретная проверка | Статус/ограничение | Ответственный / источник |
|---|---|---|---|---|
| REQ-101 | Географически определённая область Припяти | Исходный bbox WGS84 `[30.045, 51.398, 30.070, 51.414]`; Энергетик внутри | **PASS как кандидат**, эпоха/каноническая full-world extent не утверждены | [MAP_001_AREA](map/MAP_001_AREA.md), PR #38 |
| REQ-102 | Локальный **Global Mapper 26.2 Pro x64** — основной инструмент | Версия EXE, журнал и реальный batch exit 0 | **PASS для старого GM26 GIS batch**; текущий online DEM workflow — **NOT RUN** | [PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41) |
| REQ-103 | ChatGPT сообщает **координаты и правильные тайлы**, не делает новые высоты через GitHub/Python | Луна получает высоты из GM26 Online Data или разрешённого источника, запущенного **в GM** | **ACTIVE POLICY / NOT RUN для MAP-003** | [ADR-0002](DECISIONS/ADR-0002-owner-pivot-map-and-gm-only.md), [#42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42) |
| REQ-104 | Для пилота выбрать **N51 E030** | Указан tile Copernicus `Copernicus_DSM_COG_10_N51_00_E030_00_DEM`; SRTM `N51E030` только как альтернативный источник | **PASS как идентификатор тайла**, доступность встроенного слоя GM **NOT TESTED** | [MAP_003_GM26_TILES](map/MAP_003_GM26_TILES.md) |
| REQ-105 | Сначала **фиксировать целевую сетку**, потом экспортировать высоты | UTM36N EPSG:32636, 64×64, cell 30м, XLL 294373.084, YLL 5698122.108 | **ЗАДАНО / NOT RUN в GM**, это пилот, не production CRS | [MAP_003_GM26_TILES](map/MAP_003_GM26_TILES.md) |
| REQ-106 | Проверить полученный из GM ASC | `ncols=64, nrows=64, cellsize=30m, 0 real NoData`, правильные углы, 5 height samples, GeoTIFF/ASC matching, min/max, SHA, source/license, лог | **NOT RUN для нового MAP-003**; исторический 60×62 не отвечает критерию | Issue #42 |
| REQ-107 | Terrain Builder — **один** высотный импорт в собственный пустой sandbox, без затрагивания работы владельца | Сохранённая отдельно карта/скриншот, точная метрика/offset, контроль минимум 5 точек, доказана изоляция | **NOT RUN**; если нет изоляции — `BLOCKED` без попытки | Issue #42 |
| REQ-108 | Дороги сохраняются отдельно от зданий | Реальные OSM `highway` линии, классификация `footway/path/pedestrian/steps` vs дороги, 2D preview | **PARTIAL**, preview локально по отчёту, не размещено в TB | [PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41) |
| REQ-109 | Постройки — **только геокаталог**, никаких 3D и размещения | Полигональные геоданные с source_id, достоверностью и лицензией; никакого CSV/TML object placement | **PARTIAL**: 439 way-полигонов, 27 unresolved relations, `building=no` нельзя считать зданием | [BUILDING_INVENTORY_REPORT](map/BUILDING_INVENTORY_REPORT.md) |
| REQ-110 | Фото/360 как справочник для будущего мода | Проверенные URL/авторы/лицензии/соответствие зданию; Google 360 — только ссылки, не скриншоты | **PARTIAL** (фото «Энергетика»); Google 360 **NOT TESTED** | [BUILDING_INVENTORY_SCHEMA](map/BUILDING_INVENTORY_SCHEMA.md) |
| REQ-111 | Право на источники и семантическая достоверность | Источник, snapshot UTC, license, SHA, CRS, горизонтальные/вертикальные единицы, DSM≠DTM, историческое время | **PARTIAL**, исходный OSM/Copernicus документирован, историчность/ground truth не доказаны | [MAP_001_SOURCE_HANDOFF](map/MAP_001_SOURCE_HANDOFF.md) |
| REQ-112 | Production CRS, точная область и история только после измерения/решения | Масштабные и round-trip residuals на всех краях **81.92км** и решение владельца | **NOT RUN / NOT APPROVED** | [Issue #5](https://github.com/zukera2-stack/STALKER-Zone80/issues/5) (старая версия GM27 в тексте), `GIS_PIPELINE.md` |
| REQ-113 | Реальный TB/Arma build | Проверенный исходный объект/heightmap, формат WRP, игровой RPT/скриншот | **NOT RUN**, никакого GO для Stage 002/003/007 | `GO_NOGO.md` |

### Не смешивать объекты проверки

- `GITHUB CI PASS` — код/формат/синтетика **только в CI**.
- `WINDOWS GM PASS` — факт конкретного процесса GM, конкретных файлов и их SHA.
- `GIS HEIGHTMAP PASS` — доказана **именно целевая** сетка, высоты и NoData, горизонтальный/вертикальный CRS.
- `TB IMPORT PASS` — только фактически открытый и сохранённый отдельный TB-проект.
- `ARMA PLAYABLE PASS` — реальная игровая загрузка; **ещё ни разу не доказана**.

Параметры `64×64×30м` и `EPSG:32636` относятся к **пилоту**, а `4096²×20м` — к **целевому миру**; не смешивать их. Все операции над зданиями/системой объектов **отложены** по решению владельца.

## Порядок изменения требования

Обнаружив новое требование, обновить **этот ID**, ссылку на решение и критерий приёмки, затем обновить `PROJECT_STATE.yaml`, текущую Issue и доказательство в `VERIFICATION_LEDGER.md`. Новую Issue заводить только для новой самостоятельной работы; уточнения существующей Issue дописывать туда. Не переписывать исторический лог.

## Интеграционный тест MAP-003 (уточнение владельца: максимальное укрупнение)

**Одна [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42)**, один полный локальный прогон, **один сводный отчёт и один Draft PR**. Никаких новых тестовых Issues после каждого этапа. Результат — совместная проверка уже определённых `REQ-102…REQ-111`, **без** повышения Stage и без WRP/PBO/размещения объектов:

| Поток | Принятые REQ | Финальный артефакт | До нового выполнения |
|---|---|---|---|
| A GM heights | REQ-102..107 | GM-made 64×64 ASC/GeoTIFF, 0 NoData, 5+ точек, SHA, source/datum | NOT RUN |
| B road GIS | REQ-108,111 | Совмещённые метры/оси векторов и наглядное preview, OSM IDs | HISTORICAL PARTIAL; новый интегрированный результат NOT RUN |
| C separate buildings | REQ-109..111 | Геокаталог с relation reconciliation/unknowns + `BUILDING_MODEL_NEEDS.md` без моделей | HISTORICAL PARTIAL; новый интегрированный результат NOT RUN |
| D TB sandbox | REQ-107,113 | Один безопасный реальный сохранённый heightmap TB sandbox + screenshot; иначе BLOCKED | NOT RUN |

**Автономность:** конкретную безопасную ошибку исправлять в рамках того же Issue; не блокировать независимые B/C из-за A/D. Новые Python/GDAL-generated heights, TB-UIA/SOAK, строения, WRP/PBO запрещены.

## MAP-003 — актуализация приёмки

[Фактический локальный отчёт](map/MAP_003_INTEGRATED_RESULT.md): A BLOCKED (629 NoData), B PASS в пределах исходной выборки, C PARTIAL (449 записей), D BLOCKED (неполная сетка). Stage 001 / PARTIAL.

## GRM / automation acceptance — 25.11.2026
| Requirement | Acceptance | Current status |
|---|---|---|
| GRM-01 minimal runtime deps | Actual CfgPatches and transitive resource closure, no paid entitlement dependency, clean game test | PARTIAL: policy and loose scan, engine NOT RUN |
| GRM-02 surface compiler | All 16 usages exactly once, stable RGB IDs, known textures/surfaces, no silent fallbacks | PARTIAL: six restored v02 surfaces, v03 mud pending |
| GRM-03 base/ice | Verified base-world class and patch; explicit ice policy/approved replacement | BLOCKED |
| GRM-04 native generator | GM-authoritative elevation adapter, dependency graph, bounded authorized layer with evidence | BLOCKED / NOT RUN |
| GRM-05 worker | Synthetic lock/stop/resume/crash/resource tests, then separately approved native/background checks | PASS bounded Linux native synthetic CC05Q ([evidence](automation/CC05Q_NATIVE_RESULT.md)); PARTIAL overall, Windows/background/hard limits NOT RUN |
| GRM-06 ZPB | Verified manifest IDs, P3D paths, CfgPatches, anchor/heading and no duplication | Contract only; actual assets/placement NOT RUN |
Evidence: [checkpoint](map/MAP_003_CURRENT_CHECKPOINT.md), [v03](map/GRM_CONFIG_PREFLIGHT_V03.md), [worker](automation/WORKER_CONTRACT.md), [ZPB](integration/ZONE80_ZPB_CONTRACT.md). Existing REQ-106/107 still BLOCKED at 629 NoData; no stage promotion.
