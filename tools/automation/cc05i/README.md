# CC-05I — bounded native forest probe
Review-only Linux .NET 10.0.404. GRM 2aef2040836daa11a8a368bb0c7f9ecd8f405d65 and BIS 5e406d5021ba19ced8babcadd89ed26119f71f48; use authorized Library inputs listed in docs/LIBRARY_INDEX.md. Restore local feed, verify hashes, no online audit. Link unchanged CC05B GmOnlyContext.cs. Do not execute native installed tools, write P:, export map files or change upstream sources. No production API.

Set DOTNET_CLI_HOME, XDG_RUNTIME_DIR (mode 700), NUGET_PACKAGES to isolated paths; DOTNET_PROCESSOR_COUNT=2, NUGET_CERT_REVOCATION_MODE=offline. Use SDK executable explicitly:
```
dotnet restore Zone80.ForestProbe.csproj -p:GrmRoot=<source> -p:BridgeSource=<cc05b> --source <offline-feed> -p:NuGetAudit=false --force --no-cache
dotnet build Zone80.ForestProbe.csproj -p:GrmRoot=<source> -p:BridgeSource=<cc05b> --no-restore -c Release --disable-build-servers -p:GeneratePackageOnBuild=false
dotnet <actual-bin>/Zone80.ForestProbe.dll <v03-editor-config> <modelinfo.json>
```
Only a single synthetic forest polygon with an internal road, water and cutline is tested. Native ForestBuilder is rejected by the guarded catalog at ElevationWithLakesData; native OSM polygon interpretation, road, lake and cutline builders supply a separate geometry-only bounded adapter, using native polygon subtraction. Stock ForestGenerator executes both configured collections, receives ForestData before generation. Unknown road state is conservatively withheld, not classified as operational; both give the same geometry in this fixture. Native placement offsets may exceed polygon constraints, final review counts are measured, not silently fixed or approved. No generalized territorial-state polygon engine, age/density calibration, full multi-polygon repeat or physical collision proof. Tests use relative model points and in-memory transform, no WRP files. Source and input hashes unchanged; synthetic coordinate origin is not a real pilot CRS proof. See CC05I_RESULT.
