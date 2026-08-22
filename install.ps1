param(
    [ValidateSet('Global','Project')][string]$Scope = 'Global',
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$SetupMcp
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $packageRoot 'skill\eplan-development'

if ($Scope -eq 'Global') {
    $destination = Join-Path $env:USERPROFILE '.codex\skills\eplan-development'
} else {
    $destination = Join-Path $ProjectRoot '.agents\skills\eplan-development'
}

New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item -Recurse -Force (Join-Path $source '*') $destination

$downloadScript = Join-Path $packageRoot 'scripts\download-references.ps1'
& $downloadScript -Destination (Join-Path $destination 'references')

Write-Host "Installed Codex EPLAN skill to: $destination"

if ($SetupMcp) {
    & (Join-Path $packageRoot 'scripts\setup-eplan-mcp.ps1')
}

Write-Host 'Restart Codex if the skill does not appear immediately.'
