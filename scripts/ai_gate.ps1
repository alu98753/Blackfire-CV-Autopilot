param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-z0-9][a-z0-9-]*$')][string]$Task,
    [string]$ReviewModel, [switch]$SkipTests, [int]$ReviewTimeoutSeconds = 540, [int]$TestTimeoutSeconds = 60,
    [string]$_ReviewerExecutableOverride, [string[]]$_ReviewerArgumentsOverride,
    [string[]]$_SpecReviewerArgumentsOverride, [string[]]$_RegressionReviewerArgumentsOverride,
    [string[]]$_ReviewCandidatesOverride, [string]$_PythonExecutableOverride, [string[]]$_PythonArgumentsOverride,
    [string]$_FailPromotionOnTarget, [string]$_OpenCodeVersionOverride, [switch]$_InvocationProbe
)
$ErrorActionPreference = 'Stop'; $repoRoot = Split-Path $PSScriptRoot -Parent; Set-Location $repoRoot
. (Join-Path $PSScriptRoot 'opencode_contract.ps1')
$taskDir = Join-Path $repoRoot "docs\tasks\$Task"; $taskFile = Join-Path $taskDir 'task.json'; $specPath = Join-Path $taskDir 'SPEC.md'
if (-not (Test-Path $taskFile) -or -not (Test-Path $specPath)) { throw "Task package is incomplete: $Task" }
$config = Get-Content -Raw -Encoding utf8 $taskFile | ConvertFrom-Json; if ($config.id -ne $Task) { throw 'task.json id does not match Task.' }
if ($_ReviewerExecutableOverride) { if ($_OpenCodeVersionOverride) { Assert-OpenCodeSupportedVersion $_OpenCodeVersionOverride } }
else { $oc = Get-Command opencode -ErrorAction SilentlyContinue; if (-not $oc) { throw 'OpenCode is not installed.' }; Assert-OpenCodeSupportedVersion (Get-OpenCodeVersion $oc.Source) }
$baseRef = [string]$config.base_ref; if (-not $baseRef) { throw 'task.json must define base_ref.' }

function Resolve-Candidates($raw, [string]$cli, [string[]]$override) {
    if ($override -and $override.Count) { return @($override | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ }) }
    if ($cli) { return @($cli.Trim()) }; if ($null -eq $raw) { throw 'models.review is missing.' }
    return @($raw | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
}
function Invoke-BoundedProcess([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds) {
    if ($Executable -match '(?i)\.(cmd|bat)$') { $Arguments = @('/c', $Executable) + $Arguments; $Executable = 'cmd.exe' }
    $psi = [Diagnostics.ProcessStartInfo]::new(); $psi.FileName = $Executable; $psi.WorkingDirectory = $repoRoot; $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.RedirectStandardInput = $true
    $escaped = foreach ($arg in @($Arguments)) { $value = ([string]$arg) -replace '(\\*)"', '$1$1\\"'; $value = $value -replace '(\\+)$', '$1$1'; if ($value -match '[\s"]') { '"' + $value + '"' } else { $value } }
    $psi.Arguments = $escaped -join ' '
    $p = [Diagnostics.Process]::Start($psi); if (-not $p) { throw "Failed to start process: $Executable" }; $p.StandardInput.Close()
    # ReadToEndAsync drains both redirected pipes while the child is running.
    # Waiting for the process before reading either pipe is unsafe: a full pipe
    # can block the child and prevent the parent from ever observing exit.
    $stdoutTask = $p.StandardOutput.ReadToEndAsync(); $stderrTask = $p.StandardError.ReadToEndAsync()
    $sw = [Diagnostics.Stopwatch]::StartNew(); $timedOut = $false; $confirmed = $true
    while (-not $p.WaitForExit(50)) {
        if ($sw.Elapsed.TotalSeconds -ge $TimeoutSeconds) { $timedOut = $true; try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { $confirmed = $false }; $confirmed = $confirmed -and ($p.WaitForExit(3000) -or $p.HasExited); break }
    }
    if (-not $timedOut) { $p.WaitForExit() }
    if (-not $stdoutTask.Wait(300) -or -not $stderrTask.Wait(300)) {
        # A wrapper can leave descendants holding inherited pipe handles after
        # its own exit. Close that owned tree before bounded capture finalizes.
        try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { }
        if (-not $stdoutTask.Wait(1000) -or -not $stderrTask.Wait(1000)) { $confirmed = $false }
    }
    $stdout = if ($stdoutTask.IsCompleted) { $stdoutTask.GetAwaiter().GetResult() } else { '' }; $stderr = if ($stderrTask.IsCompleted) { $stderrTask.GetAwaiter().GetResult() } else { '' }; $sw.Stop()
    [pscustomobject]@{ ExitCode = if ($timedOut) { -1 } else { $p.ExitCode }; TimedOut = $timedOut; KillConfirmed = $confirmed; Pid = $p.Id; StdOut = $stdout; StdErr = $stderr; ElapsedSeconds = $sw.Elapsed.TotalSeconds }
}
function New-Invocation([string]$Agent, [string]$Model, [string]$PromptFile) {
    if ($_ReviewerExecutableOverride) {
        $args = if ($Agent -eq 'spec-reviewer' -and $_SpecReviewerArgumentsOverride) { $_SpecReviewerArgumentsOverride } elseif ($Agent -eq 'regression-reviewer' -and $_RegressionReviewerArgumentsOverride) { $_RegressionReviewerArgumentsOverride } elseif ($_ReviewerArgumentsOverride) { $_ReviewerArgumentsOverride } else { @('--agent',$Agent,'--model',$Model,'--directory',$repoRoot,'--prompt-file',$PromptFile) }
        return @{ Executable = $_ReviewerExecutableOverride; Arguments = @($args) }
    }
    return @{ Executable = 'node'; Arguments = @((Join-Path $repoRoot 'scripts\opencode_structured_review.mjs'),'--agent',$Agent,'--model',$Model,'--directory',$repoRoot,'--prompt-file',$PromptFile) }
}
function Read-Envelope([string]$text) {
    $lines = @($text -split "`r?`n" | Where-Object { $_.Trim() }); if (-not $lines.Count) { return $null }
    try { return ($lines[-1] | ConvertFrom-Json) } catch { return $null }
}
function Test-Envelope($env) {
    $classes=@('VALID_PASS','VALID_BLOCK','GROUNDING_FAILED','LIFECYCLE_UNTRUSTWORTHY','STRUCTURED_TRANSPORT_FAILED','STRUCTURED_OUTPUT_MISSING','SCHEMA_INVALID','SEMANTIC_CONTRADICTION','INFRASTRUCTURE_FAILED')
    if ($null -eq $env -or $env.schema_version -ne 1 -or $classes -notcontains [string]$env.classification) { return $false }
    if ($null -eq $env.lifecycle -or $null -eq $env.cleanup -or $env.cleanup.PSObject.Properties.Name -notcontains 'safe') { return $false }
    if ($env.cleanup.safe -ne $true -and $env.cleanup.safe -ne $false) { return $false }
    if ($env.classification -in @('VALID_PASS','VALID_BLOCK') -and $null -eq $env.structured) { return $false }
    return $true
}
function Render-Review($env, [string]$agent) {
    $title = if ($agent -eq 'spec-reviewer') { 'Spec Review' } else { 'Regression Review' }
    return "# $title`n`nGate-accepted verdict: $($env.structured.verdict)`nBlocking findings: $($env.structured.blocking_findings)`n`n$($env.structured.report_markdown)".TrimEnd()
}

$candidates = Resolve-Candidates $config.models.review $ReviewModel $_ReviewCandidatesOverride; if (-not $candidates.Count) { throw 'No review candidates configured.' }
$runtimeDir = Join-Path $repoRoot ".runtime\ai_gate\$Task"; $reviewDir = Join-Path $taskDir 'reviews'; New-Item -ItemType Directory -Force $runtimeDir,$reviewDir | Out-Null
(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git status --short" | Out-String).TrimEnd() | Set-Content (Join-Path $runtimeDir 'status.txt') -Encoding utf8
(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git diff --no-ext-diff $baseRef -- ." | Out-String).TrimEnd() | Set-Content (Join-Path $runtimeDir 'diff.patch') -Encoding utf8
$targets = @(@{ Agent='spec-reviewer'; File='spec-review.md' }, @{ Agent='regression-reviewer'; File='regression-review.md' }); $accepted=@{}; $attempts=@(); $unavailable=$false; $reason=''
foreach ($target in $targets) {
    $acceptedRole = $false; $promptFile = Join-Path $runtimeDir "prompt_$($target.Agent).txt"
    @"
Task descriptor: docs/tasks/$Task/task.json
Canonical spec: docs/tasks/$Task/SPEC.md
Status snapshot: .runtime/ai_gate/$Task/status.txt
Diff snapshot: .runtime/ai_gate/$Task/diff.patch
Comparison baseline: $baseRef

Perform a bounded read-only $($target.Agent) review. Inspect the supplied snapshots and current repository files with read, glob, or grep tools. Do not edit or execute commands. Perform repository grounding before emitting StructuredOutput. Return only the required structured review object.
"@.Trim() | Set-Content $promptFile -Encoding utf8
    foreach ($model in $candidates) {
        $inv = New-Invocation $target.Agent $model $promptFile; if ($_InvocationProbe) { [pscustomobject]@{ Agent=$target.Agent; Arguments=$inv.Arguments } | ConvertTo-Json -Compress; exit 0 }
        Write-Host "Running $($target.Agent) [$model]..."; $res = Invoke-BoundedProcess $inv.Executable $inv.Arguments $ReviewTimeoutSeconds
        $raw = ($res.StdOut,$res.StdErr | Where-Object { $_ }) -join "`n"; $raw | Set-Content (Join-Path $runtimeDir "$($target.Agent)_$($attempts.Count+1).log") -Encoding utf8
        $env = if (-not $res.TimedOut) { Read-Envelope $res.StdOut } else { $null }
        $envelopeValid = Test-Envelope $env; $class = if ($res.TimedOut -and -not $res.KillConfirmed) { 'INFRASTRUCTURE_FAILED' } elseif ($res.TimedOut) { 'INFRASTRUCTURE_FAILED' } elseif ($envelopeValid) { [string]$env.classification } elseif ($res.ExitCode -ne 0) { 'INFRASTRUCTURE_FAILED' } else { 'STRUCTURED_TRANSPORT_FAILED' }
        $attempts += [pscustomobject]@{ Role=$target.Agent; Model=$model; Classification=$class; Selected=$false; ElapsedSeconds=$res.ElapsedSeconds }
        if ($envelopeValid -and -not ($env.cleanup.safe -eq $true)) { $unavailable=$true; $reason="Adapter cleanup was not mechanically proven safe for $($target.Agent); fallback stopped."; break }
        if ($res.TimedOut -and -not $res.KillConfirmed) { $unavailable=$true; $reason="Unsafe termination for $($target.Agent) candidate $model; fallback stopped."; break }
        if (-not $envelopeValid -and $res.ExitCode -ne 0) { $unavailable=$true; $reason="Catastrophic adapter failure without a valid envelope for $($target.Agent) candidate $model; fallback stopped."; break }
        if ($envelopeValid -and ($env.cleanup.safe -eq $true) -and $class -in @('VALID_PASS','VALID_BLOCK') -and $env.structured) { $attempts[-1].Selected=$true; $accepted[$target.Agent]=@{ Envelope=$env; Path=(Join-Path $runtimeDir "candidate_$($target.File)"); Canonical=(Join-Path $reviewDir $target.File) }; (Render-Review $env $target.Agent) | Set-Content $accepted[$target.Agent].Path -Encoding utf8; $acceptedRole=$true; break }
    }
    if ($unavailable) { break }; if (-not $acceptedRole) { $unavailable=$true; $reason="No trusted $($target.Agent) verdict was obtained."; break }
}
if ($unavailable) { Write-Warning "AI verification gate VERIFICATION_UNAVAILABLE: $reason"; Write-Warning 'Canonical artifacts were left untouched.'; exit 1 }

$testResults=@(); $testsPassed=$true
if (-not $SkipTests -and $config.focused_tests) { $python = if ($_PythonExecutableOverride) { $_PythonExecutableOverride } else { Join-Path $repoRoot '.venv\Scripts\python.exe' }; if (-not (Test-Path $python) -and -not $_PythonExecutableOverride) { Write-Warning 'Focused test interpreter not found.'; exit 1 }
    foreach ($test in @($config.focused_tests)) { $name=[string]$test; if ($name -match '(?i)discover\s+tests|unittest\s+discover|^tests$|\*') { Write-Warning "Rejected unsafe focused test target: $name"; exit 1 }; $args=if ($_PythonArgumentsOverride) { $_PythonArgumentsOverride } else { @('-m','unittest',$name) }; $tr=Invoke-BoundedProcess $python $args $TestTimeoutSeconds; $passed=(-not $tr.TimedOut -and $tr.ExitCode -eq 0); $testResults += [pscustomobject]@{Target=$name;Passed=$passed;ExitCode=$tr.ExitCode}; if (-not $passed) { $testsPassed=$false } }
}
$head=(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git rev-parse HEAD" | Out-String).Trim(); $branch=(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git branch --show-current" | Out-String).Trim(); $e=@('# Verification Evidence','','Task: '+$Task,'Branch: '+$branch,'HEAD: '+$head,'Base ref: '+$baseRef,'','## Review verdicts','',"- Spec reviewer: $($accepted['spec-reviewer'].Envelope.structured.verdict) (blocking=$($accepted['spec-reviewer'].Envelope.structured.blocking_findings))","- Regression reviewer: $($accepted['regression-reviewer'].Envelope.structured.verdict) (blocking=$($accepted['regression-reviewer'].Envelope.structured.blocking_findings))",'','## Attempt provenance','')
foreach ($a in $attempts) { $e += "- $($a.Role) | model=$($a.Model) | classification=$($a.Classification) | selected=$($a.Selected)" }; $e += @('','## Focused tests',''); foreach ($t in $testResults) { $e += "- $($t.Target): $(if($t.Passed){'PASS'}else{'FAIL'}) (exit=$($t.ExitCode))" }; $e += @('','## Full suite','','Not run by the AI gate. User must run the repository full suite manually.'); $candidateEvidence=Join-Path $runtimeDir 'candidate_EVIDENCE.md'; $e -join "`n" | Set-Content $candidateEvidence -Encoding utf8
$promotion=@(@{Name='spec-review';Candidate=$accepted['spec-reviewer'].Path;Canonical=$accepted['spec-reviewer'].Canonical},@{Name='regression-review';Candidate=$accepted['regression-reviewer'].Path;Canonical=$accepted['regression-reviewer'].Canonical},@{Name='evidence';Candidate=$candidateEvidence;Canonical=(Join-Path $taskDir 'EVIDENCE.md')}); $backup=Join-Path $runtimeDir 'canonical_backup'; New-Item -ItemType Directory -Force $backup | Out-Null; foreach($item in $promotion){if(Test-Path $item.Canonical){Copy-Item $item.Canonical (Join-Path $backup "$($item.Name).bak") -Force;$item.Existed=$true}else{$item.Existed=$false}}
try { foreach($item in $promotion){Copy-Item $item.Candidate $item.Canonical -Force; if($_FailPromotionOnTarget -eq $item.Name){throw "Simulated promotion failure on $($item.Name)"}} } catch { foreach($item in $promotion){if($item.Existed){Copy-Item (Join-Path $backup "$($item.Name).bak") $item.Canonical -Force}else{if(Test-Path $item.Canonical){Remove-Item $item.Canonical -Force}}}; Write-Warning "Promotion failed and was rolled back: $($_.Exception.Message)"; exit 1 }
$blocked = -not $testsPassed -or ($accepted['spec-reviewer'].Envelope.structured.verdict -eq 'BLOCK') -or ($accepted['regression-reviewer'].Envelope.structured.verdict -eq 'BLOCK'); if($blocked){Write-Host 'AI verification gate CANDIDATE_BLOCKED.';exit 2}; Write-Host 'AI verification gate PASSED. Final ChatGPT/human review is still required.';exit 0
