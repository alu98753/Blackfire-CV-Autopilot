$NodeEngineRequiredSpec = ">=18.17"

function Get-NodeVersion {
    param(
        [string]$Executable = 'node'
    )

    $output = & $Executable --version 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine Node version from '$Executable' (exit code $LASTEXITCODE)."
    }

    $match = [regex]::Match($output, '(?<![0-9])([0-9]+\.[0-9]+(?:\.[0-9]+)?)(?![0-9])')
    if (-not $match.Success) {
        throw "Unable to parse a Node semantic version from '$($output.Trim())'."
    }

    return $match.Groups[1].Value
}

function Assert-NodeSupportedVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    $trimmed = $Version.Trim()
    if ($trimmed -match '^v?([0-9]+)\.([0-9]+)(?:\.([0-9]+))?') {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 18 -or ($major -eq 18 -and $minor -lt 17)) {
            throw "Unsupported Node.js version '$Version'. This repository requires Node.js $NodeEngineRequiredSpec (engines.node in package.json). Install a supported Node.js version."
        }
    } else {
        throw "Unable to parse Node.js version from '$Version'."
    }
}

function Test-NodeWorkflowDependencies {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [string]$Executable = 'node',
        [string]$VersionOverride,
        [switch]$SkipPackageImportProbe
    )

    # 1. Node executable check
    $nodeCmd = $null
    if (-not [string]::IsNullOrWhiteSpace($Executable) -and $Executable -ne 'node') {
        if (Test-Path $Executable) {
            $nodeCmd = $Executable
        } else {
            $cmd = Get-Command $Executable -ErrorAction SilentlyContinue
            if ($cmd) { $nodeCmd = $cmd.Source }
        }
    } else {
        $cmd = Get-Command node -ErrorAction SilentlyContinue
        if ($cmd) { $nodeCmd = $cmd.Source }
    }

    if (-not $nodeCmd) {
        return [pscustomobject]@{
            Ready = $false
            Reason = "Node.js executable not found"
            Remediation = "Install Node.js >=18.17 and ensure 'node' is available on PATH."
        }
    }

    # 2. Node version check
    $versionToAssert = if (-not [string]::IsNullOrWhiteSpace($VersionOverride)) {
        $VersionOverride
    } else {
        try { Get-NodeVersion -Executable $nodeCmd } catch { $null }
    }

    if (-not $versionToAssert) {
        return [pscustomobject]@{
            Ready = $false
            Reason = "Unable to determine Node.js version"
            Remediation = "Verify Node.js installation with 'node --version'."
        }
    }

    try {
        Assert-NodeSupportedVersion -Version $versionToAssert
    } catch {
        return [pscustomobject]@{
            Ready = $false
            Reason = $_.Exception.Message
            Remediation = "Install Node.js >=18.17 (current engine contract)."
        }
    }

    # 3. Manifest presence
    $packageJson = Join-Path $RepoRoot 'package.json'
    if (-not (Test-Path $packageJson)) {
        return [pscustomobject]@{
            Ready = $false
            Reason = "package.json not found in $RepoRoot"
            Remediation = "Ensure current directory is a valid Blackfire worktree root."
        }
    }

    # 4. Lockfile presence
    $packageLock = Join-Path $RepoRoot 'package-lock.json'
    if (-not (Test-Path $packageLock)) {
        return [pscustomobject]@{
            Ready = $false
            Reason = "package-lock.json not found in $RepoRoot"
            Remediation = "Ensure current directory contains the committed repository package-lock.json."
        }
    }

    # 5. node_modules presence
    $nodeModules = Join-Path $RepoRoot 'node_modules'
    if (-not (Test-Path $nodeModules)) {
        return [pscustomobject]@{
            Ready = $false
            Reason = "node_modules directory does not exist in $RepoRoot"
            Remediation = "Run .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci) in this worktree first."
        }
    }

    # 6. Package boundary resolvability
    if (-not $SkipPackageImportProbe) {
        $psi = [System.Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = $nodeCmd
        $psi.Arguments = '--input-type=module -e "import(''undici'').then(()=>import(''@opencode-ai/sdk/v2''))"'
        $psi.WorkingDirectory = $RepoRoot
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        try {
            $p = [System.Diagnostics.Process]::Start($psi)
            if (-not $p) {
                return [pscustomobject]@{
                    Ready = $false
                    Reason = "Failed to launch Node import probe"
                    Remediation = "Run .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci) in this worktree first."
                }
            }
            $stderrTask = $p.StandardError.ReadToEndAsync()
            if (-not $p.WaitForExit(10000)) {
                try { $p.Kill() } catch {}
                return [pscustomobject]@{
                    Ready = $false
                    Reason = "Node import probe timed out"
                    Remediation = "Run .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci) in this worktree first."
                }
            }
            $p.WaitForExit()
            $stderrTask.Wait(500) | Out-Null
            $stderr = if ($stderrTask.IsCompleted) { $stderrTask.GetAwaiter().GetResult() } else { '' }

            if ($p.ExitCode -ne 0) {
                $errDetail = if ($stderr.Trim()) { $stderr.Trim().Split("`n")[0] } else { "exit code $($p.ExitCode)" }
                return [pscustomobject]@{
                    Ready = $false
                    Reason = "Required Node packages ('undici', '@opencode-ai/sdk/v2') could not be resolved ($errDetail)"
                    Remediation = "Run .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci) in this worktree first."
                }
            }
        } catch {
            return [pscustomobject]@{
                Ready = $false
                Reason = "Error executing Node import probe: $($_.Exception.Message)"
                Remediation = "Run .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci) in this worktree first."
            }
        }
    }

    return [pscustomobject]@{
        Ready = $true
        Reason = "Node workflow dependencies are ready"
        Remediation = ""
    }
}

function Assert-NodeWorkflowDependenciesReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [string]$Executable = 'node',
        [string]$VersionOverride,
        [switch]$SkipPackageImportProbe
    )

    $result = Test-NodeWorkflowDependencies -RepoRoot $RepoRoot -Executable $Executable -VersionOverride $VersionOverride -SkipPackageImportProbe:$SkipPackageImportProbe
    if (-not $result.Ready) {
        throw "Node workflow dependencies are not ready for this worktree ($($result.Reason)). Run: .\scripts\bootstrap_node_workflow_deps.ps1 (or npm ci)"
    }
}
