# Cursor / Luna: TASK 001 — Foundation audit, no map generation

**Read AGENTS.md first.** This is a local engineering job on the owner's Windows system. ChatGPT audits; the owner decides historic/gameplay canon and approves dependencies. Work on branch feat/foundation-audit from the reviewed foundation.

## Hard limits
1. Never edit, delete, repack or overwrite original addons, PBO/P3D/PAA, GRM project or GIS source files.
2. Locate and report a candidate `Zona.grma3m` / `*.grma3a` rather than assuming its existence.
3. Never run 81.92 km generation, download a regional dataset before reporting estimated size/rights or patch GRM before baseline profiling.
4. Do not put large source data, original PBOs or local tool paths into Git. Store audit reports in ignored reports/.
5. Warning at 20 GiB process Private Bytes; controlled stop by 24 GiB in benchmark harness (not an OS limit).
6. PASS requires actual test evidence; in-game gate requires Arma 3 launch, RPT and screenshot.

## A — Verify environment
Run tools/audit/environment_audit.ps1, inspect JSON manually and supplement with actual Global Mapper 27 (exe/version), Arma 3, Arma 3 Tools, Terrain Builder, Binarize, CfgConvert, .NET SDK and GDAL/ogr2ogr. Confirm Win edition/build, CPU, physical RAM, pagefile and disk free space. Include command output and tool paths only in local report.

## B — Discover existing files
Read-only search appropriate project folders for *.grma3m, *.grma3a, local ArmaRealMap checkout and candidate mod roots. Record filename, full local path, size, timestamp and SHA256 for critical files. Do not recurse the entire disk without a bounded search plan.

## C — Original GRM
Record upstream URL https://github.com/jetelain/ArmaRealMap, tag/commit SHA and actual local repo state. Build **unchanged**. Inspect BuildContext, IDataBuilder/GetData, builder lifetimes, RawSatelliteImageBuilder, elevation, OSM parsing, HugeImages, object-layer generators, WRP writer and CLI verbs. Use small sample only. Record stage,start,end,private_bytes,working_set,managed_heap,available_system_ram,temp_disk_bytes,object_count. Stop with PARTIAL if suitable sample/tool is unavailable. Root cause of earlier OOM is UNKNOWN pending measured evidence; do not invent it.

## D — Non-destructive asset index
Run `python tools/asset_index/scan_assets.py --root "PATH_TO_ADDONS"` only on an owner-approved addon folder. This initial tool only inventories loose P3D/PBO and hashes; **it cannot yet identify config classnames, virtual paths, dimensions, LOD or addon licenses**. Check existence of BankRev and CfgConvert, then propose a separate tested metadata parser with output into assets/catalog/ and explicit UNKNOWN licenses. Never extract/repack the original mod into a tracked directory.

## E — GIS and precise extent
Run `python tools/validation/validate_config.py`. Define intended geographic square with owner; obtain control points on west/east/north/south edges. Investigate crossing of 30°E boundary. Test single UTM36N and, if needed, local Transverse Mercator via tools/gis/projection_probe.py; log inverse residual and geodesic scale error. No production CRS/XY origin approval without results. Prepare a validated Global Mapper v27 .gms DEM import, clip and export to GeoTIFF and ASC only after locating a small approved DEM. Do not label unexecuted scripts tested.

## F — Data model and first sector experiment
Review source_registry.yaml, asset_mapping.yaml, object_rules.yaml and stalker_locations.geojson. Ensure every future real feature stores source ID/dataset/date/license, confidence, historical state and manual override. Run `python tools/validation/build_sector_manifests.py`, inspect 64 files, verify adjacent coordinates, stable IDs and zero overlaps. These manifests have no geographic data.

## G — Report, then STOP
Write local reports/ENVIRONMENT_AUDIT.md, GRM_AUDIT.md, GIS_PROJECTION.md, ASSET_INVENTORY.md and stage_001_gate.md. Include real commands, dates, source SHA, measured peak memory/disk, checksums, failure logs, Git diff, screenshots if available, and explicit PASS/PARTIAL/FAIL for each item. Recommend one 1–2 km urban Pripyat micro-pilot with multiple apartment buildings and courtyards, without starting it.

**Stop after Task 001.** The owner and ChatGPT must review the evidence before authorizing Stage 002.
