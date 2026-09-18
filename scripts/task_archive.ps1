[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9-]*$')][string]$Task,
    [ValidateSet('worktree-add','mv','commit','push')][string]$_FailGitStep
)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent; Set-Location $repoRoot
. (Join-Path $PSScriptRoot 'task_package_resolver.ps1')

function Fail([string]$Code){ throw $Code }
$resolved=Resolve-TaskPackage -Task $Task -RepoRoot $repoRoot
if($resolved.Classification -ne 'ACTIVE'){ Fail "TASK_$($resolved.Classification)" }
$mainStatus=@(git status --porcelain)
if($mainStatus.Count){ Fail 'ARCHIVE_REQUIRES_CLEAN_MAIN' }
git fetch origin main --quiet
if($LASTEXITCODE -ne 0){ Fail 'ARCHIVE_ORIGIN_FETCH_FAILED' }
$mainHead=(git rev-parse HEAD).Trim(); $originMain=(git rev-parse origin/main).Trim()
if($mainHead -ne $originMain){ Fail 'ARCHIVE_REQUIRES_CANONICAL_MAIN_AT_ORIGIN_MAIN' }

# The task worktree is the topology authority. Require exactly one clean worktree
# for the active task package, and use its branch tip as the integration candidate.
$records=@(); $path=''; $branch=''; $lines=@(git worktree list --porcelain)
for($i=0;$i -lt $lines.Count;$i++){ if($lines[$i] -match '^worktree (.+)$'){$path=$Matches[1]}; if($lines[$i] -match '^branch refs/heads/(.+)$'){$branch=$Matches[1]}; if(($lines[$i] -match '^$') -or $i -eq $lines.Count-1){ if($path -and $branch){$records += [pscustomobject]@{Path=$path;Branch=$branch}}; $path='';$branch='' } }
$taskRecords=@($records | Where-Object {$_.Branch -match "(^|/)$([regex]::Escape($Task))$"})
if($taskRecords.Count -ne 1){ Fail 'ARCHIVE_INTEGRATION_UNPROVEN' }
$taskWt=$taskRecords[0]
if(@(git -C $taskWt.Path status --porcelain).Count){ Fail 'ARCHIVE_TASK_WORKTREE_DIRTY' }
$taskHead=(git -C $taskWt.Path rev-parse HEAD).Trim()
$ancestor=git merge-base --is-ancestor $taskHead origin/main 2>$null
if($LASTEXITCODE -ne 0){ Fail 'ARCHIVE_INTEGRATION_UNPROVEN' }

# Find the unique first-parent merge boundary that contains task HEAD but not
# its first parent. This avoids treating migration/path-touch commits as proof.
$boundaries=@(git log origin/main --first-parent --merges --format='%H %P' | ForEach-Object { $parts=$_.Split(' '); if($parts.Count -ge 3){$m=$parts[0];$p=$parts[1]; git merge-base --is-ancestor $taskHead $m 2>$null; $a=$LASTEXITCODE; git merge-base --is-ancestor $taskHead $p 2>$null; $b=$LASTEXITCODE; if($a -eq 0 -and $b -ne 0){$m}}})
if($boundaries.Count -ne 1){ Fail 'ARCHIVE_INTEGRATION_COMMIT_AMBIGUOUS' }
$integrationCommit=$boundaries[0].Trim()
$integrationTimestamp=(git show -s --format='%cI' $integrationCommit).Trim()
$year=([DateTimeOffset]::Parse($integrationTimestamp).ToUniversalTime().Year).ToString()
$sourcePath=Get-TaskPackageRelativePath $Task
$destination=Get-TaskArchiveRelativePath $Task $year
if(@(git ls-tree -r --name-only origin/main $destination).Count){ Fail 'ARCHIVE_DESTINATION_COLLISION' }
$closeoutBranch="archive/$Task-$year"
if(git ls-remote --heads origin $closeoutBranch){ Fail 'ARCHIVE_CLOSEOUT_BRANCH_COLLISION' }

# Prepare the move in an isolated worktree/branch; canonical main is untouched.
$closeoutPath=Join-Path ([IO.Path]::GetTempPath()) "blackfire-archive-closeout-$Task-$year-$PID"
if(Test-Path $closeoutPath){ Fail 'ARCHIVE_CLOSEOUT_PATH_COLLISION' }
New-Item -ItemType Directory -Force (Split-Path $closeoutPath) | Out-Null
$archiveGitErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$closeoutFailure = $null
$worktreeAddOutput = if ($_FailGitStep -eq 'worktree-add') { @('forced test failure') } else { @(git worktree add --detach $closeoutPath origin/main 2>$null | Out-Null) }
if ($_FailGitStep -eq 'worktree-add') { $global:LASTEXITCODE = 1 }
if ($LASTEXITCODE -ne 0) { Fail "ARCHIVE_CLOSEOUT_WORKTREE_ADD_FAILED: $($worktreeAddOutput -join ' ')" }
try {
    New-Item -ItemType Directory -Force (Join-Path $closeoutPath (Split-Path ($destination -replace '/', '\') -Parent)) | Out-Null
    $mvOutput = if ($_FailGitStep -eq 'mv') { @('forced test failure') } else { @(git -C $closeoutPath mv -- $sourcePath $destination 2>$null | Out-Null) }
    if ($_FailGitStep -eq 'mv') { $global:LASTEXITCODE = 1 }
    if ($LASTEXITCODE -ne 0) { Fail "ARCHIVE_CLOSEOUT_MOVE_FAILED: $($mvOutput -join ' ')" }
    $commitOutput = if ($_FailGitStep -eq 'commit') { @('forced test failure') } else { @(git -C $closeoutPath commit -m "archive task $Task ($year)" --quiet 2>$null | Out-Null) }
    if ($_FailGitStep -eq 'commit') { $global:LASTEXITCODE = 1 }
    if ($LASTEXITCODE -ne 0) { Fail "ARCHIVE_CLOSEOUT_COMMIT_FAILED: $($commitOutput -join ' ')" }
    $closeoutCommit=(git -C $closeoutPath rev-parse HEAD).Trim()
    $pushOutput = if ($_FailGitStep -eq 'push') { @('forced test failure') } else { @(git -C $closeoutPath push origin "HEAD:refs/heads/$closeoutBranch" --quiet 2>$null | Out-Null) }
    if ($_FailGitStep -eq 'push') { $global:LASTEXITCODE = 1 }
    if ($LASTEXITCODE -ne 0) { Fail "ARCHIVE_CLOSEOUT_PUSH_FAILED: $($pushOutput -join ' ')" }
} catch {
    $closeoutFailure = $_.Exception.Message
} finally {
    $ErrorActionPreference = 'Continue'
    $removeOutput = git worktree remove $closeoutPath 2>&1
    if($LASTEXITCODE -ne 0 -and -not $closeoutFailure){ $closeoutFailure = "ARCHIVE_CLOSEOUT_WORKTREE_REMOVE_FAILED: $($removeOutput -join ' ')" }
    $ErrorActionPreference = $archiveGitErrorAction
}
if($closeoutFailure){ throw $closeoutFailure }
[pscustomobject]@{ok=$true;outcome='ARCHIVE_CLOSEOUT_READY';task=$Task;task_head=$taskHead;integration_commit=$integrationCommit;integration_year=$year;archive_path=$destination;closeout_branch=$closeoutBranch;closeout_commit=$closeoutCommit;durability='pushed closeout branch'} | ConvertTo-Json -Compress
