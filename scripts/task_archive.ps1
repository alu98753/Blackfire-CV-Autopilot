[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9-]*$')][string]$Task)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent; Set-Location $repoRoot
. (Join-Path $PSScriptRoot 'task_package_resolver.ps1')

function Fail([string]$Code){ throw $Code }
$resolved=Resolve-TaskPackage -Task $Task -RepoRoot $repoRoot
if($resolved.Classification -ne 'ACTIVE'){ Fail "TASK_$($resolved.Classification)" }
$mainStatus=@(git status --porcelain)
if($mainStatus.Count){ Fail 'ARCHIVE_REQUIRES_CLEAN_MAIN' }
git fetch origin main --quiet
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
$destination="docs/tasks/archive/$year/$Task"
if(@(git ls-tree -r --name-only origin/main $destination).Count){ Fail 'ARCHIVE_DESTINATION_COLLISION' }
$closeoutBranch="archive/$Task-$year"
if(git ls-remote --heads origin $closeoutBranch){ Fail 'ARCHIVE_CLOSEOUT_BRANCH_COLLISION' }

# Prepare the move in an isolated worktree/branch; canonical main is untouched.
$closeoutPath=Join-Path $repoRoot ".runtime\archive-closeout-$Task-$year"
if(Test-Path $closeoutPath){ Fail 'ARCHIVE_CLOSEOUT_PATH_COLLISION' }
New-Item -ItemType Directory -Force (Split-Path $closeoutPath) | Out-Null
git worktree add --detach $closeoutPath origin/main | Out-Null
try {
    New-Item -ItemType Directory -Force (Join-Path $closeoutPath "docs\tasks\archive\$year") | Out-Null
    git -C $closeoutPath mv -- "docs/tasks/active/$Task" $destination
    git -C $closeoutPath commit -m "archive task $Task ($year)" --quiet
    $closeoutCommit=(git -C $closeoutPath rev-parse HEAD).Trim()
    git -C $closeoutPath push origin "HEAD:refs/heads/$closeoutBranch" --quiet
} finally {
    $removeOutput = git worktree remove $closeoutPath 2>&1
    if($LASTEXITCODE -ne 0){ throw "ARCHIVE_CLOSEOUT_WORKTREE_REMOVE_FAILED: $($removeOutput -join ' ')" }
}
[pscustomobject]@{ok=$true;outcome='ARCHIVE_CLOSEOUT_READY';task=$Task;task_head=$taskHead;integration_commit=$integrationCommit;integration_year=$year;archive_path=$destination;closeout_branch=$closeoutBranch;closeout_commit=$closeoutCommit;durability='pushed closeout branch'} | ConvertTo-Json -Compress
