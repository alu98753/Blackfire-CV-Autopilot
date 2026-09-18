[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9-]*$')][string]$Task)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent; Set-Location $repoRoot
. (Join-Path $PSScriptRoot 'task_package_resolver.ps1')
$resolved=Resolve-TaskPackage -Task $Task -RepoRoot $repoRoot
if($resolved.Classification -ne 'ACTIVE'){ throw "TASK_$($resolved.Classification): $Task" }
$status=@(git status --porcelain)
if($status.Count){ throw 'ARCHIVE_REQUIRES_CLEAN_MAIN' }
git fetch origin main --quiet
$head=(git rev-parse HEAD).Trim(); $originMain=(git rev-parse origin/main).Trim()
if($head -ne $originMain){ throw 'ARCHIVE_REQUIRES_LOCAL_MAIN_AT_ORIGIN_MAIN' }
$activePath="docs/tasks/active/$Task"
$evidence=Join-Path $resolved.AbsolutePath 'EVIDENCE.md'
if(-not (Test-Path -LiteralPath $evidence)){ throw 'ARCHIVE_INTEGRATION_UNPROVEN' }
$evidenceText=Get-Content -LiteralPath $evidence -Raw -Encoding UTF8
$shaMatch=[regex]::Match($evidenceText,'(?im)^(?:HEAD|Integration commit|Merged commit):\s*([0-9a-f]{7,40})\s*$')
if(-not $shaMatch.Success){ throw 'ARCHIVE_INTEGRATION_UNPROVEN' }
$integrationSha=$shaMatch.Groups[1].Value
$shaCheck=git cat-file -e "$integrationSha^{commit}" 2>$null
if($LASTEXITCODE -ne 0){ throw 'ARCHIVE_INTEGRATION_UNPROVEN' }
$ancestor=git merge-base --is-ancestor $integrationSha origin/main 2>$null
if($LASTEXITCODE -ne 0){ throw 'ARCHIVE_INTEGRATION_UNPROVEN' }
$year=(git show -s --format='%ad' --date=format:'%Y' $integrationSha).Trim()
$destination=Join-Path $repoRoot "docs\tasks\archive\$year\$Task"
if(Test-Path -LiteralPath $destination){ throw 'ARCHIVE_DESTINATION_COLLISION' }
$remoteArchived=@(git ls-tree -r --name-only origin/main "docs/tasks/archive/$year/$Task")
if($remoteArchived.Count -eq 0){ throw 'ARCHIVE_REMOTE_DURABILITY_REQUIRED' }
if(@(git ls-tree -r --name-only origin/main $activePath).Count -gt 0){ throw 'ARCHIVE_REMOTE_STILL_ACTIVE' }
[pscustomobject]@{ok=$true;task=$Task;integration_commit=$integrationSha;integration_year=$year;archived_path="docs/tasks/archive/$year/$Task";durability='origin/main'} | ConvertTo-Json -Compress
