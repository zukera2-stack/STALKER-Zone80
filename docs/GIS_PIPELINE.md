# GIS pipeline and CRS approval

## Acquisition
- Record source release/snapshot date, source URL, ODbL or provider license, retrieval UTC, SHA256, geographic coverage and expected size **before downloading**.
- For large OSM areas prefer a local PBF extract imported once to GeoPackage; do not rely on repeated large Overpass requests.
- For DEM distinguish SRTM/GLO-30 posting from true fine terrain resolution; resampling to 20 m does not add detail. Copernicus GLO-30 is a DSM, not a bare-earth survey.
- Historical buildings require separate temporal validity and quality grades, not blind reuse of modern OSM.

## Geometry
WGS84 (EPSG:4326) is the input storage convention. Test one projected metric CRS across the entire fixed square. Candidate UTM 36N or a centered custom Transverse Mercator must be evaluated quantitatively at west/east/north/south control points. Do not finalize EPSG or local XY origin before tests. Store CRS, bounds, axis order, vertical datum and inverse mapping in terrain_extent.json when approved.

## Current source-of-truth: GM-only elevations, GRID FIRST (2026-11-24)

**Новая политика владельца:** ChatGPT передаёт географическое **задание** (N51 E030, 4 угла WGS84, точная UTM36N 64×64×30м сетка), а **местная Global Mapper Pro 26.2** загружает источник высот и экспортирует файл. **Нельзя заново создавать heightmap через Python/GDAL/GitHub Actions или подменять новый GM результат старым облачным raster**. Конкретный tile [`map/MAP_003_GM26_TILES.md`](map/MAP_003_GM26_TILES.md); [ADR-0002](DECISIONS/ADR-0002-owner-pivot-map-and-gm-only.md).

**Экспорт задаётся в таком порядке:** фиксируем `EPSG:32636`, `ncols/nrows 64×64`, `cellsize 30m`, `xllcorner 294373.084`, `yllcorner 5698122.108` → Global Mapper выбирает реальный законно доступный height layer и загружает полный охват тайла N51E030 → экспорт ASC/GeoTIFF в эту **фиксированную** метровую сетку → 5 контрольных ячеек + 0 NoData + исходный datum/source и SHA. **Не** выбирать выходной размер по случайному прямоугольнику WGS84: в предыдущем реальном GM26 экспорте это дало **60×62 и 253 NoData**, хотя batch exit 0. `DSM` не равно bare-earth terrain, особенно в городской зоне.

**Состояние:** прежний Windows GM26 `60×62` batch действительно `PASS` как промежуточный GIS продукт по [PR #41](https://github.com/zukera2-stack/STALKER-Zone80/pull/41). **Новый** GM26 Online Data → `64×64` `NOT RUN`; TB импорт `NOT RUN`. Ни один успешный GitHub CI не заменяет эти два шага. Текущий источник только из GM26. Исторические облачные scripts и результаты остаются как evidence/архив (PR #43 closed), **не исполнять их для MAP-003**. Проекция/центр/размер полного мира пока не утверждены.

## Global Mapper 26.2 Pro (64-bit) — основной локальный инструмент

По уточнению владельца от **24.11.2026** используем **Global Mapper 26.2 Pro, 64-bit**, а не упоминавшуюся прежде v27. Версия/редакция указана владельцем; на Windows агент проверяет установленный EXE, Version/About, доступную лицензию, наличие функций и их фактический результат. Не обновлять программу и не менять лицензию для эксперимента.

Практический MAP-001 pipeline: открыть **небольшие законно полученные** DEM/DSM и OSM/vector источники в Global Mapper → проверить WGS84 bbox, исходную проекцию, единицы, вертикальную систему высот, NoData → обрезать кандидатный участок Припяти → измерить контрольные точки и геометрические искажения временной метрической проекции → экспортировать GeoTIFF/Arc ASCII Grid для рельефа и раздельные векторные данные дорог и **каталога контуров зданий** (GeoJSON или другой подтверждённый формат). Фактический тип и параметры каждого экспорта должны подтверждаться выходным файлом, метаданными, SHA256 и контрольными точками.

**Здания в Terrain Builder не импортировать** — геоданные предназначены для будущего мода моделей. Для карты preview показывать только рельеф и дороги; каталог строений анализировать отдельно. Скриншоты Google Street View не загружать автоматически и не использовать как GIS raster/geometric source: допустимы ссылки на просмотр и атрибуция, если они подтверждены.

Использовать Script Builder / .gms только если команда и синтаксис проверены в реально установленной **26.2 Pro** на малом образце; не заявлять, что синтаксис v27 подходит автоматически. GUI действия агента — только безопасные и изолированные, без управления несохранённым пользовательским проектом. При отсутствии проверенного скрипта допустим обычный локальный экспорт через разрешённый путь и фиксацию параметров. Global Mapper — **средство обработки**, первичные источники DEM и OSM указываются отдельно с датой и лицензией.

## Cursor/Луна → Global Mapper 26.2 Pro: официальный .gms batch (MAP-001)

После изучения документации Blue Marble и проекта [Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35) для локальной автоматизации **приоритетен не UI Automation и не SDK, а штатный `.gms` + вызов `global_mapper.exe` из PowerShell**. При передаче `.gms` как аргумента EXE приложение выполняет его в отдельном batch-процессе без обычного UI и завершает процесс после скрипта. Это относится к установленному на Windows настольному Global Mapper; не даёт облачному агенту доступа к пользовательскому компьютеру. **Базовая интеграция уже проходила реальный Windows batch по отчёту PR #41 (exit 0 для старой 60×62 GIS сетки). Это не новый MAP-003 64×64 экспорт.**

**Код и инструкции:** [`tools/gm26/README.md`](../tools/gm26/README.md), `tools/gm26/Invoke-GlobalMapper.ps1`, `tools/gm26/scripts/*.gms`. Только 4 задачи на **уже обрезанных малых источниках**: высоты → Arc ASCII / GeoTIFF, дороги → GeoJSON (линии), контуры зданий → отдельный GeoJSON (полигоны без размещения в TB/Arma). Сначала задокументировать происхождение и права источников и получить одобренные локальные файлы в `reports/MAP-001/input/`. Не заимствовать фотографические данные или геометрию у Google 360.

Луна подтверждает установленный EXE 26.2, активную Pro-лицензию, точный input и применимость параметров на реальной машине; начинает с `-DryRun`, затем **один небольшой** GMS экспорт. Проверяет log, exit code, хеш, факт существования файла, а затем отдельным GIS QC — координаты, область, NoData, высоты, source IDs и права. Все результаты идут в новый `reports/MAP-001/<run-id>`; старые слои и открытый GUI проект не меняются. Нет проверенного официального COM Automation Server; **standalone SDK лицензируется отдельно** и здесь не нужен. Python внутри Pro — дополнительный этап только при технической необходимости. Не переносить скрипты v27 вслепую в 26.2.

Официальные интерфейсы: [batch mode](https://www.bluemarblegeo.com/knowledgebase/global-mapper/Scripting_Reference/Batch_Mode_Operation.htm), [IMPORT](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/IMPORT.htm), [EXPORT_ELEVATION](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_ELEVATION.htm), [EXPORT_VECTOR](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_VECTOR.htm), [release notes 26.2](https://www.bluemarblegeo.com/knowledgebase/global-mapper/releasenotes_old.htm).

## Feature metadata (minimum)
source_id, source_dataset, source_date, license, geometry_confidence, type_confidence, height_confidence, historical_state, manual_override, production_feature_id, review_status. Use explicit unknown/null where evidence is absent. Distinguish placement_accuracy from model_authenticity.
