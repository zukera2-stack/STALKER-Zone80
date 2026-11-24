# MAP-001: guarded Global Mapper 26.2 batch runner (local Windows Cursor).
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("ElevationASC","ElevationGeoTIFF","RoadsGeoJSON","BuildingsGeoJSON")]
    [string]$Mode,
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    [Parameter(Mandatory=$true)]
    [string]$GlobalMapperExe,
    [ValidateRange(10,900)]
    [int]$TimeoutSeconds=600,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$repo=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$root=[IO.Path]::GetFullPath((Join-Path $repo "reports\MAP-001"))
[IO.Directory]::CreateDirectory($root) | Out-Null

function Confirm-LocalPath([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value) -or $value.Contains('"') -or $value.Contains('%') -or $value.IndexOfAny([char[]]@([char]10,[char]13)) -ge 0) {
        throw "Unsafe path: empty, quote, percent or control character"
    }
    return [IO.Path]::GetFullPath($value)
}
function Confirm-UnderRoot([string]$path,[string]$parent) {
    $prefix=$parent.TrimEnd('\') + '\'
    if (-not $path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) {
        throw "Input outside project-owned reports/MAP-001: $path"
    }
}
function Save-Manifest([hashtable]$data,[string]$path) {
    $data | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $path -Encoding UTF8
}
function Quote-Arg([string]$v) { return '"' + $v + '"' }

$run=$null
$manifest=$null
try {
    $input=Confirm-LocalPath $InputFile
    Confirm-UnderRoot $input $root
    if (-not [IO.File]::Exists($input)) { throw "Input file does not exist" }
    $size=(Get-Item -LiteralPath $input).Length
    if ($size -lt 1 -or $size -gt 536870912) { throw "Small MAP-001 inputs only: 1..512 MiB" }

    $exe=Confirm-LocalPath $GlobalMapperExe
    if (-not [IO.File]::Exists($exe) -or -not [IO.Path]::GetFileName($exe).Equals("global_mapper.exe",[StringComparison]::OrdinalIgnoreCase)) {
        throw "Pass exact installed global_mapper.exe, without auto-download"
    }
    $v=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe)
    if (([string]$v.FileVersion -notmatch '(^|[^0-9])26\.2([.]|$)') -and
        ([string]$v.ProductVersion -notmatch '(^|[^0-9])26\.2([.]|$)')) {
        throw "Global Mapper 26.2 not proven by Windows EXE metadata; inspect local About/version"
    }

    $spec=@{
        ElevationASC=@("export_elevation_asc.gms","terrain.asc")
        ElevationGeoTIFF=@("export_elevation_geotiff.gms","terrain.tif")
        RoadsGeoJSON=@("export_roads_geojson.gms","roads.geojson")
        BuildingsGeoJSON=@("export_buildings_geojson.gms","building_footprints.geojson")
    }[$Mode]
    $script=Join-Path $PSScriptRoot ("scripts\" + $spec[0])
    if (-not [IO.File]::Exists($script)) { throw "Missing checked-in GMS template" }
    $run=Join-Path $root ((Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + "-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $run -ErrorAction Stop | Out-Null
    $output=Join-Path $run $spec[1]
    $logfile=Join-Path $run "global_mapper.log"
    $manifestFile=Join-Path $run "MANIFEST.json"

    $manifest=@{
        status="NOT_RUN"
        mode=$Mode
        createdUTC=(Get-Date).ToUniversalTime().ToString("o")
        runDirectory=$run
        inputFile=$input
        inputBytes=$size
        inputSha256=(Get-FileHash -LiteralPath $input -Algorithm SHA256).Hash
        gmsTemplateSha256=(Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash
        gmExeSha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
        gmFileVersion=[string]$v.FileVersion
        gmProductVersion=[string]$v.ProductVersion
        proLicenseVerified=$false
        outputFile=$output
        gmsTemplate=$script
        noTerrainBuilderActions=$true
        noBuildingPlacement=$true
    }
    Save-Manifest $manifest $manifestFile
    $argsList=@((Quote-Arg $script),"-input",(Quote-Arg $input),"-output",(Quote-Arg $output),"-logfile",(Quote-Arg $logfile))
    if ($DryRun) {
        Write-Host "DRY RUN (Global Mapper not started): $run"
        return
    }

    $manifest.status="RUNNING"
    $manifest.startedUTC=(Get-Date).ToUniversalTime().ToString("o")
    Save-Manifest $manifest $manifestFile
    # New background-less, CLI batch process; never close a user's existing GM.
    $p=Start-Process -FilePath $exe -ArgumentList $argsList -WorkingDirectory $run -PassThru
    $manifest.gmPid=$p.Id
    Save-Manifest $manifest $manifestFile
    if (-not $p.WaitForExit($TimeoutSeconds * 1000)) {
        throw "Batch exceeded $TimeoutSeconds seconds; process PID $($p.Id) left untouched, STOP and inspect"
    }
    $manifest.exitCode=$p.ExitCode
    if ($p.ExitCode -ne 0) { throw "Global Mapper exited with $($p.ExitCode)" }
    if (-not [IO.File]::Exists($logfile) -or -not [IO.File]::Exists($output)) {
        throw "Missing expected log or exported file"
    }
    if ((Get-Item -LiteralPath $output).Length -le 0) { throw "Export is empty" }
    $log=[IO.File]::ReadAllText($logfile)
    if ($log -notmatch 'ZONE80_FINISHED') { throw "Missing completion marker in GM log" }
    if ($log -match '(?im)\b(error|fatal|failed)\b') {
        throw "Potential error in Global Mapper log; inspect without retry"
    }
    # Sanity only. Georeferencing, vertical datum, road/footprint provenance
    # and exact geographic extent require separate GIS verification.
    if ($Mode -eq "ElevationASC") {
        $head=@(Get-Content -LiteralPath $output -TotalCount 6)
        if ($head.Count -lt 6 -or ($head -join " " -notmatch '(?i)\bncols\b') -or
            ($head -join " " -notmatch '(?i)\bnrows\b')) {
            throw "Arc ASCII header incomplete"
        }
    }
    if ($Mode -eq "ElevationGeoTIFF") {
        $stream=[IO.File]::OpenRead($output)
        try {
            $bytes=New-Object byte[] 4
            if ($stream.Read($bytes,0,4) -ne 4 -or
                -not (($bytes[0] -eq 73 -and $bytes[1] -eq 73 -and $bytes[2] -eq 42) -or
                      ($bytes[0] -eq 77 -and $bytes[1] -eq 77 -and $bytes[3] -eq 42))) {
                throw "Output lacks TIFF byte-order signature"
            }
        } finally { $stream.Dispose() }
    }
    if ($Mode -like "*GeoJSON") {
        $geo=Get-Content -LiteralPath $output -Raw | ConvertFrom-Json
        if ($geo.type -ne "FeatureCollection" -or $null -eq $geo.features -or
            @($geo.features).Count -lt 1) { throw "GeoJSON has no exported features" }
    }

    $manifest.status="EXPORTED_NEEDS_GIS_QC"
    $manifest.outputBytes=(Get-Item -LiteralPath $output).Length
    $manifest.outputSha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
    Write-Host "Output exists; GIS/CRS/license QC NOT TESTED: $output"
} catch {
    if ($null -ne $manifest) {
        $manifest.status="BLOCKED"
        $manifest.failure=$_.Exception.Message
    }
    Write-Error $_.Exception.Message
    throw
} finally {
    if ($null -ne $manifest -and $null -ne $run) {
        $manifest.finishedUTC=(Get-Date).ToUniversalTime().ToString("o")
        Save-Manifest $manifest (Join-Path $run "MANIFEST.json")
    }
}
