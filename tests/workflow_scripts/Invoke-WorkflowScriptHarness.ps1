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
$structuredReviewer = Join-Path $helperDir 'fake-structured-reviewer.ps1'
$structuredReviewerCmd = Join-Path $helperDir 'fake-structured-reviewer.cmd'
$modeFile = Join-Path $helperDir 'structured-mode.txt'
$scoutCmd = Join-Path $helperDir 'fake-scout.cmd'
$pythonCmd = Join-Path $helperDir 'fake-test.cmd'
$passed = 0
$failed = 0
$specReviewer = Join-Path $repoRoot '.opencode\agents\spec-reviewer.md'
$regressionReviewer = Join-Path $repoRoot '.opencode\agents\regression-reviewer.md'
$workflowContract = Join-Path $repoRoot 'docs\architecture\ai_development_workflow.md'

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
            Assert-True ($text -match 'emit the canonical verdict voluntarily before forced max-step finalization') 'voluntary finalization contract missing'
            Assert-True ($text -match 'Never rely on forced max-step finalization') 'forced finalization prohibition missing'
        }
        Assert-True ($workflowText -match '`spec-reviewer`[\s\S]*?`steps: 8`') 'architecture spec-reviewer budget drifted'
        Assert-True ($workflowText -match '`regression-reviewer`[\s\S]*?`steps: 10`') 'architecture regression-reviewer budget drifted'
        Assert-True ($workflowText -match 'Forced max-step finalization remains an infrastructure failure, never a verdict source') 'architecture finalization contract missing'
    }
    Run-Case 'Gate source has no free-form verdict authority path' {
        $gateText = Get-Content $gate -Raw
        foreach ($legacy in @('_ReviewerExecutableOverride','_ReviewerArgumentsOverride','_SpecReviewerArgumentsOverride','_RegressionReviewerArgumentsOverride','Get-FinalAssistantMessageFromStructuredJson','Get-CanonicalReviewPayload','Test-ReviewVerdictStructure')) {
            Assert-True (-not ($gateText -match [regex]::Escape($legacy))) "obsolete Gate seam/function remains: $legacy"
        }
        Assert-True (-not ($gateText -match '\[regex\].*VERDICT')) 'Gate must not regex-parse verdict prose'
    }
    Run-Case 'Structured reviewer adapter uses isolated ephemeral database' {
        $adapterText = Get-Content (Join-Path $repoRoot 'scripts\opencode_structured_review.mjs') -Raw
        Assert-True ($adapterText -match 'const sessionId = session\.data\.id') 'adapter must use the pinned SDK response.data Session shape'
        Assert-True ($adapterText -notmatch 'session\.id') 'adapter must not use the direct Session shape for the response wrapper'
        $createCall = [regex]::Match($adapterText, 'client\.session\.create\(\{[\s\S]*?\}\);').Value
        Assert-True ($createCall -match 'query:\s*\{\s*directory\s*\}') 'session.create must use the pinned minimal query shape'
        Assert-True ($createCall -notmatch '\bagent\b|\bmodel\b') 'session.create must not send prompt-only agent/model fields'
        Assert-True ($adapterText -match 'client\.session\.prompt\([\s\S]*?agent, model:[\s\S]*?parts:[\s\S]*?format:\s*\{\s*type:\s*"json_schema"') 'session.prompt must retain reviewer agent/model and structured output fields'
        Assert-True (($adapterText -match 'session\.create\([\s\S]*?throwOnError:\s*true') -and ($adapterText -match 'session\.prompt\([\s\S]*?throwOnError:\s*true')) 'adapter must request SDK errors for create and prompt'
        Assert-True ($adapterText -match 'session\.create response did not contain response data') 'adapter must distinguish missing create response data'
        Assert-True ($adapterText -match 'session\.prompt response did not contain response data') 'adapter must distinguish missing prompt response data'
        Assert-True ($adapterText -match 'session\.create response contained a malformed session object') 'adapter must distinguish malformed session data'
        Assert-True ($adapterText -match 'cause\.body') 'adapter must retain the SDK parsed API error body'
        Assert-True ($adapterText -match 'MAX_ERROR_DETAIL_LENGTH\s*=\s*600') 'adapter API diagnostics must have a bounded length'
        Assert-True ($adapterText -match 'SAFE_ERROR_FIELDS') 'adapter API diagnostics must use a safe field allowlist'
        Assert-True ($adapterText -notmatch 'cause\.(headers|request|response)|authorization|cookie') 'adapter diagnostics must not expose headers or credentials'
        Assert-True ($adapterText -match 'process\.env\.OPENCODE_DB\s*=\s*":memory:"') 'adapter must set an in-memory OpenCode database'
        Assert-True ($adapterText -match 'await createOpencode') 'adapter must launch the SDK server while the override is scoped'
        Assert-True ($adapterText -match 'delete process\.env\.OPENCODE_DB') 'adapter must restore an unset database override'
        Assert-True ($adapterText -notmatch 'opencode\.db|USERPROFILE|(^|[^A-Za-z])HOME([^A-Za-z]|$)') 'adapter must not address the user global OpenCode database'
    }
    New-Item -ItemType Directory -Force -Path $fixtureDir, (Join-Path $fixtureDir 'reviews'), $helperDir | Out-Null
    '{"id":"PLACEHOLDER","base_ref":"origin/main","scope":["docs/tasks/PLACEHOLDER/"],"focused_tests":[],"models":{"scout":["first","second"],"review":["first","second"]}}'.Replace('PLACEHOLDER',$fixtureId) | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
    '# Final disposable harness fixture' | Set-Content (Join-Path $fixtureDir 'SPEC.md') -Encoding UTF8
    'existing context' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8

    @'
param([string[]]$ChildArgs)
Write-Output '{"structured_output":{"verdict":"PASS","blocking_findings":0,"report_markdown":"# Legacy fixture"}}'
'@ | Set-Content $reviewer -Encoding UTF8
    @'
param([string[]]$ChildArgs)
$rawArgs = $ChildArgs -join ' '
$mode = if (Test-Path (Join-Path $PSScriptRoot 'structured-mode.txt')) { (Get-Content (Join-Path $PSScriptRoot 'structured-mode.txt') -Raw).Trim() } else { 'pass' }
for ($i = 0; $i -lt ($ChildArgs.Count - 1); $i++) { if ($ChildArgs[$i] -eq '--fixture-mode') { $mode = $ChildArgs[$i + 1]; break } }
for ($i = 0; $i -lt ($ChildArgs.Count - 1); $i++) { if ($ChildArgs[$i] -eq '--model' -and $ChildArgs[$i + 1] -in @('block','malformed','contradict-pass','contradict-block','missing','nonzero','exhausted','incomplete','stale','prose','verdict-last','model-fallback')) { $mode = $ChildArgs[$i + 1]; break } }
if ($rawArgs -match '--model[= ]+([A-Za-z-]+)') { $candidateMode = $Matches[1]; if ($candidateMode -in @('block','malformed','contradict-pass','contradict-block','missing','nonzero','exhausted','incomplete','stale','prose','verdict-last','model-fallback')) { $mode = $candidateMode } }
if ($mode -eq 'model-fallback' -and $rawArgs -match '--model\s+first') { exit 7 }
if ($mode -eq 'nonzero' -or $mode -eq 'exhausted') { [Console]::Error.WriteLine('StructuredOutputError: validation exhausted'); exit 7 }
if ($mode -eq 'malformed') { Write-Output 'not json'; exit 0 }
if ($mode -eq 'missing') { Write-Output '{"status":"completed"}'; exit 0 }
if ($mode -eq 'incomplete') { Write-Output '{"structured_output":{"verdict":"PASS"}}'; exit 0 }
if ($mode -eq 'stale') { Write-Output '{"structured_output":{"verdict":"PASS","blocking_findings":0,"report_markdown":"old"}}'; Write-Output 'later malformed'; exit 0 }
$verdict = if ($mode -eq 'block' -or $mode -eq 'contradict-block') { 'BLOCK' } else { 'PASS' }
$blocking = if ($mode -eq 'contradict-pass') { 1 } elseif ($mode -eq 'contradict-block') { 0 } elseif ($verdict -eq 'BLOCK') { 1 } else { 0 }
$report = if ($mode -match 'prose|verdict-last') { 'Evidence first. VERDICT: BLOCK is prose only.' } else { '# Deterministic review' }
Write-Output (ConvertTo-Json @{ structured_output = @{ verdict = $verdict; blocking_findings = $blocking; report_markdown = $report } } -Compress)
'@ | Set-Content $structuredReviewer -Encoding UTF8
@'
param([string[]]$ChildArgs)
if ($ChildArgs -contains 'bad') { 'malformed scout'; exit 0 }
if ($ChildArgs -contains 'fail') { exit 9 }
if ($ChildArgs -contains 'sleep') { Start-Sleep -Seconds 2 }
Write-Output "# Scout Context`n`n## Relevant files`n- disposable fixture"
'@ | Set-Content $scoutChild -Encoding UTF8
    'exit 0' | Set-Content $pythonChild -Encoding UTF8
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$reviewer`" %*" | Set-Content $reviewerCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$structuredReviewer`" %*" | Set-Content $structuredReviewerCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scoutChild`" %*" | Set-Content $scoutCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$pythonChild`" %*" | Set-Content $pythonCmd -Encoding ASCII

    $reviewBase = @('-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-ReviewTimeoutSeconds','10','-_ReviewCandidatesOverride','first','second')
    Run-Case 'Gate PASS and candidate override resolution' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId) + $reviewBase)
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate BLOCK returns 2' {
        'block' | Set-Content $modeFile -Encoding ASCII
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_ReviewCandidatesOverride','block'))
        Assert-True ($code -eq 2) "expected 2, got $code"
    }
    Run-Case 'Gate malformed output returns 1' {
        'malformed' | Set-Content $modeFile -Encoding ASCII
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_ReviewCandidatesOverride','malformed'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate report prose cannot override structured PASS' {
        'prose' | Set-Content $modeFile -Encoding ASCII
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_ReviewCandidatesOverride','prose'))
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    foreach ($case in @(
        @('PASS contradiction is infrastructure failure','contradict-pass',1),
        @('BLOCK contradiction is infrastructure failure','contradict-block',1),
        @('Missing structured output is infrastructure failure','missing',1),
        @('Adapter non-zero is infrastructure failure','nonzero',1),
        @('Structured validation exhaustion is infrastructure failure','exhausted',1),
        @('Incomplete output is not salvaged','incomplete',1),
        @('Stale output is not salvaged','stale',1),
        @('Evidence-first verdict-last report is rendered','verdict-last',0),
        @('Normal infrastructure candidate fallback works','model-fallback',0),
        @('Valid BLOCK remains terminal','block',2)
    )) {
        Run-Case $case[0] {
            $case[1] | Set-Content $modeFile -Encoding ASCII
            $code = Invoke-Script $gate (@('-Task',$fixtureId,'-SkipTests','-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_ReviewCandidatesOverride',$(if ($case[1] -eq 'model-fallback') { 'first','second' } else { $case[1] })))
            Assert-True ($code -eq $case[2]) "expected $($case[2]), got $code"
        }
    }
    Run-Case 'Gate focused-test override passes' {
        'pass' | Set-Content $modeFile -Encoding ASCII
        $json = Get-Content (Join-Path $fixtureDir 'task.json') -Raw | ConvertFrom-Json
        $json.focused_tests = @('disposable-target')
        $json | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_PythonExecutableOverride',$pythonCmd))
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate promotion rollback preserves prior artifacts' {
        $old = Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_StructuredReviewExecutableOverride',$structuredReviewerCmd,'-_FailPromotionOnTarget','evidence'))
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
