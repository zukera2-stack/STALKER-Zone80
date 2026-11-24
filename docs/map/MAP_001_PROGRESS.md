# MAP-002 — проверка исходников и локальное превью Припяти

**PARTIAL.** [Issue #39](https://github.com/zukera2-stack/STALKER-Zone80/issues/39) · [исходники и контрольные суммы](MAP_001_SOURCE_HANDOFF.md) · [участок](MAP_001_AREA.md). Bbox WGS84: 30.045, 51.398, 30.070, 51.414.

| Проверка | Результат |
| --- | --- |
| Входы | PASS. ZIP предоставлен владельцем локально. Все шесть файлов распакованы. SHA-256 OSM, DSM, дорог и зданий совпали с handoff. Проверены атрибуция Copernicus и OSM ODbL. |
| Global Mapper | Версия 26.2 x64 подтверждена метаданными. Лицензия Pro остаётся UNKNOWN. |
| ElevationASC DryRun | PASS. Сценарий из ветки handoff принял проверенный DSM и создал manifest. |
| Реальный batch | BLOCKED на Start-Process. Windows вернула «Операция была отменена пользователем». PID, лог Global Mapper и ASC отсутствуют. Причина отмены на уровне Windows не установлена. Повторного запуска не было. |
| Проверка исходного растра | PASS вне Global Mapper. Прочитаны 3 480 float-значений, 60 × 58. Высоты 105–137,031509 м, NoData −9999, число ячеек NoData 0. Сетка EPSG:4326, шаг 0,000416667° × 0,000277778°. EGM2008 указан в метаданных источника. Это DSM. |
| Превью | Локально создан SVG из проверенных входов, без контура ни одного здания. XML прочитан обратно. В SVG 453 дорожных полилинии из 446 объектов, включая 7 MultiLineString. Указаны приблизительная шкала, север, bbox и источники. SHA-256 0B5CCB6E7D3DFCA9D00FCBDE32F31996960C3BEA461AD5B7CDC6AD06CFDAF34E. |
| Terrain Builder | NOT RUN. Метрический ASC, контрольные точки экспорта и импорт остаются открытыми. |

Команда `Invoke-GlobalMapper.ps1 -Mode ElevationASC -InputFile <verified-dsm> -GlobalMapperExe <installed-exe>` выполнена один раз после `-DryRun`. Manifest обеих попыток и производные файлы лежат локально в reports/MAP-001. Превью произведено отдельной локальной обработкой входов. Ни исходники, ни производные геоданные в Git не публиковались.

В исходном дорожном слое 187 footway, 78 path, 45 pedestrian и 10 steps. Другие классы: service 46, track 32, residential 15, tertiary 15, living_street 9, unclassified 8 и tertiary_link 1. Первые четыре пеших класса выделены в превью отдельно. Историческое состояние неизвестно. Stage 001 / PARTIAL.
