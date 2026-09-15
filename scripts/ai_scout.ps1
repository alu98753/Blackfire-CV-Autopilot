param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Task,

    [string]$Model,

    [int]$TimeoutSeconds = 480,

    # Internal test seam: override executable and arguments to verify process execution, timeout, streaming, and failure
    [string]$_ExecutableOverride,
    [string[]]$_ArgumentsOverride
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($_ExecutableOverride) -and -not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    throw "OpenCode is not installed. Run .\scripts\bootstrap_opencode.ps1 first."
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

if ([string]::IsNullOrWhiteSpace($Model) -and $null -ne $config.models) {
    $Model = [string]$config.models.scout
}

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

# Staging area for atomic promotion
$runtimeDir = Join-Path $repoRoot ".runtime\ai_scout\$Task"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$candidatePath = Join-Path $runtimeDir "candidate.md"
$rawLogPath = Join-Path $runtimeDir "raw_output.log"
$contextPath = Join-Path $taskDir "CONTEXT.md"

# Determine target executable and argument list
$execFile = ""
$execArgs = @()

if (-not [string]::IsNullOrWhiteSpace($_ExecutableOverride)) {
    $execFile = $_ExecutableOverride
    $execArgs = $_ArgumentsOverride
} else {
    $cmdInfo = Get-Command opencode -ErrorAction SilentlyContinue
    if ($cmdInfo.Source -like "*.ps1") {
        $execFile = "powershell.exe"
        $innerArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $cmdInfo.Source, "run", "--standalone", "--agent", "scout")
        if (-not [string]::IsNullOrWhiteSpace($Model)) {
            $innerArgs += @("--model", $Model)
        }
        $innerArgs += $prompt
        $execArgs = $innerArgs
    } else {
        $execFile = $cmdInfo.Source
        $innerArgs = @("run", "--standalone", "--agent", "scout")
        if (-not [string]::IsNullOrWhiteSpace($Model)) {
            $innerArgs += @("--model", $Model)
        }
        $innerArgs += $prompt
        $execArgs = $innerArgs
    }
}

Write-Host "Running OpenCode scout for task '$Task' (timeout: ${TimeoutSeconds}s)..."

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $execFile
$psi.WorkingDirectory = $repoRoot
if ($execArgs.Count -gt 0) {
    # In .NET Framework 4.8 / Windows PowerShell 5.1, ArgumentList is available in newer .NET,
    # but Arguments with escaped tokens or string join is universally supported.
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
    throw "Failed to start OpenCode process: $execFile"
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
        # Check timeout independent of stream activity
        if ($stopwatch.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
            $timedOut = $true
            Write-Warning "OpenCode scout timed out after ${TimeoutSeconds}s. Terminating client PID $($proc.Id)..."
            try {
                if (-not $proc.HasExited) {
                    $proc.Kill()
                }
            } catch {
                Write-Warning "Failed to kill process $($proc.Id): $_"
            }
            # Wait for child process to actually exit before cleanup
            $killConfirmed = $proc.WaitForExit(3000) -or $proc.HasExited
            if (-not $killConfirmed) {
                Write-Warning "Process termination unconfirmed: client PID $($proc.Id) did not exit within 3000ms after kill signal."
            }
            break
        }

        # Short-period wait loop on main thread
        if ($proc.WaitForExit(50)) {
            # Process exited; ensure async read events finish flushing
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

# Snapshot captured lines under lock
[System.Threading.Monitor]::Enter($lockObj)
try {
    $capturedArray = $capturedLines.ToArray()
    $errArray = $errLines.ToArray()
} finally {
    [System.Threading.Monitor]::Exit($lockObj)
}

$exitCode = if ($timedOut) { -1 } else { $proc.ExitCode }

# Write raw log for diagnostics
$fullRaw = ($capturedArray + $errArray) -join "`n"
Set-Content -Path $rawLogPath -Value $fullRaw -Encoding UTF8

if ($timedOut) {
    if ($killConfirmed) {
        throw "OpenCode scout timed out after ${TimeoutSeconds}s (client PID $($proc.Id) terminated). Canonical CONTEXT.md left untouched."
    } else {
        throw "OpenCode scout timed out after ${TimeoutSeconds}s (termination failure: client PID $($proc.Id) could not be confirmed exited). Canonical CONTEXT.md left untouched."
    }
}

if ($exitCode -ne 0) {
    $errSummary = $errArray -join "`n"
    throw "OpenCode scout failed with exit code $exitCode.`n$errSummary"
}

# Candidate report verification
$candidateText = ($capturedArray -join "`n").Trim()
if ([string]::IsNullOrWhiteSpace($candidateText)) {
    throw "OpenCode scout produced empty output. Canonical CONTEXT.md left untouched."
}

# Basic structural validation: verify it looks like a Scout context report
$hasHeading = $candidateText -match '(?m)^#\s+Scout\s+Context' -or $candidateText -match '(?m)^##\s+Relevant\s+files'
if (-not $hasHeading) {
    throw "OpenCode scout output missing expected Scout structure (# Scout Context). Candidate staged at '$rawLogPath'. Canonical CONTEXT.md left untouched."
}

# Atomic promotion to canonical CONTEXT.md
Set-Content -Path $candidatePath -Value $candidateText -Encoding UTF8
Move-Item -Path $candidatePath -Destination $contextPath -Force

Write-Host "Scout context successfully written to docs/tasks/$Task/CONTEXT.md"
