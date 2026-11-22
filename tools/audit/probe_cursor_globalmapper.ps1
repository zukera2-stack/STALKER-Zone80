# STALKER-Zone80 Stage 001: read-only environment audit and OPTIONAL minimal Global Mapper CLI test.
# Reports are written ONLY under ignored repository reports/. No downloads, installations,
# map generation, source-file modification, or kill of existing application processes.
[CmdletBinding()]
param(
    [switch]$RunSmoke,
    [string]$GlobalMapperExe = "",
    [ValidateRange(10, 300)][int]$TimeoutSeconds = 90
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$reportsRoot = Join-Path $repo 'reports'
New-Item -ItemType Directory -Path $reportsRoot -Force | Out-Null
$runId = 'gm_probe_' + [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$outDir = Join-Path $reportsRoot $runId
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$warnings = New-Object 'System.Collections.Generic.List[string]'
$osInfo = $null; $machineInfo = $null; $cpuInfo = @(); $gpuInfo = @(); $pageInfo = @()
try { $osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop } catch { $warnings.Add('OS CIM unavailable: ' + $_.Exception.Message) }
try { $machineInfo = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop } catch { $warnings.Add('RAM CIM unavailable: ' + $_.Exception.Message) }
try { $cpuInfo = @(Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors) } catch { $warnings.Add('CPU CIM unavailable: ' + $_.Exception.Message) }
try { $gpuInfo = @(Get-CimInstance Win32_VideoController -ErrorAction Stop | Select-Object Name, DriverVersion, AdapterRAM) } catch { $warnings.Add('GPU CIM unavailable: ' + $_.Exception.Message) }
try { $pageInfo = @(Get-CimInstance Win32_PageFileUsage -ErrorAction Stop | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage) } catch { $warnings.Add('Pagefile CIM unavailable: ' + $_.Exception.Message) }

$osReg = $null
try {
    $osReg = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction Stop |
        Select-Object ProductName, DisplayVersion, CurrentBuild, UBR
} catch { $warnings.Add('OS registry unavailable') }
$drives = @()
try {
    $drives = @([IO.DriveInfo]::GetDrives() | Where-Object { $_.IsReady -and $_.DriveType -eq [IO.DriveType]::Fixed } | ForEach-Object {
        [pscustomobject]@{ name = $_.Name; total_bytes = $_.TotalSize; free_bytes = $_.AvailableFreeSpace; format = $_.DriveFormat }
    })
} catch { $warnings.Add('DriveInfo unavailable: ' + $_.Exception.Message) }

$toolNames = @('git','python','py','pwsh','dotnet','gdalinfo','gdalwarp','ogr2ogr','qgis_process','GlobalMapper','GlobalMapper64','TerrainBuilder','Binarize','CfgConvert','BankRev')
$tools = @($toolNames | ForEach-Object {
    $cmd = Get-Command $_ -ErrorAction SilentlyContinue | Select-Object -First 1
    [pscustomobject]@{ name = $_; on_path = [bool]$cmd; location = if ($cmd) { $cmd.Source } else { $null } }
})

$registryInstalls = @()
try {
    $uninstallKeys = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    $registryInstalls = @(Get-ItemProperty -Path $uninstallKeys -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like '*Global Mapper*' } |
        Select-Object DisplayName, DisplayVersion, InstallLocation, DisplayIcon)
} catch { $warnings.Add('Uninstall registry enumeration failed') }

# Only inspect known installation roots; never search all drives or owner project data.
$gmCandidates = New-Object 'System.Collections.Generic.List[string]'
$installRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
foreach ($root in $installRoots) {
    foreach ($name in @('GlobalMapper27.0_64bit','GlobalMapper27_64bit','GlobalMapper27.0','GlobalMapper')) {
        $dir = Join-Path $root $name
        if (Test-Path -LiteralPath $dir -PathType Container) {
            Get-ChildItem -LiteralPath $dir -Filter '*.exe' -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '(?i)^(global_mapper|globalmapper)' } |
                ForEach-Object { $gmCandidates.Add($_.FullName) }
        }
    }
}
foreach ($install in $registryInstalls) {
    if ($install.InstallLocation -and (Test-Path -LiteralPath $install.InstallLocation -PathType Container)) {
        Get-ChildItem -LiteralPath $install.InstallLocation -Filter '*.exe' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)^(global_mapper|globalmapper)' } |
            ForEach-Object { $gmCandidates.Add($_.FullName) }
    }
}
if (-not [string]::IsNullOrWhiteSpace($GlobalMapperExe)) {
    if (-not (Test-Path -LiteralPath $GlobalMapperExe -PathType Leaf)) { throw "Explicit GlobalMapperExe does not exist: $GlobalMapperExe" }
    $gmCandidates.Add(([IO.Path]::GetFullPath($GlobalMapperExe)))
}
foreach ($name in @('GlobalMapper','GlobalMapper64')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source -and (Test-Path -LiteralPath $cmd.Source -PathType Leaf)) { $gmCandidates.Add($cmd.Source) }
}
$gmFiles = @($gmCandidates | Sort-Object -Unique | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | ForEach-Object {
    $f = Get-Item -LiteralPath $_
    [pscustomobject]@{ path = $f.FullName; product_version = $f.VersionInfo.ProductVersion; file_version = $f.VersionInfo.FileVersion; bytes = $f.Length }
})
$runningGm = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '(?i)global.?mapper' } |
    Select-Object Id, ProcessName, StartTime)

$selectedGmFiles = if (-not [string]::IsNullOrWhiteSpace($GlobalMapperExe)) { @($gmFiles | Where-Object { $_.path -ieq [IO.Path]::GetFullPath($GlobalMapperExe) }) } else { @($gmFiles) }

$smoke = [ordered]@{
    requested = [bool]$RunSmoke
    status = 'NOT_REQUESTED'
    script_path = $null
    log_path = $null
    process_id = $null
    exit_code = $null
    elapsed_seconds = $null
    marker_found = $false
    note = 'Run -RunSmoke explicitly to start a minimal .gms; no map data is used.'
}
if ($RunSmoke) {
    $smoke.status = 'NOT_TESTED'
    if ($selectedGmFiles.Count -eq 0) {
        $smoke.note = 'No Global Mapper executable was discovered; provide an exact executable path and rerun after reviewing it.'
    } elseif ($selectedGmFiles.Count -gt 1) {
        $smoke.note = 'Multiple Global Mapper executables were found; choose the correct v27 binary manually before running the test.'
    } elseif ($runningGm.Count -gt 0) {
        $smoke.note = 'Global Mapper is already running; close it deliberately before a separate batch-mode test. No existing instance was touched.'
    } else {
        $exe = $selectedGmFiles[0].path
        $gms = Join-Path $outDir 'zone80_cli_smoke.gms'
        $log = Join-Path $outDir 'zone80_cli_smoke.log'
        if ($gms.Contains('"') -or $log.Contains('"')) { throw 'Output path contains unsupported quotation marks.' }
        @(
            'GLOBAL_MAPPER_SCRIPT VERSION=1.00 ENABLE_PROGRESS=NO LOG_TO_COMMAND_PROMPT=YES',
            ('SET_LOG_FILE FILENAME="' + $log + '" APPEND_TO_FILE=NO'),
            'LOG_MESSAGE Zone80_GM_CLI_SMOKE_OK'
        ) | Set-Content -LiteralPath $gms -Encoding ASCII
        $smoke.script_path = $gms
        $smoke.log_path = $log
        $sw = [Diagnostics.Stopwatch]::StartNew()
        try {
            $proc = Start-Process -FilePath $exe -ArgumentList ('"' + $gms + '"') -PassThru -ErrorAction Stop
            $smoke.process_id = $proc.Id
            $exited = $proc.WaitForExit($TimeoutSeconds * 1000)
            if ($exited) {
                $proc.Refresh()
                $smoke.exit_code = $proc.ExitCode
                $smoke.marker_found = (Test-Path -LiteralPath $log -PathType Leaf) -and [bool](Select-String -LiteralPath $log -Pattern 'Zone80_GM_CLI_SMOKE_OK' -Quiet -ErrorAction SilentlyContinue)
                if ($smoke.exit_code -eq 0 -and $smoke.marker_found) {
                    $smoke.status = 'PASS'
                    $smoke.note = 'Global Mapper ran the no-data GMS from Cursor/PowerShell. GIS imports/exports and license features remain untested.'
                } else {
                    $smoke.status = 'PARTIAL'
                    $smoke.note = 'Process ended but exit code / log marker did not prove GMS execution. Review log and GUI errors.'
                }
            } else {
                $smoke.status = 'TIMEOUT'
                $smoke.note = 'Process did not exit. It may be waiting on license or a modal window; PID is recorded. No process was killed.'
            }
        } catch {
            $smoke.status = 'ERROR'
            $smoke.note = $_.Exception.Message
        } finally { $sw.Stop(); $smoke.elapsed_seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2) }
    }
}

$terminalUser = $null; $executionPolicy = 'UNKNOWN'
try { $terminalUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name } catch { }
try { $executionPolicy = (Get-ExecutionPolicy).ToString() } catch { }

$result = [ordered]@{
    status = 'LOCAL_EVIDENCE_ONLY'
    created_utc = [DateTime]::UtcNow.ToString('o')
    script_powershell_version = $PSVersionTable.PSVersion.ToString()
    cursor_terminal_context = @{
        username = $terminalUser
        current_directory = (Get-Location).Path
        process_id = $PID
        term_program = $env:TERM_PROGRAM
        vscode_pid = $env:VSCODE_PID
        execution_policy = $executionPolicy
    }
    os_registry = $osReg
    os_cim = if ($osInfo) { $osInfo | Select-Object Caption, Version, BuildNumber, OSArchitecture, FreePhysicalMemory } else { $null }
    cpu = $cpuInfo
    logical_processor_count = [Environment]::ProcessorCount
    physical_ram_bytes = if ($machineInfo) { [int64]$machineInfo.TotalPhysicalMemory } else { $null }
    graphics = $gpuInfo
    pagefiles = $pageInfo
    disks = $drives
    tools_on_path = $tools
    global_mapper_registry = $registryInstalls
    global_mapper_candidates = $gmFiles
    already_running_global_mapper = $runningGm
    global_mapper_license_type = 'UNKNOWN - verify Standard/Pro in app without copying keys'
    global_mapper_cli_smoke = $smoke
    warnings = @($warnings.ToArray())
    limitations = @(
        'Absent tools on PATH may still be installed elsewhere.',
        'Failed CIM/WMI calls are unknown measurements, not zero RAM or absent GPU.',
        'A passing GMS smoke proves scripting only, not data import/export or large-area performance.',
        'Script writes diagnostic files only in a new reports/gm_probe_* directory. The application may update its own normal settings/cache during launch.',
        'Do not publish this JSON without redacting user-specific local paths.'
    )
}
$reportFile = Join-Path $outDir 'environment.json'
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportFile -Encoding UTF8
Write-Host "Zone80 local environment audit: $reportFile"
Write-Host "Global Mapper CLI smoke status: $($smoke.status)"
Write-Host 'No GIS datasets were imported or modified.'