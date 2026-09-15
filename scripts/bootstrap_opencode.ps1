param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "npm is unavailable. Install Node.js/npm first, then rerun this script."
}

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    throw "Node.js 18+ is required by the OpenCode SDK. Node.js was not found. Upgrade Node.js (recommended: current LTS) and rerun scripts/bootstrap_opencode.ps1."
}
$nodeVersion = (& node --version 2>&1 | Out-String).Trim()
$nodeVersionMatch = [regex]::Match($nodeVersion, '^v(?<major>\d+)(?:\.\d+){0,2}')
if ($LASTEXITCODE -ne 0 -or -not $nodeVersionMatch.Success) {
    throw "Unable to determine the Node.js version from 'node --version'. Install Node.js 18+ (recommended: current LTS) and rerun scripts/bootstrap_opencode.ps1."
}
$nodeMajor = [int]$nodeVersionMatch.Groups['major'].Value
if ($nodeMajor -lt 18) {
    throw "Node.js 18+ is required by the OpenCode SDK. Current version: $nodeVersion. Upgrade Node.js (recommended: current LTS) and rerun scripts/bootstrap_opencode.ps1."
}

$packageLock = Join-Path $repoRoot "package-lock.json"
$npmArgs = @("ci", "--ignore-scripts")
& npm @npmArgs
if ($LASTEXITCODE -ne 0) { throw "Failed to install the pinned repository-local OpenCode SDK dependency." }

& node (Join-Path $repoRoot "scripts\opencode_structured_review.mjs") --check-sdk
if ($LASTEXITCODE -ne 0) { throw "Repository-local OpenCode SDK verification failed." }

function Get-OpenCodeCommand {
    return Get-Command opencode -ErrorAction SilentlyContinue
}

$existing = Get-OpenCodeCommand
if ($existing) {
    Write-Host "OpenCode is already installed:"
    & opencode --version
    Write-Host ""
    Write-Host "If no provider is connected yet, run 'opencode' in the repository and use /connect."
    exit 0
}

Write-Host "Installing OpenCode with the official npm package (opencode-ai)..."
& npm install -g opencode-ai
if ($LASTEXITCODE -ne 0) {
    throw "npm install -g opencode-ai failed with exit code $LASTEXITCODE."
}

$installed = Get-OpenCodeCommand
if (-not $installed) {
    throw "Installation completed but 'opencode' is not available on PATH. Open a new terminal and run 'opencode --version'."
}

Write-Host ""
Write-Host "OpenCode installation verified:"
& opencode --version
Write-Host ""
Write-Host "Next interactive step (credentials are never stored in this repository):"
Write-Host "  1. Set-Location to the repository root"
Write-Host "  2. Run: opencode"
Write-Host "  3. Use: /connect"
