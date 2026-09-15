param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "opencode_contract.ps1")

function Get-OpenCodeCommand {
    return Get-Command opencode -ErrorAction SilentlyContinue
}

$existing = Get-OpenCodeCommand
if ($existing) {
    $installedVersion = Get-OpenCodeVersion -Executable $existing.Source
    Assert-OpenCodeSupportedVersion -Version $installedVersion
    Write-Host "OpenCode is already installed:"
    Write-Host "OpenCode $installedVersion"
    Write-Host ""
    Write-Host "If no provider is connected yet, run 'opencode' in the repository and use /connect."
    exit 0
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "OpenCode is not installed and npm is unavailable. Install Node.js/npm first, then rerun this script."
}

Write-Host "Installing OpenCode with the official npm package (opencode-ai)..."
& npm install -g "opencode-ai@$OpenCodeSupportedVersion"
if ($LASTEXITCODE -ne 0) {
    throw "npm install -g opencode-ai@$OpenCodeSupportedVersion failed with exit code $LASTEXITCODE."
}

$installed = Get-OpenCodeCommand
if (-not $installed) {
    throw "Installation completed but 'opencode' is not available on PATH. Open a new terminal and run 'opencode --version'."
}

$installedVersion = Get-OpenCodeVersion -Executable $installed.Source
Assert-OpenCodeSupportedVersion -Version $installedVersion

Write-Host ""
Write-Host "OpenCode installation verified:"
Write-Host "OpenCode $installedVersion"
Write-Host ""
Write-Host "Next interactive step (credentials are never stored in this repository):"
Write-Host "  1. Set-Location to the repository root"
Write-Host "  2. Run: opencode"
Write-Host "  3. Use: /connect"
