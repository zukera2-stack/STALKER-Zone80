# Terrain Builder — MAP-005 commands and compatibility

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



## Remote Desktop Commander on Windows

- Use the connector to locate the authorized online device and run PowerShell, check processes and verify file hashes. If a command returns a pending call ID, poll its result before considering another launch.
- Use the existing verified launcher for an authorized Terrain Builder run on `WinSta0\Default`. Check for an existing editor first and verify the new process by executable, PID and start time before targeting it with Windows UI Automation.
- The available connector tools expose files, terminals and processes. Use Windows UI Automation separately to inspect controls. No built-in GUI input tools were exposed in the connector tested on 2026-11-27 (device agent 0.3.4).
- MAP-005 verified startup into an unnamed project. Latest owner report says Save and Save As were found but disabled in the empty project; Import terrain was enabled. Disabled is a state, not proof the operation is unsupported. In the owned instance, attempt the actual mapframe prerequisites through allowed semantic operations, verify state after every step, then save, import and reopen. If a necessary control is unavailable, test applicable supported routes and owned templates under the autonomous skill; if they are exhausted, immediately request the smallest exact manual action outside P: and continue independent layers. Record native save and reopen only after verifying the resulting project. Do not repeat unchanged UIA scans or use input emulation.

Source: https://desktopcommander.app/help/getting-started/what-can-i-do
