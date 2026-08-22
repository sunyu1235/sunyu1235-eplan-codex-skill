param(
    [Parameter(Mandatory=$true)][string]$Destination
)

$ErrorActionPreference = 'Stop'
$base = 'https://raw.githubusercontent.com/covagashi/eplan-rag-mcp/main/claude-skills/eplan-development/skills/eplan-development/references'
$files = @(
    'actions-reference.md',
    'api-data-access.md',
    'core-classes.md',
    'e3d-installation-spaces.md',
    'integration-patterns.md',
    'pitfalls.md',
    'remoting.md',
    'script-basics.md'
)

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
foreach ($file in $files) {
    $uri = "$base/$file"
    $out = Join-Path $Destination $file
    Write-Host "Fetching $file"
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $out
}
