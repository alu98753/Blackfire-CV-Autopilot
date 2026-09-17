[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$WorktreePath,

    [string]$CanonicalEnvironmentPath = 'E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot',

    [switch]$Detach,

    [switch]$ClassifyOnly,

    # Caller must prove stale registration/no-live-state before selecting this mode.
    [switch]$PartialRemovalRecovery,

    # Caller must prove this helper already detached .venv in this cleanup sequence.
    [switch]$DetachedPendingRemove
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
    SAFE_RESIDUAL_ABSENT = 0
    DETACHED_PENDING_REMOVE = 0
    INVALID_RECOVERY_MODE = 19
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
    if ($PartialRemovalRecovery -and $DetachedPendingRemove) {
        Write-Result 'INVALID_RECOVERY_MODE' 'recovery modes are mutually exclusive' @{}
    }
    if ($PartialRemovalRecovery -and $Detach -and $ClassifyOnly) {
        Write-Result 'INVALID_RECOVERY_MODE' 'recovery mode cannot combine detach and classify-only' @{}
    }

    $worktree = Normalize-WindowsPath $WorktreePath
    $canonical = Normalize-WindowsPath $CanonicalEnvironmentPath
    $venv = Join-Path $worktree '.venv'

    if (-not (Test-Path -LiteralPath $worktree -PathType Container)) {
        if ($PartialRemovalRecovery) {
            Write-Result 'SAFE_RESIDUAL_ABSENT' 'partial worktree path is absent; no residual .venv remains to detach' @{}
        }
        Write-Result 'PARTIAL_REMOVAL_REQUIRES_STALE_PROOF' 'worktree path is missing; no prune or force cleanup performed' @{}
    }
    $gitMarker = Join-Path $worktree '.git'
    $hasGitMarker = (Test-Path -LiteralPath $gitMarker -PathType Leaf) -or
        (Test-Path -LiteralPath $gitMarker -PathType Container)
    if (-not $hasGitMarker -and -not $PartialRemovalRecovery) {
        Write-Result 'PARTIAL_REMOVAL_REQUIRES_STALE_PROOF' 'worktree .git administrative marker is missing; stale proof remains the caller responsibility' @{}
    }

    # Get-Item is intentionally attempted before Test-Path: a dangling junction is
    # a residual link object even though Test-Path may report its followed target as absent.
    $item = Get-Item -LiteralPath $venv -Force -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        if ($DetachedPendingRemove -and $hasGitMarker) {
            Write-Result 'DETACHED_PENDING_REMOVE' 'local .venv is absent after an explicitly recorded detach; retry normal worktree removal' @{}
        }
        if ($PartialRemovalRecovery) {
            Write-Result 'SAFE_RESIDUAL_ABSENT' 'partial worktree has no residual .venv object; safe for caller stale-proof/prune decision' @{}
        }
        Write-Result 'MISSING_VENV' 'registered runnable worktree has no .venv junction' @{}
    }

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

    if ($DetachedPendingRemove) {
        Write-Result 'INVALID_RECOVERY_MODE' 'detached-pending-remove requires .venv to be absent' @{}
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
