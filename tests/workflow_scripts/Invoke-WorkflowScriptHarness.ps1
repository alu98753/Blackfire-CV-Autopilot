param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent | Split-Path -Parent
$gate = Join-Path $repoRoot 'scripts\ai_gate.ps1'
$scout = Join-Path $repoRoot 'scripts\ai_scout.ps1'
$fixtureId = "workflow-harness-fixture-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))-$PID"
$fixtureDir = Join-Path $repoRoot "docs\tasks\$fixtureId"
$runtimeDirs = @(
    (Join-Path $repoRoot ".runtime\ai_gate\$fixtureId"),
    (Join-Path $repoRoot ".runtime\ai_scout\$fixtureId")
)
$helperDir = Join-Path $PSScriptRoot '.runtime-fixtures'
$reviewer = Join-Path $helperDir 'fake-reviewer.ps1'
$scoutChild = Join-Path $helperDir 'fake-scout.ps1'
$pythonChild = Join-Path $helperDir 'fake-test.ps1'
$reviewerCmd = Join-Path $helperDir 'fake-reviewer.cmd'
$scoutCmd = Join-Path $helperDir 'fake-scout.cmd'
$pythonCmd = Join-Path $helperDir 'fake-test.cmd'
$secondMarker = Join-Path $helperDir 'second-candidate-invoked.marker'
$passed = 0
$failed = 0
$specReviewer = Join-Path $repoRoot '.opencode\agents\spec-reviewer.md'
$regressionReviewer = Join-Path $repoRoot '.opencode\agents\regression-reviewer.md'
$workflowContract = Join-Path $repoRoot 'docs\architecture\ai_development_workflow.md'
$openCodeContract = Join-Path $repoRoot 'scripts\opencode_contract.ps1'
$bootstrap = Join-Path $repoRoot 'scripts\bootstrap_opencode.ps1'
$scoutScript = Join-Path $repoRoot 'scripts\ai_scout.ps1'
$gateScript = Join-Path $repoRoot 'scripts\ai_gate.ps1'

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Invoke-Script([string]$Script, [string[]]$Arguments) {
    $commandParts = @('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $Script.Replace('"', '\"') + '"'))
    foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            $commandParts += ('"' + $argument.Replace('"', '\"') + '"')
        } else {
            $commandParts += $argument
        }
    }
    $command = ($commandParts -join ' ') + ' < NUL'
    try { & cmd.exe /d /s /c $command 2>&1 | Out-Null }
    catch { return 1 }
    return $LASTEXITCODE
}

function Invoke-ScriptOutput([string]$Script, [string[]]$Arguments) {
    $commandParts = @('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $Script.Replace('"', '\"') + '"'))
    foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            $commandParts += ('"' + $argument.Replace('"', '\"') + '"')
        } else {
            $commandParts += $argument
        }
    }
    $command = ($commandParts -join ' ') + ' < NUL'
    try { $output = & cmd.exe /d /s /c $command 2>&1 | Out-String }
    catch { return [pscustomobject]@{ ExitCode = 1; Output = ($_ | Out-String) } }
    return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = $output }
}

function Run-Case([string]$Name, [scriptblock]$Body) {
    try { & $Body; Write-Host "PASS $Name"; $script:passed++ }
    catch { Write-Host "FAIL $Name - $($_.Exception.Message)"; $script:failed++ }
}

try {
    Run-Case 'Reviewer budgets and bounded finalization contract' {
        $specText = Get-Content $specReviewer -Raw
        $regressionText = Get-Content $regressionReviewer -Raw
        $workflowText = Get-Content $workflowContract -Raw
        Assert-True ($specText -match '(?m)^steps: 8$') 'spec-reviewer budget drifted'
        Assert-True ($regressionText -match '(?m)^steps: 10$') 'regression-reviewer budget drifted'
        foreach ($text in @($specText, $regressionText)) {
            Assert-True ($text -match 'bounded blocker detector') 'bounded reviewer contract missing'
            Assert-True ($text -match 'configured step count is a maximum safety ceiling') 'ceiling contract missing'
            Assert-True ($text -match 'finalize with StructuredOutput before exhausting the configured safety ceiling') 'StructuredOutput finalization contract missing'
            Assert-True ($text -match 'finish == "tool-calls" is not itself a failure') 'tool-calls completion contract missing'
        }
        Assert-True ($workflowText -match '`spec-reviewer`[\s\S]*?`steps: 8`') 'architecture spec-reviewer budget drifted'
        Assert-True ($workflowText -match '`regression-reviewer`[\s\S]*?`steps: 10`') 'architecture regression-reviewer budget drifted'
        Assert-True ($workflowText -match 'Completed valid StructuredOutput is the terminal reviewer result') 'architecture StructuredOutput finalization contract missing'
    }
    Run-Case 'OpenCode launcher contract is pinned and flag-free' {
        $contractText = Get-Content $openCodeContract -Raw
        $bootstrapText = Get-Content $bootstrap -Raw
        $scoutText = Get-Content $scoutScript -Raw
        $gateText = Get-Content $gateScript -Raw
        $workflowText = Get-Content $workflowContract -Raw
        Assert-True ($contractText -match '\$OpenCodeSupportedVersion\s*=\s*"1\.18\.31"') 'supported OpenCode version declaration drifted'
        Assert-True ($contractText -match 'npm install -g opencode-ai@\$OpenCodeSupportedVersion') 'version mismatch remediation is not exact-version actionable'
        Assert-True ($bootstrapText -match 'opencode-ai@\$OpenCodeSupportedVersion') 'bootstrap install is not pinned to the authoritative version'
        Assert-True ($scoutText -notmatch '--standalone|--pure') 'Scout production launcher contains a forbidden OpenCode flag'
        Assert-True ($gateText -notmatch '--standalone|--pure') 'Gate production launcher contains a forbidden OpenCode flag'
        Assert-True ($workflowText.Contains('exactly OpenCode CLI version 1.18.31')) 'architecture version contract missing'
    }
    New-Item -ItemType Directory -Force -Path $fixtureDir, (Join-Path $fixtureDir 'reviews'), $helperDir | Out-Null
    '{"id":"PLACEHOLDER","base_ref":"origin/main","scope":["docs/tasks/PLACEHOLDER/"],"focused_tests":[],"models":{"scout":["first","second"],"review":["first","second"]}}'.Replace('PLACEHOLDER',$fixtureId) | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
    '# Final disposable harness fixture' | Set-Content (Join-Path $fixtureDir 'SPEC.md') -Encoding UTF8
    'existing context' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8

    Run-Case 'Scout rejects an unsupported OpenCode version before routing' {
        $code = Invoke-Script $scout (@('-Task',$fixtureId,'-_ExecutableOverride',$scoutCmd,'-_OpenCodeVersionOverride','1.18.30'))
        Assert-True ($code -ne 0) "expected version mismatch failure, got $code"
    }

    Run-Case 'Scout invocation probe exercises the production argument builder' {
        $result = Invoke-ScriptOutput $scout @('-Task',$fixtureId,'-_InvocationProbe','-_ModelCandidatesOverride','probe-scout')
        Assert-True ($result.ExitCode -eq 0) "expected probe success, got $($result.ExitCode): $($result.Output)"
        $probe = $result.Output.Trim() | ConvertFrom-Json
        $args = @($probe.Arguments)
        Assert-True ($args -contains 'run') 'Scout production args missing run'
        Assert-True (($args -join ' ') -match '--agent scout') 'Scout production args missing scout agent'
        Assert-True (($args -join ' ') -match '--model probe-scout') 'Scout production args missing model'
        Assert-True (($args -join ' ') -match 'Task descriptor: docs/tasks/') 'Scout production args missing prompt'
        Assert-True (($args -join ' ') -notmatch '--standalone|--pure') 'Scout production args contain unsupported flags'
    }

@'
param([string[]]$ChildArgs)
$rawArgs = $ChildArgs -join ' '
$mode = if ($rawArgs -match 'terminal-block' -and $rawArgs -match 'first') { 'block' } elseif ($rawArgs -match 'terminal-pass' -and $rawArgs -match 'first') { 'pass' } elseif ($rawArgs -match 'block') { 'block' } elseif ($rawArgs -match 'grounding') { 'grounding' } elseif ($rawArgs -match 'missing') { 'missing' } elseif ($rawArgs -match 'schema') { 'schema' } elseif ($rawArgs -match 'contradiction') { 'contradiction' } elseif ($rawArgs -match 'unsafe') { 'unsafe' } elseif ($rawArgs -match 'malformed') { 'malformed' } elseif ($rawArgs -match 'markdown') { 'markdown' } elseif ($rawArgs -match 'first') { 'fail' } else { 'pass' }
if ($rawArgs -match 'terminal-(block|pass)' -and $rawArgs -match 'second') { Set-Content -LiteralPath (Join-Path $PSScriptRoot 'second-candidate-invoked.marker') -Value 'invoked' }
if ($mode -eq 'fail') { exit 7 }
if ($mode -in @('malformed','markdown')) { if ($mode -eq 'markdown') { '**VERDICT: PASS**' } else { 'not a review' }; exit 0 }
$class = switch ($mode) { 'block' {'VALID_BLOCK'} 'grounding' {'GROUNDING_FAILED'} 'missing' {'STRUCTURED_OUTPUT_MISSING'} 'schema' {'SCHEMA_INVALID'} 'contradiction' {'SEMANTIC_CONTRADICTION'} default {'VALID_PASS'} }
$cleanup = [bool]($mode -ne 'unsafe')
$structured = if ($class -eq 'VALID_PASS') { @{ verdict='PASS'; blocking_findings=0; report_markdown='# Review' } } elseif ($class -eq 'VALID_BLOCK') { @{ verdict='BLOCK'; blocking_findings=1; report_markdown='# Block' } } else { $null }
@{ schema_version=1; classification=$class; structured=$structured; lifecycle=@{ final_message_identity=$true }; cleanup=@{ safe=$cleanup; server_exit_confirmed=$cleanup } } | ConvertTo-Json -Compress
'@ | Set-Content $reviewer -Encoding UTF8
@'
param([string[]]$ChildArgs)
if ($ChildArgs -contains 'bad') { 'malformed scout'; exit 0 }
if ($ChildArgs -contains 'fail') { exit 9 }
if ($ChildArgs -contains 'sleep') { Start-Sleep -Seconds 2 }
Write-Output "# Scout Context`n`n## Relevant files`n- disposable fixture"
'@ | Set-Content $scoutChild -Encoding UTF8
    'exit 0' | Set-Content $pythonChild -Encoding UTF8
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$reviewer`" %*" | Set-Content $reviewerCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scoutChild`" %*" | Set-Content $scoutCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$pythonChild`" %*" | Set-Content $pythonCmd -Encoding ASCII

    $reviewBase = @('-_ReviewerExecutableOverride',$reviewerCmd,'-ReviewTimeoutSeconds','10','-_ReviewCandidatesOverride','first','second')
    Run-Case 'Gate rejects an unsupported OpenCode version before routing' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_OpenCodeVersionOverride','2.0.3'))
        Assert-True ($code -ne 0) "expected version mismatch failure, got $code"
    }
    Run-Case 'Gate invocation probe exercises the production argument builder' {
        $result = Invoke-ScriptOutput $gate @('-Task',$fixtureId,'-_InvocationProbe')
        Assert-True ($result.ExitCode -eq 0) "expected probe success, got $($result.ExitCode): $($result.Output)"
        $probe = $result.Output.Trim() | ConvertFrom-Json
        $args = @($probe.Arguments)
        Assert-True ($probe.Agent -eq 'spec-reviewer') "expected spec-reviewer probe, got $($probe.Agent)"
        Assert-True (($args -join ' ') -match '--agent spec-reviewer') 'Gate production args missing reviewer agent'
        Assert-True (($args -join ' ') -match '--model first') 'Gate production args missing model'
        Assert-True (($args -join ' ') -match '--prompt-file') 'Gate production args missing prompt file'
        Assert-True (($args -join ' ') -notmatch '--standalone|--pure') 'Gate production args contain unsupported flags'
    }
    Run-Case 'Gate PASS and candidate override resolution' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId) + $reviewBase)
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate valid structured BLOCK returns 2 and is terminal' {
        if (Test-Path $secondMarker) { Remove-Item -LiteralPath $secondMarker -Force }
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','terminal-block','-_ReviewCandidatesOverride','first','second'))
        Assert-True ($code -eq 2) "expected 2, got $code"
        Assert-True (-not (Test-Path $secondMarker)) 'trusted BLOCK incorrectly invoked the second candidate'
    }
    Run-Case 'Gate valid structured PASS is terminal' {
        if (Test-Path $secondMarker) { Remove-Item -LiteralPath $secondMarker -Force }
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','terminal-pass','-_ReviewCandidatesOverride','first','second'))
        Assert-True ($code -eq 0) "expected 0, got $code"
        Assert-True (-not (Test-Path $secondMarker)) 'trusted PASS incorrectly invoked the second candidate'
    }
    Run-Case 'Gate malformed adapter envelope returns 1' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','malformed'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate legacy free-text verdict has zero authority' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','markdown'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate pre-authority failure falls back to next candidate' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId) + $reviewBase)
        Assert-True ($code -eq 0) "expected fallback success, got $code"
    }
    Run-Case 'Gate unsafe adapter cleanup stops fallback' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','unsafe'))
        Assert-True ($code -eq 1) "expected unavailable, got $code"
    }
    Run-Case 'Gate focused-test override passes' {
        $json = Get-Content (Join-Path $fixtureDir 'task.json') -Raw | ConvertFrom-Json
        $json.focused_tests = @('disposable-target')
        $json | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_PythonExecutableOverride',$pythonCmd))
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate promotion rollback preserves prior artifacts' {
        $old = Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_FailPromotionOnTarget','evidence'))
        Assert-True ($code -eq 1) "expected 1, got $code"
        Assert-True ((Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw) -eq $old) 'rollback did not preserve evidence'
    }

    Run-Case 'Scout success promotes structured output' {
        $code = Invoke-Script $scout @('-Task',$fixtureId,'-_ExecutableOverride',$scoutCmd,'-_ModelCandidatesOverride','only')
        Assert-True ($code -eq 0) "expected 0, got $code"
        Assert-True ((Get-Content (Join-Path $fixtureDir 'CONTEXT.md') -Raw) -match '# Scout Context') 'context was not promoted'
    }
    Run-Case 'Scout malformed output preserves context' {
        'preserve me' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8
        $code = Invoke-Script $scout @('-Task',$fixtureId,'-_ExecutableOverride',$scoutCmd,'-_ArgumentsOverride','bad')
        Assert-True ($code -ne 0) 'expected failure'
        Assert-True ((Get-Content (Join-Path $fixtureDir 'CONTEXT.md') -Raw) -match 'preserve me') 'context was overwritten'
    }
    Run-Case 'Scout process failure returns non-zero' {
        $code = Invoke-Script $scout @('-Task',$fixtureId,'-_ExecutableOverride',$scoutCmd,'-_ArgumentsOverride','fail')
        Assert-True ($code -ne 0) 'expected failure'
    }
    Run-Case 'Scout short timeout is bounded and preserves context' {
        'timeout preserve' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8
        $code = Invoke-Script $scout @('-Task',$fixtureId,'-TimeoutSeconds','1','-_ExecutableOverride',$scoutCmd,'-_ArgumentsOverride','sleep')
        Assert-True ($code -ne 0) 'expected timeout failure'
        Assert-True ((Get-Content (Join-Path $fixtureDir 'CONTEXT.md') -Raw) -match 'timeout preserve') 'context was overwritten'
    }
}
finally {
    foreach ($path in @($fixtureDir,$helperDir) + $runtimeDirs) {
        if (Test-Path $path) { Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

if ($failed -gt 0) { exit 1 }
Write-Host "Workflow script harness: $passed cases passed."
exit 0
