[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$WorktreePath,

    [string]$CanonicalEnvironmentPath = 'E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExitCodes = @{
    READY = 0
    NOT_REGISTERED_WORKTREE = 21
    CANONICAL_ENV_MISSING = 15
    MISSING_INTERPRETER = 17
    PHYSICAL_DIRECTORY = 11
    WRONG_TARGET = 12
    UNSUPPORTED_REPARSE = 13
    AMBIGUOUS_TARGET = 14
    JUNCTION_CREATION_FAILED = 16
    INTERPRETER_UNUSABLE = 18
    INVALID_ARGUMENT = 64
    INTERNAL_ERROR = 70
}

function Normalize-WindowsPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw 'path is empty'
    }

    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($full)
    while ($full.Length -gt $root.Length -and ($full.EndsWith('\') -or $full.EndsWith('/'))) {
        $full = $full.Substring(0, $full.Length - 1)
    }
    return $full
}

function Write-Result([string]$Code, [string]$Message, [hashtable]$Data = @{}) {
    $result = [ordered]@{
        ok = ($Code -eq 'READY')
        code = $Code
        message = $Message
        worktree = $WorktreePath
    }
    foreach ($key in $Data.Keys) { $result[$key] = $Data[$key] }
    [Console]::Out.WriteLine(($result | ConvertTo-Json -Compress))
    if ($ExitCodes.ContainsKey($Code)) { exit $ExitCodes[$Code] }
    exit $ExitCodes.INTERNAL_ERROR
}

function Classify-Venv([string]$VenvPath, [string]$ExpectedCanonicalPath) {
    $item = Get-Item -LiteralPath $VenvPath -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        return @{ State = 'ABSENT' }
    }

    $isReparse = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    if (-not $isReparse) {
        return @{ State = 'PHYSICAL_DIRECTORY'; Item = $item }
    }

    $linkType = [string]$item.LinkType
    if ($linkType -ne 'Junction' -and $linkType -ne 'MountPoint') {
        return @{ State = 'UNSUPPORTED_REPARSE'; Item = $item; LinkType = $linkType }
    }

    $targets = @($item.Target | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    if ($targets.Count -ne 1) {
        return @{ State = 'AMBIGUOUS_TARGET'; Item = $item; TargetCount = $targets.Count }
    }

    $target = Normalize-WindowsPath $targets[0]
    if (-not [string]::Equals($target, $ExpectedCanonicalPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        return @{ State = 'WRONG_TARGET'; Item = $item; Target = $target; ExpectedTarget = $ExpectedCanonicalPath }
    }

    return @{ State = 'CORRECT_JUNCTION'; Item = $item; Target = $target }
}

try {
    if ([string]::IsNullOrWhiteSpace($WorktreePath)) {
        Write-Result 'INVALID_ARGUMENT' 'WorktreePath parameter is required and cannot be whitespace.' @{}
    }
    if ([string]::IsNullOrWhiteSpace($CanonicalEnvironmentPath)) {
        Write-Result 'INVALID_ARGUMENT' 'CanonicalEnvironmentPath parameter cannot be whitespace.' @{}
    }

    $worktree = Normalize-WindowsPath $WorktreePath
    $canonical = Normalize-WindowsPath $CanonicalEnvironmentPath

    if (-not (Test-Path -LiteralPath $worktree -PathType Container)) {
        Write-Result 'NOT_REGISTERED_WORKTREE' 'WorktreePath does not exist as a directory.' @{ path = $worktree }
    }

    # Validate worktree is registered via git worktree list --porcelain
    $gitExe = if ($env:WORKTREE_BOOTSTRAP_GIT_EXE) { $env:WORKTREE_BOOTSTRAP_GIT_EXE } else { 'git' }
    $gitOldEAP = $ErrorActionPreference
    $gitOutputLines = @()
    try {
        $ErrorActionPreference = 'Continue'
        $gitOutputLines = & $gitExe -C $worktree worktree list --porcelain 2>$null
    } catch {
        Write-Result 'NOT_REGISTERED_WORKTREE' "Failed to query Git worktree registration: $($_.Exception.Message)" @{}
    } finally {
        $ErrorActionPreference = $gitOldEAP
    }

    if ($LASTEXITCODE -ne 0 -or $gitOutputLines.Count -eq 0) {
        Write-Result 'NOT_REGISTERED_WORKTREE' 'Unable to read Git worktree topology from worktree context.' @{ exit_code = $LASTEXITCODE }
    }

    $registeredPaths = @()
    foreach ($line in $gitOutputLines) {
        if ($line -match '^worktree\s+(.+)$') {
            $registeredPaths += (Normalize-WindowsPath $Matches[1])
        }
    }

    $matching = @($registeredPaths | Where-Object { [string]::Equals($_, $worktree, [System.StringComparison]::OrdinalIgnoreCase) })
    if ($matching.Count -ne 1) {
        Write-Result 'NOT_REGISTERED_WORKTREE' "WorktreePath '$worktree' is not registered as an exact Git worktree." @{
            registered_count = $matching.Count
            worktree = $worktree
        }
    }

    # Validate canonical shared environment preconditions before any mutation
    if (-not (Test-Path -LiteralPath $canonical -PathType Container)) {
        Write-Result 'CANONICAL_ENV_MISSING' "Canonical Python environment path is missing: '$canonical'." @{
            canonical_path = $canonical
        }
    }

    $canonicalPython = Join-Path (Join-Path $canonical 'Scripts') 'python.exe'
    if (-not (Test-Path -LiteralPath $canonicalPython -PathType Leaf)) {
        Write-Result 'MISSING_INTERPRETER' "Canonical Python interpreter is missing: '$canonicalPython'." @{
            interpreter_path = $canonicalPython
        }
    }

    $venv = Join-Path $worktree '.venv'
    $action = 'UNCHANGED'

    # Initial classification
    $classification = Classify-Venv $venv $canonical

    switch ($classification.State) {
        'ABSENT' {
            # Safely absent: create exact junction targeting canonical
            & cmd.exe /d /s /c ('mklink /J "' + $venv + '" "' + $canonical + '"') | Out-Null
            $creationExit = $LASTEXITCODE
            if ($creationExit -ne 0 -or -not (Test-Path -LiteralPath $venv)) {
                Write-Result 'JUNCTION_CREATION_FAILED' 'Failed to create Windows junction to canonical environment.' @{
                    exit_code = $creationExit
                    target = $canonical
                }
            }

            # Re-classify newly created junction
            $postClassification = Classify-Venv $venv $canonical
            if ($postClassification.State -ne 'CORRECT_JUNCTION') {
                Write-Result 'JUNCTION_CREATION_FAILED' "Newly created .venv failed postcondition classification: $($postClassification.State)." @{
                    post_state = $postClassification.State
                }
            }
            $action = 'CREATED'
        }
        'CORRECT_JUNCTION' {
            $action = 'UNCHANGED'
        }
        'PHYSICAL_DIRECTORY' {
            Write-Result 'PHYSICAL_DIRECTORY' '.venv is a physical directory, not a reparse object; preserved.' @{}
        }
        'WRONG_TARGET' {
            Write-Result 'WRONG_TARGET' 'Junction target is not the configured canonical environment; preserved.' @{
                target = $classification.Target
                expected_target = $classification.ExpectedTarget
            }
        }
        'UNSUPPORTED_REPARSE' {
            Write-Result 'UNSUPPORTED_REPARSE' ".venv reparse type '$($classification.LinkType)' is unsupported; preserved." @{
                reparse_type = $classification.LinkType
            }
        }
        'AMBIGUOUS_TARGET' {
            Write-Result 'AMBIGUOUS_TARGET' '.venv does not expose exactly one structured target; preserved.' @{
                target_count = $classification.TargetCount
            }
        }
        default {
            Write-Result 'JUNCTION_CREATION_FAILED' "Unknown or broken .venv reparse state: $($classification.State); preserved." @{}
        }
    }

    # Verify interpreter execution through worktree-local path
    $localPython = Join-Path (Join-Path $venv 'Scripts') 'python.exe'
    if (-not (Test-Path -LiteralPath $localPython -PathType Leaf)) {
        Write-Result 'MISSING_INTERPRETER' "Worktree-local Python interpreter does not exist: '$localPython'." @{
            local_interpreter = $localPython
        }
    }

    $pythonVersionOutput = ''
    $pythonOldEAP = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $versionLines = & $localPython --version 2>&1
        $pyExit = $LASTEXITCODE
        $pythonVersionOutput = ($versionLines -join ' ').Trim()
    } catch {
        Write-Result 'INTERPRETER_UNUSABLE' "Failed to invoke worktree-local Python interpreter: $($_.Exception.Message)" @{
            local_interpreter = $localPython
        }
    } finally {
        $ErrorActionPreference = $pythonOldEAP
    }

    if ($pyExit -ne 0) {
        Write-Result 'INTERPRETER_UNUSABLE' "Worktree-local Python interpreter exited with non-zero code $pyExit." @{
            exit_code = $pyExit
            output = $pythonVersionOutput
            local_interpreter = $localPython
        }
    }

    Write-Result 'READY' 'Worktree Python environment junction verified and runnable.' @{
        action = $action
        target = $canonical
        python_version = $pythonVersionOutput
    }
}
catch {
    Write-Result 'INTERNAL_ERROR' $_.Exception.Message @{}
}
