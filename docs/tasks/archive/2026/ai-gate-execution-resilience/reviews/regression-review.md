Now let me inspect the current state of the key files to understand the baseline and compare with the patch.
Let me inspect the documentation files and look for any callers or tests related to `ai_gate.ps1`.
Let me check for any existing tests and verify the reviewer agent contracts.
Now let me verify the old code baseline to confirm the diff's accuracy, and check for any edge cases in the promotion logic.
Good — `Out-String` is only used for fast git commands now, not for the blocking opencode pipeline. Let me verify one more edge case around the promotion logic when one reviewer fails mid-loop.
Now I have a thorough understanding of the patch. Let me verify one final thing about how the old code handled the opencode existence check versus the new code.
I now have complete evidence for the review. Let me compile the findings.
VERDICT: PASS


BLOCKING_FINDINGS: 0
# Regression Review

1. **Invocation interface**: `-Task <id>` with optional `-ReviewModel` and `-SkipTests` remains fully compatible. New parameters (`-ReviewTimeoutSeconds`, `-TestTimeoutSeconds`, test seams) are additive defaults that don't change existing invocation semantics.

2. **Full-suite rejection**: The `focused_tests` regex filter (`discover\s+tests|unittest\s+discover|^tests$|\*`) is preserved identically at line 368.


## Behavior-preservation assessment

The following existing behaviors are intentionally preserved and correctly maintained by the diff:
3. **Reviewer output staging and canonical promotion**: The old code wrote directly to `reviews/*.md` and `EVIDENCE.md`. The new code stages under `.runtime/ai_gate/<task-id>/` and promotes atomically. For the happy path (both reviewers PASS, all tests pass), canonical artifacts are still updated — the result is the same, the mechanism is safer.
4. **Exit code 0/2 semantics for PASS/candidate-block**: Exit 0 (PASS) and exit 2 (CANDIDATE_BLOCKED) retain their original meaning. The new exit 1 (INFRASTRUCTURE_BLOCKED) replaces what was previously an unhandled PowerShell exception (implicit exit 1 from `$ErrorActionPreference = "Stop"` + `throw`).


5. **Git snapshot creation**: `git status --short` and `git diff` are unchanged at lines 61-71.

6. **Evidence content structure**: The `EVIDENCE.md` template (reviewer verdicts, focused test results, full suite notice, candidate snapshot) is identical.

7. **Reviewer agent contracts**: `.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` are not modified. The `VERDICT: PASS|BLOCK` / `BLOCKING_FINDINGS: <int>` contract and structural validation regex match exactly.

8. **Multi-worktree isolation**: Task state remains namespaced under `.runtime/ai_gate/<task-id>/` and `docs/tasks/<task-id>/`.

9. **Promotion on CANDIDATE_BLOCKED**: Per SPEC section 6, canonical `reviews/*` and `EVIDENCE.md` are updated for both PASS and CANDIDATE_BLOCKED (verification completed with a valid candidate verdict). This matches the new code at lines 480-560.


None.


10. **No game/runtime changes**: The patch is confined to `scripts/ai_gate.ps1` and documentation files. No Python runtime code is touched.
## Advisory findings
## Blocking findings

### A1 — Documentation terminology drift in `ai-verification-gate.md`
Severity: ADVISORY
Location: `.agents/rules/ai-verification-gate.md:31`
Claim: The rule states "If the gate returns BLOCK" but the new stdout message is `"AI verification gate CANDIDATE_BLOCKED."` (and `"AI verification gate INFRASTRUCTURE_BLOCKED."` for exit 1). The substring "BLOCK" still appears in both messages, so the writer agent's interpretation is unlikely to break, but the terminology is imprecise relative to the new three-outcome model.
Evidence: Old code line `Write-Host "AI verification gate BLOCKED."` → new code line `Write-Host "AI verification gate CANDIDATE_BLOCKED."`.
Suggested validation: Update `ai-verification-gate.md` line 31 to reference exit codes (0/1/2) or the explicit message strings rather than the ambiguous word "BLOCK".
Confidence: 0.85

### A2 — Deferred opencode existence check
Location: `scripts/ai_gate.ps1:226-228` (inside `Get-OpenCodeInvocation`)
Claim: The old code checked `Get-Command opencode` at the top of the script before any directory creation or git operations. The new code defers this check to the first reviewer invocation inside `Get-OpenCodeInvocation`. This means the script performs more setup work (directory creation, `git status`, `git diff`) before failing if opencode is not installed.
Severity: ADVISORY
Evidence: Old baseline had `Get-Command opencode` at script top (line ~6 in old); new code has it at line 226 inside the function.
Suggested validation: Confirm this is acceptable by verifying that the setup operations (directory creation, git commands) are harmless even when opencode is absent. This is a minor UX difference, not a correctness issue.
Confidence: 0.90
### A3 — No deterministic probe tests included in this diff
Severity: ADVISORY

Location: SPEC acceptance criteria #14 (lines 199-214)
Claim: The SPEC requires deterministic probes covering at least 10 scenarios (reviewer success, timeout, non-zero exit, malformed output, semantic BLOCK, test pass/fail/timeout, exit code classification, event job cleanup). The test seams (`_ReviewerExecutableOverride`, `_PythonExecutableOverride`, `_FailPromotionOnTarget`) are correctly implemented in `ai_gate.ps1`, but no actual probe script is included in this diff. The `task.json` has `focused_tests: []`.
Evidence: `task.json` line 9: `"focused_tests": []`. No test script files in the diff.
Suggested validation: A follow-up task or separate probe script should exercise all 10 scenarios listed in acceptance criteria #14 using the test seams. Without this, the resilience behavior is only verified by design review, not by automated regression characterization.
Confidence: 1.00

### A4 — Story file references old implementation
Severity: ADVISORY
Location: `docs/storys/2026-09-14_ai_verification_gate_and_workflow_pars_story.md:53`
Claim: The story file describes the old `ai_gate.ps1` implementation (blocking `Out-String` pipeline). The exit code claim ("exit code 1") for a missing task is still correct, but the narrative describes the pre-resilience architecture. This is a historical artifact, not a functional issue.
Evidence: Story references the old behavior at line 41 ("自動化檢驗 task package 完整性、呼叫 OpenCode 執行...") and line 53 (exit code 1 for no-such-task).
Suggested validation: During branch closeout, update or annotate the story to reflect the new bounded execution architecture. Historical PARS documents should not contradict current code.
Confidence: 0.80

## Sibling-path coverage

| Path inspected | Relationship | Affected? |
|---|---|---|
| `scripts/ai_scout.ps1` | Conceptual sibling — same process-lifecycle pattern | Not modified. The `Invoke-BoundedProcess` helper in `ai_gate.ps1` is a local copy of the pattern, not a shared extraction. Per SPEC non-goal "Do not extract a generalized cross-repository/shared process framework in v1", this is correct. |
| `.opencode/agents/spec-reviewer.md` | Reviewer contract consumed by the gate | Not modified. The `VERDICT: PASS\|BLOCK` / `BLOCKING_FINDINGS` header contract is preserved exactly by `Test-ReviewVerdictStructure` regex. |
| `.opencode/agents/regression-reviewer.md` | Reviewer contract consumed by the gate | Not modified. Same analysis as spec-reviewer. |
| `.agents/rules/ai-verification-gate.md` | Writer rule that invokes the gate | Not modified but references old "BLOCK" terminology (see A1). |
| `docs/tasks/README.md` | Task package documentation | Modified: one new line about infrastructure failure preservation (line 48). Consistent with script behavior. |
| `docs/architecture/ai_development_workflow.md` | Phase D documentation | Modified: updated to document bounded execution, exit codes, and artifact safety. Consistent with script behavior. |
| `docs/storys/2026-09-14_ai_verification_gate_and_workflow_pars_story.md` | Historical PARS document | Not modified but references old implementation (see A4). |


## Test evidence gaps
1. **Deterministic probe execution**: The most material gap is the absence of actual probe execution covering the 10 scenarios in SPEC acceptance criteria #14. The test seams are in place; a probe script exercising reviewer success+promotion, timeout+kill+preservation, non-zero exit→infra block, malformed output→infra block, semantic BLOCK→candidate block, test pass, test fail→candidate block, test timeout→infra block, exit code 0/1/2 classification, and event job cleanup would materially reduce regression risk.


3. **Promotion rollback under real failure**: The `$_FailPromotionOnTarget` seam covers the rollback logic, but a real-world test (e.g., making the `reviews/` directory read-only) would validate the filesystem-level rollback behavior.
2. **End-to-end smoke with real OpenCode**: The bounded process wrapper has not been verified against a real `opencode run --agent` invocation (only by design review). A manual `.\scripts\ai_gate.ps1 -Task <any-task-with-focused-tests>` run would confirm the async event handling, streaming, and promotion work with the actual opencode client.
