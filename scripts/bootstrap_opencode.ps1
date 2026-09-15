param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "npm is unavailable. Install Node.js/npm first, then rerun this script."
}

$packageLock = Join-Path $repoRoot "package-lock.json"
$npmArgs = if (Test-Path $packageLock) { @("ci", "--ignore-scripts") } else { @("install", "--ignore-scripts") }
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
