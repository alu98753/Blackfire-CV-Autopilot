VERDICT: PASS
BLOCKING_FINDINGS: 0

# Regression Review

## Behavior-preservation assessment

The patch implements exactly the two must-fixes from `IMPLEMENTATION_REVIEW.md` plus the Final SPEC, with no scope drift:

- **`--standalone` removal (intended behavior change):** `scripts/ai_scout.ps1` `Get-ScoutOpenCodeArguments` (lines 118??30) and `scripts/ai_gate.ps1` `Get-OpenCodeInvocation` (lines 273??22) no longer emit `--standalone`; `--pure` is nowhere introduced. The remaining arguments (`run`, `--agent`, `--model`, prompt, `--format json` in gate) are unchanged, so agent/model/prompt/review semantics are preserved.
- **Process-safety invariants (SPEC #8) preserved:** Scout's `Invoke-ScoutProcessAttempt` still owns `WorkingDirectory = $repoRoot`, `UseShellExecute = false`, redirected stdio, closed stdin (`$proc.StandardInput.Close()`, line 212), bounded timeout, kill + 3s confirmation, and fail-closed handling ??untouched. Gate's `Invoke-BoundedProcess`, streaming, structured-output validation, and promotion/rollback paths are unmodified.
- **Version gate is new and pre-routing:** both launchers assert the exact 1.18.31 pin (scout lines 27??3 before `$candidates`; gate lines 48??9 before `$normalCandidates`), satisfying acceptance #7. Fail-closed on missing/unsupported/misbehaving CLI via `Get-OpenCodeVersion`/`Assert-OpenCodeSupportedVersion`.
- **Bootstrap:** accepts installed 1.18.31, throws actionable exact-version remediation on mismatch, installs exactly `opencode-ai@$OpenCodeSupportedVersion`; the only version literal is the single authoritative `$OpenCodeSupportedVersion = "1.18.31"` in `scripts/opencode_contract.ps1` (acceptance #1, #2).
- **Test seams preserved:** all existing harness cases using `_ExecutableOverride`/`_ReviewerExecutableOverride` skip the real version check (only real-process path asserts the installed CLI), and the fake-reviewer arg matching does not depend on the removed token. PRE_GATE_EVIDENCE records 16/16 harness cases passing, and the self-hosting scout reached model execution under the new path.
- **Architecture doc:** both edited paragraphs describe wrapper-owned isolation + exact 1.18.31 and do not claim `run --standalone` is required; the only `--standalone` mention is the explicit "not part of the production launcher contract" statement (line 231). Harness statically asserts this.

## Blocking findings

None.

## Advisory findings

1. **Probe tests are environment-coupled by design:** `Scout/Gate invocation probe` cases run the real version assertion against the installed CLI (no override), so they fail if the runner's opencode is missing or not 1.18.31. This matches acceptance #6's intent (real production contract), but the "deterministic" harness now has an implicit environment precondition not stated in the harness; PRE_GATE_EVIDENCE documents it is currently satisfied.
2. **`Get-OpenCodeVersion` executes the resolved command directly** without the `.ps1`-shim wrapper that the invocation builders use (`$cmdInfo.Source -like "*.ps1"`). If `Get-Command opencode` ever resolved to an npm PowerShell shim using `exit`, the version probe could terminate the caller session; empirically this does not occur in the current environment (the gate that produced this snapshot ran the real version check successfully).
3. **Stale historical claims elsewhere:** task docs outside scope (`agent-role-contract-hardening-v1-1`, `agent-model-fallback-routing-v1-1`) still describe `run --standalone` as required. These are archived task records, not the live contract; the operative architecture doc and production scripts are consistent. `CONTEXT.md` stating "15 cases" is stale (harness has 16) ??cosmetic only.
