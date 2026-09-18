Set-StrictMode -Version Latest

function Get-TaskPackageRelativePath {
    param([Parameter(Mandatory=$true)][string]$Task)
    if ($Task -notmatch '^[a-z0-9][a-z0-9-]*$') { throw "Invalid task id: $Task" }
    return "docs/tasks/active/$Task"
}

function Resolve-TaskPackage {
    param(
        [Parameter(Mandatory=$true)][string]$Task,
        [string]$RepoRoot = (Get-Location).Path,
        [switch]$RequireActive
    )
    $relative = Get-TaskPackageRelativePath $Task
    $active = Join-Path $RepoRoot ($relative -replace '/', '\\')
    $archiveRoot = Join-Path $RepoRoot 'docs\tasks\archive'
    $archives = @()
    if (Test-Path -LiteralPath $archiveRoot -PathType Container) {
        $archives = @(Get-ChildItem -LiteralPath $archiveRoot -Directory -ErrorAction Stop | ForEach-Object {
            $candidate = Join-Path $_.FullName $Task
            if (Test-Path -LiteralPath $candidate -PathType Container) { $candidate }
        })
    }
    $activeExists = Test-Path -LiteralPath $active -PathType Container
    $classification = if ($activeExists) { 'ACTIVE' } elseif ($archives.Count -gt 1) { 'AMBIGUOUS_ARCHIVE' } elseif ($archives.Count -eq 1) { 'ARCHIVED' } else { 'MISSING' }
    if ($RequireActive -and $classification -ne 'ACTIVE') { throw "TASK_${classification}: $Task" }
    $result = [pscustomobject]@{ Task=$Task; Classification=$classification; RelativePath=$relative; AbsolutePath=if($activeExists){$active}else{if($archives.Count -eq 1){$archives[0]}else{$null}}; ArchivePaths=$archives }
    if ($classification -eq 'ACTIVE') {
        $json = Join-Path $active 'task.json'; $spec = Join-Path $active 'SPEC.md'
        if (-not (Test-Path -LiteralPath $json -PathType Leaf) -or -not (Test-Path -LiteralPath $spec -PathType Leaf)) { $result.Classification='MALFORMED' }
        else { try { $parsed=Get-Content -LiteralPath $json -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop; if ($parsed.id -ne $Task) {$result.Classification='MALFORMED'} } catch {$result.Classification='MALFORMED'} }
        if ($RequireActive -and $result.Classification -ne 'ACTIVE') { throw "TASK_MALFORMED: $Task" }
    }
    return $result
}

function Get-TaskPackageGitPath { param([Parameter(Mandatory=$true)][string]$Task) return (Get-TaskPackageRelativePath $Task) }
