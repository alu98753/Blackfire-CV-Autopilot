[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [ValidateNotNullOrEmpty()] [string]$Task,
    [switch]$DeleteRemoteBranch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (git -C $scriptRoot rev-parse --show-toplevel 2>$null).Trim()
if (-not $repoRoot) { throw 'Unable to discover repository root.' }
$gitExe = if ($env:TASK_CLEANUP_GIT_EXE) { $env:TASK_CLEANUP_GIT_EXE } else { 'git' }
$helper = if ($env:TASK_CLEANUP_HELPER) { $env:TASK_CLEANUP_HELPER } else { Join-Path $repoRoot 'scripts\worktree_cleanup_safety.ps1' }
$currentCwd = [IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\')

function Invoke-Git([string[]]$Arguments, [string]$Cwd = $repoRoot) {
    $old = (Get-Location).Path
    try {
        Set-Location -LiteralPath $Cwd
        $output = @(& $gitExe @Arguments 2>&1 | ForEach-Object { [string]$_ })
        $code = $LASTEXITCODE
        return [pscustomobject]@{ Code = $code; Lines = $output; Text = ($output -join "`n") }
    } finally { Set-Location -LiteralPath $old }
}

function Stop-Cleanup([string]$Message) {
    Write-Error "TASK CLEANUP STOPPED: $Message"
    exit 1
}

function Normalize([string]$Path) { return [IO.Path]::GetFullPath($Path).TrimEnd('\').ToLowerInvariant() }

function Parse-Worktrees([string[]]$Lines) {
    $records = @(); $record = [ordered]@{}
    foreach ($line in $Lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            if ($record.Count) { $records += [pscustomobject]$record; $record = [ordered]@{} }
            continue
        }
        if ($line -match '^worktree (.+)$') { $record.path = $Matches[1]; continue }
        if ($line -match '^HEAD (.+)$') { $record.head = $Matches[1]; continue }
        if ($line -match '^branch refs/heads/(.+)$') { $record.branch = $Matches[1]; continue }
        if ($line -eq 'detached HEAD') { $record.detached = $true }
    }
    if ($record.Count) { $records += [pscustomobject]$record }
    return @($records)
}

function Require-Clean([string]$Path, [string]$Label) {
    $r = Invoke-Git @('-C', $Path, 'status', '--porcelain')
    if ($r.Code -ne 0) { Stop-Cleanup "cannot inspect $Label status: $($r.Text)" }
    if ($r.Lines.Count -gt 0) { Stop-Cleanup "$Label is dirty." }
}

$topology = Invoke-Git @('worktree', 'list', '--porcelain')
if ($topology.Code -ne 0) { Stop-Cleanup "cannot read worktree topology: $($topology.Text)" }
$records = Parse-Worktrees $topology.Lines
$canonicalExpected = if ($env:TASK_CLEANUP_CANONICAL_MAIN) { Normalize $env:TASK_CLEANUP_CANONICAL_MAIN } else { Normalize (Join-Path (Split-Path $repoRoot -Parent) 'BlackfireCrusade_tool') }
$main = @($records | Where-Object { $_.branch -eq 'main' -and (Normalize $_.path) -eq $canonicalExpected })
if ($main.Count -ne 1) { Stop-Cleanup 'canonical main worktree is missing or ambiguous.' }
$mainPath = $main[0].path
if ((Normalize $mainPath) -eq (Normalize $currentCwd)) { $mainIsCurrent = $true }
Require-Clean $mainPath 'canonical main worktree'

$fetch = Invoke-Git @('fetch', 'origin') $mainPath
if ($fetch.Code -ne 0) { Stop-Cleanup "git fetch origin failed: $($fetch.Text)" }
$topology = Invoke-Git @('worktree', 'list', '--porcelain') $mainPath
if ($topology.Code -ne 0) { Stop-Cleanup "cannot refresh worktree topology after fetch: $($topology.Text)" }
$records = Parse-Worktrees $topology.Lines

$taskCandidates = @($records | Where-Object {
    (Split-Path (Normalize $_.path) -Leaf) -eq $Task.ToLowerInvariant() -and $_.branch -and -not $_.detached
})
if ($taskCandidates.Count -ne 1) { Stop-Cleanup "task topology resolved $($taskCandidates.Count) matching attached worktrees; expected exactly one." }
$taskRecord = $taskCandidates[0]
$taskPath = [IO.Path]::GetFullPath($taskRecord.path)
$branch = [string]$taskRecord.branch
if ((Normalize $taskPath) -eq (Normalize $currentCwd) -or (Normalize $taskPath) -eq (Normalize $mainPath)) { Stop-Cleanup 'refusing to remove current or canonical main worktree.' }

$localBranch = Invoke-Git @('show-ref', '--verify', '--quiet', "refs/heads/$branch") $mainPath
if ($localBranch.Code -ne 0) { Stop-Cleanup "resolved branch '$branch' has no local branch ref." }
Require-Clean $taskPath 'task worktree'
$ancestor = Invoke-Git @('merge-base', '--is-ancestor', $branch, 'origin/main') $mainPath
if ($ancestor.Code -ne 0) { Stop-Cleanup "branch '$branch' is not an ancestor of origin/main." }

$captureDir = Join-Path ([IO.Path]::GetTempPath()) ("task-cleanup-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $captureDir -Force | Out-Null
$stdoutPath = Join-Path $captureDir 'stdout.txt'
$stderrPath = Join-Path $captureDir 'stderr.txt'
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper -WorktreePath $taskPath -Detach 1> $stdoutPath 2> $stderrPath
    $helperExit = $LASTEXITCODE
    $helperStdout = if (Test-Path $stdoutPath) { @(Get-Content $stdoutPath) } else { @() }
    $helperStderr = if (Test-Path $stderrPath) { @(Get-Content $stderrPath) } else { @() }
} finally {
    Remove-Item -LiteralPath $captureDir -Recurse -Force -ErrorAction SilentlyContinue
}
if ($helperExit -ne 0) { Stop-Cleanup "cleanup safety helper failed: $($helperStderr -join "`n") $($helperStdout -join "`n")" }
$jsonLines = @($helperStdout | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($jsonLines.Count -ne 1) { Stop-Cleanup 'cleanup safety helper did not return exactly one JSON object.' }
try { $evidence = $jsonLines[0] | ConvertFrom-Json -ErrorAction Stop } catch { Stop-Cleanup 'cleanup safety helper returned malformed JSON.' }
if ($null -eq $evidence.code) { Stop-Cleanup 'cleanup safety helper JSON is missing code.' }
if ($evidence.code -ne 'DETACHED') { Stop-Cleanup "cleanup safety helper returned '$($evidence.code)'; no worktree removal attempted." }

$remove = Invoke-Git @('worktree', 'remove', $taskPath) $mainPath
if ($remove.Code -ne 0) { Stop-Cleanup "worktree removal failed; use documented stale/partial recovery guidance: $($remove.Text)" }
$after = Invoke-Git @('worktree', 'list', '--porcelain') $mainPath
if ($after.Code -ne 0) { Stop-Cleanup "cannot verify post-removal topology: $($after.Text)" }
$remaining = Parse-Worktrees $after.Lines
if (@($remaining | Where-Object { (Normalize $_.path) -eq (Normalize $taskPath) -or $_.branch -eq $branch }).Count -ne 0) { Stop-Cleanup "post-removal topology still owns '$branch'; local branch was not deleted." }

$deleteLocal = Invoke-Git @('branch', '-d', $branch) $mainPath
if ($deleteLocal.Code -ne 0) { Stop-Cleanup "safe local branch deletion failed; remote deletion was not attempted: $($deleteLocal.Text)" }

$remoteStatus = 'omitted'
if ($DeleteRemoteBranch) {
    $remote = Invoke-Git @('push', 'origin', '--delete', $branch) $mainPath
    if ($remote.Code -ne 0) {
        $remoteStatus = 'failed'
        Write-Error "LOCAL CLEANUP SUCCEEDED; remote branch deletion failed for '$branch': $($remote.Text)"
        exit 2
    }
    $remoteStatus = 'deleted'
}
Write-Output "TASK CLEANUP SUCCEEDED: task=$Task branch=$branch remote=$remoteStatus"
exit 0
