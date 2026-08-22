param(
    [ValidateSet('Global','Project')][string]$Scope = 'Global',
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$SetupMcp
)

$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Install-CodexSkill {
    param(
        [Parameter(Mandatory=$true)][string]$SkillName,
        [Parameter(Mandatory=$true)][string]$Source
    )

    if (-not (Test-Path $Source)) {
        throw "Skill source not found: $Source"
    }

    if ($Scope -eq 'Global') {
        $destination = Join-Path $env:USERPROFILE ".codex\skills\$SkillName"
    } else {
        $destination = Join-Path $ProjectRoot ".agents\skills\$SkillName"
    }

    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Recurse -Force (Join-Path $Source '*') $destination
    Write-Host "Installed Codex skill '$SkillName' to: $destination"
    return $destination
}

$eplanSource = Join-Path $packageRoot 'skill\eplan-development'
$eplanDestination = Install-CodexSkill -SkillName 'eplan-development' -Source $eplanSource

$downloadScript = Join-Path $packageRoot 'scripts\download-references.ps1'
& $downloadScript -Destination (Join-Path $eplanDestination 'references')

$cadSource = Join-Path $packageRoot 'skill\cad-parts-no-login'
Install-CodexSkill -SkillName 'cad-parts-no-login' -Source $cadSource | Out-Null

if ($SetupMcp) {
    & (Join-Path $packageRoot 'scripts\setup-eplan-mcp.ps1')
}

Write-Host 'Installed EPLAN + no-login CAD parts skills.'
Write-Host 'Restart Codex if the skills do not appear immediately.'
