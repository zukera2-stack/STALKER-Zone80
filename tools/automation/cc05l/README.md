# CC-05L — native hydrography and bounded material mask probe
Synthetic only. Linux SDK 10.0.404, pinned GRM/BIS and CC05B bridge, offline feed as CC05K. Set DOTNET_PROCESSOR_COUNT=2, isolated DOTNET_CLI_HOME/XDG_RUNTIME_DIR/NUGET_PACKAGES, NUGET_CERT_REVOCATION_MODE=offline, DOTNET_NOLOGO=1, DOTNET_CLI_TELEMETRY_OPTOUT=1.

```
dotnet restore Zone80.WaterProbe.csproj -p:GrmRoot=<source> -p:BridgeSource=<cc05b> --source <offline-feed> -p:NuGetAudit=false
dotnet build Zone80.WaterProbe.csproj -p:GrmRoot=<source> -p:BridgeSource=<cc05b> --no-restore -c Release --disable-build-servers -p:GeneratePackageOnBuild=false
dotnet <actual-bin>/Zone80.WaterProbe.dll <v03-editor-config> <modelinfo.json>
```

Exact pinned config/cache and previous strict resolver. Native lake, watercourse, sand, ocean/coastline (land-only fixture), roads and watercourse placement. No real imagery or heights. Native full IdMapRender not run: reads ElevationWithLakesData; native radial builder actually refused at that dependency. Native public PolygonDrawHelper, exact v03 material IDs and a bounded four-usage 480x480 in-memory diagnostic mask; not stock full IdMap or production export. Six pixel controls, all colors known; three distinct colors (shared material IDs). Source river tagged width=24 produces two segments width=10, canal not emitted; StreamTunnel classified but IsTunnel=false due to enum comparison (zero width and no surface at control). Edge pond clipped at 25m inset. No upstream edits. Preserve failures: initial companion RGB constructor compile error fixed; initial incorrect tunnel expectation failed, then actual anomaly asserted. PASS refers to bounded measured behavior, not approval of defects. Actual visual water plane, shoreline elevation, broad river/Pripyat reservoir relation handling, ice/mud/base dependencies, full material priority/coverage and local runtime remain blocked/untested. 530 archived upstream files unchanged. No P: writes, WRP/PBO, real generation or merge.
