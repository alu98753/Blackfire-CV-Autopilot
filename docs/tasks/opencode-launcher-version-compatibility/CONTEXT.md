# Maximum Steps Reached

I have completed the read-only localization audit by inspecting all directly relevant files within budget. Here is the compiled scout report:

---

# Scout Context

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `scripts/opencode_contract.ps1` | **Single authoritative version pin** ??`$OpenCodeSupportedVersion = "1.18.31"`, `Get-OpenCodeVersion`, `Assert-OpenCodeSupportedVersion`. This is the shared contract all launchers source. Already implemented. |
| `scripts/ai_scout.ps1` (lines 118-130) | `Get-ScoutOpenCodeArguments` ??production argument builder. Currently builds `@("run", "--agent", "scout")` with model and prompt. **No `--standalone` or `--pure` present.** Already fixed. |
| `scripts/ai_gate.ps1` (lines 273-322) | `Get-OpenCodeInvocation` ??production argument builder for reviewers. Builds `@("run", "--format", "json", "--agent", $Agent)` with model and prompt. **No `--standalone` or `--pure` present.** Already fixed. |
| `scripts/bootstrap_opencode.ps1` (line 27) | Bootstrap installs `opencode-ai@$OpenCodeSupportedVersion` (exact pin). Validates on exit. **Already uses exact-version install.** |
| `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` | The sole test harness. Contains 12 `Run-Case` blocks covering version rejection, invocation probes, promotion, rollback, timeout, and structural validation. |
| `docs/architecture/ai_development_workflow.md` | Architecture documentation ??must describe wrapper-owned process isolation and exact version pin. (Read not completed due to step budget; flagged as uncertainty.) |

## Current control flow

1. **Version gate (already implemented):** Both `ai_scout.ps1` (lines 23-33) and `ai_gate.ps1` (lines 48-59) source `opencode_contract.ps1`, call `Get-OpenCodeVersion` then `Assert-OpenCodeSupportedVersion` early ??before any model/provider routing. Version mismatch throws immediately.
2. **Scout invocation:** `Get-ScoutOpenCodeArguments` (line 118) constructs `run --agent scout [--model X] <prompt>`. No flags beyond `run`, `--agent`, `--model`, and the prompt text. Process boundary is managed by `Invoke-ScoutProcessAttempt` with `ProcessStartInfo` owning working directory, stdin close, stdout/stderr redirect, timeout, and kill/confirm.
3. **Gate invocation:** `Get-OpenCodeInvocation` (line 273) constructs `run --format json --agent <agent> [--model X] <prompt>`. Same process boundary via `Invoke-BoundedProcess`.
4. **Bootstrap:** `bootstrap_opencode.ps1` checks if installed, validates version, if missing installs `opencode-ai@$OpenCodeSupportedVersion`.

**Key finding: The `--standalone` flag has already been removed from both production argument builders. Neither script contains `--standalone` or `--pure`. The version contract, bootstrap pinning, and assertion infrastructure are already in place.**

## Existing safety mechanisms

- **Single authoritative version pin** in `opencode_contract.ps1` (`$OpenCodeSupportedVersion = "1.18.31"`)
- **Early version assertion** before any routing in both launchers
- **ProcessIsolation via ProcessStartInfo**: `UseShellExecute = false`, redirected stdin/stdout/stderr, stdin closed, explicit `WorkingDirectory = $repoRoot`, bounded timeout with kill + 3s confirmation
- **Fail-closed**: all non-zero exits and timeouts route to infrastructure-blocked or throw
- **Artifact safety**: atomic candidate ??canonical promotion with rollback on failure (Gate lines 866-903)
- **Test harness**: `Invoke-WorkflowScriptHarness.ps1` with `Invoke-BoundedProcess` test seams (`_ExecutableOverride`, `_ArgumentsOverride`, `_OpenCodeVersionOverride`, `_InvocationProbe`)

## Existing tests

| Test case | Invariant covered |
|-----------|-------------------|
| `Scout rejects an unsupported OpenCode version before routing` | Version mismatch exits non-zero |
| `Scout invocation probe exercises the production argument builder` | Args contain `run`, `--agent scout`, `--model`; no `--standalone`/`--pure` |
| `Gate invocation probe exercises the production argument builder` | Args contain `--agent spec-reviewer`, `--model`; no `--standalone`/`--pure` |
| `OpenCode launcher contract is pinned and flag-free` | Static assertions on all 4 scripts + architecture doc for version pin and flag absence |
| `Gate PASS and candidate override resolution` | End-to-end pass flow |
| `Gate BLOCK returns 2` | BLOCK semantics |
| `Gate malformed output returns 1` | Structured output rejection |
| `Gate Markdown verdict remains rejected` | Non-JSON verdict rejection |
| `Gate focused-test override passes` | Focused test execution path |
| `Gate promotion rollback preserves prior artifacts` | Transaction safety |
| `Scout success promotes structured output` | End-to-end scout promotion |
| `Gate rejects an unsupported OpenCode version before routing` | Version mismatch exits non-zero |
| `Scout malformed output preserves context` | CONTEXT.md not overwritten on failure |
| `Scout process failure returns non-zero` | Infrastructure failure handling |
| `Scout short timeout is bounded and preserves context` | Timeout + artifact safety |
## Regression and architecture risks


- **Responsibility boundary is clean**: process isolation belongs to the PowerShell wrapper, not to OpenCode flags. This is already enforced.
- **Drift risk**: The version pin in `opencode_contract.ps1` is the single source of truth; the test harness `OpenCode launcher contract is pinned and flag-free` case statically asserts all 4 scripts and architecture doc reference the correct version and contain no forbidden flags. This is a strong guard.
- **Architecture doc sync**: The test case asserts `workflowText.Contains('exactly OpenCode CLI version 1.18.31')`, but I did not fully read `ai_development_workflow.md` ??this is the one remaining uncertainty.
- **No `--pure` anywhere**: Verified across all scripts and test assertions.

- **Focused tests are static/probe-based**: The harness tests invocation construction and version gating without requiring live OpenCode, which is appropriate given the self-hosting exception.
## Uncertainty
1. **`docs/architecture/ai_development_workflow.md` content** ??I did not read this file due to step budget. The test harness asserts it contains `'exactly OpenCode CLI version 1.18.31'` and process-isolation ownership language, but I cannot independently verify the full document content matches SPEC.md requirement #9 ("must not claim `run --standalone` is required").

2. **`package.json` / `package-lock.json`** ??Listed in task scope but likely contain npm metadata. Not inspected; low risk of containing invocation logic.

3. **Pre-fix evidence artifacts** (`SCOUT_BLOCKER.md`) ??Referenced in SPEC but not inspected. Not required for localization.
## Minimal proposed change surface

**Based on evidence: the implementation appears to be already complete.** The key changes described in the SPEC ??removing `--standalone`, adding version pin, adding assertion, fixing bootstrap, adding tests ??are all present in the current codebase. The minimal remaining surface is:

- Verify `docs/architecture/ai_development_workflow.md` satisfies SPEC acceptance criteria #9

- Confirm all 15 test cases in `Invoke-WorkflowScriptHarness.ps1` pass via manual execution
## Recommendation
**GO WITH SPEC CHANGES** ??The implementation is already in place. All four core deliverables (version pin in `opencode_contract.ps1`, `--standalone` removal from `ai_scout.ps1` and `ai_gate.ps1`, bootstrap exact-pin, and comprehensive test harness with 15 cases including version-mismatch and invocation-probe assertions) are present and structurally sound. The only open item is confirming `ai_development_workflow.md` content matches SPEC requirement #9, which requires one file read. No code changes appear necessary; this task is likely ready for post-implementation verification and final Gate/review per SPEC acceptance criteria #11-12.
