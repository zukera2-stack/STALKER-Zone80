# MAP-001 — реальные исходники Припяти через GitHub Actions (24.11.2026)

**Результат: DATA ACQUIRED / LOCAL GLOBAL MAPPER NOT RUN.** Это продолжение [Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35) и [Draft PR #38](https://github.com/zukera2-stack/STALKER-Zone80/pull/38), а не завершённая карта. Исходный участок сохранён без изменений: **WGS84 bbox [30.045, 51.398, 30.070, 51.414]**.

## Причина обходного маршрута

В отчёте PR #38 локальный Windows `curl` вернул **exit 7** ещё до HTTP для Copernicus S3 и двух Overpass. Это значит соединение не удалось из локальной среды; **не доказана** недоступность источников вообще и не доказана ошибка Global Mapper. Задача не должна возвращаться к длительным UIA/системным тестам.

На [GitHub Actions run #45360016809](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45360016809) маленькая независимая выгрузка успешно обработала **оба** публичных источника. Получено 6 файлов и выгружено как **эфемерный workflow artifact**, а **не** в Git:

[Скачать MAP001-Pripyat-source-inputs, artifact #14904072084](https://github.com/zukera2-stack/STALKER-Zone80/actions/runs/45360016809/artifacts/14904072084)

**Artifact истекает 27.11.2026 (UTC).** Его следует локально забрать до окончания срока через `gh run download 45360016809 -n MAP001-Pripyat-source-inputs -D reports/MAP-001/input` при наличии рабочего `gh auth status` и прав к репозиторию. Не записывать PAT в чат или репозиторий. Если `gh` не установлен/не авторизован, использовать скачивание артефакта в интерфейсе GitHub в свою игнорируемую проектную папку. При блокировке локальной загрузки зафиксировать конкретную причину; не менять систему/прокси без разрешения.

## Фактические данные по GitHub runner log

Сведения ниже взяты **из реальных строк stdout** run #45360016809 job #138327386163. Полная проверка на компьютере владельца и Global Mapper **NOT TESTED**.

| Компонент | Результат и атрибуция |
|---|---|
| `pripyat_dem_copernicus_dsm30m.tif` | **Copernicus GLO-30 Public**, DSM (включает растительность/сооружения, не bare earth); **EPSG:4326**, пиксели **60 × 58**, min **105.0 м**, max **137.031509 м**, NoData -9999; исходный [публичный COG-тайл N51/E030](https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/Copernicus_DSM_COG_10_N51_00_E030_00_DEM/Copernicus_DSM_COG_10_N51_00_E030_00_DEM.tif) |
| `pripyat_bbox.osm` | Срез OSM API bbox: **2 513 195 байт**, лицензия ODbL, © OpenStreetMap contributors; [один запрос API](https://api.openstreetmap.org/api/0.6/map?bbox=30.045,51.398,30.070,51.414) |
| `roads.geojson` | **446** линий `way` с тегом `highway`, WGS84; необходима семантическая фильтрация, потому что не каждый `highway` — автомобильная дорога |
| `building_footprints.geojson` | **439** корректных `way` полигонов с `building`, только **отдельный каталог**, никогда не импортировать как TB/Arma objects |
| `SOURCE_MANIFEST.json` / `LICENSE_AND_USAGE.txt` | provenance, URL, время выборки, лимиты, хеши, атрибуция; в Git исходные raster/OSM не помещать |

**Известная неполнота:** ещё **27 OSM multipolygon/связанных relations не собраны** консервативным парсером. В этот счёт входят и relations, не являющиеся зданиями. 439 — количество распознанных way-полигонов, **НЕ полное число строений**. Чтобы корректно дополнить каталог, местная Луна должна отдельно разобрать building/multipolygon relations без дублирования зданий и сохранить счётчик unresolved. Не выдумывать этажность, высоты или состояние 1986 года.

Проверенные контрольные хеши GitHub-runner:

- OSM XML: `CB1AC83CF44667FE7BD720C801A23EF02DDD25D103AF1555C21226A16F340329`
- DSM GeoTIFF: `37ECF48629A75C32184802B3B63A003E93E4A86B3D50D0C6206B1E0065D33678`
- Roads GeoJSON: `8A7F89B9732C62C0092558320E0336A9B34F37A20BB4239A1B56ACB2B5EC4BA4`
- Buildings GeoJSON: `3DEF9A4FEE5DD7A7C37A58A38FBAF222C2DA3530957949BA4FD221306FDAD105`

Хеши сравнить на **распакованных** файлах, не ZIP (его собственный хеш отличается). Сведения об изображениях Google Maps/360 **не скачивались**. Фотореференс «Энергетика» остаётся в PR #38.

## Следующий реальный GIS gate: Global Mapper 26.2 Pro

1. Взять эти входы в `reports/MAP-001/input/`, проверить размер/хеш/права; не требовать повторного доступа к Overpass и S3 из Windows. Создать immutable новый run-dir для экспортов.
2. В локальном **Global Mapper 26.2 x64**, подтвердить Pro лицензию как **доступную / недоступную / unknown**. Выполнить `-DryRun`, затем один настоящий короткий `ElevationASC` экспорт, проверить `MANIFEST.json`/лог/exit/файл. Pro license не придумывать по EXE version.
3. **Критически важно:** полученный DSM в **EPSG:4326, сетка в градусах**, тогда как карта Terrain Builder нуждается в метрах. Перед **любым** TB terrain-only импортом создать пробный **метрический** raster (кандидат UTM 36N / EPSG:32636), удостоверить единицы, несколько контрольных точек, origin, размер пикселя и вертикальную систему высот. Нельзя импортировать ASC с `cellsize` в градусах как метры.
4. `roads.geojson` — проверить 446 геометрий, source IDs, классификацию и отсутствие объектов зданий. Превью делать **только рельеф + дороги**.
5. `building_footprints.geojson` — загрузить **отдельным каталогом**, уточнить отношения/multipolygons, типы/размеры/источники и правомерные фото/360 ссылки. Не отображать дома как игровые объекты. Не создавать P3D, CSV/TML placement.
6. Обновить `docs/map/MAP_001_PROGRESS.md` и `docs/map/BUILDING_INVENTORY_REPORT.md` только после фактического локального QC; результаты в отдельном Draft PR, без merge.

**Статусы сейчас:** public acquisition **PASS**, GitHub artifact **PASS**, local GM26 import/export **NOT RUN**, roads/map preview **NOT RUN**, building catalog mapping on user's PC **NOT RUN**, TB import **NOT RUN**, Stage 001 **PARTIAL**. Исходные данные являются современной картографической выборкой, не реконструкцией Припяти 1986 года.

## Технические ограничения

Исходники и файл pipeline: `tools/map001/fetch_public_inputs.py`, `.github/workflows/map001-public-geodata.yml`. GitHub Actions, при необходимости, делает **только один** ограниченный запрос OSM API 0.6 и HTTP-range cropped Copernicus DSM, без массового получения регионов. После окончания хранения можно повторно выполнить workflow по отдельному запросу, но OSM будет на **новую** дату, поэтому старые/новые snapshots не смешивать без provenance. Не переписывать оригиналы и журналы; не запускать новые SOAK/UIA исследования, WRP/PBO/Binarize, не трогать P:/игровые ассеты, не merge и не объявлять Stage 002 GO.
