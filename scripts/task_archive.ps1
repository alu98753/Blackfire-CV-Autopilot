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
$touching=@(git log origin/main --format='%H' -- "docs/tasks/active/$Task")
if($touching.Count -eq 0){ throw 'ARCHIVE_INTEGRATION_UNPROVEN' }
$integrationSha=$touching[0].Trim()
$year=(git show -s --format='%ad' --date=format:'%Y' $integrationSha).Trim()
$destination=Join-Path $repoRoot "docs\tasks\archive\$year\$Task"
if(Test-Path -LiteralPath $destination){ throw 'ARCHIVE_DESTINATION_COLLISION' }
$archiveParent=Split-Path $destination -Parent
New-Item -ItemType Directory -Force -Path $archiveParent | Out-Null
git mv -- "docs/tasks/active/$Task" "docs/tasks/archive/$year/$Task"
git commit -m "archive task $Task ($year)" --quiet
if(@(git status --porcelain).Count){ throw 'ARCHIVE_POSTCONDITION_DIRTY' }
[pscustomobject]@{ok=$true;task=$Task;integration_commit=$integrationSha;integration_year=$year;archived_path="docs/tasks/archive/$year/$Task";commit=(git rev-parse HEAD).Trim()} | ConvertTo-Json -Compress
