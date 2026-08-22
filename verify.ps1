param(
    [ValidateSet('Global','Project')][string]$Scope = 'Global',
    [string]$ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Continue'
if ($Scope -eq 'Global') {
    $skill = Join-Path $env:USERPROFILE '.codex\skills\eplan-development'
} else {
    $skill = Join-Path $ProjectRoot '.agents\skills\eplan-development'
}

Write-Host "Skill: $skill"
if (Test-Path (Join-Path $skill 'SKILL.md')) { Write-Host '[OK] SKILL.md' } else { Write-Host '[MISSING] SKILL.md' }
$refs = Get-ChildItem (Join-Path $skill 'references') -Filter '*.md' -ErrorAction SilentlyContinue
Write-Host "References: $($refs.Count)/8"

$eplanPaths = Get-ChildItem 'C:\Program Files\EPLAN\Platform' -Directory -ErrorAction SilentlyContinue
if ($eplanPaths) {
    Write-Host '[OK] EPLAN Platform installations:'
    $eplanPaths | ForEach-Object { Write-Host "  $($_.FullName)" }
} else {
    Write-Host '[INFO] EPLAN Platform not found in default path.'
}

if (Get-Command codex -ErrorAction SilentlyContinue) {
    Write-Host ''
    Write-Host 'Codex MCP:'
    codex mcp list
} else {
    Write-Host '[MISSING] codex command'
}
