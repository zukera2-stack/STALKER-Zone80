# Stage gates: evidence rather than optimism

## Status vocabulary
- **PASS (criterion):** measured **specific criterion** satisfied by reproducible evidence; **НЕ означает GO для Stage**.
- **GO (stage):** только явное разрешение владельца после отдельной приёмки всей стадии.
- **PARTIAL:** preparatory work exists but required tests or dependencies are missing.
- **FAIL / NO-GO:** criterion contradicted or safety bound breached.
- **NOT RUN / NOT TESTED:** операция не проводилась, доказательств нет; это никогда не PASS.
- **BLOCKED:** сознательный STOP до нужного действия из-за безопасности/доступа/лицензии/недостающих входов; не равно FAIL реальной операции.
- **SUPERSEDED:** прежний метод отменён владельцем; его исторический PASS остаётся в журнале, но не служит заданием.

## Stage 001 foundation acceptance
- Actual Windows build, CPU/cores, physical RAM, pagefile, storage and tool paths/versions recorded.
- Existing local .grma3m/.grma3a, GRM tag/SHA and addon roots located *if they exist*, without mutation.
- Unchanged upstream GRM builds; small memory profile recorded with stage-by-stage peak. If not possible, PARTIAL with reason.
- Asset inventory with hashes and UNKNOWN license handling; no copyrighted binaries committed.
- Candidate CRS roundtrip and distortion measured on boundary control points; no guessed map origin.
- Git diff clean of third-party assets, credentials and source datasets; manifest tooling deterministic.
- Reports include exact commands, SHA, logs, file inventory and unresolved issues.

## Owner-approved mapping pilot (2026-11-24) — NOT a stage promotion

**Issue #35 / MAP-001 may proceed now** despite incomplete Stage 001 inventory. It is a controlled **small real 1–2 km Pripyat data/preview/sandbox** exercise, not Stage 002 GO. The decision explicitly **stops the TB-UIA/SOAK test workstream**: earlier autonomous launch/UIA 203 nodes/50 completed real SOAK cycles suffice for this pilot operationally; a 60-minute SOAK is **NOT PASS** and the old stop cause is **CAUSE_UNKNOWN**. Do not demand another soak or more generic UIA tests as a prerequisite to creating real map data.

MAP-001 uses the owner's existing **Global Mapper 26.2 Pro 64-bit** as its primary GIS processor, subject to local installation/version/license verification; primary DEM/vector data provenance is separate. No buildings or structures are to be placed in Terrain Builder. Google 360 may supply verified source links only, not scraped images or extracted model geometry.

Map-pilot acceptance: documented legally usable DEM/source + actual WGS84 area and sample metadata; a verifiable elevation-and-roads preview plus a *separate* building-footprint GIS catalog (no placement or 3D models); georeferenced coordinate/height control points; and, **only if safely isolated**, a Terrain Builder sandbox import + evidence. If TB cannot be isolated, record GUI import BLOCKED but continue producing the real offline geographic artifact. No bulk data, no copyright-bearing raw assets in Git, no unsaved user project changes. Formal promotion, final CRS/extent/epoch and in-game claims remain separate decisions.

## MAP-003 — отдельные практические ворота (актуальное решение 24.11.2026)

**Текущее задание:** [Issue #42](https://github.com/zukera2-stack/STALKER-Zone80/issues/42), [таблица N51E030 и UTM координат](map/MAP_003_GM26_TILES.md). Владелец требует **только Global Mapper Pro 26.2 на локальном Windows для получения/экспорта высот**; ChatGPT поставляет координаты/тайл, не формирует новые DEM/ASC через Python, GDAL или GitHub Actions. [PR #43](https://github.com/zukera2-stack/STALKER-Zone80/pull/43) закрыт без merge. Новая операция GM Online/Data → ASC `NOT RUN` до локального отчёта.

| Gate | **PASS только если…** | Текущий статус |
|---|---|---|
| G1 Source | В реальном GM26.2 указан **фактически доступный** слой, N51E030, фактическое покрытие, datum, license и provenance | **NOT RUN** для нового Online Data; название tile известно |
| G2 Export | Сам GM26.2 экспортировал новый ASC с process/log/exit (если CLI), SHA и новым sandbox output; не облачная подмена | **NOT RUN** для MAP-003; прежний GM `60×62` PASS только как GIS intermediate |
| G3 Heightmap | Ровно **64×64×30м**, EPSG:32636, XLL 294373.084, YLL 5698122.108, **0 NoData**, минимум 5 высотных контрольных точек | **NOT RUN** для GM26 MAP-003 |
| G4 TB sandbox | Доказана независимость пустого project-owned TB проекта от текущего пользовательского; один успешный terrain-only import, скриншот и сохранение | **NOT RUN**; иначе `BLOCKED`, **без** проб GUI |
| G5 Game | Реальная сборка WRP/PBO и RPT из Arma 3 | **NOT RUN**; **не требуется** для MAP-003, **не подразумевается** её завершением |

**Stop conditions:** NoData, CRS/размер/единицы mismatch, неверный источник, неопределённая лицензия, риск для пользовательского TB проекта → **STOP**, сохранить лог и исправлять только узкий блокер. Не запускать ещё один SOAK/UIA; здания/3D/объектное размещение не входят в разрешённый gate. Состояние проекта и ссылки на доказательства сверять по [`PROJECT_CONTROL.md`](PROJECT_CONTROL.md), [`VERIFICATION_LEDGER.md`](VERIFICATION_LEDGER.md), [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md).

## Promotion
The director audits the evidence; the owner authorizes Stage 002. Do not begin 10.24 km pilot or full world on Stage 001 authorization. For Stage 003 and Stage 007, a successful serializer is not a PASS: **the actual Arma map must load** with RPT/screenshots and package dependency checks.
