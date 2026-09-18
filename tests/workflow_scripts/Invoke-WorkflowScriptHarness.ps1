param(
    [ValidateSet('all','process/helpers','scout','gate-readiness','gate-verdict','gate-resume-cache')]
    [string]$Group = 'all'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent | Split-Path -Parent
$gate = Join-Path $repoRoot 'scripts\ai_gate.ps1'
$scout = Join-Path $repoRoot 'scripts\ai_scout.ps1'
$fixtureId = "workflow-harness-fixture-$([DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff'))-$PID"
$fixtureDir = Join-Path $repoRoot "docs\tasks\active\$fixtureId"
$runtimeDirs = @(
    (Join-Path $repoRoot ".runtime\ai_gate\$fixtureId"),
    (Join-Path $repoRoot ".runtime\ai_scout\$fixtureId")
)
$helperDir = Join-Path $repoRoot '.runtime\workflow-harness-fixtures'
$diagnosticRoot = Join-Path $repoRoot '.runtime\test_workflow_harness'
$reviewer = Join-Path $helperDir 'fake-reviewer.py'
$scoutChild = Join-Path $helperDir 'fake-scout.ps1'
$pythonChild = Join-Path $helperDir 'fake-test.ps1'
$reviewerCmd = Join-Path $helperDir 'fake-reviewer.cmd'
$scoutCmd = Join-Path $helperDir 'fake-scout.cmd'
$pythonCmd = Join-Path $helperDir 'fake-test.cmd'
$secondMarker = Join-Path $helperDir 'second-candidate-invoked.marker'
$firstMarker = Join-Path $helperDir 'first-candidate-invoked.marker'
$passed = 0
$failed = 0
$specReviewer = Join-Path $repoRoot '.opencode\agents\spec-reviewer.md'
$regressionReviewer = Join-Path $repoRoot '.opencode\agents\regression-reviewer.md'
$workflowContract = Join-Path $repoRoot 'docs\architecture\ai_development_workflow.md'
$openCodeContract = Join-Path $repoRoot 'scripts\opencode_contract.ps1'
$bootstrap = Join-Path $repoRoot 'scripts\bootstrap_opencode.ps1'
$nodeContract = Join-Path $repoRoot 'scripts\node_workflow_contract.ps1'
$bootstrapNode = Join-Path $repoRoot 'scripts\bootstrap_node_workflow_deps.ps1'
$scoutScript = Join-Path $repoRoot 'scripts\ai_scout.ps1'
$gateScript = Join-Path $repoRoot 'scripts\ai_gate.ps1'

# Helper scripts are required by process/helper cases before the disposable
# task fixture is materialized below.
New-Item -ItemType Directory -Force -Path $helperDir | Out-Null

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
    $root = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/s','/c',('"' + $command + '"')) -WorkingDirectory $repoRoot -PassThru
    try {
        if (-not $root.WaitForExit(30000)) { throw "Harness child timed out: PID $($root.Id)" }
        $root.WaitForExit()
        $root.Refresh()
        $exitCode = $root.ExitCode
        return ([int]$exitCode)
    } finally {
        $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $root.Id })
        foreach ($child in $children) {
            if (Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue) { & taskkill.exe /PID $child.ProcessId /T /F 2>$null | Out-Null }
        }
        $root.Dispose()
    }
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
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $outputPath = Join-Path $helperDir "harness-output-$PID-$([Guid]::NewGuid().ToString('N')).txt"
    $errorPath = Join-Path $helperDir "harness-error-$PID-$([Guid]::NewGuid().ToString('N')).txt"
    $shellCommand = $command + ' 1>"' + $outputPath + '" 2>"' + $errorPath + '"'
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = 'cmd.exe'
    $startInfo.Arguments = '/d /s /c "' + $shellCommand + '"'
    $startInfo.WorkingDirectory = $repoRoot
    $root = [System.Diagnostics.Process]::new()
    $root.StartInfo = $startInfo
    try {
        if (-not $root.Start()) { throw 'Harness child failed to start' }
        if (-not $root.WaitForExit(30000)) { throw "Harness child timed out: PID $($root.Id)" }
        $root.WaitForExit()
        $exitCode = $root.ExitCode
        $output = ((Get-Content -LiteralPath $outputPath -Raw -ErrorAction SilentlyContinue), (Get-Content -LiteralPath $errorPath -Raw -ErrorAction SilentlyContinue) | Where-Object { $_ }) -join "`n"
        return [pscustomobject]@{ ExitCode = [int]$exitCode; Output = $output }
    } catch { return [pscustomobject]@{ ExitCode = 1; Output = ($_ | Out-String) } }
    finally {
        $ErrorActionPreference = $prevEap
        if (Test-Path -LiteralPath $outputPath) { Remove-Item -LiteralPath $outputPath -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $errorPath) { Remove-Item -LiteralPath $errorPath -Force -ErrorAction SilentlyContinue }
    }
}

function Run-Case([string]$Name, [scriptblock]$Body) {
    $caseGroup = if ($Name -match 'Scout') { 'scout' }
        elseif ($Name -match 'candidate evidence|promotion rollback|partial resume|successful run|canonical reviews|candidate order|ForceRefresh|SPEC change|reviewer contract|fingerprint|review artifact') { 'gate-resume-cache' }
        elseif ($Name -match 'unsupported OpenCode|unsupported Node|unbootstrapped Node|SkipNodeReadiness|invocation probe') { 'gate-readiness' }
        elseif ($Name -match 'Reviewer budgets|OpenCode launcher contract|Node workflow contract|Invoke-Script|process tree|event consumer') { 'process/helpers' }
        else { 'gate-verdict' }
    if ($Group -ne 'all' -and $Group -ne $caseGroup) { return }
    try { & $Body; Write-Host "PASS $Name"; $script:passed++ }
    catch { Write-Host "FAIL $Name - $($_.Exception.Message)"; $script:failed++ }
}

function Reset-DisposableGateState {
    $reviewDir = Join-Path $fixtureDir 'reviews'
    if (Test-Path -LiteralPath $reviewDir) { Get-ChildItem -LiteralPath $reviewDir -File | Remove-Item -Force -ErrorAction SilentlyContinue }
    foreach ($path in @((Join-Path $fixtureDir 'EVIDENCE.md'), (Join-Path $repoRoot ".runtime\ai_gate\$fixtureId"), (Join-Path $repoRoot ".runtime\ai_scout\$fixtureId"))) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue }
    }
    if ($taskJsonPath -and $originalTaskJson) { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    foreach ($item in Get-ChildItem -LiteralPath $helperDir -File -ErrorAction SilentlyContinue) {
        if ($item.Extension -notin @('.py', '.cmd', '.ps1')) { Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue }
    }
}

function Run-FreshPassingGate {
    Reset-DisposableGateState
    $code = Invoke-Script $gate $cacheReviewArgs + '-ForceRefresh'
    Assert-True ($code -eq 0) "fresh passing Gate expected 0, got $code"
    Assert-True (Test-Path (Join-Path $fixtureDir 'reviews\spec-review.md')) 'fresh spec review missing'
    Assert-True (Test-Path (Join-Path $fixtureDir 'reviews\regression-review.md')) 'fresh regression review missing'
    Assert-True (Test-Path (Join-Path $fixtureDir 'EVIDENCE.md')) 'fresh EVIDENCE missing'
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
        Assert-True ($workflowText -match 'Valid structured PASS/BLOCK output is terminal for the reviewer role') 'architecture terminal reviewer contract missing'
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
        Assert-True ($workflowText -match 'Repository automation follows the pinned OpenCode version, launcher contract, CLI contract, and provider compatibility baseline') 'architecture OpenCode responsibility contract missing'
    }
    Run-Case 'Node workflow contract and bootstrap script contracts' {
        $nodeContractText = Get-Content $nodeContract -Raw
        $bootstrapNodeText = Get-Content $bootstrapNode -Raw
        $gateText = Get-Content $gateScript -Raw
        $workflowText = Get-Content $workflowContract -Raw
        Assert-True ($nodeContractText -notmatch '\$NodeEngineRequiredSpec') 'Node contract must not declare a hardcoded engine constant'
        Assert-True ($nodeContractText -match 'Get-RequiredNodeEngineSpec') 'Node contract missing Get-RequiredNodeEngineSpec'
        Assert-True ($nodeContractText -match 'engines\.node') 'Node contract does not inspect engines.node from package.json'
        Assert-True ($nodeContractText -match 'bootstrap_node_workflow_deps\.ps1') 'node contract remediation missing bootstrap script'
        Assert-True ($bootstrapNodeText -match 'Get-RequiredNodeEngineSpec') 'bootstrap script does not derive required engine spec from package.json'
        Assert-True ($bootstrapNodeText -match 'npm ci') 'bootstrap script does not use npm ci'
        Assert-True ($bootstrapNodeText -notmatch 'npm install\b') 'bootstrap script contains forbidden npm install'
        Assert-True ($gateText -match 'node_workflow_contract\.ps1') 'Gate does not include node_workflow_contract'
        Assert-True ($gateText -match 'Assert-NodeWorkflowDependenciesReady') 'Gate does not check Node readiness'
        Assert-True ($gateText -notmatch 'npm install|npm ci') 'Gate contains forbidden npm mutation'
        Assert-True ($workflowText.Contains('Canonical Node workflow environment')) 'architecture Node workflow environment section missing'
    }
    New-Item -ItemType Directory -Force -Path $fixtureDir, (Join-Path $fixtureDir 'reviews'), $helperDir | Out-Null
    New-Item -ItemType Directory -Force -Path $diagnosticRoot | Out-Null
    $env:WORKFLOW_HARNESS_DIAGNOSTIC_DIR = $diagnosticRoot
    '{"id":"PLACEHOLDER","base_ref":"origin/main","scope":["docs/tasks/active/PLACEHOLDER/"],"focused_tests":[],"models":{"scout":["first","second"],"review":"opencode/big-pickle"}}'.Replace('PLACEHOLDER',$fixtureId) | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
    $taskJsonPath = Join-Path $fixtureDir 'task.json'
    $originalTaskJson = Get-Content -LiteralPath $taskJsonPath -Raw
    '# Final disposable harness fixture' | Set-Content (Join-Path $fixtureDir 'SPEC.md') -Encoding UTF8
    'existing context' | Set-Content (Join-Path $fixtureDir 'CONTEXT.md') -Encoding UTF8
    $exitProbe = Join-Path $helperDir 'exit-code-probe.ps1'
    'param([int]$Code); exit $Code' | Set-Content -LiteralPath $exitProbe -Encoding UTF8
    $timeoutProbe = Join-Path $helperDir 'timeout-probe.ps1'
    'Start-Sleep -Seconds 35' | Set-Content -LiteralPath $timeoutProbe -Encoding UTF8

    foreach ($expected in @(0, 1, 2, 7)) {
        Run-Case "Invoke-Script preserves child exit $expected" {
            $actual = Invoke-Script $exitProbe @('-Code', $expected)
            Assert-True ($actual -eq $expected) "expected $expected, got $actual"
        }
        Run-Case "Invoke-ScriptOutput preserves child exit $expected" {
            $actual = (Invoke-ScriptOutput $exitProbe @('-Code', $expected)).ExitCode
            Assert-True ($actual -eq $expected) "expected $expected, got $actual"
        }
    }
    Run-Case 'Invoke-ScriptOutput bounds child timeout' {
        $started = [DateTime]::UtcNow
        $result = Invoke-ScriptOutput $timeoutProbe @()
        $elapsed = ([DateTime]::UtcNow - $started).TotalSeconds
        Assert-True ($result.ExitCode -eq 1) "expected timeout failure, got $($result.ExitCode)"
        Assert-True ($elapsed -lt 35) "timeout wrapper exceeded bound: $elapsed seconds"
    }

    Run-Case 'Scout rejects an unsupported OpenCode version before routing' {
        $code = Invoke-Script $scout (@('-Task',$fixtureId,'-_ExecutableOverride',$scoutCmd,'-_OpenCodeVersionOverride','1.18.30'))
        Assert-True ($code -ne 0) "expected version mismatch failure, got $code"
    }

    Run-Case 'Scout invocation probe exercises the production argument builder' {
        $result = Invoke-ScriptOutput $scout @('-Task',$fixtureId,'-_InvocationProbe','-_ModelCandidatesOverride','test/probe-scout')
        Assert-True ($result.ExitCode -eq 0) "expected probe success, got $($result.ExitCode): $($result.Output)"
        $probe = $result.Output.Trim() | ConvertFrom-Json
        $args = @($probe.Arguments)
        Assert-True ($args -contains 'run') 'Scout production args missing run'
        Assert-True (($args -join ' ') -match '--agent scout') 'Scout production args missing scout agent'
        Assert-True (($args -join ' ') -match '--model test/probe-scout') 'Scout production args missing model'
        Assert-True (($args -join ' ') -match 'Task descriptor: docs/tasks/') 'Scout production args missing prompt'
        Assert-True (($args -join ' ') -notmatch '--standalone|--pure') 'Scout production args contain unsupported flags'
    }

@'
import json
import os
import pathlib
import sys
import time

# Persist raw process argv before any argument parsing.
diagnostic_dir = pathlib.Path(os.environ["WORKFLOW_HARNESS_DIAGNOSTIC_DIR"])
diagnostic_dir.mkdir(parents=True, exist_ok=True)
(diagnostic_dir / "fake-reviewer.raw-argv.txt").write_text(repr(sys.argv), encoding="utf-8")
args = sys.argv[1:]
raw = " ".join(args)
model = args[args.index("--model") + 1] if "--model" in args else ""
model = model.rsplit("/", 1)[-1]
agent = args[args.index("--agent") + 1] if "--agent" in args else "unknown"
helper_dir = pathlib.Path(__file__).parent

# Record invocation count per agent
invocations_file = helper_dir / f"{agent}.invocations.txt"
prev_count = int(invocations_file.read_text(encoding="utf-8")) if invocations_file.exists() else 0
invocations_file.write_text(str(prev_count + 1), encoding="utf-8")

if "overlap-probe" in args or model == "overlap-probe":
    start_marker = helper_dir / f"{agent}.start.marker"
    start_marker.write_text("start", encoding="utf-8")
    sibling = "regression-reviewer" if agent == "spec-reviewer" else "spec-reviewer"
    sibling_marker = helper_dir / f"{sibling}.start.marker"
    for _ in range(40):
        if sibling_marker.exists():
            (helper_dir / "overlap-confirmed.marker").write_text("confirmed", encoding="utf-8")
            break
        time.sleep(0.05)

evidence = pathlib.Path(__file__).with_name(model + ".argv.txt") if model else pathlib.Path(__file__).with_name("missing-model.argv.txt")
evidence.write_text(json.dumps({"argv": args, "stderr": "", "exit_code": 0}), encoding="utf-8")
pathlib.Path(__file__).with_name("reviewer-invoked.marker").write_text("invoked", encoding="utf-8")
if model == "catastrophic-crash" or "catastrophic-crash" in args:
    pathlib.Path(__file__).with_name("catastrophic-crash.marker").write_text("invoked", encoding="utf-8")
    sys.stderr.write("catastrophic fixture failure\n")
    raise SystemExit(7)
elif model == "stale-evidence-probe":
    candidate = pathlib.Path(args[args.index("--prompt-file") + 1]).parent / "candidate_EVIDENCE.md"
    stale = candidate.exists() and "tests.test_workflow_scripts: FAIL" in candidate.read_text(encoding="utf-8")
    if stale:
        result = {"schema_version": 1, "classification": "VALID_BLOCK", "structured": {"verdict": "BLOCK", "blocking_findings": 1, "report_markdown": "stale candidate visible"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
    else:
        result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "clean staging"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model == "fallback-grounding":
    pathlib.Path(__file__).with_name("fallback-grounding.marker").write_text("invoked", encoding="utf-8")
    result = {"schema_version": 1, "classification": "GROUNDING_FAILED", "structured": None, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model == "fallback-pass":
    pathlib.Path(__file__).with_name("fallback-pass.marker").write_text("invoked", encoding="utf-8")
    result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model in ("terminal-first-pass", "terminal-first-block"):
    pathlib.Path(__file__).with_name("first-candidate-invoked.marker").write_text("invoked", encoding="utf-8")
    result = {"schema_version": 1, "classification": "VALID_BLOCK" if model.endswith("block") else "VALID_PASS", "structured": {"verdict": "BLOCK" if model.endswith("block") else "PASS", "blocking_findings": 1 if model.endswith("block") else 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model == "terminal-second":
    pathlib.Path(__file__).with_name("second-candidate-invoked.marker").write_text("invoked", encoding="utf-8")
    result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model == "transport-safe":
    result = {"schema_version": 1, "classification": "STRUCTURED_TRANSPORT_FAILED", "structured": None, "diagnostic": {"operation": "session.prompt", "name": "TypeError", "message": "fetch failed"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif model == "transport-unsafe":
    result = {"schema_version": 1, "classification": "INFRASTRUCTURE_FAILED", "structured": None, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": False, "server_exit_confirmed": False}}
elif "crash" in args:
    sys.stderr.write("catastrophic fixture failure\n")
    raise SystemExit(7)
elif "terminal-block" in args:
    result = {"schema_version": 1, "classification": "VALID_BLOCK", "structured": {"verdict": "BLOCK", "blocking_findings": 1, "report_markdown": "# Block"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif "terminal-pass" in args:
    result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
elif "unsafe" in args:
    result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": False, "server_exit_confirmed": False}}
elif "malformed" in args:
    print("not a review")
    raise SystemExit(0)
elif "markdown" in args:
    print("**VERDICT: PASS**")
    raise SystemExit(0)
else:
    result = {"schema_version": 1, "classification": "VALID_PASS", "structured": {"verdict": "PASS", "blocking_findings": 0, "report_markdown": "# Review"}, "lifecycle": {"final_message_identity": True}, "cleanup": {"safe": True, "server_exit_confirmed": True}}
print(json.dumps(result, separators=(",", ":")))
'@ | Set-Content $reviewer -Encoding UTF8
@'
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ChildArgs)
$diagnosticPath = Join-Path $env:WORKFLOW_HARNESS_DIAGNOSTIC_DIR 'fake-scout.args.txt'
($ChildArgs -join "`n") | Set-Content -LiteralPath $diagnosticPath -Encoding UTF8
if ($ChildArgs -contains 'bad') { 'malformed scout'; exit 0 }
if ($ChildArgs -contains 'fail') { exit 9 }
if ($ChildArgs -contains 'sleep') { Start-Sleep -Seconds 2 }
Write-Output "# Scout Context`n`n## Relevant files`n- disposable fixture"
'@ | Set-Content $scoutChild -Encoding UTF8
    'exit 0' | Set-Content $pythonChild -Encoding UTF8
    "@python `"%~dp0fake-reviewer.py`" %*" | Set-Content $reviewerCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scoutChild`" %*" | Set-Content $scoutCmd -Encoding ASCII
    "@powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$pythonChild`" %*" | Set-Content $pythonCmd -Encoding ASCII

    $reviewBase = @('-_ReviewerExecutableOverride',$reviewerCmd,'-ReviewTimeoutSeconds','10','-_ReviewCandidatesOverride','test/first','test/second')
    Run-Case 'Gate rejects an unsupported OpenCode version before routing' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_OpenCodeVersionOverride','2.0.3'))
        Assert-True ($code -ne 0) "expected version mismatch failure, got $code"
    }
    Run-Case 'Gate rejects an unsupported Node version before routing' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_NodeVersionOverride','16.0.0'))
        Assert-True ($code -ne 0) "expected Node version mismatch failure, got $code"
    }
    Run-Case 'Gate fails fast on unbootstrapped Node dependencies before reviewer execution' {
        $marker = Join-Path $helperDir 'reviewer-invoked.marker'
        if (Test-Path $marker) { Remove-Item -LiteralPath $marker -Force }
        $result = Invoke-ScriptOutput $gate @(
            '-Task', $fixtureId,
            '-_ReviewerExecutableOverride', $reviewerCmd,
            '-_NodeExecutableOverride', 'nonexistent_node_binary_for_test'
        )
        Assert-True ($result.ExitCode -ne 0) "expected missing node failure, got $($result.ExitCode)"
        Assert-True ($result.Output -match 'Node workflow dependencies are not ready for this worktree') 'missing expected bootstrap guidance'
        Assert-True ($result.Output.Contains('Run: .\scripts\bootstrap_node_workflow_deps.ps1')) 'missing bootstrap script remediation'
        Assert-True (-not (Test-Path $marker)) 'fake reviewer must NOT have been executed when Node readiness fails'
    }
    Run-Case 'Gate explicit _SkipNodeReadinessCheck bypasses readiness for testing' {
        $code = Invoke-Script $gate (@(
            '-Task', $fixtureId,
            '-_NodeExecutableOverride', 'nonexistent_node_binary_for_test',
            '-_SkipNodeReadinessCheck'
        ) + $reviewBase)
        Assert-True ($code -eq 0) "expected 0 when explicitly skipping readiness, got $code"
    }
    Run-Case 'Gate invocation probe exercises the production argument builder' {
        $result = Invoke-ScriptOutput $gate @('-Task',$fixtureId,'-_InvocationProbe')
        Assert-True ($result.ExitCode -eq 0) "expected probe success, got $($result.ExitCode): $($result.Output)"
        $probe = $result.Output.Trim() | ConvertFrom-Json
        $args = @($probe.Arguments)
        Assert-True ($probe.Agent -eq 'spec-reviewer') "expected spec-reviewer probe, got $($probe.Agent)"
        Assert-True (($args -join ' ') -match '--agent spec-reviewer') 'Gate production args missing reviewer agent'
        Assert-True (($args -join ' ') -match '--model opencode/big-pickle') 'Gate production args missing configured model'
        Assert-True (($args -join ' ') -match '--prompt-file') 'Gate production args missing prompt file'
        Assert-True (($args -join ' ') -notmatch '--standalone|--pure') 'Gate production args contain unsupported flags'
    }
    Run-Case 'Gate PASS and candidate override resolution' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId) + $reviewBase)
        Assert-True ($code -eq 0) "expected 0, got $code"
    }
    Run-Case 'Gate valid structured BLOCK returns 2 and is terminal' {
        $json = $originalTaskJson | ConvertFrom-Json; $json.models.review = 'test/terminal-first-block'; $json | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        if (Test-Path $secondMarker) { Remove-Item -LiteralPath $secondMarker -Force }; $firstMarker = Join-Path $helperDir 'first-candidate-invoked.marker'; if (Test-Path $firstMarker) { Remove-Item -LiteralPath $firstMarker -Force }
        try { $code = Invoke-Script $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride','test/terminal-first-block','test/terminal-second'); Assert-True ($code -eq 2) "expected 2, got $code"; Assert-True (Test-Path $firstMarker) 'terminal BLOCK first candidate was not invoked'; Assert-True (-not (Test-Path $secondMarker)) 'trusted BLOCK incorrectly invoked the second candidate' } finally { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    }
    Run-Case 'Gate valid structured PASS is terminal' {
        $json = $originalTaskJson | ConvertFrom-Json; $json.models.review = 'test/terminal-first-pass'; $json | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        if (Test-Path $secondMarker) { Remove-Item -LiteralPath $secondMarker -Force }; $firstMarker = Join-Path $helperDir 'first-candidate-invoked.marker'; if (Test-Path $firstMarker) { Remove-Item -LiteralPath $firstMarker -Force }
        try { $code = Invoke-Script $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride','test/terminal-first-pass','test/terminal-second'); Assert-True ($code -eq 0) "expected 0, got $code"; Assert-True (Test-Path $firstMarker) 'terminal PASS first candidate was not invoked'; Assert-True (-not (Test-Path $secondMarker)) 'trusted PASS incorrectly invoked the second candidate' } finally { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    }
    Run-Case 'Gate malformed adapter envelope returns 1' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','malformed'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate legacy free-text verdict has zero authority' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','markdown'))
        Assert-True ($code -eq 1) "expected 1, got $code"
    }
    Run-Case 'Gate pre-authority infrastructure failure is terminal' {
        $groundingMarker = Join-Path $helperDir 'fallback-grounding.marker'
        $passMarker = Join-Path $helperDir 'fallback-pass.marker'
        $json = $originalTaskJson | ConvertFrom-Json; $json.models.review = 'opencode/big-pickle'; $json | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        if (Test-Path $groundingMarker) { Remove-Item -LiteralPath $groundingMarker -Force }; if (Test-Path $passMarker) { Remove-Item -LiteralPath $passMarker -Force }
        try { $code = Invoke-ScriptOutput $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride','test/fallback-grounding','test/fallback-pass'); Assert-True ($code.ExitCode -eq 1) "expected verification unavailable, got $($code.ExitCode): $($code.Output)"; Assert-True (Test-Path $groundingMarker) 'configured reviewer was not invoked'; Assert-True (-not (Test-Path $passMarker)) 'second reviewer was silently attempted' } finally { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    }
    Run-Case 'Gate safe transport failure is unavailable without fallback' {
        $json = $originalTaskJson | ConvertFrom-Json; $json.models.review = 'opencode/big-pickle'; $json | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        $passMarker = Join-Path $helperDir 'fallback-pass.marker'; if (Test-Path $passMarker) { Remove-Item -LiteralPath $passMarker -Force }
        try { $code = Invoke-Script $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride','test/transport-safe','test/fallback-pass'); Assert-True ($code -eq 1) "expected verification unavailable, got $code"; Assert-True (-not (Test-Path $passMarker)) 'second reviewer was silently attempted' } finally { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    }
    Run-Case 'Gate clears stale candidate evidence before reviewer phase' {
        $stale = Join-Path $repoRoot ".runtime\ai_gate\$fixtureId\candidate_EVIDENCE.md"
        New-Item -ItemType Directory -Force -Path (Split-Path $stale) | Out-Null
        'Focused tests`n- tests.test_workflow_scripts: FAIL' | Set-Content -LiteralPath $stale -Encoding UTF8
        $probeArgs = @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','stale-evidence-probe','-_RegressionReviewerArgumentsOverride','stale-evidence-probe','-ForceRefresh')
        $code = Invoke-Script $gate $probeArgs
        Assert-True ($code -eq 0) "expected clean staging PASS, got $code"
        Assert-True (Test-Path (Join-Path $fixtureDir 'EVIDENCE.md')) 'Gate did not complete current evidence promotion'
    }
    Run-Case 'Gate catastrophic adapter failure has no fallback' {
        $json = $originalTaskJson | ConvertFrom-Json; $json.models.review = 'opencode/big-pickle'; $json | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        $firstMarker = Join-Path $helperDir 'catastrophic-crash.marker'; $secondMarker = Join-Path $helperDir 'fallback-pass.marker'
        if (Test-Path $firstMarker) { Remove-Item -LiteralPath $firstMarker -Force }; if (Test-Path $secondMarker) { Remove-Item -LiteralPath $secondMarker -Force }
        try { $code = Invoke-Script $gate @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride','test/catastrophic-crash','test/fallback-pass'); Assert-True ($code -eq 1) "expected catastrophic failure, got $code"; Assert-True (Test-Path $firstMarker) 'catastrophic candidate was not invoked'; Assert-True (-not (Test-Path $secondMarker)) 'catastrophic no-envelope failure incorrectly fell back' } finally { $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8 }
    }
    Run-Case 'Gate unsafe adapter cleanup stops fallback' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','unsafe'))
        Assert-True ($code -eq 1) "expected unavailable, got $code"
    }
    Run-Case 'Gate focused-test override passes' {
        try {
            $json = Get-Content (Join-Path $fixtureDir 'task.json') -Raw | ConvertFrom-Json
            $json.focused_tests = @('disposable-target')
            $json | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $fixtureDir 'task.json') -Encoding UTF8
            $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_PythonExecutableOverride',$pythonCmd))
            Assert-True ($code -eq 0) "expected 0, got $code"
        } finally {
            $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        }
    }
    Run-Case 'Gate promotion rollback preserves prior artifacts' {
        $old = Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_FailPromotionOnTarget','evidence'))
        Assert-True ($code -eq 1) "expected 1, got $code"
        Assert-True ((Get-Content (Join-Path $fixtureDir 'EVIDENCE.md') -Raw) -eq $old) 'rollback did not preserve evidence'
    }

    Run-Case 'Gate parallel reviewers overlap execution' {
        $overlapMarker = Join-Path $helperDir 'overlap-confirmed.marker'
        if (Test-Path $overlapMarker) { Remove-Item $overlapMarker -Force }
        $specStart = Join-Path $helperDir 'spec-reviewer.start.marker'
        $regStart = Join-Path $helperDir 'regression-reviewer.start.marker'
        if (Test-Path $specStart) { Remove-Item $specStart -Force }
        if (Test-Path $regStart) { Remove-Item $regStart -Force }
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewerArgumentsOverride','overlap-probe','-ForceRefresh'))
        Assert-True ($code -eq 0) "expected 0, got $code"
        Assert-True (Test-Path $overlapMarker) 'Reviewers did not overlap in execution'
    }

    Run-Case 'Gate spec BLOCK and regression PASS yields CANDIDATE_BLOCKED' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-block','-_RegressionReviewerArgumentsOverride','terminal-pass','-ForceRefresh'))
        Assert-True ($code -eq 2) "expected 2, got $code"
    }

    Run-Case 'Gate regression BLOCK and spec PASS yields CANDIDATE_BLOCKED' {
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-pass','-_RegressionReviewerArgumentsOverride','terminal-block','-ForceRefresh'))
        Assert-True ($code -eq 2) "expected 2, got $code"
    }

    Run-Case 'Gate sibling artifact survives infrastructure failure' {
        Reset-DisposableGateState
        $specCanonical = Join-Path $fixtureDir 'reviews\spec-review.md'
        $regCanonical = Join-Path $fixtureDir 'reviews\regression-review.md'
        $evidenceCanonical = Join-Path $fixtureDir 'EVIDENCE.md'
        if (Test-Path $specCanonical) { Remove-Item $specCanonical -Force }
        if (Test-Path $regCanonical) { Remove-Item $regCanonical -Force }
        if (Test-Path $evidenceCanonical) { Remove-Item $evidenceCanonical -Force }

        # spec-reviewer passes, but regression-reviewer crashes
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-pass','-_RegressionReviewerArgumentsOverride','catastrophic-crash','-ForceRefresh'))
        Assert-True ($code -eq 1) "expected 1, got $code"
        Assert-True (Test-Path $specCanonical) 'spec-reviewer valid canonical artifact was not promoted'
        Assert-True (-not (Test-Path $regCanonical)) 'regression-reviewer canonical artifact should not exist'
        Assert-True (-not (Test-Path $evidenceCanonical)) 'EVIDENCE.md must not be created on incomplete gate run'
    }

    Run-Case 'Gate partial resume reuses surviving sibling and reruns failed reviewer' {
        Reset-DisposableGateState
        '' | Set-Content -LiteralPath (Join-Path $fixtureDir 'reviews\spec-review.md')
        '' | Set-Content -LiteralPath (Join-Path $fixtureDir 'reviews\regression-review.md')
        '' | Set-Content -LiteralPath (Join-Path $fixtureDir 'EVIDENCE.md')
        $code0 = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-pass','-_RegressionReviewerArgumentsOverride','catastrophic-crash','-ForceRefresh'))
        Assert-True ($code0 -eq 1) "partial resume setup expected 1, got $code0"
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $regInvocationsFile = Join-Path $helperDir 'regression-reviewer.invocations.txt'
        $specCountBefore = if (Test-Path $specInvocationsFile) { [int](Get-Content $specInvocationsFile -Raw) } else { 0 }
        $regCountBefore = if (Test-Path $regInvocationsFile) { [int](Get-Content $regInvocationsFile -Raw) } else { 0 }
        $specHashBefore = (Get-FileHash (Join-Path $fixtureDir 'reviews\spec-review.md')).Hash
        $statusHashBefore = (Get-FileHash (Join-Path $repoRoot ('.runtime\ai_gate\' + $fixtureId + '\status.txt'))).Hash
        $diffHashBefore = (Get-FileHash (Join-Path $repoRoot ('.runtime\ai_gate\' + $fixtureId + '\diff.patch'))).Hash

        # regression-reviewer now passes as well
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-pass','-_RegressionReviewerArgumentsOverride','terminal-pass'))
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        $regCountAfter = [int](Get-Content $regInvocationsFile -Raw)
        $specHashAfter = (Get-FileHash (Join-Path $fixtureDir 'reviews\spec-review.md')).Hash
        $statusHashAfter = (Get-FileHash (Join-Path $repoRoot ('.runtime\ai_gate\' + $fixtureId + '\status.txt'))).Hash
        $diffHashAfter = (Get-FileHash (Join-Path $repoRoot ('.runtime\ai_gate\' + $fixtureId + '\diff.patch'))).Hash

        Assert-True ($specCountAfter -eq $specCountBefore) "spec-reviewer was launched despite valid cache: before=$specCountBefore, after=$specCountAfter"
        Assert-True ($regCountAfter -gt $regCountBefore) "regression-reviewer was not launched on rerun"
        Assert-True ($specHashAfter -eq $specHashBefore) 'spec canonical review was rewritten'
        Assert-True ($statusHashAfter -eq $statusHashBefore) 'status snapshot changed during partial resume'
        Assert-True ($diffHashAfter -eq $diffHashBefore) 'diff snapshot changed during partial resume'
        Assert-True (Test-Path (Join-Path $fixtureDir 'reviews\spec-review.md')) 'spec-review.md missing'
        Assert-True (Test-Path (Join-Path $fixtureDir 'reviews\regression-review.md')) 'regression-review.md missing'
        Assert-True (Test-Path (Join-Path $fixtureDir 'EVIDENCE.md')) 'EVIDENCE.md missing'
    }

    $cacheReviewArgs = @('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-pass','-_RegressionReviewerArgumentsOverride','terminal-pass')

    # 1. Gate successful run followed immediately by identical second run
    Run-Case 'Gate successful run followed immediately by identical second run reuses both reviewers' {
        Run-FreshPassingGate
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $regInvocationsFile = Join-Path $helperDir 'regression-reviewer.invocations.txt'
        $specCanonical = Join-Path $fixtureDir 'reviews\spec-review.md'
        $regCanonical = Join-Path $fixtureDir 'reviews\regression-review.md'
        $evidenceCanonical = Join-Path $fixtureDir 'EVIDENCE.md'
        # Run-FreshPassingGate owns the run-1 precondition.

        # Run 1: Fresh execution with ForceRefresh to guarantee fresh promotion
        $code1 = Invoke-Script $gate ($cacheReviewArgs + '-ForceRefresh')
        Assert-True ($code1 -eq 0) "Run 1 expected 0, got $code1"
        Assert-True (Test-Path $specCanonical) 'Run 1 spec-review.md was not promoted'
        Assert-True (Test-Path $regCanonical) 'Run 1 regression-review.md was not promoted'
        Assert-True (Test-Path $evidenceCanonical) 'Run 1 EVIDENCE.md was not promoted'

        # Record counts after Run 1 (canonical outputs now exist in the worktree!)
        $specCountRun1 = [int](Get-Content $specInvocationsFile -Raw)
        $regCountRun1 = [int](Get-Content $regInvocationsFile -Raw)

        # Run 2: Immediate identical second run with existing canonical review outputs
        $code2 = Invoke-Script $gate $cacheReviewArgs
        Assert-True ($code2 -eq 0) "Run 2 expected 0, got $code2"

        $specCountRun2 = [int](Get-Content $specInvocationsFile -Raw)
        $regCountRun2 = [int](Get-Content $regInvocationsFile -Raw)

        Assert-True ($specCountRun2 -eq $specCountRun1) "spec-reviewer launched on immediate second run: Run1=$specCountRun1, Run2=$specCountRun2 (self-invalidation detected)"
        Assert-True ($regCountRun2 -eq $regCountRun1) "regression-reviewer launched on immediate second run: Run1=$regCountRun1, Run2=$regCountRun2 (self-invalidation detected)"
    }

    Run-Case 'Gate canonical reviews in stable checkout preserve valid reuse' {
        Run-FreshPassingGate
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $regInvocationsFile = Join-Path $helperDir 'regression-reviewer.invocations.txt'
        $specCanonical = Join-Path $fixtureDir 'reviews\spec-review.md'
        $regCanonical = Join-Path $fixtureDir 'reviews\regression-review.md'
        $evidenceCanonical = Join-Path $fixtureDir 'EVIDENCE.md'

        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)
        $regCountBefore = [int](Get-Content $regInvocationsFile -Raw)

            $code = Invoke-Script $gate $cacheReviewArgs
            Assert-True ($code -eq 0) "expected 0, got $code"

            $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
            $regCountAfter = [int](Get-Content $regInvocationsFile -Raw)

        Assert-True ($specCountAfter -eq $specCountBefore) 'spec-reviewer launched despite valid canonical reuse'
        Assert-True ($regCountAfter -eq $regCountBefore) 'regression-reviewer launched despite valid canonical reuse'
    }

    Run-Case 'Gate explicit reviewer model changes fingerprint and same model reuses cache' {
        Reset-DisposableGateState
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $regInvocationsFile = Join-Path $helperDir 'regression-reviewer.invocations.txt'
        $json = $originalTaskJson | ConvertFrom-Json

        try {
            $modelOne = 'test/terminal-first-pass'
            $code1 = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride',$modelOne,'-ForceRefresh'))
            Assert-True ($code1 -eq 0) "Initial model expected 0, got $code1"

            $specCountBeforeSame = [int](Get-Content $specInvocationsFile -Raw)
            $codeSame = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride',$modelOne))
            Assert-True ($codeSame -eq 0) "Same model expected 0, got $codeSame"
            $specCountAfterSame = [int](Get-Content $specInvocationsFile -Raw)
            Assert-True ($specCountAfterSame -eq $specCountBeforeSame) 'spec-reviewer was rerun despite identical model and inputs'

            $modelTwo = 'test/terminal-second'
            $specCountBeforeChanged = [int](Get-Content $specInvocationsFile -Raw)
            $code2 = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_ReviewCandidatesOverride',$modelTwo))
            Assert-True ($code2 -eq 0) "Changed model expected 0, got $code2"
            $specCountAfterChanged = [int](Get-Content $specInvocationsFile -Raw)
            Assert-True ($specCountAfterChanged -gt $specCountBeforeChanged) 'spec-reviewer was NOT rerun when explicit model changed'
        } finally {
            $originalTaskJson | Set-Content -LiteralPath $taskJsonPath -Encoding UTF8
        }
    }

    Run-Case 'Gate ForceRefresh bypasses cache and reruns both reviewers' {
        Run-FreshPassingGate
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $regInvocationsFile = Join-Path $helperDir 'regression-reviewer.invocations.txt'
        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)
        $regCountBefore = [int](Get-Content $regInvocationsFile -Raw)

        $code = Invoke-Script $gate ($cacheReviewArgs + '-ForceRefresh')
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        $regCountAfter = [int](Get-Content $regInvocationsFile -Raw)

        Assert-True ($specCountAfter -gt $specCountBefore) 'spec-reviewer was not rerun on -ForceRefresh'
        Assert-True ($regCountAfter -gt $regCountBefore) 'regression-reviewer was not rerun on -ForceRefresh'
    }

    Run-Case 'Gate SPEC change invalidates cache' {
        Run-FreshPassingGate
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)

        '# Modified spec content for invalidation test' | Set-Content (Join-Path $fixtureDir 'SPEC.md') -Encoding UTF8

        $code = Invoke-Script $gate $cacheReviewArgs
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        Assert-True ($specCountAfter -gt $specCountBefore) 'spec-reviewer was not rerun when SPEC changed'
    }

    Run-Case 'Gate reviewer contract or config change invalidates cache' {
        Run-FreshPassingGate
        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)

        # Run with different spec reviewer arguments to simulate prompt/config change
        $code = Invoke-Script $gate (@('-Task',$fixtureId,'-_ReviewerExecutableOverride',$reviewerCmd,'-_SpecReviewerArgumentsOverride','terminal-first-pass','-_RegressionReviewerArgumentsOverride','terminal-pass'))
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        Assert-True ($specCountAfter -gt $specCountBefore) 'spec-reviewer was not rerun when arguments/config changed'
    }

    Run-Case 'Gate malformed or missing fingerprint invalidates cache' {
        Run-FreshPassingGate
        $specReview = Join-Path $fixtureDir 'reviews\spec-review.md'
        $content = Get-Content $specReview -Raw
        $corrupted = $content -replace 'blackfire-gate-fingerprint: \{.*?\}', 'blackfire-gate-fingerprint: {invalid-json'
        $corrupted | Set-Content $specReview -Encoding UTF8

        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)

        $code = Invoke-Script $gate $cacheReviewArgs
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        Assert-True ($specCountAfter -gt $specCountBefore) 'spec-reviewer was not rerun when fingerprint was malformed'
    }

    Run-Case 'Gate malformed review artifact invalidates cache' {
        Run-FreshPassingGate
        $specReview = Join-Path $fixtureDir 'reviews\spec-review.md'
        $content = Get-Content $specReview -Raw
        $corrupted = $content -replace 'Gate-accepted verdict: PASS', 'Gate-accepted verdict: UNKNOWN'
        $corrupted | Set-Content $specReview -Encoding UTF8

        $specInvocationsFile = Join-Path $helperDir 'spec-reviewer.invocations.txt'
        $specCountBefore = [int](Get-Content $specInvocationsFile -Raw)

        $code = Invoke-Script $gate $cacheReviewArgs
        Assert-True ($code -eq 0) "expected 0, got $code"

        $specCountAfter = [int](Get-Content $specInvocationsFile -Raw)
        Assert-True ($specCountAfter -gt $specCountBefore) 'spec-reviewer was not rerun when review was malformed'
    }

    Run-Case 'Scout success promotes structured output' {
        $result = Invoke-ScriptOutput $scout @('-Task',$fixtureId,'-Model','test/only','-_ExecutableOverride',$scoutCmd)
        Assert-True ($result.ExitCode -eq 0) "expected 0, got $($result.ExitCode): $($result.Output)"
        $scoutArgs = Get-Content (Join-Path $diagnosticRoot 'fake-scout.args.txt') -Raw
        Assert-True ($scoutArgs -match '--model\s+test/only') 'fake scout did not receive --model test/only'
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
    $diagnosticPath = Join-Path $diagnosticRoot $fixtureId
if ($failed -gt 0) {
        New-Item -ItemType Directory -Force -Path $diagnosticPath | Out-Null
        if (Test-Path $helperDir) { Copy-Item $helperDir $diagnosticPath -Recurse -Force }
        if (Test-Path $fixtureDir) { Copy-Item $fixtureDir (Join-Path $diagnosticPath 'fixture') -Recurse -Force }
    }
    foreach ($path in @($fixtureDir,$helperDir) + $runtimeDirs) {
        if (Test-Path $path) { Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item Env:WORKFLOW_HARNESS_DIAGNOSTIC_DIR -ErrorAction SilentlyContinue
}

if ($failed -gt 0) { exit 1 }
Write-Host "Workflow script harness: $passed cases passed."
exit 0


