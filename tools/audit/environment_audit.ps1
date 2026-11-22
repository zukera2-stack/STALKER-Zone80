# Stage 001: non-destructive Windows inventory; writes only local ignored reports/
param(
    [string]$OutFile = ""
)
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Reports = Join-Path $Repo "reports"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
    $OutFile = Join-Path $Reports "environment_audit.json"
}
$ResolvedTarget = [IO.Path]::GetFullPath($OutFile)
if (-not $ResolvedTarget.StartsWith(([IO.Path]::GetFullPath($Reports) + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Output must be inside the repository reports directory."
}
New-Item -ItemType Directory -Path $Reports -Force | Out-Null
$OS = Get-CimInstance Win32_OperatingSystem
$Computer = Get-CimInstance Win32_ComputerSystem
$CPU = Get-CimInstance Win32_Processor
$Pagefile = @(Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage)
$Disks = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, Size, FreeSpace, FileSystem)
$Candidates = @("git","python","dotnet","gdalinfo","ogr2ogr","GlobalMapper64","GlobalMapper","TerrainBuilder","Binarize","CfgConvert","BankRev")
$Found = @()
foreach ($Name in $Candidates) {
    $Cmd = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    $Found += [pscustomobject]@{ name = $Name; found_on_path = [bool]$Cmd; path = if ($Cmd) { $Cmd.Source } else { $null } }
}
$Audit = [ordered]@{
    status = "PARTIAL - registry/path discovery only, not manual version verification"
    generated_utc = [DateTime]::UtcNow.ToString("o")
    os = @{ caption = $OS.Caption; version = $OS.Version; build_number = $OS.BuildNumber; architecture = $OS.OSArchitecture }
    cpu = @($CPU | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors)
    physical_ram_bytes = [int64]$Computer.TotalPhysicalMemory
    pagefile = $Pagefile
    local_disks = $Disks
    tools_on_path = $Found
    notes = "Arma 3, Arma 3 Tools and Global Mapper installed versions may not be in PATH; manually verify paths/versions."
}
$Audit | ConvertTo-Json -Depth 8 | Out-File -FilePath $ResolvedTarget -Encoding UTF8
Write-Host "Report: $ResolvedTarget"
Write-Host "Source addon files and GIS datasets were not modified."
