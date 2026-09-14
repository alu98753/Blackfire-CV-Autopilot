# AI Gate Execution Resilience

Status: Draft

## Goal

Make `scripts/ai_gate.ps1` a bounded, observable, artifact-safe verification orchestrator so a hung OpenCode reviewer or focused test cannot block the task workflow indefinitely.

The gate must distinguish candidate verification outcomes from infrastructure/execution failures. A reviewer `BLOCK` is evidence about the candidate; a reviewer/test process timeout, crash, malformed output, or termination failure is an infrastructure failure and must not masquerade as either PASS or semantic BLOCK.

## Observed problem

A real `scout-efficiency-v1` gate run exposed the current failure mode: the first `spec-reviewer` OpenCode client remained running for roughly 27 minutes with no useful terminal output until manually terminated. Current `Invoke-ReviewAgent` executes `opencode` through a blocking `Out-String` pipeline with no wrapper-enforced timeout.

The same gate script also runs configured focused tests through a blocking external-process invocation without a timeout. Therefore bounding reviewers alone would not make the complete gate execution bounded.

## Initial scope

Primary likely change surface:

- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` only if user-facing gate execution/failure semantics need documentation

A small script-level deterministic verification seam may be added to exercise reviewer/test process success, timeout, non-zero exit, streaming, and artifact-preservation behavior without real long-running model/test calls.

Reviewer prompt semantics under `.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` are not expected to change unless Scout finds a direct execution-contract reason.

No game/runtime behavior may change.

## Known invariants

1. `spec-reviewer` and `regression-reviewer` remain read-only independent reviewers.
2. Reviewer semantic contract remains `VERDICT: PASS|BLOCK` plus `BLOCKING_FINDINGS`.
3. A semantic reviewer `BLOCK` must remain distinguishable from reviewer infrastructure failure.
4. Gate infrastructure failure must never be reported as PASS.
5. Timeout, non-zero process exit, malformed/incomplete reviewer output, or unconfirmed process termination must not overwrite a previously valid canonical `reviews/*.md` with partial output.
6. `EVIDENCE.md` must not claim complete successful verification if one required reviewer/test execution failed at the infrastructure layer.
7. User-visible terminal progress must improve; long-running child processes must not remain opaque until completion.
8. Timeout/termination must target only the child process launched by the gate and must not kill the persistent `opencode serve` service.
9. The gate must continue to reject obvious full-suite test targets and must never run the repository full suite automatically.
10. Existing normal invocation `./scripts/ai_gate.ps1 -Task <id>` remains valid.
11. Multi-worktree/task-id isolation under `.runtime/ai_gate/<task-id>/` remains intact.
12. This task must not change reviewer findings merely to make a candidate pass.

## Provisional target behavior

### Reviewer execution

Each OpenCode reviewer should run through a bounded child-process wrapper that provides:

- real-time stdout/stderr visibility;
- a hard wall-clock timeout;
- client-only termination on timeout;
- confirmed child exit or explicit termination-failure reporting;
- candidate output staged outside canonical `reviews/*.md`;
- canonical review promotion only after successful process exit and minimal reviewer-structure validation.

A default reviewer timeout around 8 minutes is provisional pending Scout/local evidence. The two reviewers are sequential in v1; no parallel-review redesign is required.

### Focused-test execution

Configured focused tests are also child processes and must not remain unbounded.

The smallest acceptable v1 behavior is:

- per-focused-test wall-clock timeout with a sensible default/override seam;
- live or sufficiently observable test output;
- timeout/non-zero exit recorded as test failure/infrastructure evidence without hanging the gate;
- no expansion into a new test framework.

Exact timeout values and public parameter shape remain provisional until Scout confirms nearby conventions and simplest implementation.

### Failure classification

The gate should make at least these states unambiguous to humans and automation:

1. `PASS` — both reviewers validly PASS and required focused tests pass.
2. `CANDIDATE_BLOCKED` — one or more valid reviewer reports return semantic BLOCK, or a focused test completes and fails.
3. `INFRASTRUCTURE_BLOCKED` — a required reviewer/test cannot complete validly because of timeout, process-launch failure, non-reviewer process failure, malformed reviewer output, or unconfirmed termination.

The exact exit-code mapping is provisional. Scout must inspect existing callers before Final SPEC chooses whether to preserve exit `2` for all blocked states or introduce a distinct non-zero code for infrastructure failure.

### Artifact safety

Canonical artifacts must be success/validity gated:

- `reviews/spec-review.md`
- `reviews/regression-review.md`
- `EVIDENCE.md`

Partial reviewer stdout/stderr and diagnostics belong under ignored `.runtime/ai_gate/<task-id>/` state.

A failed rerun must not silently destroy a previously valid canonical review report. `EVIDENCE.md` may be updated to describe an incomplete/infrastructure-blocked verification attempt only if its semantics are explicit and cannot be mistaken for completed verification; otherwise preserve the previous canonical evidence and emit runtime diagnostics.

This exact `EVIDENCE.md` policy is intentionally open for Scout evidence because current downstream closeout behavior must be checked before deciding.

## Provisional acceptance criteria

1. Both reviewer invocations have a real wrapper-enforced timeout and real-time terminal visibility.
2. A completely silent reviewer child cannot block the gate beyond its configured timeout.
3. Reviewer timeout kills only the launched client process and does not kill persistent OpenCode service state.
4. Timeout/non-zero/malformed reviewer execution cannot replace a valid canonical review report with partial content.
5. Valid reviewer `BLOCK` remains a semantic candidate result, not an infrastructure error.
6. Focused-test child execution is also bounded; a silent/hung focused test cannot hang the gate indefinitely.
7. The gate produces an explicit machine/human-visible distinction between candidate blocking and infrastructure blocking.
8. `EVIDENCE.md` semantics cannot claim complete verification when required reviewer/test execution was infrastructure-blocked.
9. Existing `-Task <id>` usage remains compatible.
10. Full-suite policy is unchanged.
11. Deterministic focused probes cover at least reviewer success, silent reviewer timeout, reviewer non-zero/malformed output, canonical review preservation, focused-test timeout, and failure classification.
12. No production/game behavior changes.

## Non-goals

- Do not redesign reviewer semantic responsibilities.
- Do not add autonomous repair/retry loops.
- Do not parallelize reviewers in v1.
- Do not introduce queues, background services, dashboards, or distributed orchestration.
- Do not run or automate the full test suite.
- Do not change production/game code.
- Do not start `intent-routing-observability` in this task.
- Do not extract a generalized repository-wide process framework unless Scout proves duplication already warrants it; local/simple implementation is preferred in v1.
- Do not solve hangs by only increasing timeout values.

## Uncertainty / Scout questions

Before this spec becomes Final, Scout/local evidence should answer:

1. Which existing scripts/callers depend on `ai_gate.ps1` exit code `0`/`2`, and can infrastructure failure safely use a distinct exit code?
2. Should `EVIDENCE.md` be replaced on an infrastructure-blocked rerun with an explicit incomplete-verification report, or should the last valid canonical evidence remain untouched while failure diagnostics stay under `.runtime/`?
3. What is the smallest safe reviewer structural validation beyond process exit 0 — only verdict header, or additional required headings/count consistency?
4. What reviewer timeout is appropriate by default given the newly bounded Scout path and observed 27-minute hang?
5. What per-focused-test timeout/default override is appropriate without creating unnecessary configuration surface?
6. Can the proven `ai_scout.ps1` async process pattern be reused locally inside `ai_gate.ps1` without prematurely extracting a shared helper?
7. Are focused tests expected to stream output for user observability, or is bounded execution plus per-test runtime log sufficient?
8. What deterministic PowerShell probe strategy best verifies these behaviors without invoking real OpenCode/model calls or long-running tests?
