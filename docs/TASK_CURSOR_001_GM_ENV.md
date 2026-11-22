# Stage 001-A/GM — Cursor local resources and Global Mapper 27 capability probe

**Read [AGENT_START.md](../AGENT_START.md), [AGENTS.md](../AGENTS.md) and [docs/GO_NOGO.md](GO_NOGO.md) first.**

Purpose: verify what Cursor can actually access on the owner's Windows workstation and whether the installed **Global Mapper 27.0 64-bit** can be controlled through a `.gms` file from a terminal. No DEM, online tile, OSM, image or WRP generation in this task.

## Why this probe exists

Earlier *private* Zone80 reports dated 2026-11-21 indicated Windows 10 Pro, Xeon E5-2690 v4, 32 GB RAM reported but not independently measured via CIM, Global Mapper 27.0, Arma 3/Tools and GRM Studio 0.9. Some system queries were blocked; the prior GRM failure was a Task-disposal exception, not demonstrated OOM. **Recheck all claims**, do not treat them as this probe's test results.

Official Global Mapper docs state that passing a `.gms` file as the Global Mapper executable's argument runs it in batch mode without UI. `GLOBAL_MAPPER_SCRIPT`, `SET_LOG_FILE`, and `LOG_MESSAGE` are supported commands:
- https://www.bluemarblegeo.com/knowledgebase/global-mapper/Scripting_Reference/Batch_Mode_Operation.htm
- https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/LOG_MESSAGE.htm
- https://www.bluemarblegeo.com/knowledgebase/global-mapper/cmd/SET_LOG_FILE.htm

## Execution — only through terminal, no mouse required

1. Open a terminal in the repository root in Cursor. Work in a separate local branch `feat/001-gm-env-audit` (if it doesn't exist). Confirm `git status` before starting; do not overwrite unrelated work.
2. Inspect the probe code before running; do not assume it is safe merely because it is in the repository.
3. Inventory only (no application launch):

   ```powershell
   pwsh -NoProfile -File .\tools\audit\probe_cursor_globalmapper.ps1
   ```

   If PowerShell 7 is absent, run from an existing Windows PowerShell 5.1 terminal instead:

   ```powershell
   powershell.exe -NoProfile -File .\tools\audit\probe_cursor_globalmapper.ps1
   ```

4. Locate the generated `reports/gm_probe_*/environment.json`. Check actual CPU, logical processors, physical RAM, free RAM, swap/pagefile, fixed disk free space, GPU info, Windows edition/build, and application paths. Report **UNKNOWN** if CIM/WMI is blocked. `PATH` absence is not proof of no installation.
5. Check Global Mapper's real executable/version. In its existing UI confirm license **Standard vs Pro**, without exporting the license key. Identify whether it is currently running; do not close the owner's working session.
6. If exactly one v27 executable was discovered, Global Mapper is not already running, the application license is valid, and the owner agrees to a short local launch, test a no-data GMS:

   ```powershell
   pwsh -NoProfile -File .\tools\audit\probe_cursor_globalmapper.ps1 -RunSmoke -TimeoutSeconds 90
   ```

   If several installations are found or the correct binary is not under a known installation root, provide its reviewed exact path with `-GlobalMapperExe "C:\Program Files\GlobalMapper27.0_64bit\global_mapper27.0.exe"`. Use `powershell.exe` instead of `pwsh` if appropriate. The test script only sets its own log path and writes a `Zone80_GM_CLI_SMOKE_OK` marker; it never imports or exports GIS layers. A valid PASS needs the marker in the generated log **and** a zero exit code. If the application hangs on a dialog, script times out after 90 seconds and **does not kill** the process; record the PID and inspect manually.
7. If `-RunSmoke` cannot run safely, do not improvise an unreviewed batch script. Mark the capability NOT TESTED/PARTIAL with a reason.

## Constraints and evidence

- No installations, downloads, external URLs, full-disk searches, activation attempts, administrative changes, config resets, changes to Windows pagefile, or extraction of user mods.
- Do not open or modify original user project `.gmw`, `.grma3m`, `.pbo`, or geospatial source files.
- `reports/` is `.gitignore`d; keep the raw report local. Publish only a sanitized summary.
- This checks launch and scripting capability, **not** Global Mapper export format support, GUI editing automation, usable licensing of Pro-only tools, or memory footprint of DEM generation.

## Return a short report to ChatGPT

| Question | Required evidence |
|---|---|
| OS and privilege context | Windows version/build, PowerShell version, Cursor terminal identity/effective account |
| CPU/RAM/GPU | Hardware names, reliable/unknown memory amounts, free space, pagefile |
| Available software | Cursor terminal, Python, .NET, Git, Global Mapper, GDAL, QGIS, Arma Tools/GRM — versions/path verified or UNKNOWN |
| GM license | Standard, Pro, or UNKNOWN (never include secrets) |
| Terminal control of GM | GMS file path, log marker, exit code, duration, timeout or blocking dialog |
| Agent access scope | Can launch local executables? read/write inside repository? Can run PowerShell without dialogs? |
| Final result | GO / PARTIAL / NO-GO for **environment audit only**; exact blocker and next action |

When complete, **STOP** and submit sanitized findings for review. Do not proceed to tile generation or Stage 002.