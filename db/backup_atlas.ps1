# db/backup_atlas.ps1 - mongodump of one database to a folder OUTSIDE the repository (ml/docs/DECISIONS.md D93).
# See db/BACKUP.md. Uses the mongo:7 image's database tools through Docker, so nothing needs installing.
# The connection string is read from the environment or the repo's .env (BACKEND_MONGO_URI, else MONGO_URI) and
# handed to the container as an environment variable: it is never printed and never on a command line.
#
#   powershell -ExecutionPolicy Bypass -File db\backup_atlas.ps1 -OutDir D:\altinvest-backups
#   powershell -ExecutionPolicy Bypass -File db\backup_atlas.ps1 -OutDir D:\altinvest-backups -Database altinvest_db
param(
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Database = "altinvest_db"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$out = [System.IO.Path]::GetFullPath($OutDir)        # checked before anything is created
$repoKey = $repo.TrimEnd("\").ToLower() + "\"
if (($out.TrimEnd("\").ToLower() + "\").StartsWith($repoKey)) {
    throw "refusing: $out is inside the repository ($repo); backups must never be committed. Choose a folder outside it."
}
New-Item -ItemType Directory -Force $out | Out-Null

function Get-EnvFileValue([string]$name) {
    $envFile = Join-Path $repo ".env"
    if (-not (Test-Path $envFile)) { return $null }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$name\s*=\s*(.+?)\s*$") { return $Matches[1].Trim('"').Trim("'") }
    }
    return $null
}
$uri = $env:BACKEND_MONGO_URI
if (-not $uri) { $uri = Get-EnvFileValue "BACKEND_MONGO_URI" }
if (-not $uri) { $uri = $env:MONGO_URI }
if (-not $uri) { $uri = Get-EnvFileValue "MONGO_URI" }
if (-not $uri) { throw "no BACKEND_MONGO_URI or MONGO_URI in the environment or .env" }
$hostOnly = ($uri -replace "^[a-z+]+://", "" -replace "^[^@]*@", "" -split "[/?]")[0]

$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ssZ")
$folder = "$Database-$stamp"
Write-Host "mongodump of $Database on $hostOnly -> $out\$folder"
$env:ALTINVEST_DUMP_URI = $uri
try {
    docker run --rm -e ALTINVEST_DUMP_URI -v "${out}:/backup" mongo:7 sh -c "mongodump --uri=`"`$ALTINVEST_DUMP_URI`" --db=$Database --gzip --out=/backup/$folder"
    if ($LASTEXITCODE -ne 0) { throw "mongodump failed (exit $LASTEXITCODE)" }
} finally {
    Remove-Item Env:\ALTINVEST_DUMP_URI -ErrorAction SilentlyContinue
}
Get-ChildItem "$out\$folder\$Database" | Measure-Object -Property Length -Sum | ForEach-Object { Write-Host ("{0} files, {1:N0} bytes" -f $_.Count, $_.Sum) }
Write-Host ""
Write-Host "Restore (REPLACES each collection in the dump with its backed-up content; see db/BACKUP.md):"
Write-Host "  `$env:ALTINVEST_DUMP_URI = <the same URI>"
Write-Host "  docker run --rm -e ALTINVEST_DUMP_URI -v `"${out}:/backup`" mongo:7 sh -c 'mongorestore --uri=`"`$ALTINVEST_DUMP_URI`" --gzip --drop --nsInclude=`"$Database.*`" /backup/$folder'"
