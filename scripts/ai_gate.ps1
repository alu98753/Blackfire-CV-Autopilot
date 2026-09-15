param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Task,

    [string]$ReviewModel,

    [switch]$SkipTests,

    [int]$ReviewTimeoutSeconds = 480,

    [int]$TestTimeoutSeconds = 60,

    # Internal test seams for deterministic verification probes without invoking live OpenCode or Python
    [string]$_ReviewerExecutableOverride,
    [string[]]$_ReviewerArgumentsOverride,
    [string[]]$_SpecReviewerArgumentsOverride,
    [string[]]$_RegressionReviewerArgumentsOverride,
    [string]$_PythonExecutableOverride,
    [string[]]$_PythonArgumentsOverride,
    [string]$_FailPromotionOnTarget
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$taskDir = Join-Path $repoRoot "docs\tasks\$Task"
$taskFile = Join-Path $taskDir "task.json"
$specPath = Join-Path $taskDir "SPEC.md"

if (-not (Test-Path $taskFile)) {
    throw "Task descriptor not found: docs/tasks/$Task/task.json"
}
if (-not (Test-Path $specPath)) {
    throw "Canonical spec not found: docs/tasks/$Task/SPEC.md"
}

$config = Get-Content $taskFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.id -ne $Task) {
    throw "task.json id '$($config.id)' does not match directory/task argument '$Task'."
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

$gitDiff = & git diff --no-ext-diff $baseRef -- . 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "git diff against '$baseRef' failed.`n$gitDiff"
}
Set-Content -Path $diffPath -Value "$($gitDiff.TrimEnd())`n`n# END OF DIFF SNAPSHOT`n" -Encoding UTF8

function Invoke-BoundedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds,
        [switch]$StreamToConsole
    )

    if ($Executable -match '(?i)\.(cmd|bat)$') {
        $Arguments = @("/c", $Executable) + $Arguments
        $Executable = "cmd.exe"
    }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Executable
    $psi.WorkingDirectory = $repoRoot
    if ($null -ne $Arguments -and $Arguments.Count -gt 0) {
        $escapedArgs = @()
        foreach ($arg in $Arguments) {
            if ($arg -match '[\s"]') {
                $escaped = $arg -replace '(\\*)(")', '$1$1\"'
                $escaped = $escaped -replace '(\\+)$', '$1$1'
                $escapedArgs += "`"$escaped`""
            } else {
                $escapedArgs += $arg
            }
        }
        $psi.Arguments = $escapedArgs -join " "
    }
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.UseShellExecute = $false

    $proc = [System.Diagnostics.Process]::Start($psi)
    if ($null -eq $proc) {
        throw "Failed to start process: $Executable"
    }
    # Close stdin immediately so child processes expecting EOF never hang
    $proc.StandardInput.Close()

    $lockObj = [object]::new()
    $capturedLines = [System.Collections.Generic.List[string]]::new()
    $errLines = [System.Collections.Generic.List[string]]::new()

    $outEvent = Register-ObjectEvent -InputObject $proc -EventName 'OutputDataReceived' -Action {
        if ($null -ne $EventArgs.Data) {
            if ($Event.MessageData.Stream) {
                [Console]::WriteLine($EventArgs.Data)
            }
            [System.Threading.Monitor]::Enter($Event.MessageData.Lock)
            try {
                $Event.MessageData.Captured.Add($EventArgs.Data)
            } finally {
                [System.Threading.Monitor]::Exit($Event.MessageData.Lock)
            }
        }
    } -MessageData @{ Lock = $lockObj; Captured = $capturedLines; Stream = [bool]$StreamToConsole }

    $errEvent = Register-ObjectEvent -InputObject $proc -EventName 'ErrorDataReceived' -Action {
        if ($null -ne $EventArgs.Data) {
            if ($Event.MessageData.Stream) {
                [Console]::Error.WriteLine($EventArgs.Data)
            }
            [System.Threading.Monitor]::Enter($Event.MessageData.Lock)
            try {
                $Event.MessageData.Err.Add($EventArgs.Data)
            } finally {
                [System.Threading.Monitor]::Exit($Event.MessageData.Lock)
            }
        }
    } -MessageData @{ Lock = $lockObj; Err = $errLines; Stream = [bool]$StreamToConsole }

    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $timedOut = $false
    $killConfirmed = $false

    try {
        while ($true) {
            if ($stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                $timedOut = $true
                Write-Warning "Process timed out after ${TimeoutSeconds}s. Terminating client PID $($proc.Id)..."
                try {
                    if (-not $proc.HasExited) {
                        $proc.Kill()
                    }
                } catch {
                    Write-Warning "Failed to kill process $($proc.Id): $_"
                }
                $killConfirmed = $proc.WaitForExit(3000) -or $proc.HasExited
                if (-not $killConfirmed) {
                    Write-Warning "Process termination unconfirmed: client PID $($proc.Id) did not exit within 3000ms after kill signal."
                }
                break
            }

            if ($proc.WaitForExit(50)) {
                $proc.WaitForExit()
                break
            }
        }
    } finally {
        Unregister-Event -SourceIdentifier $outEvent.Name -Force -ErrorAction SilentlyContinue
        Unregister-Event -SourceIdentifier $errEvent.Name -Force -ErrorAction SilentlyContinue
        Get-Job -Name $outEvent.Name -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
        Get-Job -Name $errEvent.Name -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
    }

    [System.Threading.Monitor]::Enter($lockObj)
    try {
        $capturedArray = $capturedLines.ToArray()
        $errArray = $errLines.ToArray()
    } finally {
        [System.Threading.Monitor]::Exit($lockObj)
    }

    $exitCode = if ($timedOut) { -1 } else { $proc.ExitCode }
    $elapsed = $stopwatch.Elapsed.TotalSeconds

    return [pscustomobject]@{
        ExitCode = $exitCode
        TimedOut = $timedOut
        KillConfirmed = $killConfirmed
        Pid = $proc.Id
        StdOut = ($capturedArray -join "`n")
        StdErr = ($errArray -join "`n")
        ElapsedSeconds = $elapsed
    }
}

function Get-OpenCodeInvocation {
    param(
        [string]$Agent,
        [string]$PromptText
    )

    if (-not [string]::IsNullOrWhiteSpace($_ReviewerExecutableOverride)) {
        $args = @()
        if ($Agent -eq "spec-reviewer" -and $null -ne $_SpecReviewerArgumentsOverride) {
            $args = $_SpecReviewerArgumentsOverride
        } elseif ($Agent -eq "regression-reviewer" -and $null -ne $_RegressionReviewerArgumentsOverride) {
            $args = $_RegressionReviewerArgumentsOverride
        } elseif ($null -ne $_ReviewerArgumentsOverride) {
            $args = $_ReviewerArgumentsOverride
        }
        return @{
            Executable = $_ReviewerExecutableOverride
            Arguments = $args
            IsStructured = $false
        }
    }

    $cmdInfo = Get-Command opencode -ErrorAction SilentlyContinue
    if (-not $cmdInfo) {
        throw "OpenCode is not installed. Run .\scripts\bootstrap_opencode.ps1 first."
    }

    $innerArgs = @("run", "--standalone", "--format", "json", "--agent", $Agent)
    if (-not [string]::IsNullOrWhiteSpace($ReviewModel)) {
        $innerArgs += @("--model", $ReviewModel)
    }
    $innerArgs += $PromptText

    if ($cmdInfo.Source -like "*.ps1") {
        return @{
            Executable = "powershell.exe"
            Arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $cmdInfo.Source) + $innerArgs
            IsStructured = $true
        }
    }

    return @{
        Executable = $cmdInfo.Source
        Arguments = $innerArgs
        IsStructured = $true
    }
}

function Get-FinalAssistantMessageFromStructuredJson {
    param([string]$JsonlText)

    if ([string]::IsNullOrWhiteSpace($JsonlText)) {
        return [pscustomobject]@{
            Success = $false
            Text = $null
            Error = "Structured reviewer output was empty."
        }
    }

    $lines = $JsonlText -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    if ($lines.Count -eq 0) {
        return [pscustomobject]@{
            Success = $false
            Text = $null
            Error = "Structured reviewer output contained no non-empty lines."
        }
    }

    $events = [System.Collections.Generic.List[object]]::new()
    $lineNum = 0
    foreach ($line in $lines) {
        $lineNum++
        try {
            $parsed = $line | ConvertFrom-Json
            $events.Add($parsed)
        } catch {
            return [pscustomobject]@{
                Success = $false
                Text = $null
                Error = "Invalid JSON on line $lineNum : $_"
            }
        }
    }

    $textEvents = [System.Collections.Generic.List[object]]::new()
    foreach ($evt in $events) {
        if ($evt.type -eq "text" -and $null -ne $evt.part -and -not [string]::IsNullOrEmpty($evt.part.text)) {
            $textEvents.Add($evt)
        }
    }

    if ($textEvents.Count -eq 0) {
        return [pscustomobject]@{
            Success = $false
            Text = $null
            Error = "No assistant text events found in structured output."
        }
    }

    $lastTextEvt = $textEvents[$textEvents.Count - 1]
    $finalMessageId = $lastTextEvt.part.messageID
    if ([string]::IsNullOrWhiteSpace($finalMessageId)) {
        return [pscustomobject]@{
            Success = $true
            Text = [string]$lastTextEvt.part.text
            Error = $null
        }
    }

    $finalParts = [System.Collections.Generic.List[string]]::new()
    foreach ($te in $textEvents) {
        if ($te.part.messageID -eq $finalMessageId) {
            $finalParts.Add([string]$te.part.text)
        }
    }

    $concatenated = $finalParts -join ""
    return [pscustomobject]@{
        Success = $true
        Text = $concatenated
        Error = $null
    }
}

function Get-CanonicalReviewPayload {
    param([string]$FinalAssistantMessage)

    if ([string]::IsNullOrWhiteSpace($FinalAssistantMessage)) {
        return [pscustomobject]@{
            Success = $false
            Payload = $null
            Error = "Final assistant message was empty."
        }
    }

    # Strip optional leading UTF-8 BOM only
    $cleanText = $FinalAssistantMessage.TrimStart([char]0xFEFF)

    # Header must begin at the start of a line and have consecutive VERDICT and BLOCKING_FINDINGS lines
    $headerMatches = [regex]::Matches($cleanText, '(?m)^VERDICT:\s*(PASS|BLOCK)\r?\nBLOCKING_FINDINGS:\s*(\d+)(?:\r?\n|$)')

    if ($headerMatches.Count -eq 0) {
        return [pscustomobject]@{
            Success = $false
            Payload = $null
            Error = "No valid VERDICT/BLOCKING_FINDINGS header found in final assistant message."
        }
    }

    if ($headerMatches.Count -gt 1) {
        return [pscustomobject]@{
            Success = $false
            Payload = $null
            Error = "Ambiguous review payload: multiple ($($headerMatches.Count)) VERDICT/BLOCKING_FINDINGS headers found in final assistant message."
        }
    }

    $payload = $cleanText.Substring($headerMatches[0].Index)

    return [pscustomobject]@{
        Success = $true
        Payload = $payload
        Error = $null
    }
}

function Test-ReviewVerdictStructure {
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return [pscustomobject]@{ IsValid = $false; Verdict = "EMPTY"; Blocking = -1; Error = "Reviewer produced empty output." }
    }

    # Strip optional leading UTF-8 BOM only; do not allow any whitespace, blank lines, preamble, or prose
    $cleanText = $Text.TrimStart([char]0xFEFF)

    $headerMatch = [regex]::Match($cleanText, '\AVERDICT:\s*(PASS|BLOCK)\r?\nBLOCKING_FINDINGS:\s*(\d+)(?:\r?\n|$)')
    if (-not $headerMatch.Success) {
        return [pscustomobject]@{ IsValid = $false; Verdict = "MALFORMED"; Blocking = -1; Error = "Output does not begin on line 1 with required VERDICT / BLOCKING_FINDINGS header." }
    }

    $verdict = $headerMatch.Groups[1].Value
    $blocking = [int]$headerMatch.Groups[2].Value

    if ($verdict -eq "PASS" -and $blocking -ne 0) {
        return [pscustomobject]@{ IsValid = $false; Verdict = $verdict; Blocking = $blocking; Error = "Contract violation: VERDICT is PASS but BLOCKING_FINDINGS is $blocking (must be 0)." }
    }
    if ($verdict -eq "BLOCK" -and $blocking -lt 1) {
        return [pscustomobject]@{ IsValid = $false; Verdict = $verdict; Blocking = $blocking; Error = "Contract violation: VERDICT is BLOCK but BLOCKING_FINDINGS is $blocking (must be >= 1)." }
    }

    return [pscustomobject]@{ IsValid = $true; Verdict = $verdict; Blocking = $blocking; Error = $null }
}

$infraBlocked = $false
$infraReason = ""
$candidateBlocked = $false

$reviewTargets = @(
    @{ Agent = "spec-reviewer"; File = "spec-review.md" },
    @{ Agent = "regression-reviewer"; File = "regression-review.md" }
)

$verdicts = @{}
$candidates = @{}

foreach ($rev in $reviewTargets) {
    $agentName = $rev.Agent
    $fileName = $rev.File
    $canonicalPath = Join-Path $reviewDir $fileName
    $candidatePath = Join-Path $runtimeDir "candidate_${agentName}.md"
    $rawLogPath = Join-Path $runtimeDir "${agentName}_raw.log"

    $prompt = @"
Task descriptor: docs/tasks/$Task/task.json
Canonical spec: docs/tasks/$Task/SPEC.md
Repository status snapshot: .runtime/ai_gate/$Task/status.txt
Candidate diff snapshot: .runtime/ai_gate/$Task/diff.patch
Comparison baseline: $baseRef

Review the candidate patch using the current repository state. Follow the '$agentName' agent contract exactly. Treat the snapshots as evidence, but inspect current repository files with read/search tools when needed. Do not edit files or run shell commands. Stop using tools early once enough evidence exists to determine PASS or BLOCK.
The final response MUST begin with:
VERDICT: PASS|BLOCK
BLOCKING_FINDINGS: <count>
"@

    $invocation = Get-OpenCodeInvocation -Agent $agentName -PromptText $prompt
    Write-Host "Running OpenCode agent '$agentName' (timeout limit: ${ReviewTimeoutSeconds}s)..."

    $procResult = Invoke-BoundedProcess -Executable $invocation.Executable -Arguments $invocation.Arguments -TimeoutSeconds $ReviewTimeoutSeconds -StreamToConsole:$true
    Write-Host "OpenCode agent '$agentName' finished in $([math]::Round($procResult.ElapsedSeconds, 1))s (exit code: $($procResult.ExitCode))."

    $fullRaw = ($procResult.StdOut, $procResult.StdErr | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
    Set-Content -Path $rawLogPath -Value $fullRaw -Encoding UTF8

    if ($procResult.TimedOut) {
        $infraBlocked = $true
        if ($procResult.KillConfirmed) {
            $infraReason = "OpenCode agent '$agentName' timed out after ${ReviewTimeoutSeconds}s (client PID $($procResult.Pid) terminated). Canonical reviews left untouched."
        } else {
            $infraReason = "OpenCode agent '$agentName' timed out after ${ReviewTimeoutSeconds}s (termination failure: client PID $($procResult.Pid) could not be confirmed exited). Canonical reviews left untouched."
        }
        break
    }

    if ($procResult.ExitCode -ne 0) {
        $infraBlocked = $true
        $infraReason = "OpenCode agent '$agentName' failed with exit code $($procResult.ExitCode). Canonical review left untouched."
        break
    }

    $assistantMessage = $procResult.StdOut
    if ($invocation.IsStructured) {
        $extraction = Get-FinalAssistantMessageFromStructuredJson -JsonlText $procResult.StdOut
        if (-not $extraction.Success) {
            $infraBlocked = $true
            $infraReason = "OpenCode agent '$agentName' structured output malformed: $($extraction.Error). Canonical review left untouched."
            break
        }
        $assistantMessage = $extraction.Text
    }

    $payloadResult = Get-CanonicalReviewPayload -FinalAssistantMessage $assistantMessage
    if (-not $payloadResult.Success) {
        $infraBlocked = $true
        $infraReason = "OpenCode agent '$agentName' canonical payload extraction failed: $($payloadResult.Error). Canonical review left untouched."
        break
    }

    $validation = Test-ReviewVerdictStructure -Text $payloadResult.Payload
    if (-not $validation.IsValid) {
        $infraBlocked = $true
        $infraReason = "OpenCode agent '$agentName' output malformed: $($validation.Error). Canonical review left untouched."
        break
    }

    # Stage candidate review output; gate-level promotion is deferred until all reviewers and tests complete
    Set-Content -Path $candidatePath -Value $payloadResult.Payload.TrimEnd() -Encoding UTF8
    $candidates[$agentName] = @{
        CandidatePath = $candidatePath
        CanonicalPath = $canonicalPath
    }
    $verdicts[$agentName] = $validation

    if ($validation.Verdict -eq "BLOCK") {
        $candidateBlocked = $true
    }
}

$testResults = @()
$testsPassed = $true

if (-not $infraBlocked -and -not $SkipTests -and $null -ne $config.focused_tests -and $config.focused_tests.Count -gt 0) {
    $python = ""
    if (-not [string]::IsNullOrWhiteSpace($_PythonExecutableOverride)) {
        $python = $_PythonExecutableOverride
    } else {
        $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
        if (-not (Test-Path $python)) {
            $infraBlocked = $true
            $infraReason = "Focused tests are configured but .venv\Scripts\python.exe was not found."
        }
    }

    if (-not $infraBlocked) {
        foreach ($target in $config.focused_tests) {
            $targetText = [string]$target
            if ($targetText -match '(?i)discover\s+tests|unittest\s+discover|^tests$|\*') {
                $infraBlocked = $true
                $infraReason = "Rejected unsafe/full-suite focused test target: '$targetText'"
                break
            }
            if ([string]::IsNullOrWhiteSpace($targetText)) {
                continue
            }

            $safeName = ($targetText -replace '[^A-Za-z0-9_.-]', '_')
            $logPath = Join-Path $runtimeDir ("test-" + $safeName + ".log")
            Write-Host "Running focused test: $targetText (timeout: ${TestTimeoutSeconds}s)..."

            $pyArgs = if ($null -ne $_PythonArgumentsOverride) { $_PythonArgumentsOverride } else { @("-m", "unittest", $targetText) }
            $testRes = Invoke-BoundedProcess -Executable $python -Arguments $pyArgs -TimeoutSeconds $TestTimeoutSeconds -StreamToConsole:$false

            $testLog = ($testRes.StdOut, $testRes.StdErr | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
            Set-Content -Path $logPath -Value $testLog.TrimEnd() -Encoding UTF8

            if ($testRes.TimedOut) {
                $infraBlocked = $true
                if ($testRes.KillConfirmed) {
                    Write-Warning "  -> TIMEOUT ($($testRes.ElapsedSeconds.ToString('F2'))s) - Focused test '$targetText' timed out after ${TestTimeoutSeconds}s (client PID $($testRes.Pid) terminated)."
                    $infraReason = "Focused test '$targetText' timed out after ${TestTimeoutSeconds}s (client PID $($testRes.Pid) terminated)."
                } else {
                    Write-Warning "  -> TIMEOUT ($($testRes.ElapsedSeconds.ToString('F2'))s) - Focused test '$targetText' timed out after ${TestTimeoutSeconds}s (termination failure: client PID $($testRes.Pid) could not be confirmed exited)."
                    $infraReason = "Focused test '$targetText' timed out after ${TestTimeoutSeconds}s (termination failure: client PID $($testRes.Pid) could not be confirmed exited)."
                }
                break
            }

            if ($testRes.ExitCode -eq 0) {
                Write-Host "  -> PASS ($($testRes.ElapsedSeconds.ToString('F2'))s) - Log: .runtime/ai_gate/$Task/$(Split-Path $logPath -Leaf)"
                $testResults += [pscustomobject]@{
                    Target = $targetText
                    Passed = $true
                    ExitCode = 0
                    Log = ".runtime/ai_gate/$Task/$(Split-Path $logPath -Leaf)"
                }
            } else {
                Write-Host "  -> FAIL ($($testRes.ElapsedSeconds.ToString('F2'))s, exit $($testRes.ExitCode)) - Log: .runtime/ai_gate/$Task/$(Split-Path $logPath -Leaf)"
                $testsPassed = $false
                $candidateBlocked = $true
                $testResults += [pscustomobject]@{
                    Target = $targetText
                    Passed = $false
                    ExitCode = $testRes.ExitCode
                    Log = ".runtime/ai_gate/$Task/$(Split-Path $logPath -Leaf)"
                }
            }
        }
    }
}

if ($infraBlocked) {
    Write-Warning "AI verification gate INFRASTRUCTURE_BLOCKED: $infraReason"
    Write-Warning "Canonical reviews and EVIDENCE.md preserved untouched. Diagnostics saved under .runtime/ai_gate/$Task/."
    exit 1
}

$specVerdict = $verdicts["spec-reviewer"]
$regressionVerdict = $verdicts["regression-reviewer"]

$head = (& git rev-parse HEAD 2>&1 | Out-String).Trim()
$branch = (& git branch --show-current 2>&1 | Out-String).Trim()
$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")

$evidence = New-Object System.Collections.Generic.List[string]
$evidence.Add("# Verification Evidence")
$evidence.Add("")
$evidence.Add("Task: $Task")
$evidence.Add("Generated: $timestamp")
$evidence.Add("Branch: $branch")
$evidence.Add("HEAD: $head")
$evidence.Add("Base ref: $baseRef")
$evidence.Add("")
$evidence.Add("## Review verdicts")
$evidence.Add("")
$evidence.Add("- Spec reviewer: $($specVerdict.Verdict) (blocking=$($specVerdict.Blocking))")
$evidence.Add("- Regression reviewer: $($regressionVerdict.Verdict) (blocking=$($regressionVerdict.Blocking))")
$evidence.Add("")
$evidence.Add("Detailed reports:")
$evidence.Add("")
$evidence.Add("- reviews/spec-review.md")
$evidence.Add("- reviews/regression-review.md")
$evidence.Add("")
$evidence.Add("## Focused tests")
$evidence.Add("")
if ($SkipTests) {
    $evidence.Add("Focused tests skipped by explicit -SkipTests.")
} elseif ($testResults.Count -eq 0) {
    $evidence.Add("No focused tests declared in task.json.")
} else {
    foreach ($result in $testResults) {
        $status = if ($result.Passed) { "PASS" } else { "FAIL" }
        $evidence.Add("- $status $($result.Target) (exit=$($result.ExitCode)); local log: $($result.Log)")
    }
}
$evidence.Add("")
$evidence.Add("## Full suite")
$evidence.Add("")
$evidence.Add("Not run by the AI gate. Repository policy requires the user to run the full suite manually when required.")
$evidence.Add("")
$evidence.Add("## Candidate snapshot")
$evidence.Add("")
$evidence.Add("Ephemeral status/diff snapshots are stored under .runtime/ai_gate/$Task/ and are intentionally git-ignored.")

# Write candidate EVIDENCE.md to runtime directory before promotion
$candidateEvidencePath = Join-Path $runtimeDir "candidate_EVIDENCE.md"
$evidencePath = Join-Path $taskDir "EVIDENCE.md"
Set-Content -Path $candidateEvidencePath -Value ($evidence -join "`n") -Encoding UTF8

# Both reviewers and focused tests completed without infrastructure failures!
# Transaction-safe promotion: backup existing canonical artifacts and promote candidates
$promotionItems = @(
    @{
        Name = "spec-review"
        CandidatePath = $candidates["spec-reviewer"].CandidatePath
        CanonicalPath = $candidates["spec-reviewer"].CanonicalPath
    },
    @{
        Name = "regression-review"
        CandidatePath = $candidates["regression-reviewer"].CandidatePath
        CanonicalPath = $candidates["regression-reviewer"].CanonicalPath
    },
    @{
        Name = "evidence"
        CandidatePath = $candidateEvidencePath
        CanonicalPath = $evidencePath
    }
)

$backupDir = Join-Path $runtimeDir "canonical_backup"
if (Test-Path $backupDir) {
    Remove-Item -Path $backupDir -Recurse -Force
}
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

foreach ($item in $promotionItems) {
    if (Test-Path $item.CanonicalPath) {
        $backupPath = Join-Path $backupDir "$($item.Name).bak"
        Copy-Item -Path $item.CanonicalPath -Destination $backupPath -Force
        $item["Existed"] = $true
        $item["BackupPath"] = $backupPath
    } else {
        $item["Existed"] = $false
    }
}

$promotionFailed = $false
$promotionError = ""
$rollbackFailures = New-Object System.Collections.Generic.List[string]

try {
    foreach ($item in $promotionItems) {
        Copy-Item -Path $item.CandidatePath -Destination $item.CanonicalPath -Force
        if (-not [string]::IsNullOrWhiteSpace($_FailPromotionOnTarget) -and $_FailPromotionOnTarget -eq $item.Name) {
            throw "Simulated promotion failure on target '$($item.Name)' after copy"
        }
    }
} catch {
    $promotionFailed = $true
    $promotionError = $_.Exception.Message

    # Rollback all promotion items to pre-gate state; each item independently try/catched
    foreach ($item in $promotionItems) {
        try {
            if ($item.Existed) {
                Copy-Item -Path $item.BackupPath -Destination $item.CanonicalPath -Force
            } else {
                if (Test-Path $item.CanonicalPath) {
                    Remove-Item -Path $item.CanonicalPath -Force
                }
            }
        } catch {
            $rollbackFailures.Add("Rollback failure on '$($item.Name)' ($($item.CanonicalPath)): $($_.Exception.Message)")
        }
    }
}

if ($promotionFailed) {
    if ($rollbackFailures.Count -gt 0) {
        Write-Warning "AI verification gate INFRASTRUCTURE_BLOCKED: Promotion to canonical artifacts failed: $promotionError."
        foreach ($rf in $rollbackFailures) {
            Write-Warning "  -> $rf"
        }
    } else {
        Write-Warning "AI verification gate INFRASTRUCTURE_BLOCKED: Promotion to canonical artifacts failed: $promotionError. Rolled back all canonical artifacts to pre-gate state."
    }
    exit 1
}

Write-Host "Canonical reviewer reports and EVIDENCE.md successfully promoted."

if ($candidateBlocked -or $specVerdict.Verdict -ne "PASS" -or $specVerdict.Blocking -ne 0 -or $regressionVerdict.Verdict -ne "PASS" -or $regressionVerdict.Blocking -ne 0 -or -not $testsPassed) {
    Write-Host "AI verification gate CANDIDATE_BLOCKED. Inspect EVIDENCE.md and reviewer reports."
    exit 2
}

Write-Host "AI verification gate PASSED. Final ChatGPT/human review is still required."
exit 0
