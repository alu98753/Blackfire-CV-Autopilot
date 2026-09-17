param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-z0-9][a-z0-9-]*$')][string]$Task,
    [string]$ReviewModel, [switch]$SkipTests, [switch]$ForceRefresh,
    [int]$ReviewTimeoutSeconds = 540, [int]$TestTimeoutSeconds = 60,
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
function Get-Sha256String([string]$Text) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $hasher.ComputeHash($bytes)
    return -join ($hashBytes | ForEach-Object { $_.ToString('x2') })
}
function Get-Sha256File([string]$Path) {
    if (-not (Test-Path $Path)) { return '' }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $hasher.ComputeHash($bytes)
    return -join ($hashBytes | ForEach-Object { $_.ToString('x2') })
}
function Get-ReviewPromptText([string]$Agent) {
    return @"
Task descriptor: docs/tasks/$Task/task.json
Canonical spec: docs/tasks/$Task/SPEC.md
Status snapshot: .runtime/ai_gate/$Task/status.txt
Diff snapshot: .runtime/ai_gate/$Task/diff.patch
Comparison baseline: $baseRef

Perform a bounded read-only $Agent review. Inspect the supplied snapshots and current repository files with read, glob, or grep tools. Do not edit or execute commands. Perform repository grounding before emitting StructuredOutput. Return only the required structured review object.
"@.Trim()
}
function Get-ReviewFingerprint([string]$Agent, [string[]]$ModelsList) {
    $specHash = Get-Sha256File $specPath
    $statusHash = Get-Sha256File (Join-Path $runtimeDir 'status.txt')
    $diffHash = Get-Sha256File (Join-Path $runtimeDir 'diff.patch')
    $contractPath = Join-Path $repoRoot ".opencode\agents\$Agent.md"
    $contractHash = Get-Sha256File $contractPath
    $promptHash = Get-Sha256String (Get-ReviewPromptText $Agent)
    $modelsStr = ($ModelsList | ForEach-Object { [string]$_ } | Sort-Object) -join ','
    $argsOverride = if ($Agent -eq 'spec-reviewer' -and $_SpecReviewerArgumentsOverride) { $_SpecReviewerArgumentsOverride -join ' ' }
                    elseif ($Agent -eq 'regression-reviewer' -and $_RegressionReviewerArgumentsOverride) { $_RegressionReviewerArgumentsOverride -join ' ' }
                    elseif ($_ReviewerArgumentsOverride) { $_ReviewerArgumentsOverride -join ' ' }
                    else { '' }
    $elements = @(
        "role:$Agent",
        "spec:$specHash",
        "status:$statusHash",
        "diff:$diffHash",
        "base:$baseRef",
        "contract:$contractHash",
        "prompt:$promptHash",
        "models:$modelsStr",
        "args:$argsOverride"
    )
    if ($Agent -eq 'regression-reviewer' -and $config.scope) {
        $sortedScope = ($config.scope | ForEach-Object { [string]$_ } | Sort-Object) -join ','
        $elements += "scope:$sortedScope"
    }
    $compositeHash = Get-Sha256String ($elements -join "`n")
    $fpObj = [ordered]@{
        schema = 1
        role = $Agent
        hash = $compositeHash
    }
    $fpJson = ($fpObj | ConvertTo-Json -Compress)
    return @{ Hash = $compositeHash; Json = $fpJson }
}
function Test-CanonicalReviewReuse([string]$Path, [string]$ExpectedRole, [string]$ExpectedHash) {
    if (-not (Test-Path $Path)) { return $null }
    $content = Get-Content -Raw -Encoding utf8 $Path
    if (-not $content) { return $null }
    $commentRegex = '(?m)^<!--\s*blackfire-gate-fingerprint:\s*(\{.*?\})\s*-->\s*$'
    if ($content -match $commentRegex) {
        try {
            $fp = $matches[1] | ConvertFrom-Json
            if ($fp.schema -ne 1 -or $fp.role -ne $ExpectedRole -or $fp.hash -ne $ExpectedHash) {
                return $null
            }
        } catch {
            return $null
        }
    } else {
        return $null
    }
    if ($content -match '(?m)^Gate-accepted verdict:\s*(PASS|BLOCK)\s*$') {
        $verdict = $matches[1]
    } else {
        return $null
    }
    if ($content -match '(?m)^Blocking findings:\s*(\d+)\s*$') {
        $findings = [int]$matches[1]
    } else {
        return $null
    }
    if ($verdict -eq 'PASS' -and $findings -ne 0) { return $null }
    if ($verdict -eq 'BLOCK' -and $findings -lt 1) { return $null }
    return @{
        Verdict = $verdict
        BlockingFindings = $findings
        Content = $content
    }
}
function Invoke-BoundedProcess([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds) {
    if ($Executable -match '(?i)\.(cmd|bat)$') { $Arguments = @('/c', $Executable) + $Arguments; $Executable = 'cmd.exe' }
    $psi = [Diagnostics.ProcessStartInfo]::new(); $psi.FileName = $Executable; $psi.WorkingDirectory = $repoRoot; $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.RedirectStandardInput = $true
    $escaped = foreach ($arg in @($Arguments)) { $value = ([string]$arg) -replace '(\\*)"', '$1$1\\"'; $value = $value -replace '(\\+)$', '$1$1'; if ($value -match '[\s"]') { '"' + $value + '"' } else { $value } }
    $psi.Arguments = $escaped -join ' '
    $p = [Diagnostics.Process]::Start($psi); if (-not $p) { throw "Failed to start process: $Executable" }; $p.StandardInput.Close()
    $stdoutTask = $p.StandardOutput.ReadToEndAsync(); $stderrTask = $p.StandardError.ReadToEndAsync()
    $sw = [Diagnostics.Stopwatch]::StartNew(); $timedOut = $false; $confirmed = $true
    while (-not $p.WaitForExit(50)) {
        if ($sw.Elapsed.TotalSeconds -ge $TimeoutSeconds) { $timedOut = $true; try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { $confirmed = $false }; $confirmed = $confirmed -and ($p.WaitForExit(3000) -or $p.HasExited); break }
    }
    if (-not $timedOut) { $p.WaitForExit() }
    if (-not $stdoutTask.Wait(300) -or -not $stderrTask.Wait(300)) {
        try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { }
        if (-not $stdoutTask.Wait(1000) -or -not $stderrTask.Wait(1000)) { $confirmed = $false }
    }
    $stdout = if ($stdoutTask.IsCompleted) { $stdoutTask.GetAwaiter().GetResult() } else { '' }; $stderr = if ($stderrTask.IsCompleted) { $stderrTask.GetAwaiter().GetResult() } else { '' }; $sw.Stop()
    [pscustomobject]@{ ExitCode = if ($timedOut) { -1 } else { $p.ExitCode }; TimedOut = $timedOut; KillConfirmed = $confirmed; Pid = $p.Id; StdOut = $stdout; StdErr = $stderr; ElapsedSeconds = $sw.Elapsed.TotalSeconds }
}
function Start-SlotProcess($slot, [string]$Executable, [string[]]$Arguments) {
    if ($Executable -match '(?i)\.(cmd|bat)$') { $Arguments = @('/c', $Executable) + $Arguments; $Executable = 'cmd.exe' }
    $psi = [Diagnostics.ProcessStartInfo]::new(); $psi.FileName = $Executable; $psi.WorkingDirectory = $repoRoot; $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.RedirectStandardInput = $true
    $escaped = foreach ($arg in @($Arguments)) { $value = ([string]$arg) -replace '(\\*)"', '$1$1\\"'; $value = $value -replace '(\\+)$', '$1$1'; if ($value -match '[\s"]') { '"' + $value + '"' } else { $value } }
    $psi.Arguments = $escaped -join ' '
    $p = [Diagnostics.Process]::Start($psi); if (-not $p) { throw "Failed to start process: $Executable" }; $p.StandardInput.Close()
    $slot.Process = $p
    $slot.StdoutTask = $p.StandardOutput.ReadToEndAsync()
    $slot.StderrTask = $p.StandardError.ReadToEndAsync()
    $slot.Stopwatch = [Diagnostics.Stopwatch]::StartNew()
}
function Complete-SlotProcess($slot, [bool]$timedOut) {
    $p = $slot.Process; $sw = $slot.Stopwatch; $confirmed = $true
    if ($timedOut) {
        try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { $confirmed = $false }
        $confirmed = $confirmed -and ($p.WaitForExit(3000) -or $p.HasExited)
    } else { $p.WaitForExit() }
    if (-not $slot.StdoutTask.Wait(300) -or -not $slot.StderrTask.Wait(300)) {
        try { & taskkill.exe /PID $p.Id /T /F 2>$null | Out-Null } catch { }
        if (-not $slot.StdoutTask.Wait(1000) -or -not $slot.StderrTask.Wait(1000)) { $confirmed = $false }
    }
    $stdout = if ($slot.StdoutTask.IsCompleted) { $slot.StdoutTask.GetAwaiter().GetResult() } else { '' }
    $stderr = if ($slot.StderrTask.IsCompleted) { $slot.StderrTask.GetAwaiter().GetResult() } else { '' }
    $sw.Stop(); $exitCode = if ($timedOut) { -1 } else { $p.ExitCode }
    $elapsed = $sw.Elapsed.TotalSeconds; $procId = $p.Id
    $slot.Process = $null; $slot.StdoutTask = $null; $slot.StderrTask = $null; $slot.Stopwatch = $null
    [pscustomobject]@{ ExitCode = $exitCode; TimedOut = $timedOut; KillConfirmed = $confirmed; Pid = $procId; StdOut = $stdout; StdErr = $stderr; ElapsedSeconds = $elapsed }
}
function New-Invocation([string]$Agent, [string]$Model, [string]$PromptFile) {
    if ($_ReviewerExecutableOverride) {
        $custom = if ($Agent -eq 'spec-reviewer' -and $_SpecReviewerArgumentsOverride) { $_SpecReviewerArgumentsOverride }
                  elseif ($Agent -eq 'regression-reviewer' -and $_RegressionReviewerArgumentsOverride) { $_RegressionReviewerArgumentsOverride }
                  elseif ($_ReviewerArgumentsOverride) { $_ReviewerArgumentsOverride }
                  else { $null }
        if ($custom) {
            $args = if ($custom -contains '--agent') { @($custom) } else { @('--agent', $Agent) + @($custom) }
            return @{ Executable = $_ReviewerExecutableOverride; Arguments = @($args) }
        }
        return @{ Executable = $_ReviewerExecutableOverride; Arguments = @('--agent',$Agent,'--model',$Model,'--directory',$repoRoot,'--prompt-file',$PromptFile) }
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

$candidates = @(Resolve-Candidates $config.models.review $ReviewModel $_ReviewCandidatesOverride); if (-not $candidates.Count) { throw 'No review candidates configured.' }
$runtimeDir = Join-Path $repoRoot ".runtime\ai_gate\$Task"; $reviewDir = Join-Path $taskDir 'reviews'; New-Item -ItemType Directory -Force $runtimeDir,$reviewDir | Out-Null
(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git status --short" | Out-String).TrimEnd() | Set-Content (Join-Path $runtimeDir 'status.txt') -Encoding utf8
(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git diff --no-ext-diff $baseRef -- ." | Out-String).TrimEnd() | Set-Content (Join-Path $runtimeDir 'diff.patch') -Encoding utf8

$targets = @(@{ Agent='spec-reviewer'; File='spec-review.md' }, @{ Agent='regression-reviewer'; File='regression-review.md' })
$backup = Join-Path $runtimeDir 'canonical_backup'; New-Item -ItemType Directory -Force $backup | Out-Null

if ($_InvocationProbe) {
    $probeTarget = $targets[0]
    $probePrompt = Join-Path $runtimeDir "prompt_$($probeTarget.Agent).txt"
    (Get-ReviewPromptText $probeTarget.Agent) | Set-Content $probePrompt -Encoding utf8
    $inv = New-Invocation $probeTarget.Agent $candidates[0] $probePrompt
    [pscustomobject]@{ Agent=$probeTarget.Agent; Arguments=$inv.Arguments } | ConvertTo-Json -Compress
    exit 0
}

$slots = [ordered]@{}
foreach ($target in $targets) {
    $promptFile = Join-Path $runtimeDir "prompt_$($target.Agent).txt"
    (Get-ReviewPromptText $target.Agent) | Set-Content $promptFile -Encoding utf8
    $fp = Get-ReviewFingerprint $target.Agent $candidates
    $canonical = Join-Path $reviewDir $target.File
    $reuse = if (-not $ForceRefresh) {
        Test-CanonicalReviewReuse $canonical $target.Agent $fp.Hash
    } else { $null }

    if ($reuse) {
        Write-Host "Reusing valid canonical $($target.Agent)..."
        $slots[$target.Agent] = @{
            Agent = $target.Agent
            File = $target.File
            Status = 'REUSED'
            Verdict = $reuse.Verdict
            BlockingFindings = $reuse.BlockingFindings
            Canonical = $canonical
            CandidatePath = $null
            Attempts = @([pscustomobject]@{
                Role = $target.Agent
                Model = 'reused-artifact'
                Classification = if ($reuse.Verdict -eq 'PASS') { 'VALID_PASS' } else { 'VALID_BLOCK' }
                Selected = $true
                ElapsedSeconds = 0
            })
            FailureReason = ''
        }
    } else {
        $slots[$target.Agent] = @{
            Agent = $target.Agent
            File = $target.File
            Status = 'NEEDS_RUN'
            CandidateIndex = 0
            Process = $null
            StdoutTask = $null
            StderrTask = $null
            Stopwatch = $null
            Attempts = @()
            CandidatePath = Join-Path $runtimeDir "candidate_$($target.File)"
            Canonical = $canonical
            FingerprintJson = $fp.Json
            FailureReason = ''
        }
    }
}

foreach ($target in $targets) {
    $slot = $slots[$target.Agent]
    if ($slot.Status -eq 'NEEDS_RUN') {
        $model = $candidates[$slot.CandidateIndex]
        $promptFile = Join-Path $runtimeDir "prompt_$($target.Agent).txt"
        $inv = New-Invocation $target.Agent $model $promptFile
        Write-Host "Running $($target.Agent) [$model]..."
        Start-SlotProcess $slot $inv.Executable $inv.Arguments
        $slot.Status = 'RUNNING'
        $slot.ActiveModel = $model
    }
}

while ($true) {
    $runningCount = 0
    foreach ($target in $targets) {
        $slot = $slots[$target.Agent]
        if ($slot.Status -eq 'RUNNING') {
            $runningCount++
            $p = $slot.Process
            $sw = $slot.Stopwatch
            $timedOut = $false
            $exited = $p.WaitForExit(0)
            if (-not $exited -and $sw.Elapsed.TotalSeconds -ge $ReviewTimeoutSeconds) {
                $timedOut = $true
            }
            if ($exited -or $timedOut) {
                $res = Complete-SlotProcess $slot $timedOut
                $raw = ($res.StdOut, $res.StdErr | Where-Object { $_ }) -join "`n"
                $raw | Set-Content (Join-Path $runtimeDir "$($target.Agent)_$($slot.Attempts.Count+1).log") -Encoding utf8
                $env = if (-not $res.TimedOut) { Read-Envelope $res.StdOut } else { $null }
                $envelopeValid = Test-Envelope $env
                $class = if ($res.TimedOut -and -not $res.KillConfirmed) { 'INFRASTRUCTURE_FAILED' }
                         elseif ($res.TimedOut) { 'INFRASTRUCTURE_FAILED' }
                         elseif ($envelopeValid) { [string]$env.classification }
                         elseif ($res.ExitCode -ne 0) { 'INFRASTRUCTURE_FAILED' }
                         else { 'STRUCTURED_TRANSPORT_FAILED' }
                $slot.Attempts += [pscustomobject]@{
                    Role = $target.Agent
                    Model = $slot.ActiveModel
                    Classification = $class
                    Selected = $false
                    ElapsedSeconds = $res.ElapsedSeconds
                }

                $unsafeCleanup = ($envelopeValid -and -not ($env.cleanup.safe -eq $true))
                $unsafeKill = ($res.TimedOut -and -not $res.KillConfirmed)
                $catastrophic = (-not $envelopeValid -and $res.ExitCode -ne 0)
                $isTrusted = ($envelopeValid -and ($env.cleanup.safe -eq $true) -and ($class -in @('VALID_PASS','VALID_BLOCK')) -and $env.structured)

                if ($isTrusted) {
                    $slot.Attempts[-1].Selected = $true
                    $slot.Status = 'COMPLETED'
                    $slot.Verdict = $env.structured.verdict
                    $slot.BlockingFindings = $env.structured.blocking_findings
                    $rendered = Render-Review $env $target.Agent
                    $withFp = $rendered + "`n`n<!-- blackfire-gate-fingerprint: $($slot.FingerprintJson) -->"
                    $withFp | Set-Content $slot.CandidatePath -Encoding utf8

                    $targetBackup = Join-Path $backup "$($target.Agent).bak"
                    $slot.Existed = (Test-Path $slot.Canonical)
                    if ($slot.Existed) { Copy-Item $slot.Canonical $targetBackup -Force }
                    try {
                        Copy-Item $slot.CandidatePath $slot.Canonical -Force
                        if ($_FailPromotionOnTarget -in @($target.Agent, $target.File, 'spec-review', 'regression-review')) {
                            if ($_FailPromotionOnTarget -eq 'spec-review' -and $target.Agent -eq 'spec-reviewer') {
                                throw "Simulated promotion failure on spec-review"
                            }
                            if ($_FailPromotionOnTarget -eq 'regression-review' -and $target.Agent -eq 'regression-reviewer') {
                                throw "Simulated promotion failure on regression-review"
                            }
                        }
                    } catch {
                        if ($slot.Existed) { Copy-Item $targetBackup $slot.Canonical -Force }
                        else { if (Test-Path $slot.Canonical) { Remove-Item $slot.Canonical -Force } }
                        Write-Warning "Promotion failed and was rolled back: $($_.Exception.Message)"
                        exit 1
                    }
                } elseif ($unsafeCleanup -or $unsafeKill -or $catastrophic) {
                    $slot.Status = 'FAILED'
                    $slot.FailureReason = if ($unsafeCleanup) { "Adapter cleanup was not mechanically proven safe for $($target.Agent); fallback stopped." }
                                          elseif ($unsafeKill) { "Unsafe termination for $($target.Agent) candidate $($slot.ActiveModel); fallback stopped." }
                                          else { "Catastrophic adapter failure without a valid envelope for $($target.Agent) candidate $($slot.ActiveModel); fallback stopped." }
                } else {
                    $slot.CandidateIndex++
                    if ($slot.CandidateIndex -lt $candidates.Count) {
                        $nextModel = $candidates[$slot.CandidateIndex]
                        $promptFile = Join-Path $runtimeDir "prompt_$($target.Agent).txt"
                        $inv = New-Invocation $target.Agent $nextModel $promptFile
                        Write-Host "Running $($target.Agent) [$nextModel]..."
                        Start-SlotProcess $slot $inv.Executable $inv.Arguments
                        $slot.ActiveModel = $nextModel
                    } else {
                        $slot.Status = 'FAILED'
                        $slot.FailureReason = "No trusted $($target.Agent) verdict was obtained."
                    }
                }
            }
        }
    }
    if ($runningCount -eq 0) { break }
    Start-Sleep -Milliseconds 50
}

$unavailableReasons = @()
foreach ($target in $targets) {
    $slot = $slots[$target.Agent]
    if ($slot.Status -eq 'FAILED') {
        $unavailableReasons += $slot.FailureReason
    }
}
if ($unavailableReasons.Count -gt 0) {
    Write-Warning "AI verification gate VERIFICATION_UNAVAILABLE: $($unavailableReasons -join '; ')"
    Write-Warning 'Canonical artifacts were left untouched for failed reviewer(s).'
    exit 1
}

$testResults=@(); $testsPassed=$true
if (-not $SkipTests -and $config.focused_tests) {
    $python = if ($_PythonExecutableOverride) { $_PythonExecutableOverride } else { Join-Path $repoRoot '.venv\Scripts\python.exe' }
    if (-not (Test-Path $python) -and -not $_PythonExecutableOverride) { Write-Warning 'Focused test interpreter not found.'; exit 1 }
    foreach ($test in @($config.focused_tests)) {
        $name=[string]$test
        if ($name -match '(?i)discover\s+tests|unittest\s+discover|^tests$|\*') { Write-Warning "Rejected unsafe focused test target: $name"; exit 1 }
        $args=if ($_PythonArgumentsOverride) { $_PythonArgumentsOverride } else { @('-m','unittest',$name) }
        $tr=Invoke-BoundedProcess $python $args $TestTimeoutSeconds
        $passed=(-not $tr.TimedOut -and $tr.ExitCode -eq 0)
        $testResults += [pscustomobject]@{Target=$name;Passed=$passed;ExitCode=$tr.ExitCode}
        if (-not $passed) { $testsPassed=$false }
    }
}

$head=(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git rev-parse HEAD" | Out-String).Trim()
$branch=(& cmd.exe /d /s /c "chcp 65001 >nul && <nul git branch --show-current" | Out-String).Trim()
$e=@('# Verification Evidence','','Task: '+$Task,'Branch: '+$branch,'HEAD: '+$head,'Base ref: '+$baseRef,'','## Review verdicts','')
$e += "- Spec reviewer: $($slots['spec-reviewer'].Verdict) (blocking=$($slots['spec-reviewer'].BlockingFindings))"
$e += "- Regression reviewer: $($slots['regression-reviewer'].Verdict) (blocking=$($slots['regression-reviewer'].BlockingFindings))"
$e += @('','## Attempt provenance','')
foreach ($target in $targets) {
    foreach ($a in $slots[$target.Agent].Attempts) {
        $e += "- $($a.Role) | model=$($a.Model) | classification=$($a.Classification) | selected=$($a.Selected)"
    }
}
$e += @('','## Focused tests','')
foreach ($t in $testResults) { $e += "- $($t.Target): $(if($t.Passed){'PASS'}else{'FAIL'}) (exit=$($t.ExitCode))" }
$e += @('','## Full suite','','Not run by the AI gate. User must run the repository full suite manually.')
$candidateEvidence=Join-Path $runtimeDir 'candidate_EVIDENCE.md'
$e -join "`n" | Set-Content $candidateEvidence -Encoding utf8

$evidenceCanonical = Join-Path $taskDir 'EVIDENCE.md'
$evidenceBackup = Join-Path $backup 'evidence.bak'
$evidenceExisted = Test-Path $evidenceCanonical
if ($evidenceExisted) { Copy-Item $evidenceCanonical $evidenceBackup -Force }
try {
    Copy-Item $candidateEvidence $evidenceCanonical -Force
    if ($_FailPromotionOnTarget -eq 'evidence') {
        throw "Simulated promotion failure on evidence"
    }
} catch {
    if ($evidenceExisted) { Copy-Item $evidenceBackup $evidenceCanonical -Force }
    else { if (Test-Path $evidenceCanonical) { Remove-Item $evidenceCanonical -Force } }
    Write-Warning "Promotion failed and was rolled back: $($_.Exception.Message)"
    exit 1
}

$blocked = -not $testsPassed -or ($slots['spec-reviewer'].Verdict -eq 'BLOCK') -or ($slots['regression-reviewer'].Verdict -eq 'BLOCK')
if ($blocked) { Write-Host 'AI verification gate CANDIDATE_BLOCKED.'; exit 2 }
Write-Host 'AI verification gate PASSED. Final ChatGPT/human review is still required.'; exit 0

