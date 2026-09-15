param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Task,

    [string]$Model,

    [int]$TimeoutSeconds = 480,

    # Internal test seam: override executable and arguments to verify process execution, timeout, streaming, and failure
    [string]$_ExecutableOverride,
    [string[]]$_ArgumentsOverride,
    [string[]]$_ModelCandidatesOverride,
    [string]$_OpenCodeVersionOverride,
    [switch]$_InvocationProbe
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot
. (Join-Path $PSScriptRoot "opencode_contract.ps1")

if ([string]::IsNullOrWhiteSpace($_ExecutableOverride) -and -not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    throw "OpenCode is not installed. Run .\scripts\bootstrap_opencode.ps1 first."
}

if ([string]::IsNullOrWhiteSpace($_ExecutableOverride)) {
    $openCodeCommand = Get-Command opencode -ErrorAction Stop
    $installedVersion = Get-OpenCodeVersion -Executable $openCodeCommand.Source
    Assert-OpenCodeSupportedVersion -Version $installedVersion
} elseif (-not [string]::IsNullOrWhiteSpace($_OpenCodeVersionOverride)) {
    Assert-OpenCodeSupportedVersion -Version $_OpenCodeVersionOverride.Trim()
}

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

function Resolve-NormalModelList {
    param(
        $RawConfigModels,
        [string]$CliOverride,
        [string[]]$TestCandidatesOverride
    )

    if ($null -ne $TestCandidatesOverride -and $TestCandidatesOverride.Count -gt 0) {
        $clean = @()
        foreach ($m in $TestCandidatesOverride) {
            $trimmed = ([string]$m).Trim()
            if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                $clean += $trimmed
            }
        }
        if ($clean.Count -eq 0) {
            throw "Model candidate list override contained no non-blank identifiers."
        }
        return $clean
    }

    if (-not [string]::IsNullOrWhiteSpace($CliOverride)) {
        return @($CliOverride.Trim())
    }

    if ($null -eq $RawConfigModels) {
        throw "Missing models configuration in task.json."
    }

    $raw = $RawConfigModels
    $list = @()
    if ($raw -is [System.Collections.IEnumerable] -and -not ($raw -is [string])) {
        foreach ($item in $raw) {
            $trimmed = ([string]$item).Trim()
            if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                $list += $trimmed
            }
        }
    } else {
        $single = ([string]$raw).Trim()
        if (-not [string]::IsNullOrWhiteSpace($single)) {
            $list += $single
        }
    }

    if ($list.Count -eq 0) {
        throw "Model candidate list is empty or contains only blank entries."
    }

    return $list
}

$candidates = Resolve-NormalModelList -RawConfigModels $config.models.scout -CliOverride $Model -TestCandidatesOverride $_ModelCandidatesOverride

$prompt = @"
Task descriptor: docs/tasks/$Task/task.json
Canonical spec: docs/tasks/$Task/SPEC.md

Perform a read-only localization audit for this task using the repository state currently checked out.
Follow the scout agent contract exactly:
- Be a light task localizer, not a general codebase auditor.
- Strictly follow the file and word budget limits defined in the scout agent contract.
- Stop once the minimal change surface, risks, and uncertainty are established; prefer reporting uncertainty over continued exploration.
- Do not edit files or run shell commands.
Return only the requested Markdown scout report.
"@

function Get-ScoutOpenCodeArguments {
    param(
        [string]$CandidateModel,
        [string]$PromptText
    )

    $arguments = @("run", "--agent", "scout")
    if (-not [string]::IsNullOrWhiteSpace($CandidateModel)) {
        $arguments += @("--model", $CandidateModel)
    }
    $arguments += $PromptText
    return $arguments
}

if ($_InvocationProbe) {
    $probeModel = @($candidates)[0]
    [pscustomobject]@{
        Arguments = @(Get-ScoutOpenCodeArguments -CandidateModel $probeModel -PromptText $prompt)
    } | ConvertTo-Json -Compress
    exit 0
}

# Staging area for atomic promotion
$runtimeDir = Join-Path $repoRoot ".runtime\ai_scout\$Task"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$candidatePath = Join-Path $runtimeDir "candidate.md"
$contextPath = Join-Path $taskDir "CONTEXT.md"

function Invoke-ScoutProcessAttempt {
    param(
        [string]$CandidateModel,
        [int]$AttemptIndex,
        [int]$TimeoutLimit
    )

    $rawLogPath = Join-Path $runtimeDir "raw_output_attempt_${AttemptIndex}.log"
    $execFile = ""
    $execArgs = @()

    if (-not [string]::IsNullOrWhiteSpace($_ExecutableOverride)) {
        $execFile = $_ExecutableOverride
        if ($null -ne $_ArgumentsOverride -and $_ArgumentsOverride.Count -gt 0) {
            $execArgs = $_ArgumentsOverride
        } else {
            $execArgs = @("--model", $CandidateModel)
        }
    } else {
        $cmdInfo = Get-Command opencode -ErrorAction SilentlyContinue
        $innerArgs = Get-ScoutOpenCodeArguments -CandidateModel $CandidateModel -PromptText $prompt

        if ($cmdInfo.Source -like "*.ps1") {
            $execFile = "powershell.exe"
            $execArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $cmdInfo.Source) + $innerArgs
        } else {
            $execFile = $cmdInfo.Source
            $execArgs = $innerArgs
        }
    }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $execFile
    $psi.WorkingDirectory = $repoRoot
    if ($execArgs.Count -gt 0) {
        $escapedArgs = @()
        foreach ($arg in $execArgs) {
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
        return [pscustomobject]@{
            Launched = $false
            TimedOut = $false
            KillConfirmed = $false
            ExitCode = -1
            ElapsedSeconds = 0.0
            CapturedArray = @()
            ErrArray = @()
            RawLogPath = $rawLogPath
            LaunchError = "Failed to start process: $execFile"
        }
    }
    $proc.StandardInput.Close()

    $lockObj = [object]::new()
    $capturedLines = [System.Collections.Generic.List[string]]::new()
    $errLines = [System.Collections.Generic.List[string]]::new()

    $outEvent = Register-ObjectEvent -InputObject $proc -EventName 'OutputDataReceived' -Action {
        if ($null -ne $EventArgs.Data) {
            [Console]::WriteLine($EventArgs.Data)
            [System.Threading.Monitor]::Enter($Event.MessageData.Lock)
            try {
                $Event.MessageData.Captured.Add($EventArgs.Data)
            } finally {
                [System.Threading.Monitor]::Exit($Event.MessageData.Lock)
            }
        }
    } -MessageData @{ Lock = $lockObj; Captured = $capturedLines }

    $errEvent = Register-ObjectEvent -InputObject $proc -EventName 'ErrorDataReceived' -Action {
        if ($null -ne $EventArgs.Data) {
            [Console]::Error.WriteLine($EventArgs.Data)
            [System.Threading.Monitor]::Enter($Event.MessageData.Lock)
            try {
                $Event.MessageData.Err.Add($EventArgs.Data)
            } finally {
                [System.Threading.Monitor]::Exit($Event.MessageData.Lock)
            }
        }
    } -MessageData @{ Lock = $lockObj; Err = $errLines }

    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $timedOut = $false
    $killConfirmed = $false

    try {
        while ($true) {
            if ($stopwatch.Elapsed.TotalSeconds -ge $TimeoutLimit) {
                $timedOut = $true
                Write-Warning "OpenCode scout timed out after ${TimeoutLimit}s. Terminating client PID $($proc.Id)..."
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

    $fullRaw = ($capturedArray + $errArray) -join "`n"
    Set-Content -Path $rawLogPath -Value $fullRaw -Encoding UTF8

    return [pscustomobject]@{
        Launched = $true
        TimedOut = $timedOut
        KillConfirmed = $killConfirmed
        ExitCode = $exitCode
        ElapsedSeconds = $elapsed
        CapturedArray = $capturedArray
        ErrArray = $errArray
        RawLogPath = $rawLogPath
        LaunchError = $null
    }
}

$attemptIndex = 0
$selectedResult = $null
$provenanceList = [System.Collections.Generic.List[object]]::new()

foreach ($candidateModel in $candidates) {
    $attemptIndex++
    Write-Host "Running OpenCode scout candidate [$attemptIndex/$($candidates.Count)] '$candidateModel' (timeout: ${TimeoutSeconds}s)..."

    $attempt = Invoke-ScoutProcessAttempt -CandidateModel $candidateModel -AttemptIndex $attemptIndex -TimeoutLimit $TimeoutSeconds

    if (-not $attempt.Launched) {
        $provenanceList.Add([pscustomobject]@{
            Role = "scout"
            Type = "NORMAL"
            Index = $attemptIndex
            Model = $candidateModel
            ElapsedSeconds = 0.0
            Outcome = "LAUNCH_FAILED"
            Reason = $attempt.LaunchError
            Selected = $false
        })
        Write-Warning "Scout candidate '$candidateModel' failed to launch: $($attempt.LaunchError)"
        continue
    }

    if ($attempt.TimedOut) {
        if (-not $attempt.KillConfirmed) {
            $provenanceList.Add([pscustomobject]@{
                Role = "scout"
                Type = "NORMAL"
                Index = $attemptIndex
                Model = $candidateModel
                ElapsedSeconds = $attempt.ElapsedSeconds
                Outcome = "TIMEOUT_UNCONFIRMED_KILL"
                Reason = "Process timed out and termination could not be confirmed."
                Selected = $false
            })
            throw "OpenCode scout candidate '$candidateModel' timed out after ${TimeoutSeconds}s and process termination could not be confirmed. Routing terminated for safety; canonical CONTEXT.md left untouched."
        }

        $provenanceList.Add([pscustomobject]@{
            Role = "scout"
            Type = "NORMAL"
            Index = $attemptIndex
            Model = $candidateModel
            ElapsedSeconds = $attempt.ElapsedSeconds
            Outcome = "TIMEOUT"
            Reason = "Process timed out after ${TimeoutSeconds}s (terminated)."
            Selected = $false
        })
        Write-Warning "Scout candidate '$candidateModel' timed out after $([math]::Round($attempt.ElapsedSeconds, 1))s."
        continue
    }

    if ($attempt.ExitCode -ne 0) {
        $provenanceList.Add([pscustomobject]@{
            Role = "scout"
            Type = "NORMAL"
            Index = $attemptIndex
            Model = $candidateModel
            ElapsedSeconds = $attempt.ElapsedSeconds
            Outcome = "NON_ZERO_EXIT"
            Reason = "Process exited with code $($attempt.ExitCode)."
            Selected = $false
        })
        Write-Warning "Scout candidate '$candidateModel' exited with non-zero code $($attempt.ExitCode)."
        continue
    }

    $candidateText = ($attempt.CapturedArray -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($candidateText)) {
        $provenanceList.Add([pscustomobject]@{
            Role = "scout"
            Type = "NORMAL"
            Index = $attemptIndex
            Model = $candidateModel
            ElapsedSeconds = $attempt.ElapsedSeconds
            Outcome = "EMPTY_OUTPUT"
            Reason = "Process produced empty output."
            Selected = $false
        })
        Write-Warning "Scout candidate '$candidateModel' produced empty output."
        continue
    }

    $hasHeading = $candidateText -match '(?m)^#\s+Scout\s+Context' -or $candidateText -match '(?m)^##\s+Relevant\s+files'
    if (-not $hasHeading) {
        $provenanceList.Add([pscustomobject]@{
            Role = "scout"
            Type = "NORMAL"
            Index = $attemptIndex
            Model = $candidateModel
            ElapsedSeconds = $attempt.ElapsedSeconds
            Outcome = "MALFORMED_OUTPUT"
            Reason = "Output missing expected Scout structure (# Scout Context)."
            Selected = $false
        })
        Write-Warning "Scout candidate '$candidateModel' output malformed (missing # Scout Context)."
        continue
    }

    # Valid structural output!
    $provenanceList.Add([pscustomobject]@{
        Role = "scout"
        Type = "NORMAL"
        Index = $attemptIndex
        Model = $candidateModel
        ElapsedSeconds = $attempt.ElapsedSeconds
        Outcome = "SUCCESS"
        Reason = "Valid Scout report produced."
        Selected = $true
    })

    $selectedResult = @{
        Model = $candidateModel
        Text = $candidateText
        RawLogPath = $attempt.RawLogPath
    }
    break
}

Write-Host "Scout attempt provenance summary:"
foreach ($prov in $provenanceList) {
    Write-Host ("  Attempt {0} [{1}] Model: '{2}' in {3}s -> {4} (Selected: {5})" -f $prov.Index, $prov.Type, $prov.Model, [math]::Round($prov.ElapsedSeconds, 1), $prov.Outcome, $prov.Selected)
}

if ($null -eq $selectedResult) {
    throw "All configured Scout candidate models failed infrastructurally. Canonical CONTEXT.md left untouched."
}

# Atomic promotion to canonical CONTEXT.md
Set-Content -Path $candidatePath -Value $selectedResult.Text -Encoding UTF8
Move-Item -Path $candidatePath -Destination $contextPath -Force

Write-Host "Scout context successfully written to docs/tasks/$Task/CONTEXT.md (selected candidate: '$($selectedResult.Model)')."
