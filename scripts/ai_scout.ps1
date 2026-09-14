param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Task,

    [string]$Model
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    throw "OpenCode is not installed. Run .\scripts\bootstrap_opencode.ps1 first."
}

$taskDir = Join-Path $repoRoot ".ai\tasks\$Task"
$taskFile = Join-Path $taskDir "task.json"
if (-not (Test-Path $taskFile)) {
    throw "Task descriptor not found: .ai/tasks/$Task/task.json"
}

$config = Get-Content $taskFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.id -ne $Task) {
    throw "task.json id '$($config.id)' does not match directory/task argument '$Task'."
}

$specRel = [string]$config.spec
if ([string]::IsNullOrWhiteSpace($specRel)) {
    throw "task.json must define a repository-relative 'spec' path."
}
$specPath = Join-Path $repoRoot $specRel
if (-not (Test-Path $specPath)) {
    throw "Canonical spec not found: $specRel"
}

if ([string]::IsNullOrWhiteSpace($Model) -and $null -ne $config.models) {
    $Model = [string]$config.models.scout
}

$prompt = @"
Task descriptor: .ai/tasks/$Task/task.json
Canonical spec: $specRel

Perform a read-only localization audit for this task using the repository state currently checked out. Follow the scout agent contract exactly. Do not edit files or run shell commands. Return only the requested Markdown scout report.
"@

$args = @("run", "--agent", "scout")
if (-not [string]::IsNullOrWhiteSpace($Model)) {
    $args += @("--model", $Model)
}
$args += $prompt

Write-Host "Running OpenCode scout for task '$Task'..."
$output = & opencode @args 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "OpenCode scout failed with exit code $LASTEXITCODE.`n$output"
}

New-Item -ItemType Directory -Force -Path $taskDir | Out-Null
$contextPath = Join-Path $taskDir "CONTEXT.md"
Set-Content -Path $contextPath -Value $output.TrimEnd() -Encoding UTF8

Write-Host "Scout context written to .ai/tasks/$Task/CONTEXT.md"
