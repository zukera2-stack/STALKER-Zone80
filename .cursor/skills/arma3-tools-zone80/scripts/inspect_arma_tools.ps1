# STALKER-Zone80 / Cursor - read-only Arma 3 Tools inventory.
# Does not start programs, mount P:, change preferences, or inspect/copy PBOs.
[CmdletBinding()]
param([string]$ToolsRoot = "")
$ErrorActionPreference = 'Stop'
$warnings = New-Object 'System.Collections.Generic.List[string]'
$roots = New-Object 'System.Collections.Generic.List[string]'
if (-not [string]::IsNullOrWhiteSpace($ToolsRoot)) {
    if (Test-Path -LiteralPath $ToolsRoot -PathType Container) {
        $roots.Add([IO.Path]::GetFullPath($ToolsRoot))
    } else { $warnings.Add('Specified ToolsRoot is inaccessible or absent. No fallback search.') }
} else {
    $programRoots = @($env:ProgramFiles, [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))
    foreach ($root in $programRoots) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $location = Join-Path $root 'Steam\steamapps\common\Arma 3 Tools'
        if (Test-Path -LiteralPath $location -PathType Container) {
            $roots.Add([IO.Path]::GetFullPath($location))
        }
    }
}
$wanted = @('Arma3Tools.exe', 'TerrainBuilder.exe', 'ObjectBuilder.exe',
            'AddonBuilder.exe', 'Binarize.exe', 'CfgConvert.exe',
            'TerrainProcessor.exe', 'WorkDrive.exe', 'BankRev.exe')
$found = New-Object 'System.Collections.Generic.List[object]'
foreach ($root in ($roots | Sort-Object -Unique)) {
    $l1 = @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)
    $l2 = @($l1 | ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Directory -ErrorAction SilentlyContinue })
    $dirs = @($root) + @($l1 | ForEach-Object FullName) + @($l2 | ForEach-Object FullName)
    foreach ($dir in ($dirs | Sort-Object -Unique)) {
        foreach ($item in @(Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue)) {
            if ($wanted -notcontains $item.Name) { continue }
            $found.Add([pscustomobject]@{
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
try { $p = Get-PSDrive -Name P -PSProvider FileSystem -ErrorAction SilentlyContinue }
catch { $warnings.Add('Cannot query P: ' + $_.Exception.Message) }
[pscustomobject]@{
    status = if ($found.Count -gt 0) { 'FOUND_NOT_FUNCTIONALLY_TESTED' } else { 'NOT_FOUND_OR_INACCESSIBLE' }
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    powershell = $PSVersionTable.PSVersion.ToString()
    roots_seen = @($roots | Sort-Object -Unique)
    p_drive = @{
        present_as_psdrive = [bool]$p
        root = if ($p) { $p.Root } else { $null }
        mounted_by_script = $false
    }
    tools = @($found | Sort-Object executable, path)
    warnings = @($warnings)
    notice = 'Read-only inventory. No Arma tools were executed; keep raw paths private.'
} | ConvertTo-Json -Depth 7
