Now let me check the workflow test harness and confirm `ai_gate.ps1` boundaries:
# Scout Context ??gate-reviewer-step-budget-reliability

**Maximum steps reached.** All six tool calls were completed before the step limit was hit.

## Relevant files and symbols

1. **`docs/tasks/gate-reviewer-step-budget-reliability/task.json`** ??Defines scope: both reviewer agent files, architecture doc, workflow test harness, and the task's own directory.
2. **`.opencode/agents/spec-reviewer.md`** ??The primary file to change. Line 4: `steps: 5`. Prompt body (lines 41-88) instructs early-stop, read-only bounded detection, 300-600 word PASS output target, and mandatory two-line verdict header. This is where the budget mismatch lives.
3. **`.opencode/agents/regression-reviewer.md`** ??Identical structure. Line 4: `steps: 5`. Same early-stop + bounded-detector contract. Same vulnerability to max-step finalization under realistic workload.
4. **`docs/architecture/ai_development_workflow.md`** ??Lines 160-164: Architecture doc codifies "initial `steps: 5`" for both reviewers. Must be updated to stay consistent with any agent file change (invariant #5 in SPEC).
5. **`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`** ??134-line PowerShell test harness. Already tests gate exit codes (0/1/2), malformed output rejection, markdown verdict rejection, focus-test pass, promotion rollback, scout success/failure/timeout. Does NOT currently test reviewer step-budget behavior or max-step finalization scenarios.
6. **`scripts/ai_gate.ps1`** ??Confirmed: timeout is 480s per reviewer. No code references to "max step" or "finalization" ??the gate detects infrastructure failure via process timeout/unconfirmed termination/malformed output/invalid verdict structure. The "max-step finalization" problem is an OpenCode runtime behavior that produces text starting with "Maximum steps..." without a structured assistant-message boundary, causing the gate's structured-extraction to fail and classify as INFRASTRUCTURE_BLOCKED.

## Current control flow

The problematic path:
1. `ai_gate.ps1` launches OpenCode with `spec-reviewer.md` (configured `steps: 5`).
2. OpenCode allocates 5 tool-call steps. The reviewer performs read/glob/grep operations.
3. If 5 steps are exhausted before producing the final VERDICT response, OpenCode forces max-step finalization.
4. The forced response is a text-only message (no structured assistant-message boundary), beginning with "Maximum steps for this agent have been reached..."
5. `ai_gate.ps1` extracts structured output ??extraction fails (no valid VERDICT header in the expected format) ??classified as infrastructure failure ??exit code 1.
6. Even though the reviewer may have semantically completed its review in the forced text, the gate cannot parse it.

## Existing safety mechanisms

- Both reviewer prompts already instruct early stopping (line 46 in spec-reviewer, line 46 in regression-reviewer).
- Gate has robust verdict parsing with contract-violation detection (PASS/BLOCK consistency checks).
- Gate preserves canonical `reviews/*` and `EVIDENCE.md` on infrastructure failure.
- Model fallback chain exists for infrastructure failures (but max-step finalization produces invalid structure, so fallback triggers ??review-shopping risk if not handled carefully).
- Workflow test harness covers gate exit codes and malformed output but NOT step-budget exhaustion scenarios.

## Existing tests

`Invoke-WorkflowScriptHarness.ps1` covers:
- Gate PASS/BLOCK/malformed/markdown verdict ??correct exit codes
- Focused test pass-through
- Promotion rollback preservation
- Scout success/malformed/timeout/short-timeout

**Gap:** No test exercises reviewer step-budget exhaustion or max-step finalization detection.

## Regression and architecture risks
- **Consistency risk:** Architecture doc (line 160-164) hardcodes "initial `steps: 5`". If agent files change budget but doc is missed, invariant #5 is violated.
- **Budget justification:** No evidence in repo for what step count is actually sufficient. SPEC uncertainty #2 explicitly flags this.

- **Inequality risk:** `spec-reviewer` reads task.json + SPEC.md + diff + repo files ??potentially more tool calls than `regression-reviewer`. SPEC uncertainty #3 asks whether budgets should differ.
- **Fallback chain interaction:** If max-step is still hit after budget increase, fallback triggers ??potential review-shopping if the fallback model produces a valid but unearned PASS.

- **Early-stop tension:** Increasing budget without refining prompt efficiency may just delay the problem rather than solve it. Prompt already says "stop using tools as soon as enough concrete evidence exists."
## Uncertainty
1. **Empirical step consumption:** No logged data in repo showing actual tool-call counts per reviewer invocation. The budget increase is hypothesis-driven, not evidence-driven.

2. **OpenCode max-step signal:** Unknown whether OpenCode exposes a stable exit code or structured signal for max-step finalization. SPEC uncertainty #5 flags this. The gate would need to observe this to avoid false infrastructure classification if a valid verdict IS present in the forced text.
3. **Prompt efficiency vs. budget:** Cannot determine from static analysis whether the reviewer prompts are inefficiently consuming steps (e.g., redundant reads) or whether the workload genuinely requires more steps.
4. **Test harness coverage limit:** The harness uses `fake-reviewer.ps1` stubs that exit with pre-baked verdicts; it cannot realistically simulate step-budget exhaustion through OpenCode's runtime.

## Minimal proposed change surface

1. **`.opencode/agents/spec-reviewer.md`** ??Line 4: increase `steps` value. Possibly minor prompt wording adjustments.
2. **`.opencode/agents/regression-reviewer.md`** ??Line 4: increase `steps` value (possibly different value). Possibly minor prompt wording adjustments.
3. **`docs/architecture/ai_development_workflow.md`** ??Lines 160, 164: update "initial `steps: 5`" to match new values.

4. **Possibly** `Invoke-WorkflowScriptHarness.ps1` if deterministic regression coverage is warranted (SPEC provisional scope mentions this as conditional).
## Recommendation

**GO WITH SPEC CHANGES**

The core problem is well-defined and localized: `steps: 5` in two agent markdown files and corresponding architecture doc is insufficient for realistic reviewer workloads. The fix surface is tiny (3 lines of `steps:` + doc consistency). However:
- The SPEC should explicitly require **empirical justification** for the chosen budget (e.g., cite a real reviewer run's step count) rather than picking an arbitrary higher number.
- The SPEC should clarify whether the two reviewers should share the same budget or receive independent values.
- Consider adding a note that the architecture doc must stay in sync with agent files (currently only implicit).
- The test harness gap is acceptable for v1 since step-budget behavior is an OpenCode runtime concern that cannot be realistically mocked in the existing stub-based harness.
