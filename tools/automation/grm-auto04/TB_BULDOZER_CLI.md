# TB-BULDOZER-CLI-01 — direct viewer launch without configuration edits

27.11.2026. Owner requested command-line launch rather than editing Terrain Builder preferences. Base b54a89a489fefeb5953927e3289f725063478acf, task #42 comment 7221298438. Standalone native render/launch PASS; TB map connection NOT PROVEN, map preview NOT RUN. Stage001 PARTIAL.

## Measured launch
Existing installed P: buldozer.exe x86 (v2.22, SHA256 49e76f17e4c14bfe4d92bf9f6e85f3799d05a3a17910aea2688d291c2f893538), existing owned TB project clean, no pre-existing viewer/game process. Created separate local BuldozerCLI directory and profiles subfolder on D:, copied existing cfg byte-for-byte; no installed configuration edit. Invoked PowerShell Start-Process with verified executable, explicit D: working directory and arguments:
```powershell
$cfg = Join-Path $ownedRoot 'buldozer.cfg'
$profiles = Join-Path $ownedRoot 'profiles'
Start-Process -FilePath $verifiedViewerExe -WorkingDirectory $ownedRoot -ArgumentList "-buldozer -name=Buldozer -window -exThreads=0 -disableSteam -noAsserts -cfg=$cfg -profiles=$profiles -showScriptErrors" -PassThru
```
For this actual run the owned ASCII paths contained no spaces. Confirmed real command line, process birth identity, same interactive Windows session, responding native Buldozer window, DX11 initialized RTX3060, audio initialization complete, local RPT and profile files generated under explicit profiles directory. Actual screenshot 1456x939 obtained via PrintWindow of exact owned viewer HWND, SHA256 250f6d4a8dbcbe2b54a134f34e29716f0119829328a1e1f71f566126ae89cbac. Inspected image shows default empty grey scene, disc position outside 1920m fixture, no selected object. This is native engine render, NOT GRMAUTO04 map rendering. Viewer left running intentionally for next connection inspection.

## Connection gate
Official Arma 3 Buldozer manual describes TB Tools > Connect to Buldozer and configured viewer launch. Historical official Visitor 3 manual documents -connect=pipe\\name; Arma 3 forum logs show TB-generated -connect=pipe\\... arguments with additional value. Installed build's actual channel and handshake have not been established. No guessed pipe, no direct IPC writes, no second launch through existing P: settings, no changed TB config. Current standalone viewer command does not include that argument. Local installed TB Log folder did not yield current channel evidence in the checked location. Next identify supported attach-only mechanism or obtain explicit permission for a narrowly scoped temporary TB viewer-launch setting with restoration; do not treat direct launch as connected project. No PAA candidate linked to map.

## Integrity
Readback: original P: buldozer.cfg SHA256 be8e78701df41ca5281315b99608fed2b30cf5538aa0b948fc3f1dbeffd35161, installed TerrainBuilder.opt SHA256 9161e1f3a74b79e3099c27934ccced6bb74b511999ce63fc2a3bb64f74371e88, native GRMAUTO04 tv4p SHA256 24792dc28883be888b92c84d3f277477e7829febd86541bcf0bf6393388075e2 unchanged. P: root file metadata 10/10 matched after normalizing JSON millisecond timestamps (initial PowerShell comparisons incorrectly compared deserialized dates/arrays); not comprehensive filesystem write tracing. No intentional P: writes, input emulation, WRP/PBO, process termination or merge. Raw RPT, screenshot and launch manifest remain local. Stage001 PARTIAL.

References: https://community.bistudio.com/wiki/Buldozer_Manual ; https://community.bistudio.com/wiki/Visitor_3_Manual ; https://forums.bohemia.net/forums/topic/165159-buldozer-not-start/ ; https://community.bistudio.com/wiki/Arma_3_Startup_Parameters .
