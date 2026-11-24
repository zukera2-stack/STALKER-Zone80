# GIS pipeline and CRS approval

## Acquisition
- Record source release/snapshot date, source URL, ODbL or provider license, retrieval UTC, SHA256, geographic coverage and expected size **before downloading**.
- For large OSM areas prefer a local PBF extract imported once to GeoPackage; do not rely on repeated large Overpass requests.
- For DEM distinguish SRTM/GLO-30 posting from true fine terrain resolution; resampling to 20 m does not add detail. Copernicus GLO-30 is a DSM, not a bare-earth survey.
- Historical buildings require separate temporal validity and quality grades, not blind reuse of modern OSM.

## Geometry
WGS84 (EPSG:4326) is the input storage convention. Test one projected metric CRS across the entire fixed square. Candidate UTM 36N or a centered custom Transverse Mercator must be evaluated quantitatively at west/east/north/south control points. Do not finalize EPSG or local XY origin before tests. Store CRS, bounds, axis order, vertical datum and inverse mapping in terrain_extent.json when approved.

## Global Mapper 26.2 Pro (64-bit) — основной локальный инструмент

По уточнению владельца от **24.11.2026** используем **Global Mapper 26.2 Pro, 64-bit**, а не упоминавшуюся прежде v27. Версия/редакция указана владельцем; на Windows агент проверяет установленный EXE, Version/About, доступную лицензию, наличие функций и их фактический результат. Не обновлять программу и не менять лицензию для эксперимента.

Практический MAP-001 pipeline: открыть **небольшие законно полученные** DEM/DSM и OSM/vector источники в Global Mapper → проверить WGS84 bbox, исходную проекцию, единицы, вертикальную систему высот, NoData → обрезать кандидатный участок Припяти → измерить контрольные точки и геометрические искажения временной метрической проекции → экспортировать GeoTIFF/Arc ASCII Grid для рельефа и раздельные векторные данные дорог и **каталога контуров зданий** (GeoJSON или другой подтверждённый формат). Фактический тип и параметры каждого экспорта должны подтверждаться выходным файлом, метаданными, SHA256 и контрольными точками.

**Здания в Terrain Builder не импортировать** — геоданные предназначены для будущего мода моделей. Для карты preview показывать только рельеф и дороги; каталог строений анализировать отдельно. Скриншоты Google Street View не загружать автоматически и не использовать как GIS raster/geometric source: допустимы ссылки на просмотр и атрибуция, если они подтверждены.

Использовать Script Builder / .gms только если команда и синтаксис проверены в реально установленной **26.2 Pro** на малом образце; не заявлять, что синтаксис v27 подходит автоматически. GUI действия агента — только безопасные и изолированные, без управления несохранённым пользовательским проектом. При отсутствии проверенного скрипта допустим обычный локальный экспорт через разрешённый путь и фиксацию параметров. Global Mapper — **средство обработки**, первичные источники DEM и OSM указываются отдельно с датой и лицензией.

## Cursor/Луна → Global Mapper 26.2 Pro: официальный .gms batch (MAP-001)

После изучения документации Blue Marble и проекта [Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35) для локальной автоматизации **приоритетен не UI Automation и не SDK, а штатный `.gms` + вызов `global_mapper.exe` из PowerShell**. При передаче `.gms` как аргумента EXE приложение выполняет его в отдельном batch-процессе без обычного UI и завершает процесс после скрипта. Это относится к установленному на Windows настольному Global Mapper; не даёт облачному агенту доступа к пользовательскому компьютеру. **Базовая интеграция подготовлена, запуск на Windows ещё NOT RUN.**

**Код и инструкции:** [`tools/gm26/README.md`](../tools/gm26/README.md), `tools/gm26/Invoke-GlobalMapper.ps1`, `tools/gm26/scripts/*.gms`. Только 4 задачи на **уже обрезанных малых источниках**: высоты → Arc ASCII / GeoTIFF, дороги → GeoJSON (линии), контуры зданий → отдельный GeoJSON (полигоны без размещения в TB/Arma). Сначала задокументировать происхождение и права источников и получить одобренные локальные файлы в `reports/MAP-001/input/`. Не заимствовать фотографические данные или геометрию у Google 360.

Луна подтверждает установленный EXE 26.2, активную Pro-лицензию, точный input и применимость параметров на реальной машине; начинает с `-DryRun`, затем **один небольшой** GMS экспорт. Проверяет log, exit code, хеш, факт существования файла, а затем отдельным GIS QC — координаты, область, NoData, высоты, source IDs и права. Все результаты идут в новый `reports/MAP-001/<run-id>`; старые слои и открытый GUI проект не меняются. Нет проверенного официального COM Automation Server; **standalone SDK лицензируется отдельно** и здесь не нужен. Python внутри Pro — дополнительный этап только при технической необходимости. Не переносить скрипты v27 вслепую в 26.2.

Официальные интерфейсы: [batch mode](https://www.bluemarblegeo.com/knowledgebase/global-mapper/Scripting_Reference/Batch_Mode_Operation.htm), [IMPORT](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/IMPORT.htm), [EXPORT_ELEVATION](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_ELEVATION.htm), [EXPORT_VECTOR](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_VECTOR.htm), [release notes 26.2](https://www.bluemarblegeo.com/knowledgebase/global-mapper/releasenotes_old.htm).

## Feature metadata (minimum)
source_id, source_dataset, source_date, license, geometry_confidence, type_confidence, height_confidence, historical_state, manual_override, production_feature_id, review_status. Use explicit unknown/null where evidence is absent. Distinguish placement_accuracy from model_authenticity.
