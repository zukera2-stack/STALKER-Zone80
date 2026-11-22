param([string]$MapperHome)
$ErrorActionPreference = 'Stop'
if (!$IsWindows) { Write-Output 'SKIP / NOT TESTED: Windows required'; exit 0 }
if (!$MapperHome) { $MapperHome = Join-Path $env:ProgramFiles 'GlobalMapper26.2_64bit' }
$ErrorActionPreference='Stop'
$exe = Join-Path $MapperHome 'global_mapper26.2.exe'
if (!(Test-Path -LiteralPath $exe -PathType Leaf) -or !(Test-Path -LiteralPath (Join-Path $MapperHome 'gdal.dll') -PathType Leaf)) {
    Write-Output 'SKIP / NOT TESTED: Global Mapper 26.2 launcher or GDAL DLL missing'
    exit 0
}
$MapperHome = (Resolve-Path -LiteralPath $MapperHome).Path
$exe = Join-Path $MapperHome 'global_mapper26.2.exe'
if (!(Get-Command python -ErrorAction SilentlyContinue)) { Write-Output 'SKIP / NOT TESTED: Python missing'; exit 0 }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$reports = New-Item -ItemType Directory -Path (Join-Path $repo 'reports') -Force
if ($reports.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'reports must be a local directory' }
$Root = (New-Item -ItemType Directory -Path (Join-Path $reports.FullName ('gis04-' + [guid]::NewGuid().ToString('N')))).FullName
$env:GIS_TILE_ROOT = $Root
$env:GIS_MAPPER_HOME = $MapperHome
$env:PROJ_DATA = $MapperHome
$env:PYTHONOPTIMIZE = ''
Write-Output "Evidence: $Root"
python (Join-Path $PSScriptRoot 'generate.py')
if ($LASTEXITCODE) { throw 'Fixture generation failed' }
$sourceBefore = (Get-FileHash -LiteralPath (Join-Path $Root 'features.geojson')).Hash
function Snapshot($dir){
Get-ChildItem -LiteralPath $dir -File | Sort-Object Name | ForEach-Object {
[pscustomobject]@{name=$_.Name; bytes=$_.Length; sha256=(Get-FileHash -LiteralPath $_.FullName).Hash; modified=$_.LastWriteTimeUtc.Ticks}
}
}
$round=0
foreach($tile in 'W','E','W'){
$round++
$d=Join-Path $Root $tile
if($round -eq 3){$eastBefore=@(Snapshot (Join-Path $Root 'E'))}
$prior=@(Get-Process -Name 'global_mapper*' -ErrorAction SilentlyContinue | ForEach-Object Id)
if($prior.Count){throw 'Close existing test/app processes before capturing isolated metrics'}
$oldLog=Join-Path $d 'batch.log'
if(Test-Path $oldLog){Move-Item $oldLog (Join-Path $Root 'W-first.log')}
$watch=[Diagnostics.Stopwatch]::StartNew()
$proc=Start-Process -FilePath $exe -ArgumentList ('"{0}"' -f (Join-Path $d 'tile.gms')) -WorkingDirectory $d -WindowStyle Hidden -PassThru
$peaks=@{}
$names=@{}
$done=$false
while($watch.Elapsed.TotalSeconds -lt 20){
 foreach($item in @(Get-Process -Name 'global_mapper*' -ErrorAction SilentlyContinue)){
 try {
 $v=$item.PeakWorkingSet64
 if($v -gt 0 -and (!$peaks.ContainsKey([string]$item.Id) -or $v -gt $peaks[[string]$item.Id])){
 $peaks[[string]$item.Id]=$v
 $names[[string]$item.Id]=$item.ProcessName
 }
 } catch {}
 }
 if((Test-Path $oldLog) -and (Select-String -LiteralPath $oldLog -Pattern 'Script processing COMPLETED' -Quiet)){$done=$true;break}
 Start-Sleep -Milliseconds 10
}
[pscustomobject]@{run=$round; tile=$tile; wall_ms=$watch.ElapsedMilliseconds; completed=$done; peak_working_set_by_pid=$peaks; process_names=$names; files=@(Snapshot $d)} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $Root "run-$round.json")
if (!$done) { throw "GMS timeout: $tile" }
if (!(Select-String -LiteralPath $oldLog -Pattern 'GIS04_COMPLETE' -Quiet) -or
    !(Select-String -LiteralPath $oldLog -Pattern 'Global Mapper Pro v26\.2(?:\s|\()' -Quiet)) {
    throw 'Expected Global Mapper Pro 26.2 and completion marker'
}
$null=$proc.WaitForExit(3000)
Get-Content $oldLog
$deadline = [DateTime]::UtcNow.AddSeconds(5)
while ((Get-Process -Name 'global_mapper*' -ErrorAction SilentlyContinue) -and [DateTime]::UtcNow -lt $deadline) {
    Start-Sleep -Milliseconds 50
}
}
$eastAfter=@(Snapshot (Join-Path $Root 'E'))
if((ConvertTo-Json -InputObject $eastBefore -Compress) -cne (ConvertTo-Json -InputObject $eastAfter -Compress)){throw 'East tile changed on west repeat'}
$eastAfter | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $Root 'east-unchanged.json')
if ((Get-FileHash -LiteralPath (Join-Path $Root 'features.geojson')).Hash -ne $sourceBefore) { throw 'Shared input changed' }
python (Join-Path $PSScriptRoot 'verify.py')
if ($LASTEXITCODE) { throw 'GIS verification failed' }
Write-Output 'PASS: Global Mapper synthetic tile integration'
