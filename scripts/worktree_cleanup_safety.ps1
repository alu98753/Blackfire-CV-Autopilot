[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$WorktreePath,

    [string]$CanonicalEnvironmentPath = 'E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot',

    [switch]$Detach,

    [switch]$ClassifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExitCodes = @{
    DETACHED = 0
    EXPECTED_JUNCTION = 0
    MISSING_VENV = 10
    PHYSICAL_DIRECTORY = 11
    WRONG_TARGET = 12
    UNSUPPORTED_REPARSE = 13
    AMBIGUOUS_TARGET = 14
    TARGET_MISSING = 15
    POSTCONDITION_FAILED = 16
    PARTIAL_REMOVAL_REQUIRES_STALE_PROOF = 20
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
        ok = ($Code -eq 'DETACHED' -or $Code -eq 'EXPECTED_JUNCTION')
        code = $Code
        message = $Message
        worktree = $WorktreePath
    }
    foreach ($key in $Data.Keys) { $result[$key] = $Data[$key] }
    [Console]::Out.WriteLine(($result | ConvertTo-Json -Compress))
    if ($ExitCodes.ContainsKey($Code)) { exit $ExitCodes[$Code] }
    exit $ExitCodes.INTERNAL_ERROR
}

try {
    $worktree = Normalize-WindowsPath $WorktreePath
    $canonical = Normalize-WindowsPath $CanonicalEnvironmentPath
    $venv = Join-Path $worktree '.venv'

    if (-not (Test-Path -LiteralPath $worktree -PathType Container)) {
        Write-Result 'PARTIAL_REMOVAL_REQUIRES_STALE_PROOF' 'worktree path is missing; no prune or force cleanup performed' @{}
    }
    if (-not (Test-Path -LiteralPath (Join-Path $worktree '.git') -PathType Leaf) -and
        -not (Test-Path -LiteralPath (Join-Path $worktree '.git') -PathType Container)) {
        Write-Result 'PARTIAL_REMOVAL_REQUIRES_STALE_PROOF' 'worktree .git administrative marker is missing; stale proof remains the caller responsibility' @{}
    }
    if (-not (Test-Path -LiteralPath $venv)) {
        Write-Result 'MISSING_VENV' 'registered runnable worktree has no .venv junction' @{}
    }

    $item = Get-Item -LiteralPath $venv -Force
    $isReparse = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    if (-not $isReparse) {
        Write-Result 'PHYSICAL_DIRECTORY' '.venv is not a reparse object; preserved' @{}
    }

    $linkType = [string]$item.LinkType
    if ($linkType -ne 'Junction' -and $linkType -ne 'MountPoint') {
        Write-Result 'UNSUPPORTED_REPARSE' ".venv reparse type '$linkType' is unsupported; preserved" @{ reparse_type = $linkType }
    }

    $targets = @($item.Target | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
    if ($targets.Count -ne 1) {
        Write-Result 'AMBIGUOUS_TARGET' '.venv does not expose exactly one structured target; preserved' @{ target_count = $targets.Count }
    }
    $target = Normalize-WindowsPath $targets[0]
    if (-not [string]::Equals($target, $canonical, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Result 'WRONG_TARGET' 'junction target is not the configured canonical environment; preserved' @{ target = $target; expected_target = $canonical }
    }
    if (-not (Test-Path -LiteralPath $canonical -PathType Container)) {
        Write-Result 'TARGET_MISSING' 'canonical environment is missing before detach; preserved' @{ target = $canonical }
    }

    if ($ClassifyOnly -or -not $Detach) {
        Write-Result 'EXPECTED_JUNCTION' 'exact canonical junction verified; no detach requested' @{ target = $target }
    }

    # rmdir without /s removes the junction object, not the directory behind it.
    & cmd.exe /d /s /c ('rmdir "' + $venv + '"') | Out-Null
    if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $venv)) {
        Write-Result 'POSTCONDITION_FAILED' 'local junction could not be detached; canonical target was not recursively touched' @{ target = $target }
    }
    if (-not (Test-Path -LiteralPath $canonical -PathType Container)) {
        Write-Result 'POSTCONDITION_FAILED' 'canonical environment disappeared after detach; cleanup stopped' @{ target = $canonical }
    }
    Write-Result 'DETACHED' 'local canonical junction detached and target survived' @{ target = $target }
}
catch {
    Write-Result 'INTERNAL_ERROR' $_.Exception.Message @{}
}
