# Project audit — STALKER-Zone80, 2026-11-24

**Аудитор:** ChatGPT на основании **живого состояния GitHub** (PR, Issues, исходники, документы и отдельные Actions runs). Не имел доступа к работающему Windows/Terrain Builder и не запускал локальный Global Mapper. Поэтому все локальные цифры помечаются как *опубликованный Windows-отчёт*, не переизмеряются по памяти.

**Проверенная база:** [Draft PR #44](https://github.com/zukera2-stack/STALKER-Zone80/pull/44), HEAD `36aab2ce3462f02a9e18597facd05f7a3125eca4` (она включает стек map PR #36 → #37 → #38 → #40 → #41 → #44); стабильная `main` имеет merged PR #1, #7, #8. Дополнительно просмотрены Issue #5/#6/#15/#35/#39/#42, [#43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) closed/superseded, [CI #45391108532](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45391108532) SUCCESS на HEAD #44. **Только документы** этого аудита находятся в новом зависимом Draft PR — не `main`.

## Результат аудита по направлениям

| Контур | Достигнуто | Не достигнуто |
|---|---|---|
| Организация GitHub | Репозиторий, CI foundation, проектные инструкции/PR, Issue-first, много репродуцируемых экспериментов | Нет единой давно принятой актуальной документации в main, отсутствовала единая матрица требований/фактов |
| TB-DEFAULT, UIA | Исторически запущен TB, прочитаны ~203 UIA элементов, диагностика потомка Windows Job успешна | `Import terrain...` только обнаружен, не Invoke; **реальный TB heightmap ещё не импортирован** |
| TB SOAK/recovery | 50/120 real cycles, 5/12 UIA; 55 child exit 0; immutable 113 files; synthetic 27min PASS; 75 CI тестов по PR #33 | **60min SOAK не PASS; CAUSE_UNKNOWN**; отказались от дальнейшего stress-тестирования по решению владельца |
| DEM/GIS | Источник Copernicus идентифицирован; реальный локальный **GM Pro 26.2 batch exit 0**; ASC/GeoTIFF EPSG:32636 `60×62×30м`, 3 точки; SVG preview дорог | Старый output имеет **253 NoData** и не квадратный для целевого TB пилота; **последняя** `GM Online Data → 64²` операция **NOT RUN** |
| Дороги / здания | OSM 446 way-lines, SVG 453 line segments; GeoJSON 439 way-poly, source IDs, частично теги/площади | 27 unresolved relations, `building=no`, историческое соответствие/полнота непроверены; **нет 3D и не планировать на этом этапе** |
| Сетка / CRS | Для пилота заданы `64×64×30м EPSG:32636`, XLL/YLL, 4 WGS84 угла, tile `N51 E030` | Производственный CRS всего 81.92 км мира, поля высот из GM Online, TB local XY не утверждены |
| Игра Arma 3 | Архитектурное требование одного будущего WRP, 8×8 preprocessing | **Ни одной подтверждённой игровой сборки или загрузки карты** |

## Критические противоречия (и решение)

| № | Противоречие | Где проявилось | Как устранено в данном документационном PR |
|---|---|---|---|
| C-01 | `main` объявлялся «истиной об актуальном коде», но последние GIS результаты только в зависимых Draft PR | `AGENT_START.md`, PR #36–#44 | Отделить **stable main** от **current authorized work in Issue #42 / branch PR #44**, указать порядок доверия |
| C-02 | В `PROJECT_STATE.yaml` сказано `global_mapper_local_install_verified=false`, `gm26_gms_windows_runtime_verified=false`, `real_pripyat_pilot=NOT STARTED`; PR #41 утверждает два batch exit 0 | `PROJECT_STATE.yaml` vs `map/MAP_001_PROGRESS.md` | Изменить state с делением **старый реальный GM batch PASS**, **новая онлайн-выгрузка GM NOT RUN** |
| C-03 | MAP-002 report начинается с `PARTIAL` и «batch BLOCKED», далее append задокументировал успешный повтор | `map/MAP_001_PROGRESS.md` | Добавить **хронологический верхний блок**: прежний отказ остаётся историей, поздний batch PASS |
| C-04 | `MAP_001_AREA` и `SOURCE_HANDOFF` говорят «исходники не получены» / «GM NOT RUN» после более поздних фактов | архивные MAP-001 docs | Добавить датированную ссылку на evidence ledger, не стирать старые условия/хеши |
| C-05 | `GM 27` всё ещё требуется старой открытой Issue #5 и `TASK_CURSOR_001_GM_ENV` | legacy foundation | Пометить superseded GM 27, заменить **только актуальное задание**; Issue #5 сохранить как вопрос full-world CRS, но убрать его зависимость от v27 либо пометить исторической |
| C-06 | Старое `HANDOFF` предлагает `TASK_CURSOR_001` и «audit first, no map» | `HANDOFF.md`, README, `AGENT_START.md` foundation block | Переделать маршрутизацию на **Issue #42, PROJECT_CONTROL**, старую задачу — только архив |
| C-07 | Много отдельных обязательных тестовых задач вместо создания рельефа; старый Issue #15 требует synthetic TB | Issue #15, TB-UIA ветки, #34 closed | Не возобновлять. Текущее разрешение — **не** synthetic placement, а один terrain-only из GM в отдельный TB sandbox |
| C-08 | Шаблон отчёта почти целиком о RawSatelliteImage/OOM вместо текущего GIS | `AGENT_REPORT_TEMPLATE.md` | Создать общий task/gate/actual-observation шаблон с GM/TB acceptance и источниками доказательств |
| C-09 | GRID-FIRST формулировался как обязанность генерировать высоты через GitHub Actions, позже отменено владельцем | [PR #43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) (closed), [PR #44](https://github.com/zukera2-stack/STALKER-Zone80/pull/44) | Закрепить **последнее решение**: ChatGPT координаты/тайл; **GM26 на Windows получает и экспортирует** высоты. CI/GDAL результат остаётся историческим, не используется как текущая высота |
| C-10 | Промежуточная сетка `60×62` выдавалась за почти готовую TB карту | PR #41 / Issue #42 до уточнения | Разделить реальные локальные GIS exports от настоящей 64² heightmap и факта TB-импорта |
| C-11 | Stage 002 план обещает размещение зданий; владелец прямо запретил их на текущем этапе | `MASTER_PLAN.md`, Issue #6 | Здание только геокаталог/будущий отдельный мод; Stage 002 по-прежнему BLOCKED и требует нового явного решения |
| C-12 | Слова `PASS`, `GO`, `NOT RUN` не сопровождались ссылкой на оригинальный run/platform SHA | разрозненные отчёты | `VERIFICATION_LEDGER.md` и `REQUIREMENTS_MATRIX.md` с привязкой каждого Gate |
| C-13 | Некоторые Markdown содержали буквальные символы `\\n` вместо переводов строк | README и `AGENTS.md` | Убрать синтаксический мусор без изменения смысловых ограничений |
| C-14 | Исторический спор Windows 11 host vs Windows 10 runner | README, `AGENT_START.md` | Не выдавать единую OS без актуального локального `systeminfo` и контекста host/VM; фиксировать конкретный исполнитель и версию ОС в каждом отчёте |

## Как устроены ветки (НЕ делать самостоятельный merge)

- **Stable `main`:** merged PR #1, #7, #8 — базовая структура.
- **Картография (зависимый Draft stack):** PR [#36](https://github.com/zukera2-stack/STALKER-Zone80/pull/36) → [#37](https://github.com/zukera2-stack/STALKER-Zone80/pull/37) → [#38](https://github.com/zukera2-stack/STALKER-Zone80/pull/38) → [#40](https://github.com/zukera2-stack/STALKER-Zone80/pull/40) → [#41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41) → [#44](https://github.com/zukera2-stack/STALKER-Zone80/pull/44). **В ветке #44 есть предки, но ничего из цепочки не слито в main.**
- **Прежняя облачная генерация:** [#43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) closed **without merge**, больше не активна.
- **TB/diagnostics Draft stack:** [#22](https://github.com/zukera2-stack/STALKER-Zone80/pull/22) → #25 → #27 → #29 → #31 → #33, а также другие исторические PR #16–#20. Устаревшие задачи Soak были закрыты, **PR оставлены как evidence**, не рекомендовано объединение их цепочки автоматически.
- **Синтетика/экспорт:** PR #12/#14 + Issue #15; требуется новый владелецкий приоритет для продолжения.
- **Неустранённая структурная проблема:** открытых Draft/legacy PR много, и из-за дерева зависимостей автоматическая массовая интеграция может затронуть исторические инструменты. Нужен отдельный точечный план merge **только после** приёмки документации, с обзором файлов/diff; сейчас **не merge**.

## Риски с приоритетом

| Приоритет | Риск | Мера |
|---|---|---|
| P0 | Агент выполнит старую Issue/GM27/облачный генератор вместо текущей MAP-003 | `PROJECT_CONTROL` + активная Issue #42 + датированный ADR-0002, запрет silent task switching |
| P0 | Высотный `60×62` с `-9999` будет импортирован как корректная карта | Точная grid-first 64² конфигурация + NoData=0 и контроль 5 точек перед TB |
| P0 | Повреждение несохранённого проекта TB или исходных модов | Только независимый project-owned sandbox, stop on uncertainty; immutable assets, никаких P: |
| P1 | Термины GM/CI/TB/Arma PASS смешаются | `VERIFICATION_LEDGER` + тестовые уровни T0–T5, evidence на SHA |
| P1 | OSM содержимое будет трактоваться как исторические здания/город | Каталог с confidence/valid_time и ODbL, никаких 3D/placements сейчас |
| P1 | Решение по whole-world CRS будет основано на маленькой пилотной зоне | CRS для пилота vs производственного мира разделены |
| P2 | Истёкший GitHub artifact станет «потерянным исходником» | Исторический SHA/log сохранить как факт, новый source только через Global Mapper по решению владельца |
| P2 | Задания разрастаются быстрее готовых элементов карты | Один активный исполняемый Issue, отчёт и проверка прежде следующего |

## Реалистичный ближайший результат

**Исключительно [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42):** Cursor/Луна открывает установленный GM26.2, выбирает реально доступный DEM по тайлу **N51 E030**, выставляет **64×64×30м, UTM36N**, экспортирует высоты локально, сверяет 5 контрольных точек/NoData/CRS/hash. Если можно безопасно — импортирует **только рельеф** в отдельный TB sandbox, сохраняет снимок и проект. Если нельзя — `BLOCKED` только для TB, но GIS результат не теряется. **Не** проверять снова часовой SOAK, не импортировать здания и не выполнять Stage 002.

Приёмка аудита ограничена **документацией и доказательствами GitHub**: не принимать её за новый запуск программ на Windows, финальный выбор CRS, собранный WRP или работающую Arma 3 карту.
