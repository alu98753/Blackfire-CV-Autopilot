param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Task,

    [string]$ReviewModel,

    [switch]$SkipTests
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
$specPath = Join-Path $repoRoot $specRel
if ([string]::IsNullOrWhiteSpace($specRel) -or -not (Test-Path $specPath)) {
    throw "Canonical spec not found: $specRel"
}

$baseRef = [string]$config.base_ref
if ([string]::IsNullOrWhiteSpace($baseRef)) {
    throw "task.json must define base_ref."
}

if ([string]::IsNullOrWhiteSpace($ReviewModel) -and $null -ne $config.models) {
    $ReviewModel = [string]$config.models.review
}

$runtimeDir = Join-Path $repoRoot ".runtime\ai_gate\$Task"
$reviewDir = Join-Path $taskDir "reviews"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null

$statusPath = Join-Path $runtimeDir "status.txt"
$diffPath = Join-Path $runtimeDir "diff.patch"

$gitStatus = & git status --short 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "git status failed.`n$gitStatus"
}
Set-Content -Path $statusPath -Value $gitStatus.TrimEnd() -Encoding UTF8

$gitDiff = & git diff --no-ext-diff --unified=80 $baseRef -- . 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "git diff against '$baseRef' failed.`n$gitDiff"
}
Set-Content -Path $diffPath -Value $gitDiff.TrimEnd() -Encoding UTF8

function Invoke-ReviewAgent {
    param(
        [Parameter(Mandatory = $true)][string]$Agent,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $prompt = @"
Task descriptor: .ai/tasks/$Task/task.json
Canonical spec: $specRel
Repository status snapshot: .runtime/ai_gate/$Task/status.txt
Candidate diff snapshot: .runtime/ai_gate/$Task/diff.patch
Comparison baseline: $baseRef

Review the candidate patch using the current repository state. Follow the '$Agent' agent contract exactly. Treat the snapshots as evidence, but inspect current repository files with read/search tools when needed. Do not edit files or run shell commands.
"@

    $args = @("run", "--agent", $Agent)
    if (-not [string]::IsNullOrWhiteSpace($ReviewModel)) {
        $args += @("--model", $ReviewModel)
    }
    $args += $prompt

    Write-Host "Running OpenCode agent '$Agent'..."
    $result = & opencode @args 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "OpenCode agent '$Agent' failed with exit code $LASTEXITCODE.`n$result"
    }

    Set-Content -Path $OutputPath -Value $result.TrimEnd() -Encoding UTF8
    return $result
}

$specReviewPath = Join-Path $reviewDir "spec-review.md"
$regressionReviewPath = Join-Path $reviewDir "regression-review.md"
$specReview = Invoke-ReviewAgent -Agent "spec-reviewer" -OutputPath $specReviewPath
$regressionReview = Invoke-ReviewAgent -Agent "regression-reviewer" -OutputPath $regressionReviewPath

function Get-ReviewVerdict {
    param([string]$Text)
    $verdict = [regex]::Match($Text, '(?m)^VERDICT:\s*(PASS|BLOCK)\s*$')
    $count = [regex]::Match($Text, '(?m)^BLOCKING_FINDINGS:\s*(\d+)\s*$')
    if (-not $verdict.Success -or -not $count.Success) {
        return [pscustomobject]@{ Verdict = "INVALID"; Blocking = -1 }
    }
    return [pscustomobject]@{ Verdict = $verdict.Groups[1].Value; Blocking = [int]$count.Groups[1].Value }
}

$specVerdict = Get-ReviewVerdict $specReview
$regressionVerdict = Get-ReviewVerdict $regressionReview

$testResults = @()
$testsPassed = $true
if (-not $SkipTests -and $null -ne $config.focused_tests -and $config.focused_tests.Count -gt 0) {
    $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Focused tests are configured but .venv\Scripts\python.exe was not found."
    }

    foreach ($target in $config.focused_tests) {
        $targetText = [string]$target
        if ($targetText -match '(?i)discover\s+tests|unittest\s+discover|^tests$|\*') {
            throw "Rejected unsafe/full-suite focused test target: '$targetText'"
        }
        if ([string]::IsNullOrWhiteSpace($targetText)) {
            continue
        }

        $safeName = ($targetText -replace '[^A-Za-z0-9_.-]', '_')
        $logPath = Join-Path $runtimeDir ("test-" + $safeName + ".log")
        Write-Host "Running focused test: $targetText"
        $testOutput = & $python -m unittest $targetText 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
        Set-Content -Path $logPath -Value $testOutput.TrimEnd() -Encoding UTF8
        $passed = ($exitCode -eq 0)
        if (-not $passed) {
            $testsPassed = $false
        }
        $testResults += [pscustomobject]@{
            Target = $targetText
            Passed = $passed
            ExitCode = $exitCode
            Log = ".runtime/ai_gate/$Task/$(Split-Path $logPath -Leaf)"
        }
    }
}

$head = (& git rev-parse HEAD 2>&1 | Out-String).Trim()
$branch = (& git branch --show-current 2>&1 | Out-String).Trim()
$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")

$evidence = New-Object System.Collections.Generic.List[string]
$evidence.Add("# Verification Evidence")
$evidence.Add("")
$evidence.Add("Task: `$Task`")
$evidence.Add("Generated: $timestamp")
$evidence.Add("Branch: `$branch`")
$evidence.Add("HEAD: `$head`")
$evidence.Add("Base ref: `$baseRef`")
$evidence.Add("")
$evidence.Add("## Review verdicts")
$evidence.Add("")
$evidence.Add("- Spec reviewer: $($specVerdict.Verdict) (blocking=$($specVerdict.Blocking))")
$evidence.Add("- Regression reviewer: $($regressionVerdict.Verdict) (blocking=$($regressionVerdict.Blocking))")
$evidence.Add("")
$evidence.Add("Detailed reports:")
$evidence.Add("")
$evidence.Add("- `reviews/spec-review.md`")
$evidence.Add("- `reviews/regression-review.md`")
$evidence.Add("")
$evidence.Add("## Focused tests")
$evidence.Add("")
if ($SkipTests) {
    $evidence.Add("Focused tests skipped by explicit `-SkipTests`.")
} elseif ($testResults.Count -eq 0) {
    $evidence.Add("No focused tests declared in task.json.")
} else {
    foreach ($result in $testResults) {
        $status = if ($result.Passed) { "PASS" } else { "FAIL" }
        $evidence.Add("- $status `$($result.Target)` (exit=$($result.ExitCode)); local log: `$($result.Log)`")
    }
}
$evidence.Add("")
$evidence.Add("## Full suite")
$evidence.Add("")
$evidence.Add("Not run by the AI gate. Repository policy requires the user to run the full suite manually when required.")
$evidence.Add("")
$evidence.Add("## Candidate snapshot")
$evidence.Add("")
$evidence.Add("Ephemeral status/diff snapshots are stored under `.runtime/ai_gate/$Task/` and are intentionally git-ignored.")

$evidencePath = Join-Path $taskDir "EVIDENCE.md"
Set-Content -Path $evidencePath -Value ($evidence -join "`n") -Encoding UTF8

$blocked = (
    $specVerdict.Verdict -ne "PASS" -or
    $specVerdict.Blocking -ne 0 -or
    $regressionVerdict.Verdict -ne "PASS" -or
    $regressionVerdict.Blocking -ne 0 -or
    -not $testsPassed
)

Write-Host "Verification evidence written to .ai/tasks/$Task/EVIDENCE.md"
if ($blocked) {
    Write-Error "AI verification gate BLOCKED. Inspect EVIDENCE.md and reviewer reports."
    exit 2
}

Write-Host "AI verification gate PASSED. Final ChatGPT/human review is still required."
exit 0
