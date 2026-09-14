# AI Gate Execution Resilience

Status: Final

## Goal

Make `scripts/ai_gate.ps1` a bounded, observable, artifact-safe verification orchestrator so a hung OpenCode reviewer or focused test cannot block the task workflow indefinitely.

The gate must distinguish candidate verification outcomes from infrastructure/execution failures. A reviewer `BLOCK` or completed focused-test failure is evidence about the candidate; a reviewer/test timeout, launch failure, malformed reviewer payload, or unconfirmed termination is an infrastructure failure and must not masquerade as either PASS or semantic BLOCK.

## Observed problem

A real `scout-efficiency-v1` gate run exposed the current failure mode: the first `spec-reviewer` OpenCode client remained running for roughly 27 minutes with no useful terminal output until manually terminated. Current `Invoke-ReviewAgent` executes `opencode` through a blocking `Out-String` pipeline with no wrapper-enforced timeout.

The same gate script also runs configured focused tests through a blocking external-process invocation without a timeout. Therefore bounding reviewers alone would not make the complete gate execution bounded.

A subsequent Scout run for this task itself hit the newly enforced 480-second Scout timeout and terminated safely, confirming that bounded orchestration is necessary for all external model/test child execution.

## Scope

Primary change surface:

- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` only where user-facing gate execution/failure semantics need documentation

A small deterministic script-level verification seam may be added to exercise reviewer/test process success, timeout, non-zero exit, malformed output, streaming, and artifact-preservation behavior without live long-running model/test calls.

Reviewer semantic contracts under `.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` are not changed by this task unless a strictly execution-related compatibility fix is required.

No game/runtime behavior may change.

## Known invariants

1. `spec-reviewer` and `regression-reviewer` remain read-only independent reviewers.
2. Reviewer semantic contract remains `VERDICT: PASS|BLOCK` plus `BLOCKING_FINDINGS`.
3. A semantic reviewer `BLOCK` must remain distinguishable from reviewer infrastructure failure.
4. Gate infrastructure failure must never be reported as PASS or candidate semantic BLOCK.
5. Timeout, non-zero process exit, malformed/incomplete reviewer output, or unconfirmed process termination must not overwrite a previously valid canonical `reviews/*.md` with partial output.
6. `EVIDENCE.md` must not claim complete verification if any required reviewer/test execution failed at the infrastructure layer.
7. Long-running reviewer execution must be user-observable from the terminal.
8. Timeout/termination must target only the launched child process and must not kill the persistent `opencode serve` service.
9. The gate must continue to reject obvious full-suite test targets and must never run the repository full suite automatically.
10. Existing normal invocation `./scripts/ai_gate.ps1 -Task <id>` remains valid.
11. Multi-worktree/task-id isolation under `.runtime/ai_gate/<task-id>/` remains intact.
12. This task must not change reviewer findings merely to make a candidate pass.

## Target behavior

### 1. Reviewer execution

Each OpenCode reviewer must run through a bounded child-process wrapper that provides:

- real-time stdout/stderr visibility;
- hard wall-clock timeout;
- client-only termination on timeout;
- confirmed child exit or explicit termination-failure reporting;
- candidate output staged outside canonical `reviews/*.md`;
- canonical review promotion only after successful process exit and minimal structural validation.

Default reviewer timeout: **480 seconds per reviewer**.

The two reviewers remain sequential in v1. With defaults, the reviewer phase therefore has a nominal upper bound of approximately 16 minutes plus small cleanup overhead.

Provide a simple timeout override seam suitable for deterministic probes and local diagnosis. Existing `-Task <id>` usage must remain unchanged.

### 2. Reviewer structural validation

A reviewer process exit code of 0 is necessary but not sufficient for canonical promotion.

Minimal validation:

1. output is non-empty after trimming;
2. contains `VERDICT: PASS|BLOCK`;
3. contains `BLOCKING_FINDINGS: <integer>`;
4. `PASS` requires `BLOCKING_FINDINGS: 0`;
5. `BLOCK` requires `BLOCKING_FINDINGS >= 1`.

Do not parse every natural-language finding field with brittle regexes. Detailed prose remains reviewer evidence for later inspection.

Malformed reviewer output is an infrastructure failure, not a semantic candidate block.

### 3. Focused-test execution

Every configured focused test is also a bounded child process.

Default per-focused-test timeout: **60 seconds**.

This is a workflow default, not a claim that all valid focused tests objectively finish within 60 seconds. The script must support an override seam for legitimate slower focused tests or deterministic probes.

Focused-test requirements:

- hard per-test wall-clock timeout;
- client-only termination on timeout;
- confirmed termination or explicit infrastructure failure;
- stdout/stderr captured to `.runtime/ai_gate/<task-id>/test-*.log`;
- clear terminal status at start/completion including result, elapsed time, and log path;
- no requirement for line-by-line test streaming in v1;
- no expansion into a new test framework.

A focused test that **completes normally and exits non-zero** is a candidate verification failure (`CANDIDATE_BLOCKED`).

A focused test that **cannot complete validly because of timeout, launch failure, or unconfirmed termination** is `INFRASTRUCTURE_BLOCKED`.

### 4. Failure classification and exit codes

The gate has three externally meaningful terminal outcomes:

- `PASS` → exit **0**
- `CANDIDATE_BLOCKED` → exit **2**
- `INFRASTRUCTURE_BLOCKED` → exit **1**

`CANDIDATE_BLOCKED` includes:

- valid reviewer `BLOCK`;
- valid reviewer output that semantically blocks according to the existing contract;
- focused test completed and exited non-zero.

`INFRASTRUCTURE_BLOCKED` includes:

- reviewer/test launch failure;
- reviewer/test timeout;
- reviewer malformed/structurally inconsistent output;
- reviewer/test process crash that prevents a valid result;
- unconfirmed child termination;
- required verification child result otherwise unavailable.

Repository survey found no automated caller currently depending on a different `ai_gate.ps1` exit-code interpretation, so this mapping may be made explicit without breaking known automation.

### 5. Canonical artifact safety

Canonical review artifacts:

- `docs/tasks/<task-id>/reviews/spec-review.md`
- `docs/tasks/<task-id>/reviews/regression-review.md`

must be staged under `.runtime/ai_gate/<task-id>/` and promoted only after:

- process exit 0;
- no timeout/infrastructure failure;
- minimal reviewer structural validation passes.

On reviewer infrastructure failure, any previous valid canonical review file remains untouched.

### 6. `EVIDENCE.md` semantics

Canonical `EVIDENCE.md` represents a completed gate evaluation, not an incomplete attempt.

Therefore:

- on `PASS`, write/update canonical `EVIDENCE.md` with reviewer/test results;
- on `CANDIDATE_BLOCKED`, write/update canonical `EVIDENCE.md` because verification completed and reached a valid candidate verdict;
- on `INFRASTRUCTURE_BLOCKED`, do **not** overwrite an existing canonical `EVIDENCE.md` and do not create a canonical completed-verification artifact from partial results.

Infrastructure diagnostics belong under ignored `.runtime/ai_gate/<task-id>/` state and should be sufficient for local diagnosis.

A rerun that fails at infrastructure level must not erase the last valid canonical verification evidence.

### 7. Observability

Reviewer stdout/stderr must be visible in real time while the reviewer runs.

Focused tests need not stream every line, but the user must see:

- test start;
- configured timeout;
- completion/failure classification;
- elapsed time;
- runtime log path.

No required child process should appear as an indefinitely silent black box.

### 8. Implementation boundary

Reuse the proven execution design from `scripts/ai_scout.ps1` conceptually:

- `System.Diagnostics.Process` ownership;
- async reviewer stdout/stderr handling;
- wall-clock timeout on the control thread;
- client-only kill;
- termination confirmation;
- runtime staging before canonical promotion;
- cleanup of event jobs/handlers.

Implement the smallest coherent private/local helper(s) inside `scripts/ai_gate.ps1`.

Do **not** extract a generalized cross-repository/shared process framework in v1. The second use of the pattern is not by itself sufficient reason to create a new abstraction boundary before this gate behavior is proven in real use.

## Acceptance criteria

1. Both reviewer invocations have a wrapper-enforced 480-second default timeout and real-time stdout/stderr visibility.
2. A completely silent reviewer child cannot block the gate beyond configured timeout plus small termination/cleanup overhead.
3. Reviewer timeout terminates only the launched client process and does not kill persistent OpenCode service state.
4. Reviewer timeout/non-zero/malformed execution cannot replace a valid canonical review report with partial content.
5. Reviewer output is structurally validated for verdict/count consistency before canonical promotion.
6. Valid reviewer `BLOCK` remains `CANDIDATE_BLOCKED`, not infrastructure failure.
7. Every focused test has a default 60-second per-test timeout with override seam.
8. A focused test that completes non-zero is `CANDIDATE_BLOCKED`; a timeout/launch/termination failure is `INFRASTRUCTURE_BLOCKED`.
9. Gate exit semantics are explicit: `0=PASS`, `2=CANDIDATE_BLOCKED`, `1=INFRASTRUCTURE_BLOCKED`.
10. `EVIDENCE.md` is written for PASS or completed candidate BLOCK, but not overwritten/created from an infrastructure-incomplete run.
11. Reviewer canonical artifacts and `EVIDENCE.md` preserve the previous valid version across infrastructure-failed reruns.
12. Existing `-Task <id>` invocation remains compatible.
13. Full-suite policy is unchanged and obvious full-suite focused-test targets remain rejected.
14. Deterministic probes verify at least:
    - reviewer success + canonical promotion;
    - silent reviewer timeout + client-only kill + canonical preservation;
    - reviewer non-zero process exit → infrastructure block;
    - malformed reviewer output → infrastructure block;
    - valid reviewer semantic BLOCK → candidate block;
    - focused-test pass;
    - focused-test completed failure → candidate block;
    - focused-test silent timeout → infrastructure block;
    - distinct exit-code classification 0/1/2;
    - no lingering event jobs/processes after probe execution.
15. No production/game behavior changes.

## Non-goals

- Do not redesign reviewer semantic responsibilities.
- Do not add autonomous repair/retry loops.
- Do not parallelize reviewers in v1.
- Do not introduce queues, background services, dashboards, or distributed orchestration.
- Do not run or automate the full test suite.
- Do not change production/game code.
- Do not start `intent-routing-observability` in this task.
- Do not extract a generalized repository-wide process framework in v1.
- Do not solve hangs by only increasing timeout values.
- Do not add per-task timeout schema to `task.json` in v1; script defaults + explicit invocation/test seams are sufficient.

## Evidence basis

Confirmed by repository and local Scout evidence:

- current reviewer invocation uses blocking `Out-String` without timeout/live output;
- current focused-test invocation is also unbounded;
- a real reviewer invocation previously hung for about 27 minutes;
- this task's Scout itself hit 480-second timeout and terminated safely under the new Scout wrapper;
- no repository automation was found that requires a different `ai_gate.ps1` exit-code mapping;
- existing reviewer contracts already provide explicit `VERDICT` and `BLOCKING_FINDINGS` fields suitable for minimal structural validation;
- the `ai_scout.ps1` process-lifecycle pattern has deterministic probe coverage and is the appropriate conceptual basis for a local gate implementation.

Timeout defaults in this spec are workflow defaults chosen for bounded operation and practical testing; they are not claims of universal model/test latency.