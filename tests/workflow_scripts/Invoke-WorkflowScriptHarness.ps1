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
$fallbackCounter = Join-Path $helperDir 'fallback-count.txt'
$structuredChild = Join-Path $helperDir 'fake-opencode.ps1'
$structuredCmd = Join-Path $helperDir 'opencode.cmd'
$passed = 0
$failed = 0

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Invoke-Script([string]$Script, [string[]]$Arguments) {
    if ($Script -eq $gate -and $Arguments -notcontains '-ReviewTimeoutSeconds') {
        $Arguments = @('-ReviewTimeoutSeconds', '5') + $Arguments
    }
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

function Invoke-StructuredGate([string]$Mode) {
    $oldPath = $env:Path
    $oldMode = $env:WORKFLOW_STRUCTURED_MODE
    try {
        $env:Path = "$helperDir;$oldPath"
        $env:WORKFLOW_STRUCTURED_MODE = $Mode
        return Invoke-Script $gate @('-Task',$fixtureId,'-_PythonExecutableOverride',$pythonCmd)
    } finally {
        $env:Path = $oldPath
        if ($null -eq $oldMode) { Remove-Item Env:WORKFLOW_STRUCTURED_MODE -ErrorAction SilentlyContinue } else { $env:WORKFLOW_STRUCTURED_MODE = $oldMode }
    }
}

try {
    New-Item -ItemType Directory -Force -Path $fixtureDir, (Join-Path $fixtureDir 'reviews'), $helperDir | Out-Null
    '{"id":"PLACEHOLDER","base_ref":"origin/main","scope":["docs/tasks/PLACEHOLDER/"],"focused_tests":[],"models":{"scout":["first","second"],"review":["first","second"]}}'.Replace('PLACEHOLDER',$fixtureId) | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
    '# Final disposable harness fixture' | Set-Content (Join-Path $fixtureDir 'SPEC.md') -Encoding UTF8
    'existing context' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8

    $reviewerContent = @'
param([string[]]$ChildArgs)
$rawArgs = $ChildArgs -join ' '
$mode = if ($rawArgs -match 'passnonzero') { 'passnonzero' } elseif ($rawArgs -match 'blockzero') { 'blockzero' } elseif ($rawArgs -match 'duplicatebold') { 'duplicatebold' } elseif ($rawArgs -match 'duplicate') { 'duplicate' } elseif ($rawArgs -match 'competing') { 'competing' } elseif ($rawArgs -match 'mixed') { 'mixed' } elseif ($rawArgs -match 'heading') { 'heading' } elseif ($rawArgs -match 'backtick') { 'backtick' } elseif ($rawArgs -match 'block') { 'block' } elseif ($rawArgs -match 'malformed') { 'malformed' } elseif ($rawArgs -match 'markdown') { 'markdown' } elseif ($rawArgs -match 'fallback') { 'fallback' } else { 'pass' }
if ($mode -eq 'fallback') { $count = if (Test-Path 'STATEFILE') { [int](Get-Content 'STATEFILE') } else { 0 }; $count++; $count | Set-Content 'STATEFILE'; if ($count -eq 1) { exit 7 } }
if ($mode -eq 'fail') { exit 7 }
$text = switch ($mode) {
    'block' { "VERDICT: BLOCK`nBLOCKING_FINDINGS: 1`n" }
    'malformed' { 'not a review' }
    'markdown' { "**VERDICT: PASS**`n**BLOCKING_FINDINGS: 0**`n" }
    'passnonzero' { "VERDICT: PASS`nBLOCKING_FINDINGS: 1`n" }
    'blockzero' { "VERDICT: BLOCK`nBLOCKING_FINDINGS: 0`n" }
    'duplicate' { "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n`nVERDICT: PASS`nBLOCKING_FINDINGS: 0`n" }
    'duplicatebold' { "**VERDICT: PASS**`n**BLOCKING_FINDINGS: 0**`n`n**VERDICT: PASS**`n**BLOCKING_FINDINGS: 0**`n" }
    'competing' { "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n`n**VERDICT: PASS**`n**BLOCKING_FINDINGS: 0**`n" }
    'mixed' { "**VERDICT: PASS**`nBLOCKING_FINDINGS: 0`n" }
    'heading' { "# VERDICT: PASS`n# BLOCKING_FINDINGS: 0`n" }
    'backtick' { "``VERDICT: PASS``n``BLOCKING_FINDINGS: 0``n" }
    default { "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n" }
}
$text
'@
    $reviewerContent = $reviewerContent.Replace('STATEFILE',$fallbackCounter)
    Set-Content -Path $reviewer -Value $reviewerContent -Encoding UTF8
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
    @'
$mode = $env:WORKFLOW_STRUCTURED_MODE
function Event($messageId, $text, $synthetic = $false) {
    @{ type = 'text'; synthetic = $synthetic; part = @{ messageID = $messageId; text = $text } } | ConvertTo-Json -Compress
}
function Finish($messageId) { @{ type = 'step_finish'; part = @{ messageID = $messageId } } | ConvertTo-Json -Compress }
if ($mode -eq 'incomplete') {
    Event 'm1' "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n"; Finish 'm1'; Event 'm2' 'headerless incomplete text'
} elseif ($mode -eq 'malformed-latest') {
    Event 'm1' "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n"; Finish 'm1'; Event 'm2' 'later completed headerless text'; Finish 'm2'
} elseif ($mode -eq 'synthetic-trailing') {
    Event 'm1' "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n"; Finish 'm1'; Event 'm2' 'synthetic trailing text' $true; Finish 'm2'
} else { Event 'm1' "VERDICT: PASS`nBLOCKING_FINDINGS: 0`n" }
'@ | Set-Content $structuredChild -Encoding UTF8
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$structuredChild`" %*" | Set-Content $structuredCmd -Encoding ASCII

    $reviewBase = @('-_ReviewerExecutableOverride',$reviewerCmd,'-ReviewTimeoutSeconds','10','-_ReviewerArgumentsOverride','pass','-_ReviewCandidatesOverride','first','second')
    Run-Case 'Gate PASS and candidate override resolution' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId) + $reviewBase)
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate BLOCK returns 2' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','block'))
        Assert-True ($code -eq 2) "expected 2, got $code"
    }
    Run-Case 'Gate malformed output returns 1' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','malformed'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate Markdown bold PASS is accepted' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','markdown'))
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    foreach ($mode in @('passnonzero','blockzero','duplicate','duplicatebold','competing','mixed','heading','backtick')) {
        Run-Case "Gate rejects $mode" {
            $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride',$mode))
            Assert-True ($code -eq 1) "expected 1, got $code"
        }
    }
    Run-Case 'Gate first success creates attempt history' {
        $historyPath = Join-Path $fixtureDir 'ATTEMPT_HISTORY.md'
        Assert-True (Test-Path $historyPath) 'attempt history was not created'
        $script:firstHistory = Get-Content $historyPath -Raw
        Assert-True ($script:firstHistory -match 'Historical observability only') 'history authority label missing'
    }
    Run-Case 'Gate rerun appends attempt history' {
        $historyPath = Join-Path $fixtureDir 'ATTEMPT_HISTORY.md'
        $before = Get-Content $historyPath -Raw
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','pass'))
        Assert-True ($code -eq 0) "expected 0, got $code"
        $after = Get-Content $historyPath -Raw
        Assert-True ($after.Length -gt $before.Length) 'history was replaced instead of appended'
        Assert-True (($after -split '## Gate run').Count -ge 3) 'distinct run section was not appended'
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
        $oldHistory = Get-Content (Join-Path $fixtureDir 'ATTEMPT_HISTORY.md') -Raw
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_FailPromotionOnTarget','evidence'))
        Assert-True ($code -eq 1) "expected 1, got $code"
        Assert-True ((Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw) -eq $old) 'rollback did not preserve evidence'
        Assert-True ((Get-Content (Join-Path $fixtureDir 'ATTEMPT_HISTORY.md') -Raw) -eq $oldHistory) 'rollback did not preserve attempt history'
    }
    Run-Case 'Gate failed candidate then fallback success records both attempts' {
        Remove-Item $fallbackCounter -Force -ErrorAction SilentlyContinue
        $code = Invoke-Script $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','fallback','-_PythonExecutableOverride',$pythonCmd)
        Assert-True ($code -eq 0) "expected 0, got $code"
        $history = Get-Content (Join-Path $fixtureDir 'ATTEMPT_HISTORY.md') -Raw
        Assert-True ($history -match 'NON_ZERO_EXIT') 'failed fallback attempt was not recorded'
        Assert-True ($history -match 'VALID_VERDICT') 'successful fallback attempt was not recorded'
    }
    Run-Case 'Structured completed canonical beats later incomplete text' {
        $code = Invoke-StructuredGate 'incomplete'
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Structured later completed malformed message is authoritative' {
        $code = Invoke-StructuredGate 'malformed-latest'
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Structured synthetic trailing text is excluded' {
        $code = Invoke-StructuredGate 'synthetic-trailing'
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Structured output with no completed assistant fails' {
        $code = Invoke-StructuredGate 'none-completed'
        Assert-True ($code -eq 1) "expected 1, got $code"
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
