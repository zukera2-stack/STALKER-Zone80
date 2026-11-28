# Terrain Builder — MAP-005 commands and compatibility

**Действующий регламент передачи (28.11.2026):** [AI_WORKSPACE / Google Drive](../../../../docs/AI_WORKSPACE.md). ChatGPT ведёт разработку, анализ и доступные тесты, Cursor/Codex исполняет локально через PowerShell и разрешённые нативные API. GitHub — код и задания; Drive — разрешённые архивы и доказательства с уникальным именем, манифестом и SHA256. Library — историческая справка, Desktop Commander не использовать. Локальная sandbox и технические ограничения сохраняются.

Checked 2026-11-27. Installed TerrainBuilder.exe reports FileVersion 1.32 and ProductVersion 1.32.0.153956. The 2026-11-19 Tools Dev-Branch changelog reports adding a command-line argument to open an existing project. The changelog does not specify a switch or confirm it for the installed executable. Treat the following PowerShell command as a candidate for a verified supporting build with an owned saved project, never as an import command.

```powershell
& $terrainBuilderExe $ownedProjectTv4p
```

The sources reviewed do not document headless Terrain Builder commands for importing rasters or shapes, creating a mapframe, or saving a project. Terrain Processor is a separate executable. Its documented line call is `TerrainProcessor.exe`. It processes TPP tasks with SHP/ASC inputs and can produce LBT data for a separate Terrain Builder import. No unattended TPP flags were verified.

## Editor command map

| Action | Menu or panel | Evidence to record |
|---|---|---|
| Create mapframe | Mapframe > Add Mapframe | CRS and origin, grid dimensions, cell spacing, extent |
| Import elevation | File > Import > Terrains | ASC orientation, five asymmetric height controls and extent |
| Import imagery | File > Import > Satellite Images | Pixel spacing, orientation and extent. GeoTIFF acceptance on the installed build is unverified. Community examples use BMP or PNG with a world file. |
| Import mask | File > Import > Surface mask images | Dimensions match the mapframe's mask source settings and material colors are validated |
| Import road geometry | File > Import > Shapes | SHP, SHX, DBF and PRJ kept together. Check placement and feature count. |
| Save project | File > Save | Owned .tv4p plus its sidecar directories. Reopen and confirm the imported layers. |

## MAP-005 input checks

Use the GM26.2 synthetic bundle in reports/MAP-005. ASC: 64 by 64 at 30 m. Imagery: 480 by 480 at 4 m. Source extent: EPSG:32636, southwest (294373.084, 5698122.108), northeast (296293.084, 5700042.108). ASC starts at a lower-left cell corner. The TFW starts at the upper-left pixel center. Verify both against their own convention.

The stock terrain tutorial uses an origin of (200000, 0). Preserve the source coordinates. If the selected TB workflow requires local game coordinates, derive and validate a consistent transform on copies of all layers. Verify road vertices and raster controls after the same transform. The two MAP-005 polylines are editor geometry. The engine road workflow also needs validated road attributes and RoadsLib.cfg.

Use only a verified isolated project. Existing owner sessions are left alone. Project rules exclude mouse and keyboard emulation, writes to P:, and WRP/PBO generation for this task.

## Sources

- [Terrain Builder, Bohemia Interactive Community](https://community.bohemia.net/wiki/Terrain_Builder)
- [Tools Dev-Branch changelog mirror, entries for June, July and November 2026](https://wiki.arma3.io/topics/Tools_Dev-Branch_Change_Log.html)
- [Terrain Processor, Bohemia Interactive Community](https://community.bohemia.net/wiki/Terrain_Processor)
- [Terrain Processor tutorial sample, including road files](https://community.bohemia.net/wiki/Terrain_Processor%3A_Tutorial_Sample_project)
- [Common Terrain Creation Problems, Bohemia Interactive Community](https://community.bohemia.net/wiki/Arma_3%3A_Common_Terrain_Creation_Problems)
- [The Atlas tutorial, PMC Editing Wiki](https://pmc.editing.wiki/doku.php?id=arma3%3Aterrain%3Athe-atlas-by-jakerod)
- [QGIS terrain tutorial and Shapes import, PMC Editing Wiki](https://pmc.editing.wiki/doku.php?id=arma3%3Aterrain%3Aqgis-real-world-data-tutorial)



## Local execution on Windows (current owner policy)

Use local Cursor/Codex PowerShell and the verified semantic UIA route in [zone80-tb-mouseless](../../zone80-tb-mouseless/SKILL.md). Desktop Commander is retired. Verify editor ownership and full project identity, preserve isolated paths, do not emulate input or bypass denials. Save disabled is a state, not evidence of unsupported operation. Preserve native readback and transfer evidence via AI_WORKSPACE under the current policy.
