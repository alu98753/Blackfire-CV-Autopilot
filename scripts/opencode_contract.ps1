$OpenCodeSupportedVersion = "1.18.31"

function Get-OpenCodeVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable
    )

    $output = & $Executable --version 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine OpenCode version from '$Executable' (exit code $LASTEXITCODE)."
    }

    $match = [regex]::Match($output, '(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+)(?![0-9])')
    if (-not $match.Success) {
        throw "Unable to parse an OpenCode semantic version from '$($output.Trim())'."
    }

    return $match.Groups[1].Value
}

function Assert-OpenCodeSupportedVersion {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Version
    )

    if ($Version -ne $OpenCodeSupportedVersion) {
        throw "Unsupported OpenCode CLI version '$Version'. This repository requires exactly OpenCode $OpenCodeSupportedVersion. Install the supported version with: npm install -g opencode-ai@$OpenCodeSupportedVersion ; then rerun .\scripts\bootstrap_opencode.ps1 to verify."
    }
}
