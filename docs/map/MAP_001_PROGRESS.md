# MAP-001 — Windows preflight

**PARTIAL. Получение геоданных BLOCKED. Stage 001 / PARTIAL.** [Issue #35](https://github.com/zukera2-stack/STALKER-Zone80/issues/35#issuecomment-7126501912). Проверенная техническая база [PR #37](https://github.com/zukera2-stack/STALKER-Zone80/pull/37), HEAD `efdfd2794c178518354d58f18281a07e7684fa10`, база документации PR #36 `5ba7af182e39329c2d923182017b1d629058842b`.

| Проверка | Результат |
| --- | --- |
| Установка Windows | PASS по метаданным. global_mapper.exe FileVersion и ProductVersion 26.2, PE machine 0x8664 (x64). SHA-256 71097E955B206DB28C2B37FB3AFC1C98D38AC8926C3984DCCACDF224D00C89A0. |
| Pro и лицензия | NOT VERIFIED в этой проверке. Метаданные EXE подтверждают версию и архитектуру. |
| PowerShell | PASS. Parser.ParseFile для Invoke-GlobalMapper.ps1 из закреплённого HEAD: 0 ошибок AST. Запись в reports/MAP-001 подтверждена. |
| Сеть для входных данных | BLOCKED. curl HEAD завершился кодом 7 на AWS Copernicus и на обоих Overpass endpoints. HTTP-ответа не было. |
| DryRun и реальный GMS batch | NOT RUN. Малый проверенный вход отсутствует. |
| Arc ASCII, GeoTIFF, дороги и preview | NOT RUN. Выходных файлов, CRS/NoData QC и SHA выходов нет. |
| Terrain Builder | NOT RUN. Отдельный terrain-only импорт не проводился. |

[MAP_001_AREA.md](MAP_001_AREA.md) фиксирует участок и кандидаты источников. [BUILDING_INVENTORY_REPORT.md](BUILDING_INVENTORY_REPORT.md) содержит отдельный статус геокаталога. Локальный технический журнал reports/MAP-001/preflight-pr37/WINDOWS_PREFLIGHT.json. Синтетические файлы старых проверок не использованы в качестве реальных данных Припяти.
