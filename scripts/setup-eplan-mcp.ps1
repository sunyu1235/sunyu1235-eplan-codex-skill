param(
    [string]$InstallRoot = "$env:USERPROFILE\.codex\eplan-tools\eplan-rag-mcp",
    [switch]$SkipRag
)

$ErrorActionPreference = 'Stop'

function Require-Command([string]$name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "Required command not found: $name" }
    return $cmd.Source
}

$git = Require-Command 'git'
$codex = Require-Command 'codex'

$pythonCmd = $null
$pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = (Get-Command py).Source
    $pythonArgs = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = (Get-Command python).Source
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = (Get-Command python3).Source
} else {
    throw 'Python 3.10+ (64-bit) is required.'
}

if (Test-Path (Join-Path $InstallRoot '.git')) {
    Write-Host 'Updating upstream EPLAN toolkit...'
    & $git -C $InstallRoot pull --ff-only
} else {
    if (Test-Path $InstallRoot) { Remove-Item -Recurse -Force $InstallRoot }
    New-Item -ItemType Directory -Force -Path (Split-Path $InstallRoot -Parent) | Out-Null
    Write-Host 'Cloning upstream EPLAN toolkit...'
    & $git clone --depth 1 https://github.com/covagashi/eplan-rag-mcp.git $InstallRoot
}

$serverDir = Join-Path $InstallRoot 'eplan-p8-mcp-server\mcp_server'
$server = Join-Path $serverDir 'server.py'
$requirements = Join-Path $serverDir 'requirements.txt'
if (-not (Test-Path $server)) { throw "EPLAN MCP server.py not found: $server" }

Write-Host 'Installing EPLAN MCP Python dependencies...'
& $pythonCmd @pythonArgs -m pip install -r $requirements

# Replace only our own MCP entries. Unrelated Codex config is preserved.
& $codex mcp remove eplan 2>$null | Out-Null
$stdioArgs = @('mcp','add','eplan','--',$pythonCmd) + $pythonArgs + @($server)
& $codex @stdioArgs

if (-not $SkipRag) {
    & $codex mcp remove eplan_rag 2>$null | Out-Null
    & $codex mcp add eplan_rag --url 'https://rag2026.covaga.xyz/mcp'
}

Write-Host ''
Write-Host 'Configured Codex MCP servers:'
& $codex mcp list
Write-Host ''
Write-Host 'In EPLAN enable: File > Settings > Workstation > Interfaces > Remote access > Allow remote access via Remote Client.'
Write-Host 'Then restart Codex and start EPLAN before asking Codex to connect to eplan.'
