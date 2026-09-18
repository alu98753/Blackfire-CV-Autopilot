[CmdletBinding()]
param(
    [string]$Task,
    [string]$Branch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'task_package_resolver.ps1')

function Write-TaskStartResult([bool]$Ok, [string]$Code, [string]$Message, [hashtable]$Data = @{}) {
    $result = [ordered]@{
        ok = $Ok
        code = $Code
        message = $Message
        task = if ($Task) { $Task } else { '' }
    }
    foreach ($key in $Data.Keys) {
        $result[$key] = $Data[$key]
    }
    [Console]::Out.WriteLine(($result | ConvertTo-Json -Compress))
    if ($Ok) {
        exit 0
    }
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Task) -or $Task -notmatch '^[a-z0-9][a-z0-9-]*$') {
    Write-TaskStartResult $false 'INVALID_ARGUMENT' "Task parameter '$Task' is invalid. Must match '^[a-z0-9][a-z0-9-]*$'." @{}
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


$effectiveBranch = if (-not [string]::IsNullOrWhiteSpace($Branch)) {
    $trimmedBranch = $Branch.Trim()
    if ($trimmedBranch -match '\s') {
        Write-TaskStartResult $false 'INVALID_ARGUMENT' "Branch parameter '$Branch' is invalid. Must not contain whitespace." @{}
    }
    $trimmedBranch
} else {
    $Task
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$gitExe = if ($env:TASK_START_GIT_EXE) { $env:TASK_START_GIT_EXE } else { 'git' }
$pythonHelper = if ($env:TASK_START_PYTHON_HELPER) { $env:TASK_START_PYTHON_HELPER } else { Join-Path $scriptRoot 'worktree_environment_bootstrap.ps1' }

function Invoke-GitProcess([string[]]$Arguments, [string]$Cwd) {
    $old = (Get-Location).Path
    $captureDir = Join-Path ([System.IO.Path]::GetTempPath()) ("task-start-git-" + [guid]::NewGuid().ToString('N'))
    $stdoutPath = Join-Path $captureDir 'stdout.txt'
    $stderrPath = Join-Path $captureDir 'stderr.txt'
    try {
        New-Item -ItemType Directory -Path $captureDir -Force | Out-Null
        Set-Location -LiteralPath $Cwd
        $oldEAP = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & $gitExe @Arguments 1> $stdoutPath 2> $stderrPath
        } finally {
            $ErrorActionPreference = $oldEAP
        }
        $code = $LASTEXITCODE
        $output = @(if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath })
        $stderr = @(if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath })
        return [pscustomobject]@{
            Code = $code
            Lines = $output
            Stderr = $stderr
            Text = (($output + $stderr) -join "`n")
        }
    } finally {
        Set-Location -LiteralPath $old
        Remove-Item -LiteralPath $captureDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Parse-Worktrees([string[]]$Lines) {
    $records = @()
    $record = [ordered]@{}
    foreach ($line in $Lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            if ($record.Count) {
                $records += [pscustomobject]$record
                $record = [ordered]@{}
            }
            continue
        }
        if ($line -match '^worktree (.+)$') { $record.path = $Matches[1]; continue }
        if ($line -match '^HEAD (.+)$') { $record.head = $Matches[1]; continue }
        if ($line -match '^branch refs/heads/(.+)$') { $record.branch = $Matches[1]; continue }
        if ($line -eq 'detached HEAD' -or $line -match '^detached') { $record.detached = $true }
    }
    if ($record.Count) { $records += [pscustomobject]$record }
    return @($records)
}

try {
    # 1. Discover canonical root / canonical main
    $commonDirResult = if ($env:TASK_START_COMMON_DIR_OVERRIDE) {
        $env:TASK_START_COMMON_DIR_OVERRIDE
    } else {
        $rAbs = Invoke-GitProcess @('-C', $scriptRoot, 'rev-parse', '--path-format=absolute', '--git-common-dir') $scriptRoot
        if ($rAbs.Code -eq 0 -and $rAbs.Lines.Count -ge 1 -and -not [string]::IsNullOrWhiteSpace($rAbs.Lines[0])) {
            $rAbs.Lines[0].Trim()
        } else {
            $rLeg = Invoke-GitProcess @('-C', $scriptRoot, 'rev-parse', '--git-common-dir') $scriptRoot
            if ($rLeg.Code -eq 0 -and $rLeg.Lines.Count -ge 1 -and -not [string]::IsNullOrWhiteSpace($rLeg.Lines[0])) {
                $rLeg.Lines[0].Trim()
            } else {
                $null
            }
        }
    }

    if (-not $commonDirResult) {
        Write-TaskStartResult $false 'CANONICAL_MAIN_MISSING' 'Unable to discover Git common directory.' @{}
    }

    $commonDirText = ([string]$commonDirResult).Trim()
    $commonDir = if ([System.IO.Path]::IsPathRooted($commonDirText)) {
        Normalize-WindowsPath $commonDirText
    } else {
        Normalize-WindowsPath (Join-Path $scriptRoot $commonDirText)
    }

    $canonicalRoot = if ($env:TASK_START_CANONICAL_MAIN_OVERRIDE) {
        Normalize-WindowsPath $env:TASK_START_CANONICAL_MAIN_OVERRIDE
    } elseif ((Split-Path $commonDir -Leaf) -ieq '.git') {
        Normalize-WindowsPath (Split-Path $commonDir -Parent)
    } else {
        $null
    }

    if (-not $canonicalRoot -or -not (Test-Path -LiteralPath $canonicalRoot -PathType Container)) {
        Write-TaskStartResult $false 'CANONICAL_MAIN_MISSING' 'Canonical main worktree path is missing or could not be determined.' @{}
    }

    # 2. Inspect worktree topology for canonical main
    $topoBefore = Invoke-GitProcess @('worktree', 'list', '--porcelain') $canonicalRoot
    if ($topoBefore.Code -ne 0) {
        Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to read worktree topology: $($topoBefore.Text)" @{}
    }
    $recordsBefore = Parse-Worktrees $topoBefore.Lines
    $mainMatches = @($recordsBefore | Where-Object {
        (Normalize-WindowsPath $_.path) -eq $canonicalRoot
    })

    if ($mainMatches.Count -ne 1) {
        Write-TaskStartResult $false 'CANONICAL_MAIN_MISSING' "Canonical main worktree at '$canonicalRoot' is not registered in Git topology." @{}
    }

    $mainRecord = $mainMatches[0]
    if ($mainRecord.PSObject.Properties.Name -contains 'detached' -and $mainRecord.detached) {
        Write-TaskStartResult $false 'CANONICAL_MAIN_DETACHED' 'Canonical main worktree is in detached HEAD state.' @{}
    }
    if ($mainRecord.branch -ne 'main') {
        Write-TaskStartResult $false 'CANONICAL_MAIN_WRONG_BRANCH' "Canonical main worktree is attached to branch '$($mainRecord.branch)', expected 'main'." @{
            actual_branch = $mainRecord.branch
        }
    }

    # 3. Canonical main cleanliness
    $mainStatus = Invoke-GitProcess @('-C', $canonicalRoot, 'status', '--porcelain') $canonicalRoot
    if ($mainStatus.Code -ne 0) {
        Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to inspect canonical main status: $($mainStatus.Text)" @{}
    }
    if ($mainStatus.Lines.Count -gt 0) {
        Write-TaskStartResult $false 'CANONICAL_MAIN_DIRTY' 'Canonical main worktree is dirty. Aborting task startup.' @{}
    }

    # 4. Fetch origin from canonical main
    $fetchRes = Invoke-GitProcess @('-C', $canonicalRoot, 'fetch', 'origin') $canonicalRoot
    if ($fetchRes.Code -ne 0) {
        Write-TaskStartResult $false 'FETCH_FAILED' "git fetch origin failed: $($fetchRes.Text)" @{}
    }

    # 5. Canonical main synchronization
    $mainHeadRes = Invoke-GitProcess @('-C', $canonicalRoot, 'rev-parse', 'HEAD') $canonicalRoot
    $originMainRes = Invoke-GitProcess @('-C', $canonicalRoot, 'rev-parse', 'refs/remotes/origin/main') $canonicalRoot
    if ($mainHeadRes.Code -ne 0 -or $originMainRes.Code -ne 0) {
        Write-TaskStartResult $false 'INTERNAL_ERROR' 'Unable to resolve HEAD or origin/main refs in canonical main.' @{}
    }
    $mainHeadSha = $mainHeadRes.Lines[0].Trim()
    $originMainSha = $originMainRes.Lines[0].Trim()

    if ($mainHeadSha -ne $originMainSha) {
        # Check if HEAD is ancestor of origin/main
        $ancRes = Invoke-GitProcess @('-C', $canonicalRoot, 'merge-base', '--is-ancestor', 'HEAD', 'refs/remotes/origin/main') $canonicalRoot
        if ($ancRes.Code -ne 0) {
            Write-TaskStartResult $false 'CANONICAL_MAIN_DIVERGED' 'Canonical main has diverged or contains local-only unpushed commits relative to origin/main.' @{
                main_head = $mainHeadSha
                origin_main = $originMainSha
            }
        }
        # Safe fast-forward
        $ffRes = Invoke-GitProcess @('-C', $canonicalRoot, 'merge', '--ff-only', 'refs/remotes/origin/main') $canonicalRoot
        if ($ffRes.Code -ne 0) {
            Write-TaskStartResult $false 'CANONICAL_MAIN_DIVERGED' "Failed to fast-forward canonical main to origin/main: $($ffRes.Text)" @{}
        }
        $refreshedHead = Invoke-GitProcess @('-C', $canonicalRoot, 'rev-parse', 'HEAD') $canonicalRoot
        $mainHeadSha = $refreshedHead.Lines[0].Trim()
    }

    # 6. Approved remote task branch verification
    $remoteRef = "refs/remotes/origin/$effectiveBranch"
    $remoteCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'show-ref', '--verify', '--quiet', $remoteRef) $canonicalRoot
    if ($remoteCheck.Code -ne 0) {
        Write-TaskStartResult $false 'REMOTE_TASK_BRANCH_MISSING' "Approved remote task branch '$remoteRef' does not exist." @{
            remote_ref = $remoteRef
            branch = $effectiveBranch
        }
    }

    # 7. Fresh-base validation: origin/main must be ancestor of origin/<branch>
    $baseCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'merge-base', '--is-ancestor', 'refs/remotes/origin/main', $remoteRef) $canonicalRoot
    if ($baseCheck.Code -ne 0) {
        Write-TaskStartResult $false 'TASK_BRANCH_STALE_BASE' "Remote task branch '$remoteRef' does not contain current origin/main ($originMainSha) as an ancestor." @{
            base_sha = $originMainSha
            remote_ref = $remoteRef
        }
    }

    # 8. Remote task artifact preflight
    $taskGitPath = Get-TaskPackageGitPath $Task
    $specRemoteCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'cat-file', '-e', "$remoteRef`:$taskGitPath/SPEC.md") $canonicalRoot
    $taskJsonRemoteCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'cat-file', '-e', "$remoteRef`:$taskGitPath/task.json") $canonicalRoot
    if ($specRemoteCheck.Code -ne 0 -or $taskJsonRemoteCheck.Code -ne 0) {
        Write-TaskStartResult $false 'TASK_PACKAGE_MISSING' "Approved remote task branch is missing required task artifacts under '$taskGitPath/' (SPEC.md, task.json)." @{
            task = $Task
            remote_ref = $remoteRef
        }
    }

    # Verify task.json content on remote
    $taskJsonContentRes = Invoke-GitProcess @('-C', $canonicalRoot, 'show', "$remoteRef`:$taskGitPath/task.json") $canonicalRoot
    if ($taskJsonContentRes.Code -ne 0) {
        Write-TaskStartResult $false 'TASK_PACKAGE_INVALID' "Failed to read remote '$taskGitPath/task.json'." @{}
    }
    try {
        $parsedRemoteTaskJson = ($taskJsonContentRes.Lines -join "`n") | ConvertFrom-Json -ErrorAction Stop
        if ($parsedRemoteTaskJson.id -ne $Task) {
            Write-TaskStartResult $false 'TASK_PACKAGE_INVALID' "Remote task.json id '$($parsedRemoteTaskJson.id)' does not match Task '$Task'." @{
                expected = $Task
                actual = $parsedRemoteTaskJson.id
            }
        }
    } catch {
        Write-TaskStartResult $false 'TASK_PACKAGE_INVALID' "Remote task.json is malformed JSON: $($_.Exception.Message)" @{}
    }

    # 9. Worktree topology state machine
    $worktreesRoot = if ($env:TASK_START_WORKTREES_ROOT_OVERRIDE) {
        Normalize-WindowsPath $env:TASK_START_WORKTREES_ROOT_OVERRIDE
    } else {
        Normalize-WindowsPath (Join-Path (Split-Path $canonicalRoot -Parent) 'worktrees')
    }
    $targetWorktreePath = Normalize-WindowsPath (Join-Path $worktreesRoot $Task)

    # Refresh topology
    $topoNow = Invoke-GitProcess @('worktree', 'list', '--porcelain') $canonicalRoot
    if ($topoNow.Code -ne 0) {
        Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to read worktree topology: $($topoNow.Text)" @{}
    }
    $currentRecords = Parse-Worktrees $topoNow.Lines

    # Check if branch is checked out in any worktree
    $branchCheckedOutIn = @($currentRecords | Where-Object {
        $_.branch -eq $effectiveBranch
    })

    # Check if target path is registered
    $pathRegisteredIn = @($currentRecords | Where-Object {
        (Normalize-WindowsPath $_.path) -eq $targetWorktreePath
    })

    $action = 'CREATED'

    if ($pathRegisteredIn.Count -gt 0) {
        # Canonical target path is already registered
        $wRec = $pathRegisteredIn[0]
        if ($wRec.PSObject.Properties.Name -contains 'detached' -and $wRec.detached) {
            Write-TaskStartResult $false 'DETACHED_TASK_WORKTREE' "Canonical task worktree at '$targetWorktreePath' is in detached HEAD state." @{
                worktree = $targetWorktreePath
            }
        }
        if ($wRec.branch -ne $effectiveBranch) {
            Write-TaskStartResult $false 'WORKTREE_PATH_CONFLICT' "Canonical task path '$targetWorktreePath' is registered to branch '$($wRec.branch)', expected '$effectiveBranch'." @{
                actual_branch = $wRec.branch
                expected_branch = $effectiveBranch
            }
        }

        # Worktree path registered to correct branch -> State C (Reuse)
        $action = 'REUSED'

        # Worktree must be clean
        $taskStatus = Invoke-GitProcess @('-C', $targetWorktreePath, 'status', '--porcelain') $targetWorktreePath
        if ($taskStatus.Code -ne 0) {
            Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to inspect task worktree status: $($taskStatus.Text)" @{}
        }
        if ($taskStatus.Lines.Count -gt 0) {
            Write-TaskStartResult $false 'REUSED_TASK_WORKTREE_DIRTY' "Reused task worktree '$targetWorktreePath' is dirty." @{
                worktree = $targetWorktreePath
            }
        }

        # Compare local task branch with remote
        $localTaskShaRes = Invoke-GitProcess @('-C', $targetWorktreePath, 'rev-parse', 'HEAD') $targetWorktreePath
        $remoteTaskShaRes = Invoke-GitProcess @('-C', $targetWorktreePath, 'rev-parse', $remoteRef) $targetWorktreePath
        if ($localTaskShaRes.Code -ne 0 -or $remoteTaskShaRes.Code -ne 0) {
            Write-TaskStartResult $false 'INTERNAL_ERROR' 'Failed to resolve HEAD or remote ref in task worktree.' @{}
        }
        $localTaskSha = $localTaskShaRes.Lines[0].Trim()
        $remoteTaskSha = $remoteTaskShaRes.Lines[0].Trim()

        if ($localTaskSha -ne $remoteTaskSha) {
            $isBehind = Invoke-GitProcess @('-C', $targetWorktreePath, 'merge-base', '--is-ancestor', 'HEAD', $remoteRef) $targetWorktreePath
            if ($isBehind.Code -ne 0) {
                # Either ahead or diverged
                Write-TaskStartResult $false 'TASK_BRANCH_DIVERGED' "Local task branch '$effectiveBranch' has diverged from or is ahead of '$remoteRef'." @{
                    local_sha = $localTaskSha
                    remote_sha = $remoteTaskSha
                }
            }
            # Fast-forward clean worktree
            $taskFf = Invoke-GitProcess @('-C', $targetWorktreePath, 'merge', '--ff-only', $remoteRef) $targetWorktreePath
            if ($taskFf.Code -ne 0) {
                Write-TaskStartResult $false 'TASK_BRANCH_DIVERGED' "Failed to fast-forward task branch to '$remoteRef': $($taskFf.Text)" @{}
            }
        }
    } else {
        # Canonical target path is NOT registered in Git topology
        if (Test-Path -LiteralPath $targetWorktreePath) {
            # Unregistered directory exists -> State E
            Write-TaskStartResult $false 'WORKTREE_PATH_CONFLICT' "Path '$targetWorktreePath' already exists on disk but is not a registered Git worktree." @{
                worktree = $targetWorktreePath
            }
        }

        if ($branchCheckedOutIn.Count -gt 0) {
            # Branch checked out in another worktree -> State D
            $otherRec = $branchCheckedOutIn[0]
            Write-TaskStartResult $false 'BRANCH_OWNED_ELSEWHERE' "Branch '$effectiveBranch' is already checked out in worktree '$($otherRec.path)'." @{
                other_worktree = $otherRec.path
                branch = $effectiveBranch
            }
        }

        # Check if local branch ref exists
        $localRefCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'show-ref', '--verify', '--quiet', "refs/heads/$effectiveBranch") $canonicalRoot
        if ($localRefCheck.Code -eq 0) {
            # Local branch exists, not checked out anywhere -> State B
            # Compare local branch with remote before creating worktree
            $localShaRes = Invoke-GitProcess @('-C', $canonicalRoot, 'rev-parse', "refs/heads/$effectiveBranch") $canonicalRoot
            $remoteShaRes = Invoke-GitProcess @('-C', $canonicalRoot, 'rev-parse', $remoteRef) $canonicalRoot
            $lSha = $localShaRes.Lines[0].Trim()
            $rSha = $remoteShaRes.Lines[0].Trim()
            if ($lSha -ne $rSha) {
                $behindCheck = Invoke-GitProcess @('-C', $canonicalRoot, 'merge-base', '--is-ancestor', "refs/heads/$effectiveBranch", $remoteRef) $canonicalRoot
                if ($behindCheck.Code -ne 0) {
                    Write-TaskStartResult $false 'TASK_BRANCH_DIVERGED' "Local branch '$effectiveBranch' has diverged from or is ahead of '$remoteRef'." @{
                        local_sha = $lSha
                        remote_sha = $rSha
                    }
                }
            }

            $addRes = Invoke-GitProcess @('-C', $canonicalRoot, 'worktree', 'add', $targetWorktreePath, $effectiveBranch) $canonicalRoot
            if ($addRes.Code -ne 0) {
                Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to attach worktree: $($addRes.Text)" @{}
            }

            # If it was behind, fast-forward after attachment
            if ($lSha -ne $rSha) {
                $pullRes = Invoke-GitProcess @('-C', $targetWorktreePath, 'merge', '--ff-only', $remoteRef) $targetWorktreePath
                if ($pullRes.Code -ne 0) {
                    Write-TaskStartResult $false 'TASK_BRANCH_DIVERGED' "Failed to fast-forward local branch after worktree attachment: $($pullRes.Text)" @{}
                }
            }
        } else {
            # Local branch absent, remote branch exists -> State A
            $addRes = Invoke-GitProcess @('-C', $canonicalRoot, 'worktree', 'add', '-b', $effectiveBranch, $targetWorktreePath, $remoteRef) $canonicalRoot
            if ($addRes.Code -ne 0) {
                Write-TaskStartResult $false 'INTERNAL_ERROR' "Failed to create task worktree from '$remoteRef': $($addRes.Text)" @{}
            }
        }

        $action = 'CREATED'
    }

    # Post-attachment validation of local task artifacts
    $localTaskRoot = Join-Path $targetWorktreePath ($taskGitPath -replace '/', '\\')
    $localSpecPath = Join-Path $localTaskRoot 'SPEC.md'
    $localTaskJsonPath = Join-Path $localTaskRoot 'task.json'
    if (-not (Test-Path -LiteralPath $localSpecPath) -or -not (Test-Path -LiteralPath $localTaskJsonPath)) {
        Write-TaskStartResult $false 'TASK_PACKAGE_MISSING' "Task worktree is missing checked-out task artifacts in '$taskGitPath/'." @{
            worktree = $targetWorktreePath
        }
    }
    try {
        $localTaskJson = Get-Content -LiteralPath $localTaskJsonPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($localTaskJson.id -ne $Task) {
            Write-TaskStartResult $false 'TASK_PACKAGE_INVALID' "Checked out task.json id '$($localTaskJson.id)' does not match Task '$Task'." @{
                expected = $Task
                actual = $localTaskJson.id
            }
        }
    } catch {
        Write-TaskStartResult $false 'TASK_PACKAGE_INVALID' "Failed to parse checked-out task.json: $($_.Exception.Message)" @{}
    }

    # 10. Python bootstrap integration
    if (-not (Test-Path -LiteralPath $pythonHelper -PathType Leaf)) {
        Write-TaskStartResult $false 'INTERNAL_ERROR' "Python environment bootstrap helper not found at '$pythonHelper'." @{}
    }

    $captureDir = Join-Path ([System.IO.Path]::GetTempPath()) ("task-start-py-" + [guid]::NewGuid().ToString('N'))
    $stdoutFile = Join-Path $captureDir 'stdout.txt'
    $stderrFile = Join-Path $captureDir 'stderr.txt'
    $helperExit = -1
    $pyLines = @()
    $pyStderr = @()
    try {
        New-Item -ItemType Directory -Path $captureDir -Force | Out-Null
        $oldEAP = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $pyArgs = @('-WorktreePath', $targetWorktreePath)
            if ($env:TASK_START_CANONICAL_ENV_OVERRIDE) {
                $pyArgs += @('-CanonicalEnvironmentPath', $env:TASK_START_CANONICAL_ENV_OVERRIDE)
            }
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pythonHelper @pyArgs 1> $stdoutFile 2> $stderrFile
            $helperExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $oldEAP
        }
        $pyLines = @(if (Test-Path $stdoutFile) { Get-Content -LiteralPath $stdoutFile | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } })
        $pyStderr = @(if (Test-Path $stderrFile) { Get-Content -LiteralPath $stderrFile })
    } finally {
        Remove-Item -LiteralPath $captureDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($helperExit -ne 0 -or $pyLines.Count -ne 1) {
        Write-TaskStartResult $false 'PYTHON_BOOTSTRAP_FAILED' "Python bootstrap helper failed or returned unexpected line count ($($pyLines.Count), exit $helperExit)." @{
            helper_exit = $helperExit
            output = ($pyLines -join "`n")
            stderr = ($pyStderr -join "`n")
        }
    }

    $pyJson = $null
    try {
        $pyJson = $pyLines[0] | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Write-TaskStartResult $false 'PYTHON_BOOTSTRAP_FAILED' "Python bootstrap helper returned malformed JSON: $($_.Exception.Message)" @{
            raw_stdout = $pyLines[0]
        }
    }

    $hasOk = ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'ok') -and $pyJson.ok -eq $true)
    $hasReady = ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'code') -and $pyJson.code -eq 'READY')

    if (-not $hasOk -or -not $hasReady) {
        $helperCode = if ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'code')) { [string]$pyJson.code } else { 'UNKNOWN' }
        $helperMsg = if ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'message')) { [string]$pyJson.message } else { 'No message' }
        Write-TaskStartResult $false 'PYTHON_BOOTSTRAP_FAILED' "Python bootstrap helper did not report READY status." @{
            helper_code = $helperCode
            helper_message = $helperMsg
        }
    }

    $pyAction = if ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'action')) { [string]$pyJson.action } else { 'UNCHANGED' }
    $pyVersion = if ($null -ne $pyJson -and ($pyJson.PSObject.Properties.Name -contains 'python_version')) { [string]$pyJson.python_version } else { '' }

    # Success!
    Write-TaskStartResult $true 'TASK_READY' "Task worktree is ready for development." @{
        task = $Task
        branch = $effectiveBranch
        worktree = $targetWorktreePath
        base_sha = $originMainSha
        remote_ref = $remoteRef
        action = $action
        python_action = $pyAction
        python_version = $pyVersion
    }
}
catch {
    Write-TaskStartResult $false 'INTERNAL_ERROR' $_.Exception.Message @{}
}
