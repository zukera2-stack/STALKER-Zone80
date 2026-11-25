# VERIFICATION LEDGER — что именно проверено, а что нет

Последний аудит: **2026-11-24**. Доказательство привязано к **конкретной операции, среде и версии**, не ко всему проекту. Новые результаты добавлять с датой и ссылкой, не переписывать исторические сведения.

**Словарь:** `PASS` подтверждено для названного критерия; `PARTIAL` часть; `BLOCKED` безопасно остановлено до проверки; `FAIL` реально не выполнен критерий; `NOT RUN` отсутствует запуск; `HISTORICAL` прошлый достоверный тест, но **не инструкция к повтору**; `SUPERSEDED` прежний подход отменён владельцем. Отчёт из Windows = **reported local evidence**, а не облачное непосредственное исполнение.

## Хронология фактических результатов

| ID | Что и где | Факт и ограничения | Статус / доказательство |
|---|---|---|---|
| E-001 | Foundation репозиторий | Приняты базовые файлы проекта и первичные ограничения | **PASS для документации**, merged PR [#1](https://github.com/zukera2-stack/STALKER-Zone80/pull/1), [#7](https://github.com/zukera2-stack/STALKER-Zone80/pull/7), [#8](https://github.com/zukera2-stack/STALKER-Zone80/pull/8); это не карта |
| E-002 | Исторический GRM incident | Лог `A task may only be disposed if it is in a completion state` во время RawSatelliteImage; ~8.3–8.7GB по отчёту | **CAUSE_UNKNOWN / NOT PROVEN OOM**; `AGENT_START.md`, `BASELINE_FROM_PRIOR_REPORTS.md` |
| E-003 | GIS/GRM синтетические сектора | Предлагались/проверялись форматы ASC/CSV/TML и контрольные сегменты; настоящий игровой импорт синтетики не подтверждён | **Синтетика/архив** [PR #12](https://github.com/zukera2-stack/STALKER-Zone80/pull/12), [#14](https://github.com/zukera2-stack/STALKER-Zone80/pull/14), [Issue #15](https://github.com/zukera2-stack/STALKER-Zone80/issues/15) ещё OPEN (исторический scope) |
| E-004 | TB-DEFAULT / Windows, прежний локальный отчёт | Автономное обнаружение и запуск редактора; журналы/хеши привязаны к конкретному прошлому окну/процессу, не к текущему PID | **PASS в рамках того запуска**, PR #22 и прежние TB-DEFAULT отчёты, не повторять как общий SOAK |
| E-005 | TB-UIA / Windows | Прочитано **203** элемента; `Import terrain...` был обнаружен как доступный `InvokePattern`; нажатие **не** совершалось | **PASS READ-ONLY / INVOKE NOT RUN**, [PR #22](https://github.com/zukera2-stack/STALKER-Zone80/pull/22) |
| E-006 | SOAK-60 / Windows | Реально завершено **50/120** циклов и **5/12** снимков; 55 дочерних diagnostic exit 0; основной runner exit code не сохранился | **PARTIAL, CAUSE_UNKNOWN**, [PR #31](https://github.com/zukera2-stack/STALKER-Zone80/pull/31), [Issue #32](https://github.com/zukera2-stack/STALKER-Zone80/issues/32) |
| E-007 | Recovery + synthetic lifetime / Windows | Восстановлены 50/5; 113 исходных хешей сохранились; синтетический процесс **27m 0.112s, exit 0**, Ctrl+C через реальный терминал не проверялся | **PASS recovery/probe, НЕ SOAK**, [PR #33](https://github.com/zukera2-stack/STALKER-Zone80/pull/33), CI [#45274819788](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45274819788) 75/75; серия SOAK отменена |
| E-008 | MAP-001 / Windows preflight | Определён WGS84 bbox `30.045,51.398,30.070,51.414`; EXE GM26.2 x64 найден, PowerShell синтаксис PASS; Windows curl exit 7 к AWS/Overpass | **AREA/EXE PASS, источники блокированы в том запуске**, [PR #38](https://github.com/zukera2-stack/STALKER-Zone80/pull/38) |
| E-009 | Github-hosted public geodata | В прошлом GitHub Actions получены Copernicus DSM 60×58 и OSM XML 2.51MB, roads 446 way-lines, building footprints 439 way-polygons; 27 unresolved relations | **PASS для старого удалённого acquisition, HISTORICAL**, [run #45360016809](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45360016809), [PR #40](https://github.com/zukera2-stack/STALKER-Zone80/pull/40). **Не новый способ доставки высот по текущему решению** |
| E-010 | MAP-002 / Windows Global Mapper Pro 26.2 | В локальном отчёте **два batch процесса exit 0**; исходный WGS84 ASC 60×58, затем UTM36N `60×62×30м`, 105–136.2558м, **253 NoData**, 3 ASC height samples и GeoTIFF half-pixel tiepoint | **PASS локального GIS экспорта, FAIL как TB-ready 64²**, [PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41), SHA `1eb251f5c48aeb2291f0f6cf7751a75b531ed538`, `map/MAP_001_PROGRESS.md`. Облачный аудитор не повторял Windows |
| E-011 | MAP-002 / локальное 2D preview | `MAP002-Pripyat-preview.svg` с рельефом и 453 SVG-road полилиниями из 446 OSM way, **без зданий** | **PASS как локальное preview по отчёту**, raw SVG не лежит в Git, [PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41) |
| E-012 | Building catalog / локальный | Отдельный GeoJSON: **439 way IDs**, один `building=no`, **27 relations unresolved**; этажность тегом 404/439, подлинность/высота/история не подтверждены | **PARTIAL**, [BUILDING_INVENTORY_REPORT](map/BUILDING_INVENTORY_REPORT.md) |
| E-013 | Облачный GRID-FIRST эксперимент / GitHub Actions | Был получен `64×64×30м` Copernicus-derived ASC+GeoTIFF и 0 NoData; 5 регрессионных тестов PASS | **HISTORICAL PASS СИНТЕТИКИ/УДАЛЁННОЙ ОБРАБОТКИ**, [run #45386386065](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45386386065), [PR #43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) **CLOSED/SUPERSEDED без merge**. **НЕ использовать как готовый raster для текущего MAP-003** |
| E-014 | MAP-003 / Global Mapper Online Data | Нужен N51 E030 и точный квадрат 64²×30м EPSG:32636. Доступность онлайн-слоя, настоящая GM загрузка и новый экспорт **пока не показаны** | **NOT RUN**, [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), [Draft PR #44](https://github.com/zukera2-stack/STALKER-Zone80/pull/44) — только координаты |
| E-015 | Terrain Builder import из пилота | Нет реального отдельно открытого и сохранённого TB-проекта с импортированными высотами; до сих пор только read-only UIA и отчёты | **NOT RUN**; Issue #42 |
| E-016 | Arma 3 / готовый мир 81.92 км | Нет WRP/PBO/RPT с проверенным запуском в игре | **NOT RUN**, Stage 001/PARTIAL |

### Отдельные уровни тестирования (не заменяют друг друга)

| Уровень | Реальное доказательство PASS | Чего этот PASS НЕ доказывает |
|---|---|---|
| T0 docs/CI | валидатор и unit/negative тесты по конкретному SHA, реальные логи GitHub job | запуск GUI, корректную географию, работоспособность Arma |
| T1 источники | идентификатор тайла, license/date, coverage и исходные heights/OSM фактически доступны | точность ground truth, исторические высоты |
| T2 GIS local | GM26.2 процесс/лог/exit + проверенные выходные размеры/NoData/CRS/контрольные точки | соответствие heightmap Terrain Builder, полноценный мир |
| T3 heightmap готов к TB | целевая **квадратная** сетка 64²×30м, origin, 5+ samples, NoData=0, одинаковые ASC/GeoTIFF/CRS | фактический импорт Terrain Builder |
| T4 TB sandbox | один реально открытый/сохранённый безопасно изолированный heightmap, скриншот и метрики | валидный WRP/PBO и игровой FPS |
| T5 Arma runtime | фактический WRP/PBO, in-game RPT/скриншот, measured load/perf | готовность всего региона без отдельной приёмки |

**Правило обновления:** у каждой новой строки указать `ID; local/cloud; exact task/commit; command; version; actual result; source log/sha/screenshot; caveats`. Не переносить статус между платформами, версиями, datasets и новыми сетками по аналогии. Истекший artifact — не живой источник, но его прошлая проверка остаётся архивным фактом.

## Назначено, но пока не проверено: крупная сквозная MAP-003 Issue #42

**Смена масштаба задания 24.11.2026:** вместо очередной точечной проверки принят **один интеграционный локальный pilot**: высоты из GM26 → синхронные дороги/preview → отдельный OSM геокаталог/будущие model families → один sandbox TB height import при безопасности. [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42) дополнена, **это план, не свидетельство исполнения**. Новых E-строк `PASS` за эту работу до Windows отчёта нет. Предыдущие E-010/E-011/E-012 остаются исторически действительными лишь в их собственной области. Сдача одной полной `MAP_003_INTEGRATED_RESULT.md` после реального выполнения; статусы потоков A/B/C/D отдельно.

## Локальное измерение MAP-003

[Единый отчёт](map/MAP_003_INTEGRATED_RESULT.md), 24.11.2026. Global Mapper Pro 26.2 экспортировал диагностический ASC 64×64 / 30 м с 629 NoData, а также UTM дороги с 446 уникальными IDs. Каталог зданий 449 записей остаётся PARTIAL. Terrain Builder не запускался.

## E-017 — офлайн-аудит геокаталога Припяти (24.11.2026)

[PRIPYAT_DIGITAL_GEOCATALOG](map/PRIPYAT_DIGITAL_GEOCATALOG.md). Реально обработан предоставленный владельцем MAP-003 verification ZIP из PR #46. 449 валидных полигонов/мультиполигонов, 0 точных геометрических дублей, 12 пар положительных наложений, 11 выше порога ревью. 135 жилых записей допущены к проверке сходства, 28 групп / 96 записей; 39 одиночных. 446 дорожных ID, 69,863 км суммы длин, 25 компонент геометрического графа. Два прогона дали побайтно одинаковые выходы. **PASS только для офлайн-анализа данного снимка**, не окончательный каталог физических зданий, не маршрутизируемая сеть, не доказательство советских серий. Исходные OSM роли отношений отсутствуют в ZIP. Исторические референсы и типы остаются PARTIAL; GM высоты с полным покрытием BLOCKED, TB NOT RUN. Никаких новых высот или игровых файлов.

## Дополнение 25.11.2026 — актуальные свидетельства (E-018…E-023)
| ID | Среда / операция | Измерение | Статус и источник |
|---|---|---|---|
| E-018 | Offline Python GIS, existing snapshot | 444/449 building records, 427/446 road IDs fully covered; two identical runs | PASS analysis only [coverage](map/MAP_003_COVERAGE_AUDIT.md) |
| E-019 | Offline road/surface audit | 784 contact candidates, 45 malformed tag fields, 45 area polygons; deterministic repeat | PASS static analysis only [roads](map/MAP_003_ROAD_AUDIT.md), [surfaces](map/MAP_003_SURFACE_AUDIT.md) |
| E-020 | Pinned GRM source / in-memory JS | 204 combined references, 23 external; 5+8+10 negative cases reported | PASS reference analysis only [vegetation](map/GRM_VEGETATION_PREFLIGHT.md), [roads/materials](map/GRM_ROADS_MATERIALS_PREFLIGHT.md), [infrastructure](map/GRM_INFRASTRUCTURE_PREFLIGHT.md) |
| E-021 | Owner Windows, read-only inventory | 321/321 a3 loose refs present, 23 external absent loose; 55 color candidates, 54 pairs | PASS existence scan only [inventory](map/GRM_LOCAL_INVENTORY_RESULT.md) |
| E-022 | Owner Studio open/save v02 | 6/7 changed materials restored Surface metadata; all 11 IDs/16 usages preserved | PASS editor roundtrip only [roundtrip](map/GRM_STUDIO_ROUNDTRIP.md) |
| E-023 | Cloud Python v03 transformer | 2 unittest methods PASS, 12 negative subcases; 203 refs, ZIP CRC PASS | PASS bounded transform only [v03 hashes/tests](map/GRM_CONFIG_PREFLIGHT_V03.md); native v03 NOT RUN |
E-014 original online acquisition remains NOT RUN; later local diagnostic export in integrated report has 629 NoData. No final full heightmap, no native generation, no TB import, no game PASS. [Current checkpoint](map/MAP_003_CURRENT_CHECKPOINT.md).

## E-024 — CC-01 Linux synthetic Worker (25.11.2026)
Actual Python 3.13.5 Linux tests: `python -m unittest -v test_worker.py` 9 methods PASS, 14 negative manifest subcases, repeat suite PASS 2.104s. Actual CLI two dependent jobs PASS then two verified skips. Code blobs checked against tested Git blob SHA, artifact hashes and scope in [CC01_RESULT](automation/CC01_RESULT.md). No native tools, Windows, detached survival, full process tree or scheduler tested. CC-02 next; Stage 001 PARTIAL.

## E-025 — CC-02 Linux synthetic failure/recovery (25.11.2026)
Actual Python 3.13.5 Linux, `python -m py_compile worker.py test_worker.py cc01_base.py`; `python -m unittest -v test_worker.py` twice, 13/13 methods in 14.418s / 14.198s, 9 invalid manifest subcases rejected. Actual runner SIGKILL during B, recovery blocked while child holds flock, then explicit recovery preserves A and creates new B attempt. Active child + descendant cancellation, unrelated sentinel alive, concurrent runner, nonzero/missing/wrong output, timeout, low disk and sampled RSS breach, two subprocess checkpoint exits around replace. CLI first a/b PASS, second both verified skip; measured sample peaks 11141120 and 10878976 bytes. [Report](automation/CC02_RESULT.md) / logs and source hashes. PASS only within fixed Linux synthetic scope; no hard tree/cgroup guarantee, Windows or native operation. Stage 001 PARTIAL.

## E-026 — CC-03 logical sector manager (25.11.2026)
Python 3.13.5 Linux stdlib. `python -m py_compile sector_manager.py demo.py test_sector_manager.py`; `python -m unittest -v test_sector_manager.py` twice: 11/11 methods, 0.042s / 0.041s. Demo used five exact base repository blobs (existing foundation generator and validator plus three config files) verified by Git blob IDs: 64 coordinate-only manifests, 112 shared edges, zero seam issues for fixture, boundary anchor S01_00, interior edit dirty S00_00 only, reordered input hash identical. [Report and hashes](automation/CC03_RESULT.md). PASS synthetic planning only; not native seams, real CRS, placement, worker scheduling or Stage promotion.

## E-027 — CC-04 Config Builder review / Asset Manager (25.11.2026)
Linux Python 3.13.5, standard library. `python -m py_compile config_builder.py test_config_builder.py demo.py` PASS; `python -m unittest -v test_config_builder.py` twice 13/13 in 1.380s and 1.430s. Real owner v02/inventory/v03 ZIP SHA matched previous reports, two demo reports byte-identical; counts 203/179/22/2, 0 runtime approval. Separate connector source audit 204 unique reference paths (181 stock candidates, 23 external). [CC04_RESULT](automation/CC04_RESULT.md), source/tests/logs in tools/automation/cc04. PASS review-only, production/native BLOCKED. No native output, GIS generation, placement, Windows validation or stage promotion.
