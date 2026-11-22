# Read-only inventory; never start tools, mount P:, or inspect any PBO.
[CmdletBinding()]
param([string]$ToolsRoot = "")
$ErrorActionPreference = "Stop"
$warnings = New-Object 'System.Collections.Generic.List[string]'
$roots = New-Object 'System.Collections.Generic.List[string]'
if (-not [string]::IsNullOrWhiteSpace($ToolsRoot)) {
    if (Test-Path -LiteralPath $ToolsRoot -PathType Container) {
        $roots.Add([IO.Path]::GetFullPath($ToolsRoot))
    } else { $warnings.Add("Explicit ToolsRoot not found; no fallback performed.") }
} else {
    $programRoots = @($env:ProgramFiles, [Environment]::GetEnvironmentVariable("ProgramFiles(x86)"))
    foreach ($programRoot in $programRoots) {
        if ([string]::IsNullOrWhiteSpace($programRoot)) { continue }
        $candidate = Join-Path $programRoot "Steam\steamapps\common\Arma 3 Tools"
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            $roots.Add([IO.Path]::GetFullPath($candidate))
        }
    }
}
$wanted = @(
    "Arma3Tools.exe", "TerrainBuilder.exe", "ObjectBuilder.exe",
    "AddonBuilder.exe", "Binarize.exe", "CfgConvert.exe",
    "TerrainProcessor.exe", "WorkDrive.exe", "BankRev.exe"
)
$results = New-Object 'System.Collections.Generic.List[object]'
foreach ($rootPath in ($roots | Sort-Object -Unique)) {
    # Installation root and two subdirectory levels only. No full-disk/P: scan.
    $level1 = @(Get-ChildItem -LiteralPath $rootPath -Directory -ErrorAction SilentlyContinue)
    $level2 = @($level1 | ForEach-Object {
        Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue
    })
    $dirs = @($rootPath) + @($level1 | ForEach-Object FullName) + @($level2 | ForEach-Object FullName)
    foreach ($dir in ($dirs | Sort-Object -Unique)) {
        foreach ($item in @(Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue)) {
            if ($wanted -notcontains $item.Name) { continue }
            $results.Add([pscustomobject]@{
                executable = $item.Name
                path = $item.FullName
                file_version = $item.VersionInfo.FileVersion
                product_version = $item.VersionInfo.ProductVersion
                bytes = $item.Length
            })
        }
    }
}
$p = $null
try { $p = Get-PSDrive -Name P -PSProvider FileSystem -ErrorAction SilentlyContinue } catch {
    $warnings.Add("P: PSDrive query denied: " + $_.Exception.Message)
}
[pscustomobject]@{
    status = if ($results.Count -gt 0) { "FOUND_EXECUTABLES_NOT_FUNCTIONALLY_TESTED" } else { "NOT_FOUND_OR_INACCESSIBLE" }
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    power_shell = $PSVersionTable.PSVersion.ToString()
    scan_scope = "Explicit ToolsRoot or default Steam roots; max two directory levels"
    requested_root = if ($ToolsRoot) { $ToolsRoot } else { $null }
    roots_seen = @($roots | Sort-Object -Unique)
    p_drive = @{
        present_as_psdrive = [bool]$p
        root = if ($p) { $p.Root } else { $null }
        mounted_by_this_script = $false
    }
    tools = @($results | Sort-Object executable, path)
    warnings = @($warnings)
    notice = "Read-only inventory. No GUI, addon packing, protected-asset access or Cursor launch tested. Keep paths local."
} | ConvertTo-Json -Depth 7
