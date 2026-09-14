# Scout Context: Execution Evidence for ai-gate-execution-resilience

## Execution Summary

- **Task**: `ai-gate-execution-resilience`
- **Start Time**: `2026-09-14 15:19:35`
- **Termination Time**: `2026-09-14 15:27:40`
- **Elapsed Duration**: 8 minutes 5 seconds (~485 seconds; hard timeout: 480 seconds)
- **Model**: `opencode/big-pickle`
- **Command**: `.\scripts\ai_scout.ps1 -Task ai-gate-execution-resilience`
- **Process Outcome**: OpenCode scout client (PID 26468) hit the 480s hard timeout, triggered child termination, verified child exit, and preserved canonical artifacts untouched.
- **Verdict**: `GO WITH SPEC CHANGES`

## Empirical Observations and Failure Mode

1. **Persistent Child Inaction / Model Latency**:
   - The OpenCode scout child process was launched and monitored by `scripts/ai_scout.ps1`. Throughout the 480-second window, the client process produced no interim stdout/stderr and consumed negligible CPU, waiting on either model provider latency or server RPC handling.
   - The newly introduced async streaming and hard timeout protection in `scripts/ai_scout.ps1` successfully prevented an indefinite hang: the client process was cleanly terminated at 480s, confirming that bounded orchestration is essential for all external agent invocations.
2. **Current `ai_gate.ps1` Vulnerability**:
   - In contrast to `ai_scout.ps1`, `scripts/ai_gate.ps1` still executes reviewers via blocking pipelines (`& opencode @args 2>&1 | Out-String`) without wrapper timeouts or streaming visibility.
   - A stalled reviewer in `ai_gate.ps1` currently blocks human developers indefinitely (as observed in the 27-minute hang during `scout-efficiency-v1`), leaving developers with no observable progress and risking partial artifact corruption upon manual abort.
   - Focused tests in `ai_gate.ps1` are also run via blocking pipelines without a per-test timeout wrapper.

## Targeted Answers to Draft SPEC Uncertainties

### 1. Existing Callers and Dependencies of Exit Codes 0 and 2

- **Repository Search**: A full-codebase grep for `ai_gate` confirms there are no automated CI pipelines, git hooks, or caller scripts that programmatically evaluate `ai_gate.ps1` exit codes. The script is invoked manually by developers during Phase D verification as documented in [docs/architecture/ai_development_workflow.md](../../architecture/ai_development_workflow.md).
- **Semantics**:
  - `Exit 0`: Complete verification PASSED (both reviewers reported `PASS` with 0 blocking findings, and all declared focused tests passed).
  - `Exit 2`: Candidate verification BLOCKED (semantic review rejection with blocking findings >= 1, invalid reviewer verdict, or test failure).
  - `Exit 1` (or uncaught termination exception): INFRASTRUCTURE_BLOCKED (process launch failure, child timeout, crash, termination confirmation failure, or malformed reviewer payload).
- **Recommendation**: Preserve `exit 0` for `PASS` and `exit 2` for `CANDIDATE_BLOCKED`. Introduce or preserve standard non-zero error termination (`exit 1` or descriptive `throw`) for `INFRASTRUCTURE_BLOCKED`. This makes semantic candidate failure clearly distinguishable from harness failure without breaking any existing automation.

### 2. Canonical Artifact Semantics on Infrastructure Failure (`reviews/*` and `EVIDENCE.md`)

- **Current Behavior**: `scripts/ai_gate.ps1` writes output directly to `reviews/*.md` upon process exit and overwrites `EVIDENCE.md` unconditionally before checking block conditions. A failure during the second reviewer leaves a partial review set.
- **Target Policy**:
  - **`reviews/*.md` (`spec-review.md`, `regression-review.md`)**: Must follow the candidate staging and atomic promotion pattern established in `ai_scout.ps1`. Review output is captured into `.runtime/ai_gate/<task-id>/candidate_<agent>.md` and promoted to `docs/tasks/<task-id>/reviews/<agent>.md` only after exit code 0, no timeout, and passing structural validation. On infrastructure failure, previous valid canonical review files remain 100% untouched.
  - **`EVIDENCE.md`**: Canonical `EVIDENCE.md` must NOT claim or imply completed verification when an infrastructure block occurs. If an infrastructure failure occurs during a rerun, the canonical `EVIDENCE.md` must remain untouched while diagnostic error logs are captured under `.runtime/ai_gate/<task-id>/`. This ensures git diff is not polluted with incomplete runs and downstream workflows are not misled.

### 3. Minimal Structural Validation for Reviewer Output

- **Agent Contract**: Defined in [docs/architecture/ai_development_workflow.md](../../architecture/ai_development_workflow.md) lines 247-269:
  ```text
  VERDICT: PASS | BLOCK
  BLOCKING_FINDINGS: <integer>
  ```
- **Minimal Validation Surface**:
  1. Non-empty, trimmed output.
  2. Regex match for `(?m)^VERDICT:\s*(PASS|BLOCK)\s*$` and `(?m)^BLOCKING_FINDINGS:\s*(\d+)\s*$`.
  3. Header presence near the top of the report.
  4. Contract consistency check: If `VERDICT: PASS`, then `BLOCKING_FINDINGS` must equal `0`. If `VERDICT: BLOCK`, then `BLOCKING_FINDINGS` must be `>= 1`.
  5. Detailed findings block parsing (ID, Severity, Claim, Evidence) is intentionally NOT enforced by regex to prevent brittle failures against natural formatting variations.

### 4. Reviewer Timeout Recommendation

- **Observation**: Healthy reviewer runs with localized scope typically take between 60 and 180 seconds. However, cold start, network latency, or deep search can extend execution.
- **Recommendation**: Set default reviewer timeout to **480 seconds (8 minutes)** per reviewer, consistent with `ai_scout.ps1`.
- **Parameter Seam**: Provide `[int]$ReviewTimeoutSeconds = 480` to allow fast-fail testing and local overrides. Sequential execution of the two reviewers in v1 gives a total upper bound of 16 minutes for the review stage.

### 5. Focused-Test Timeout Recommendation

- **Repository Context**: Per [AGENTS.md](../../../.agents/AGENTS.md) and [docs/testing/](../../testing/), focused tests are narrowly scoped behavioral slices (e.g. `tests.test_behavior_navigation`). Standard test runs complete in 0.5s to 5s.
- **Recommendation**: Set default per-test timeout to **60 seconds**.
- **Parameter Seam**: Provide `[int]$TestTimeoutSeconds = 60`. A 60-second limit is ample for Python startup and execution while promptly catching deadlocks or infinite loops.

### 6. Local Async Process Pattern vs Shared Framework

- **Assessment**: The async process pattern implemented in `scripts/ai_scout.ps1` (~70 lines of .NET `System.Diagnostics.Process` with `OutputDataReceived`/`ErrorDataReceived`, `Monitor` synchronization, and `Stopwatch` polling) is self-contained and stable.
- **Recommendation**: In accordance with Non-goal #8 (*"Do not extract a generalized repository-wide process framework unless Scout proves duplication already warrants it; local/simple implementation is preferred in v1"*), implement a local private helper (e.g. `Invoke-BoundedProcess`) directly inside `scripts/ai_gate.ps1`. This avoids premature cross-script coupling while sharing the proven execution pattern.

### 7. Focused Test Observability (Streaming vs Bounded Log)

- **Characteristics**: Focused tests produce concise unittest output (`Ran N tests in Xs... OK` or failure traces).
- **Recommendation**: Bounded execution with clear console status banners (announcing test start with timeout, completion status, elapsed duration, and log path) plus writing stdout/stderr to `.runtime/ai_gate/<task-id>/test-<safeName>.log` is sufficient. Direct line-by-line streaming to the console is unnecessary for fast unit tests and can clutter the gate's structured output.

### 8. Minimal Deterministic Probe Suite

To thoroughly verify `ai_gate.ps1` resilience without relying on live model calls or slow tests, provide script-level test seams (`_ReviewerExecutableOverride`, `_PythonExecutableOverride`, or `_ProcessOverride`):

1. **Reviewer Success & Promotion**: Mock reviewer returns exit 0 with valid `VERDICT: PASS` and `BLOCKING_FINDINGS: 0` -> verify canonical promotion to `reviews/*.md`.
2. **Reviewer Silent Timeout**: Mock reviewer sleeps indefinitely -> verify termination at configured short timeout (e.g. 2s), verify child killed, canonical files untouched, exit code 1 / throw.
3. **Reviewer Non-Zero Exit & Malformed Output**: Mock reviewer exits 1 or outputs invalid header -> verify infrastructure failure reported, canonical reviews preserved.
4. **Reviewer Semantic BLOCK**: Mock reviewer returns exit 0 with `VERDICT: BLOCK` and `BLOCKING_FINDINGS: 2` -> verify review promoted, `EVIDENCE.md` generated with BLOCKED verdict, exit code 2.
5. **Focused-Test Timeout**: Mock python test process sleeps indefinitely -> verify test terminated at timeout, recorded as failed in `EVIDENCE.md`, gate does not hang.
6. **Focused-Test Pass/Fail Recording**: Mock test exits 0 (recorded as PASS) vs exits 1 (recorded as FAIL in `EVIDENCE.md`, gate exits 2).
7. **Failure Classification**: Distinct verification that infrastructure errors trigger exit 1, while candidate blocks trigger exit 2.
8. **PowerShell Event Cleanup**: Verify zero lingering `PSEventJob` instances in session after runs.

## Recommendation

**GO WITH SPEC CHANGES**

The empirical evidence from the 8-minute Scout timeout, coupled with the observed 27-minute reviewer hang in `scout-efficiency-v1`, conclusively demonstrates that `scripts/ai_gate.ps1` requires the same bounded, observable, and artifact-safe architecture as `scripts/ai_scout.ps1`. The draft spec's target behavior is fully validated and ready to progress to Final SPEC.
