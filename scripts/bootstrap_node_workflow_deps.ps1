param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

. (Join-Path $PSScriptRoot 'node_workflow_contract.ps1')

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    throw "Node.js is not installed or not available on PATH. Install Node.js $NodeEngineRequiredSpec first."
}

$installedNodeVersion = Get-NodeVersion -Executable $nodeCmd.Source
Assert-NodeSupportedVersion -Version $installedNodeVersion

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    throw "npm is not installed or not available on PATH. Install Node.js/npm first."
}

$packageJson = Join-Path $repoRoot 'package.json'
if (-not (Test-Path $packageJson)) {
    throw "Root package.json not found in '$repoRoot'."
}

$packageLock = Join-Path $repoRoot 'package-lock.json'
if (-not (Test-Path $packageLock)) {
    throw "Root package-lock.json not found in '$repoRoot'."
}

Write-Host "Installing repository Node workflow dependencies with 'npm ci'..."
Write-Host "Target worktree: $repoRoot"
Write-Host "Node.js: $installedNodeVersion"
Write-Host ""

& cmd.exe /d /s /c "npm ci"
if ($LASTEXITCODE -ne 0) {
    throw "npm ci failed with exit code $LASTEXITCODE."
}

# Verify readiness after installation
Assert-NodeWorkflowDependenciesReady -RepoRoot $repoRoot -Executable $nodeCmd.Source

Write-Host ""
Write-Host "Node workflow dependencies verified for worktree:"
Write-Host "  $repoRoot"
Write-Host "  Node.js: $installedNodeVersion"
Write-Host "  Packages ready: @opencode-ai/sdk, cross-spawn, undici"
