param(
    [ValidateSet('starter','expanded')]
    [string]$Mode = 'starter',
    [ValidateSet('yes','no')]
    [string]$IncludeVendor = 'yes',
    [string]$OutDir = '.cad-cache'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Collector = Join-Path $PSScriptRoot 'collect_cad_libraries.py'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3 is required.'
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required.'
}

Push-Location $RepoRoot
try {
    python $Collector --out $OutDir --mode $Mode --include-vendor $IncludeVendor
    if ($LASTEXITCODE -ne 0) { throw "collector failed with exit code $LASTEXITCODE" }
    Write-Host "CAD cache: $(Resolve-Path $OutDir)"
} finally {
    Pop-Location
}
