# Аудит окружения Cursor и Global Mapper

22–23 ноября 2026 года, Stage 001. **Итог — PARTIAL.** На Global Mapper Pro 26.2 подтверждены запуск GMS и синтетический экспорт. Для версии 27 успешное выполнение GMS не подтверждено.

## Окружение

| Проверка | Статус | Результат |
| --- | --- | --- |
| ОС и CPU | PASS | Windows 10 Pro 19045.6456 по реестру. Intel Xeon E5-2690 v4 @ 2.60 GHz, процессу видны 28 логических процессоров. |
| Ресурсы | PARTIAL | Синтетический прогон зафиксировал 31,91 GiB физической памяти и 17,54 GiB доступной на старте. Системный лимит commit около 113,91 GiB. Свободно около 163 GiB на системном томе и 3 529 GiB на томе проекта. Размещение и размер файла подкачки не подтверждены. |
| Скрипт инвентаризации | FAIL | Скрипт tools/audit/environment_audit.ps1 остановился на Get-CimInstance Win32_OperatingSystem с Access denied. Повторные запросы CIM для ОС и CPU также отклонены. |
| Командная среда | PASS | PowerShell 7.6.9, Python 3.15.2, Git 2.56.1.windows.1, .NET SDK 11.0.100. |
| Cursor | PARTIAL | Собраны результаты локального задания TASK_CURSOR_001. Версия Cursor и запуск Global Mapper из собственного терминала Cursor не подтверждены. |
| GDAL | PARTIAL | gdalinfo и ogr2ogr не найдены в PATH. Python использовал GDAL 3.9.2 через DLL в раннем прогоне. Для проверки GeoTIFF после переустановки использована GDAL DLL из Global Mapper 26.2. |
| Игровые инструменты | PARTIAL | По локальной инвентаризации обнаружены Arma 3 2.22, Terrain Builder 1.32, Binarize 2.21, CfgConvert 1.2.0.1, BankRev 1.0.0.2 и файлы Studio 0.11.1. Функциональные запуски за рамками аудита. |

## Global Mapper

| Проверка | Статус | Результат |
| --- | --- | --- |
| Идентификация версии 27 | PARTIAL | В ранней инвентаризации 27.0 определена по имени exe. Поле FileVersion отсутствовало. После переустановки в проверенном каталоге программ обнаружена 26.2. |
| GMS в раннем окружении 27 | FAIL | Две попытки экспорта с относительными и абсолютными путями превысили лимит наблюдения около 15 с каждая. Журналы запуска не подтверждают, до какой команды дошёл скрипт. Причина тайм-аутов неизвестна. |
| Четыре синтетических тайла через Python и GDAL | PASS | После двух ранних падений проверок сравнения SW успешно выполнены SW, SE, NW, NE. Зафиксированы 68 проверок на швах, 6 исходных ID, 8 уникальных частей, 20 совпавших хешей и 15 неизменённых файлов. |
| GMS после переустановки | PASS | Лаунчер global_mapper26.2.exe выполнен с аргументом smoke.gms. Журнал подтвердил Global Mapper Pro v26.2 (b110625), Zone80_GM_CLI_SMOKE_OK и Script processing COMPLETED. Лаунчер вернул 0 до появления журнала. Прямой запуск global_mapper.exe вернул ошибку запуска процесса. |
| ASCII Grid на 26.2 | PASS | Совпали геопривязка, шаг 8 м и все 1 089 высот сетки 33 × 33. Вход задаёт центр нижней левой ячейки, выход задаёт её угол. |
| GeoTIFF с локальной CRS на 26.2 | FAIL | Размер, геотрансформ и 1 089 высот совпали. Выход получил метку WGS 84 в градусах при метровых численных координатах. Маркер NoData изменился с −9999 на −32767. |
| GeoTIFF с явной EPSG:32636 на 26.2 | PASS | GDAL подтвердил EPSG:32636, 33 × 33, геотрансформ (399996, 8, 0, 5700260, 0, −8) и совпадение всех 1 089 высот. Максимальная разница 0 м. |
| GeoJSON на 26.2 | PASS | Сохранены ID, виды геометрии, координаты и атрибуты всех шести объектов. Порядок записи изменился. |

EPSG:32636 использована как контрольная проекция. Утверждение проектной CRS требует проверки реальных контрольных точек.

## Выполненные команды

Аргументы с локальными путями обезличены. Запуски GMS выполнены в отдельных временных каталогах.

```powershell
pwsh -File tools/audit/environment_audit.ps1
Get-CimInstance Win32_OperatingSystem
Get-CimInstance Win32_Processor
Get-PSDrive -PSProvider FileSystem
python --version
git --version
dotnet --version
python probe.py SW
python probe.py SE
python probe.py NW
python probe.py NE
Start-Process -FilePath $gmLauncher -ArgumentList $quotedScript -WorkingDirectory $testDir -WindowStyle Hidden
```

В повторных GMS использованы SET_LOG_FILE, LOG_MESSAGE, IMPORT, EXPORT_ELEVATION с параметрами TYPE=GEOTIFF или TYPE=ARCASCIIGRID, ELEV_UNITS=METERS и SPATIAL_RES=8,8. Для вектора использованы IMPORT и EXPORT_VECTOR TYPE=GEOJSON. Для контрольной UTM-сетки использованы LOAD_PROJECTION PROJ_EPSG_CODE=32636 и IMPORT с PROJ="EPSG:32636". Через GDAL проверены геотрансформ, код CRS и численные отсчёты (GDALRasterIO). Повторные скрипты выполнялись без UNLOAD_ALL.

## Доказательства

Оригиналы доступны локально в reports/. [Правила исключения из Git](../../.gitignore).

| Локальный журнал или файл | Содержание |
| --- | --- |
| reports/global_mapper_environment/ENVIRONMENT_AUDIT.md и reports/global_mapper_environment/task001-local-evidence.txt | Инвентаризация TASK_CURSOR_001, ограничения доступа, обнаруженные версии |
| reports/gis_probe_001/gm_export_launch.log и reports/gis_probe_001/gm_absolute_launch.log | Два ранних тайм-аута |
| reports/gis_probe_001/process.log, reports/gis_probe_001/measurements.json и reports/gis_probe_001/probe.py | Разрез на четыре тайла, измерения и проверки |
| reports/global_mapper_environment/gm26-retest/smoke.log | Версия приложения и завершение GMS |
| reports/global_mapper_environment/gm26-retest/raster/batch.log, reports/global_mapper_environment/gm26-retest/vector/batch.log и reports/global_mapper_environment/gm26-retest/projected/batch.log | Журналы экспорта. Синтетические входы, скрипты и выходы сохранены в этих же каталогах |

Задания проекта — [TASK_CURSOR_001](../TASK_CURSOR_001.md), [Issue #2](https://github.com/zukera2-stack/STALKER-Zone80/issues/2), [Issue #3](https://github.com/zukera2-stack/STALKER-Zone80/issues/3), [Issue #4](https://github.com/zukera2-stack/STALKER-Zone80/issues/4), [Issue #5](https://github.com/zukera2-stack/STALKER-Zone80/issues/5).

## Не подтверждено

- Запуск GMS, импорт, обрезка и экспорт непосредственно в Global Mapper 27.
- Запуск из терминала Cursor и автономное управление Global Mapper через Cursor.
- Экспорт реального тайла Zone80, сохранение маски NoData на входе с пропусками и пригодность CRS для карты. Исходный тайл не найден в обследованных папках проекта и кэше GRM.
- Потребление ресурсов на реальных данных, формирование WRP и игровой запуск. Полная генерация карты не запускалась.
