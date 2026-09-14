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
- Inspect at most 10 directly relevant repository files. When the 10-file budget is reached, stop immediately and report uncertainty.
- Keep the report concise (target <= 1500 words).
- Stop once the minimal change surface, risks, and uncertainty are established.
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
        $innerArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $cmdInfo.Source, "run", "--agent", "scout")
        if (-not [string]::IsNullOrWhiteSpace($Model)) {
            $innerArgs += @("--model", $Model)
        }
        $innerArgs += $prompt
        $execArgs = $innerArgs
    } else {
        $execFile = $cmdInfo.Source
        $innerArgs = @("run", "--agent", "scout")
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
$psi.UseShellExecute = $false

$proc = [System.Diagnostics.Process]::Start($psi)
if ($null -eq $proc) {
    throw "Failed to start OpenCode process: $execFile"
}

$capturedLines = [System.Collections.Generic.List[string]]::new()
$errLines = [System.Collections.Generic.List[string]]::new()
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$timedOut = $false

while ($true) {
    # Read available stdout lines in real-time
    while ($proc.StandardOutput.Peek() -ge 0) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -ne $line) {
            [Console]::WriteLine($line)
            $capturedLines.Add($line)
        }
    }
    # Read available stderr lines in real-time
    while ($proc.StandardError.Peek() -ge 0) {
        $eline = $proc.StandardError.ReadLine()
        if ($null -ne $eline) {
            [Console]::Error.WriteLine($eline)
            $errLines.Add($eline)
        }
    }

    # Check timeout
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
        break
    }

    # Check if process exited
    if ($proc.WaitForExit(50)) {
        # Drain remaining streams
        while (-not $proc.StandardOutput.EndOfStream) {
            $line = $proc.StandardOutput.ReadLine()
            if ($null -ne $line) {
                [Console]::WriteLine($line)
                $capturedLines.Add($line)
            }
        }
        while (-not $proc.StandardError.EndOfStream) {
            $eline = $proc.StandardError.ReadLine()
            if ($null -ne $eline) {
                [Console]::Error.WriteLine($eline)
                $errLines.Add($eline)
            }
        }
        break
    }
}

$exitCode = if ($timedOut) { -1 } else { $proc.ExitCode }

# Write raw log for diagnostics
$fullRaw = ($capturedLines + $errLines) -join "`n"
Set-Content -Path $rawLogPath -Value $fullRaw -Encoding UTF8

if ($timedOut) {
    throw "OpenCode scout timed out after ${TimeoutSeconds}s (client PID $($proc.Id) terminated). Canonical CONTEXT.md left untouched."
}

if ($exitCode -ne 0) {
    $errSummary = $errLines -join "`n"
    throw "OpenCode scout failed with exit code $exitCode.`n$errSummary"
}

# Candidate report verification
$candidateText = ($capturedLines -join "`n").Trim()
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
