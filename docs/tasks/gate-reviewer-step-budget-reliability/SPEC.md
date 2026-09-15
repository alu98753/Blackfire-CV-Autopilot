# gate-reviewer-step-budget-reliability

Status: Final

## Goal

Prevent otherwise valid OpenCode Gate reviews from becoming `INFRASTRUCTURE_BLOCKED` solely because the configured reviewer tool-step ceiling is too small for a normal bounded review to reach its own canonical final response.

This task fixes the reviewer-budget contract. It does **not** make forced max-step output an acceptable verdict carrier and does not widen Gate parsing.

## Confirmed problem

A fresh `gate-payload-robustness-v1` Gate exposed the actual failure chain:

1. `spec-reviewer` was configured with `steps: 5`.
2. The reviewer consumed the available tool-step budget during an otherwise legitimate bounded review.
3. OpenCode entered forced max-step finalization.
4. The terminal text began with `Maximum steps for this agent have been reached...` and only later contained semantically plausible `VERDICT: PASS` / `BLOCKING_FINDINGS: 0` text.
5. That forced terminal response did not provide the normal completed structured assistant-message boundary required by the Gate contract.
6. Gate therefore correctly classified the attempt as infrastructure failure rather than salvaging a verdict from text.

Scout confirms both formal reviewers still use `steps: 5`, while their prompts simultaneously require grounded evidence gathering, early stopping, canonical verdict output, and `Never rely on forced max-step finalization.` Scout also reached its own six-step ceiling after completing six tool calls, reinforcing that a ceiling near five or six leaves effectively no operational headroom for tool-using repository inspection.

The defect is therefore a configuration/contract reliability mismatch, not a P1 parser/extractor defect.

## Expected behavior

A normal reviewer must have a finite budget large enough to inspect the mandatory supplied artifacts plus a small number of directly relevant repository/test paths and still voluntarily terminate with a canonical final response before OpenCode forces finalization.

The budget is a **ceiling, not a target**. Reviewers must continue to stop as soon as sufficient concrete evidence exists. Additional available steps do not authorize exhaustive traversal.

If a reviewer nevertheless reaches forced max-step finalization, that attempt remains an infrastructure failure. No verdict may be recovered from forced-finalization prose, partial output, tool results, or older messages.

## Final implementation scope

Required:

1. `.opencode/agents/spec-reviewer.md`
   - change `steps: 5` to `steps: 8`;
   - retain the bounded blocker-detector and early-stop contract;
   - make the voluntary-finalization requirement explicit: preserve enough remaining budget to stop tool use and emit the canonical verdict rather than treating the ceiling as an exploration allowance.

2. `.opencode/agents/regression-reviewer.md`
   - change `steps: 5` to `steps: 10`;
   - retain the bounded blocker-detector and early-stop contract;
   - make the same voluntary-finalization requirement explicit.

3. `docs/architecture/ai_development_workflow.md`
   - update the documented reviewer ceilings to match the actual configurations;
   - document that these values are finite ceilings with early-stop pressure, not expected consumption;
   - document that forced max-step finalization remains infrastructure failure and is never a verdict source.

4. `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
   - add lightweight deterministic contract/configuration assertions only if they fit the existing offline harness cleanly;
   - such assertions may verify the configured reviewer ceilings and the presence/consistency of the bounded/early-stop/never-forced-finalization contract;
   - do **not** attempt to fake OpenCode runtime max-step behavior as if that proved the transport behavior.

5. `docs/tasks/gate-reviewer-step-budget-reliability/`
   - normal task evidence/review artifacts.

### Explicitly outside implementation scope

`scripts/ai_gate.ps1` is not to be modified. Scout found no independent responsibility gap there: Gate already classifies malformed/non-canonical reviewer completion as infrastructure failure, which is the required behavior for forced max-step finalization.

## Budget decision and rationale

### `spec-reviewer`: `steps: 8`

Five is proven insufficient by the real P1 incident. The spec reviewer must consume the supplied task descriptor, canonical spec, status/diff snapshots, and may need focused reads/searches of changed code or tests. Eight provides three steps of headroom over the failed ceiling while remaining small enough to preserve the bounded-review architecture.

`8` is the **minimum adopted reliable ceiling for this workflow version**, not a claim that every review empirically requires eight calls. Repository evidence does not contain enough per-call telemetry to derive a mathematically exact minimum. The engineering basis is: a demonstrated failure at five, mandatory multi-artifact inspection, and bounded headroom for focused repository evidence plus voluntary finalization.

### `regression-reviewer`: `steps: 10`

The regression reviewer has a structurally broader evidence responsibility: relevant callers/callees, sibling paths, state ownership, lifecycle/timing/concurrency, tests, and architecture boundaries for the highest-risk reachable paths. It therefore receives two additional steps over the spec reviewer.

This difference is intentional. Equal budgets would ignore the roles' different evidence surfaces. Ten remains a tight finite ceiling and does not authorize distant or exhaustive traversal.

### Future calibration

These ceilings may be changed later only from accumulated real Gate telemetry/evidence. This task does not add adaptive budgets or dynamic step routing.

## Prompt / early-stop contract

Increasing the ceiling alone is necessary but not sufficient as a durable contract. Both reviewer prompts already contain the correct early-stop principle, so this task must **refine rather than redesign** it.

The prompt should make clear that:

- the configured step count is a maximum safety ceiling, not a coverage quota;
- once enough evidence exists for PASS or BLOCK, stop tool use immediately;
- prioritize mandatory supplied artifacts and highest-risk directly relevant paths;
- do not spend the last available exploration opportunity merely for confidence/coverage;
- voluntarily produce the canonical final response before forced max-step finalization;
- lack of exhaustive traversal is not itself a reason to BLOCK.

Do not introduce complex step accounting, per-file quotas, or a proof obligation that encourages the model to consume the entire ceiling.

## Hard invariants

1. Reviewers remain read-only bounded blocker detectors, not exhaustive proof engines.
2. PASS/BLOCK semantics and blocking-finding authority are unchanged.
3. P1 canonical payload grammar and structured-message completion rules are unchanged.
4. Forced max-step finalization remains `INFRASTRUCTURE_BLOCKED` / infrastructure failure when no normal canonical completed reviewer response exists.
5. Gate must not recover a verdict from forced-finalization text, partial output, tool results, older assistant messages, or other alternate carriers.
6. Canonical `reviews/*` and `EVIDENCE.md` preservation behavior on infrastructure failure is unchanged.
7. Model fallback remains an infrastructure-reliability mechanism. A valid semantic verdict is terminal; review-shopping remains forbidden.
8. No degraded automatic reviewer is added.
9. No timeout-policy change.
10. No production/game-code changes.
11. `scripts/ai_gate.ps1` remains unchanged in this task.
12. Reviewer configuration and `docs/architecture/ai_development_workflow.md` must describe the same ceilings and semantics.

## Non-goals

- changing Gate payload grammar or parser/extractor tolerance;
- recognizing `Maximum steps...` text as a new protocol signal or verdict envelope;
- salvaging verdicts from non-canonical output;
- changing PASS/BLOCK semantics;
- adding degraded automatic review fallback;
- changing review-model candidate order or fallback policy;
- adaptive/dynamic step budgets;
- changing reviewer or focused-test timeout policy;
- changing Scout behavior or Scout's step budget;
- modifying production/game code;
- solving general workflow orchestration or GitHub Actions automation.

## Deterministic validation

Offline deterministic validation must protect what the repository itself owns, without pretending to reproduce OpenCode runtime behavior.

Required checks:

1. Direct/config assertion that `spec-reviewer.md` declares `steps: 8`.
2. Direct/config assertion that `regression-reviewer.md` declares `steps: 10`.
3. Direct inspection or harness assertion that both reviewer contracts still contain bounded-review / early-stop / no-forced-finalization semantics.
4. Architecture-document inspection/assertion that documented ceilings and semantics match agent configuration.
5. Existing workflow harness behavior must remain passing if the harness is touched.

A deterministic fake reviewer that merely prints `Maximum steps...` cannot establish the real OpenCode structured-message boundary behavior and is therefore not required.

### Runtime validation

After implementation, run this task's normal Gate. A successful normal Gate is useful evidence that the new ceilings permit these reviewers to terminate canonically on a representative workflow patch.

After this task is merged, return to `gate-payload-robustness-v1` and rerun its fresh Gate. That downstream rerun is the decisive regression validation for the incident that motivated this task. It must not be replaced by parser widening here.

## Acceptance criteria

1. `spec-reviewer` is configured with `steps: 8`.
2. `regression-reviewer` is configured with `steps: 10`.
3. Both reviewers remain read-only bounded blocker detectors and retain explicit early-stop pressure.
4. Both contracts explicitly require voluntary canonical finalization before exhausting the ceiling; the ceiling is not presented as a target.
5. Architecture documentation matches the reviewer configurations and states that forced max-step finalization is infrastructure failure, not a verdict source.
6. No Gate parser/extractor, PASS/BLOCK, fallback, timeout, or evidence-promotion semantics change.
7. `scripts/ai_gate.ps1` is unchanged.
8. Any added offline harness assertions pass and test repository-owned configuration/contract facts rather than simulating OpenCode transport semantics.
9. The implementation contains no production/game-code changes.
10. The task's own Gate completes with canonical reviewer verdicts rather than forced max-step finalization.
11. After merge, `gate-payload-robustness-v1` is eligible for a fresh Gate rerun to confirm the original P1 blocker is removed.

## Required focused validation

Implementation writer should run only the smallest relevant checks:

- if `Invoke-WorkflowScriptHarness.ps1` is modified, run that offline harness through the repository's required Windows non-interactive `cmd.exe /d /s /c` wrapper;
- otherwise perform direct configuration/contract inspection plus the normal task Gate;
- do not run the repository full test suite.

## Regression risks

- **Over-budgeting:** a large ceiling could encourage exhaustive exploration. Mitigated by 8/10 finite ceilings plus strengthened early-stop wording.
- **Under-budgeting:** ceilings could still be reached on unusually broad diffs. This remains infrastructure failure by design; future evidence may justify recalibration.
- **Role flattening:** identical budgets would obscure the regression reviewer's broader reachable-path responsibility. Avoided by 8/10 split.
- **Contract drift:** docs and agent frontmatter can diverge. Deterministic config/contract assertions are preferred when cleanly supportable by the existing harness.
- **Parser regression:** treating forced output as valid would erase the structured-completion invariant. Explicitly forbidden.

## Forbidden shortcuts

- Do not solve this by accepting text after `Maximum steps for this agent have been reached...`.
- Do not search older messages/tool results/partial streams for a verdict.
- Do not modify `scripts/ai_gate.ps1` for this task.
- Do not raise budgets to a large arbitrary value to approximate unbounded review.
- Do not remove early-stop wording.
- Do not make reviewers exhaustive.
- Do not add automatic degraded review.
- Do not alter model fallback to obtain a more favorable semantic verdict.
- Do not edit P1 implementation as part of this task.

## Closeout dependency

This task is an urgent workflow-infrastructure unblocker for `gate-payload-robustness-v1`.

After this task is implemented, Gate-reviewed, semantically reviewed, and merged, do **not** start P2. Return to the original `gate-payload-robustness-v1` conversation/worktree and rerun its Gate under the merged reviewer-budget contract.
