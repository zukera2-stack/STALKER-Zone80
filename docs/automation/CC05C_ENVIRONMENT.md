# CC-05C — SDK and dependency intake checkpoint
Owner supplied .NET SDK 10.0.403 and 10.0.404 Linux x64 tarballs and pinned GRM source ZIP. Isolated Linux x86_64 environment. Base 0424c108be15d111e41dd6c5b8079b3abfcbe5be, Issue #42, Draft PR #47.

## Measured evidence
- .NET 10.0.403 archive SHA256 cd7224fe8e8ba57c15f1601439ff8785a1a72b54ae5c89dd5302a32dcfbddf18; not extracted/tested.
- .NET 10.0.404 archive SHA256 c0610757a818fde4b960d27a0ac421f273068a05dc5ec7abafc01dbf84e9cb4d; extracted successfully. dotnet --info SDK 10.0.404, host 10.0.15, MSBuild 18.9.15, Debian 13 linux-x64. These are measured local hashes, not verified official published checksums.
- GRM ZIP SHA256 00c0ea9ae0d996df3476cd64117ca1c35de55caaf8554067e469008e03e9e3e0, 2035 entries, CRC PASS; ZIP comment and root name match pinned commit 2aef2040836daa11a8a368bb0c7f9ecd8f405d65. No claim of independently authenticated complete tree. Extracted into isolated scratch. CC05B source package CRC PASS.
- curl -I --connect-timeout 3 --max-time 5 https://api.nuget.org/v3/index.json exit 6, DNS resolution failed.
- First dotnet restore failed during NuGet-Migrations mutex because inherited XDG_RUNTIME_DIR=/run/oai absent. Resolved by setting a private existing XDG_RUNTIME_DIR (0700). Then actual restore against empty local feed failed exit 1/NU1101 for all nine direct packages; transitive closure cannot be measured until packages arrive.
- Minimal net10.0 dependency-free console project restore using empty feed and build --no-restore succeeded, 0 warnings/errors; first launch used wrong output path, corrected to actual build path, exit 0 printed SDK_SMOKE_PASS 10.0.15. This tests the SDK, not GRM.
- Re-ran CC05B Python tests: 8/8 PASS. Actual GRM core and bridge compilation/smoke remain BLOCKED on NuGet.

## Owner handoff
Delivered Zone80_NuGet_Collector_CC05C.zip (3581 bytes, SHA256 b9f1c3b101c52923c3a1735f93eedc94adef7cd8d9325f37f3bda2819cb822bb, CRC PASS). Contains START.cmd, Collect-NuGet.ps1, Packages.csproj and README.txt. XML package reference list checked against extracted GRM core project: exact nine direct IDs/versions. Collector uses isolated work/cache, official NuGet.org, lock file, nupkg bytes and SHA256 manifest, optionally fetches portable Microsoft Windows SDK 10.0.404 and verifies downloaded SHA512 against official release metadata. Windows script execution NOT RUN; no network restore measured here. Owner uploads resulting Zone80_NuGet_Offline_*.zip. No admin install, no P: writes, no upstream binaries/sources committed. Local package transfer only; dependency licenses still require review before redistribution. NuGet audit disabled in collector, not a safety approval.

Next: verify received package manifest/lock/hashes, restore bridge and GRM core from local package feed only, compile actual source, run synthetic GRM consumer/guard tests. Do not enable real generation, modify GM elevation, generate WRP/PBO, merge or promote Stage 001. UI deferred.
