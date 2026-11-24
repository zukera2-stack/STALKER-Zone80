# MAP-001: Cursor → PowerShell → Global Mapper 26.2 Pro (64-bit)

**Цель:** использовать установленный у владельца Global Mapper 26.2 Pro через официальный пакетный интерфейс **Global Mapper Script (.gms)**. **Это интеграция-черновик: реальный запуск на Windows ещё NOT RUN.** Не устанавливает SDK и не управляет пользовательскими окнами. GMS из отдельного запуска `global_mapper.exe` работает без обычного GUI и завершается после обработки.

[Активное задание #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35) · [документация MAP-001](../../docs/MAP_001_TASK.md)

## Что умеет первоначальный пакет

| Режим | Источник (уже подготовлен на малый участок) | Выход | Что подтверждает |
|---|---|---|---|
| `ElevationASC` | небольшой геопривязанный DEM/DSM | `terrain.asc` | только формат Arc ASCII; координаты/NoData/высоты проверить отдельно |
| `ElevationGeoTIFF` | такой же DEM/DSM | `terrain.tif` | GeoTIFF, требуется контроль реального CRS/vertical datum |
| `RoadsGeoJSON` | отдельный векторный слой дорожных линий | `roads.geojson` | только линии, без построек |
| `BuildingsGeoJSON` | отдельный векторный слой геоконтуров построек | `building_footprints.geojson` | только **каталог геоданных**; не размещение домов/3D |

Сценарии расположены в `tools/gm26/scripts/`. Используются `IMPORT TYPE=AUTO PROMPT_IF_TYPE_UNKNOWN=NO`, `EXPORT_ELEVATION TYPE=ARCASCIIGRID/GEOTIFF`, `EXPORT_VECTOR TYPE=GEOJSON SHAPE_TYPE=LINES/AREAS`, `SET_LOG_FILE`, `LOG_MESSAGE`. Их синтаксис описан в документации Blue Marble; конкретные возможности, поведение файлов, лицензия и настройки экспорта на **локальной 26.2 Pro** проверяются **первым малым пробным запуском**, а не утверждаются заранее.

## Использование локальной Луной

Сначала подтвердить *на своём Windows ПК*: действительный путь `global_mapper.exe`, EXE file/product version **26.2**, доступность настольной лицензии Pro и исходных **лицензионно допустимых** небольших файлов. Поместить входные DEM и векторы в игнорируемую локальную папку `reports/MAP-001/input/`. Не менять содержимое источников, не выгружать их в Git.

Из корня репозитория PowerShell (свои реальные пути, не копировать строки как реальные пути владельца):

```powershell
$gm = "<verified full path to global_mapper.exe>"
$dem = (Resolve-Path ".\reports\MAP-001\input\small_dem.tif").Path
$roads = (Resolve-Path ".\reports\MAP-001\input\roads.geojson").Path
$buildings = (Resolve-Path ".\reports\MAP-001\input\buildings.geojson").Path

# Check-only; no Global Mapper process:
.\tools\gm26\Invoke-GlobalMapper.ps1 -Mode ElevationASC -InputFile $dem -GlobalMapperExe $gm -DryRun

# Run exactly one small export after input provenance/rights check:
.\tools\gm26\Invoke-GlobalMapper.ps1 -Mode ElevationASC -InputFile $dem -GlobalMapperExe $gm

# Subsequent map tasks as needed:
.\tools\gm26\Invoke-GlobalMapper.ps1 -Mode RoadsGeoJSON -InputFile $roads -GlobalMapperExe $gm
.\tools\gm26\Invoke-GlobalMapper.ps1 -Mode BuildingsGeoJSON -InputFile $buildings -GlobalMapperExe $gm
```

**Не запускать всё сразу**, пока не прошёл первый короткий проверенный экспорт. В настоящем участке перед экспортом нужно убедиться в bbox, временнóм метрическом CRS, корректных единицах высоты и лицензии. Эти четыре сценария **не выполняют обрезку/репроекцию**; их входы уже должны быть корректно ограничены участком. Для обрезки сначала записать и проверить конкретные .gms команды в 26.2 (например через Copy Script/Script Builder), затем расширить пайплайн — не угадывать аргументы.

## Защита и журналы

- Только локальные входы `reports/MAP-001/**` (1..512 MiB), проверенный EXE с FileVersion/ProductVersion 26.2, заранее зафиксированные шаблоны; запрет внешних URL, макроподстановок `%`, кавычек/переводов строк в передаваемых путях.
- Новый уникальный `reports/MAP-001/<UTC-GUID>/` для каждого запуска. Создаются `MANIFEST.json` (hash input/exe/template, статус, PID и exit code при наличии), `global_mapper.log`, выходной файл. Старые каталоги/оригиналы не перезаписываются.
- Отдельный процесс Global Mapper, **не** текущая пользовательская GUI-сессия. При 10-900 сек timeout wrapper фиксирует BLOCKED и PID, **не убивает процесс и не повторяет** экспорт автоматически; проверить состояние процессa вручную через агента.
- `EXPORTED_NEEDS_GIS_QC` означает лишь существование непустого выходного файла, лог без обнаруженной ошибки и базовый формат. **Не PASS географических данных**: проверить геопривязку, оси, bbox, вертикальный datum, NoData, многократные высотные контрольные точки и сохранность source IDs. Геометрия GeoJSON не обязательно WGS84 без проверенной корректной проекции экспорта.
- `BuildingsGeoJSON` — **только каталог**: группа 3D-моделей для будущего отдельного мода, без TB object placements, P3D, CSV/TML или создания города сейчас.
- Не записывать в `P:`, не трогать оригинальные PBO/P3D/PAA, не скачивать из Google и не создавать Street View screenshots. Google 360 — только URL для фотоанализа.

## Технический выбор

1. **.gms + CLI** — первый шаг, без SDK и мыши, не нужен COM server.
2. **PowerShell** запускает отдельный процесс, пишет журнал и хеши; Python можно использовать для анализа GeoJSON/ASC/QC, не обязательно для вызова GM.
3. **Python внутри Global Mapper Pro** — резерв для более сложных операций, требующий реально доступных Pro функций.
4. **Самостоятельный Global Mapper SDK** лицензируется отдельно и здесь НЕ используется.
5. **UI Automation** GUI — последний резерв, а не самостоятельная большая тестовая программа. Отсутствует проверенный официальный COM ProgID для `GlobalMapper.Application`: не придумывать его.

## Официальные ссылки

- [Scripting Reference / batch mode](https://www.bluemarblegeo.com/knowledgebase/global-mapper/Scripting_Reference/Batch_Mode_Operation.htm)
- [IMPORT](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/IMPORT.htm)
- [EXPORT_ELEVATION](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_ELEVATION.htm)
- [EXPORT_VECTOR](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/EXPORT_VECTOR.htm)
- [SET_LOG_FILE](https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/SET_LOG_FILE.htm)
- [Release Notes v26.2](https://www.bluemarblegeo.com/knowledgebase/global-mapper/releasenotes_old.htm)

**Критерий приёмки:** доказанный на Windows контролируемый малый экспорт, нужный для MAP-001, с точными input/output/hashes, журналом и отдельной проверкой GIS координат. Статус до запуска — NOT RUN.
