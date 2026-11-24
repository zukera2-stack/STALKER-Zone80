# Agent handoff — один Issue → один результат → один аудит

**Владелец** разрешает действия, source/asset licensing, исторический канон и переход стадий. **ChatGPT** выдаёт в GitHub только конкретные координаты/тайл/приёмку и проверяет доказательства. **Cursor/Луна** действительно выполняет локальные операции на Windows и сдаёт воспроизводимое evidence. У ChatGPT нет автоматического доступа к этому ПК.

**Старт:** `AGENT_START.md` → `AGENTS.md` → [`PROJECT_CONTROL.md`](PROJECT_CONTROL.md) → [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml) → **[Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42)** → [`map/MAP_003_GM26_TILES.md`](map/MAP_003_GM26_TILES.md). Issue #35 — эпик. `TASK_CURSOR_001.md` — исторический foundation, **не текущее поручение**.

## Протокол назначения задачи

В каждой новой Issue/корректировке старой обязательно:
1. **Контекст:** одна цель, owner directive/ADR, точный базовый SHA/ref и связанный PR; явно указать, находится ли код в Draft, а не в `main`.
2. **Вход:** точный tile, bbox, EPSG/units, сетка, источник, snapshot/license, существующие файлы/hashes (либо явное `NOT PROVIDED`).
3. **Действия:** только разрешённые инструменты/настоящие команды; для высот **только локальный Global Mapper 26.2 Pro**; для зданий только отдельный GIS-инвентарь.
4. **Один измеримый результат:** имя/путь собственного выходного файла, формат, критерии полноты, точность координат, образцы, лог, exit, скриншот/хеш.
5. **Стоп-условия:** лицензия/NoData/CRS, несохранённый пользовательский TB проект, чужие процессы, отсутствие безопасной изоляции, системные привилегии — **STOP**, никаких незапрошенных обходов.
6. **Приёмка:** по [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md), [`VERIFICATION_LEDGER.md`](VERIFICATION_LEDGER.md) и [`GO_NOGO.md`](GO_NOGO.md); без auto-merge и самовольного Stage GO.

## После выполнения

Локальная Луна добавляет комментарий к **той же Issue** со ссылкой на Draft PR/commit/отчёт:
- `UTC time; Windows context; actual GM/TB version; exact executed commands`, а не примерные команды;
- `source/license/date/size; file SHA256; geometry/NoData`; источник `Copernicus DSM` не равен bare-earth/1986;
- каждый Gate **`PASS/PARTIAL/BLOCKED/FAIL/NOT RUN`** отдельно — **CI**, **GM**, **GIS heightmap**, **TB**, **Arma**;
- где фактические логи/артефакты и что **НЕ** выполнялось. Исходные GIS/OSM/P3D/PBO/приватные пути не публиковать;
- при ошибке — конкретный первый безопасный STOP и **один** минимальный следующий шаг, не повторять SOAK или массовые тесты автоматически.

ChatGPT сопоставляет с отчётом и SHA, обновляет `PROJECT_STATE.yaml`, `VERIFICATION_LEDGER.md` и `REQUIREMENTS_MATRIX.md` **только если есть новый реальный факт**. Приёмка одной операции **не** означает приёмку следующей (например, ASC ≠ TB ≠ WRP ≠ in-game).

## Пример применительно к текущему MAP-003

Вход `N51E030`, `EPSG:32636`, 64×64×30м, XLL 294373.084, YLL 5698122.108. Выход — **реально локально экспортированный Global Mapper** ASC с 0 NoData и пятью подтверждёнными ячейками, source/layer/GMS/GM log/SHA. Второй, **необязательный** gate — один terrain-only TB импорт в отдельном пустом проекте, если доказана безопасность. Никаких зданий/3D, Python/CI heightmap генерации, пользовательского рабочего TB проекта, WRP/PBO, массовых тестов или merge.

Шаблон: [`AGENT_REPORT_TEMPLATE.md`](AGENT_REPORT_TEMPLATE.md). Старые отчёты — доказательства прежних действий, а не задание их повторить.
