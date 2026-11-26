[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$OutputPath,
    [string]$ProjectPath = (Get-Location).Path,
    [string[]]$ProcessName = @('Unity','blender','TerrainBuilder','global_mapper')
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows required' }
$root = (Resolve-Path -LiteralPath $ProjectPath).ProviderPath
$out = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
if (Test-Path -LiteralPath $out) { throw 'Output already exists; choose a new file' }
$parent = Split-Path -Parent $out
if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw 'Output directory must already exist' }
$report = [ordered]@{
    schema = 1; utc = [DateTime]::UtcNow.ToString('o'); project = $root
    powershell = $PSVersionTable.PSVersion.ToString(); edition = $PSVersionTable.PSEdition
    os = [Environment]::OSVersion.VersionString; process64 = [Environment]::Is64BitProcess
    interactive = [Environment]::UserInteractive; session = (Get-Process -Id $PID).SessionId
    commands = @(); processes = @(); git = $null; warnings = @()
}
foreach ($name in @('git','dotnet','python','py','pwsh','powershell.exe')) {
    $cmd = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $cmd) { $report.commands += @{name=$name; status='NOT_ON_PATH'} }
    else { $report.commands += @{name=$name; status='FOUND'; path=$cmd.Source; version=[string]$cmd.Version} }
}
foreach ($name in $ProcessName) {
    foreach ($p in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
        $item = @{name=$p.ProcessName; pid=$p.Id; session=$null; path=$null; start=$null; window=$null}
        try { $item.session = $p.SessionId; $item.path = $p.Path; $item.start = $p.StartTime.ToUniversalTime().ToString('o'); $item.window = $p.MainWindowHandle.ToInt64() }
        catch { $report.warnings += "Process $($p.Id) metadata incomplete" }
        $report.processes += $item
    }
}
$git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -ne $git) {
    Push-Location -LiteralPath $root
    try {
        $top = & $git.Source rev-parse --show-toplevel 2>&1
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            $sha = & $git.Source rev-parse HEAD; $shaCode = $LASTEXITCODE
            $branch = & $git.Source rev-parse --abbrev-ref HEAD; $branchCode = $LASTEXITCODE
            $status = & $git.Source --no-optional-locks status --porcelain=v1; $statusCode = $LASTEXITCODE
            $report.git = @{root=[string]$top; sha=[string]$sha; branch=[string]$branch; status=@($status); exit_codes=@($shaCode,$branchCode,$statusCode)}
        } else { $report.warnings += "git root unavailable (exit $code)" }
    } catch { $report.warnings += 'Git probe incomplete; inspect locally' }
    finally { Pop-Location }
}
$json = $report | ConvertTo-Json -Depth 8
# CreateNew refuses to overwrite even if another process created the file meanwhile.
$stream = [System.IO.File]::Open($out,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write)
try {
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json)
    $stream.Write($bytes,0,$bytes.Length)
} finally { $stream.Dispose() }
Write-Output "Report: $out"
Get-FileHash -LiteralPath $out -Algorithm SHA256
