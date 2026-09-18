# Context: AI Workflow Resume + Parallel Gate

## Executive Findings

1. **Current Gate Reviewer Loop is Strictly Sequential:**
   In [scripts/ai_gate.ps1](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1#L76-L101), reviewer execution is serialized by `foreach ($target in $targets)` where `$targets = @(@{ Agent='spec-reviewer'... }, @{ Agent='regression-reviewer'... })`. `spec-reviewer` runs to completion or fallback exhaustion first; only then does `regression-reviewer` begin. Furthermore, if `spec-reviewer` encounters an infrastructure failure, `regression-reviewer` is never executed at all ([scripts/ai_gate.ps1:100-101](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1#L100-L101)).

2. **Parallel Reviewer Execution is Architecturally Safe:**
   Both reviewers are strictly read-only blocker detectors that inspect the same frozen snapshot ([status.txt](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/.runtime/ai_gate), [diff.patch](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/.runtime/ai_gate), and [SPEC.md](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/docs/tasks/ai-workflow-resume-parallel-gate/SPEC.md)). At the adapter layer in [scripts/opencode_structured_review.mjs](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/opencode_structured_review.mjs#L170-L199), each reviewer spawns an independent `opencode serve` daemon using an ephemeral OS port (`--port=0`) and an isolated in-memory database (`OPENCODE_DB: ":memory:"`). There is no shared socket, database, or mutable process state between concurrent reviewers.

3. **Draft SPEC Assumption of Existing Reuse Logic is Inaccurate:**
   Draft SPEC (§Current evidence, item 19) assumed that `ai_gate.ps1` already implemented narrower reuse concepts (prior review artifact handling, generation state, implementation revision checks, and `-ForceRefresh`). **Actual survey reveals none of these exist in `scripts/ai_gate.ps1` today.** The script is 113 lines, executes unconditionally from scratch on every run, and has no `-ForceRefresh` parameter. This assumption must be formally revised.

4. **No Auto-Finalize Side Effects in Gate Script:**
   `scripts/ai_gate.ps1` performs verification, tests, and atomic artifact promotion, then terminates with exit code 0 (`PASSED`), 1 (`VERIFICATION_UNAVAILABLE`), or 2 (`CANDIDATE_BLOCKED`). There is no auto-commit, branch merge, or lifecycle mutation executed upon Gate success. Gate is already idempotent; re-running it with cached results causes no duplicate downstream mutations.

5. **Smallest Reliable Concurrency Mechanism:**
   A two-slot coordinator loop in PowerShell using .NET `[Diagnostics.Process]` is recommended over PowerShell Background Jobs (`Start-Job`) or Runspaces. It avoids child-job serialization penalties, runs natively on Windows PowerShell 5.1 and Core without extra modules, and preserves per-reviewer wall-clock timeout and kill confirmation.

---

## Current Architecture

The Blackfire development verification workflow is defined in [docs/architecture/ai_development_workflow.md](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/docs/architecture/ai_development_workflow.md):

```text
Human / ChatGPT (Draft SPEC + task.json)
  -> OpenCode Scout (CONTEXT.md)
  -> ChatGPT + user (Final SPEC.md)
  -> Gemini / Antigravity (Implementation)
  -> Verification Gate (scripts/ai_gate.ps1)
       ├─ spec-reviewer (reviews/spec-review.md)
       ├─ regression-reviewer (reviews/regression-review.md)
       ├─ focused tests (.venv\Scripts\python.exe -m unittest ...)
       └─ evidence assembly (EVIDENCE.md)
  -> ChatGPT final semantic review
  -> User-authorized integration
```

Key architectural boundaries:
- **Specification Authority:** ChatGPT + User own `SPEC.md`. `Status: Draft` forbids production implementation.
- **Review Authority:** OpenCode reviewers are independent, bounded semantic blocker detectors. They finalize via structured machine JSON (`PASS` or `BLOCK`).
- **Adapter Authority:** [scripts/opencode_structured_review.mjs](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/opencode_structured_review.mjs) owns process management, SSE lifecycle auditing, schema validation, and transport safety.
- **Orchestration Authority:** [scripts/ai_gate.ps1](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1) coordinates candidate fallback, test execution, fail-closed exit codes, and transactional artifact promotion.

---

## Current Gate Dataflow

Tracing execution in [scripts/ai_gate.ps1](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1):

```text
Final SPEC (docs/tasks/<task>/SPEC.md) & task.json
   ↓ (lines 11-16: validation, base_ref resolution)
Snapshot Generation
   ↓ (lines 73-75: status.txt, diff.patch created under .runtime/ai_gate/<task>/)
Review Input Generation
   ↓ (lines 78-87: prompt_spec-reviewer.txt, prompt_regression-reviewer.txt)
Reviewer Execution Loop (lines 77-101)
   ├─ Target 1: spec-reviewer
   │    └─ Candidate loop (lines 88-99): New-Invocation -> Invoke-BoundedProcess
   │         └─ node scripts/opencode_structured_review.mjs
   │         └─ Validate envelope -> write .runtime/.../candidate_spec-review.md
   └─ Target 2: regression-reviewer (SEQUENTIAL: only runs if Target 1 didn't set $unavailable)
        └─ Candidate loop -> write .runtime/.../candidate_regression-review.md
   ↓
Focused Tests
   ↓ (lines 104-107: .venv/Scripts/python.exe -m unittest <target>)
Aggregation
   ↓ (line 112: deterministic check: any BLOCK or test fail -> CANDIDATE_BLOCKED)
Artifact Promotion
   ↓ (lines 110-111: atomic backup to canonical_backup/*.bak -> promote candidates)
Gate Report / Evidence
   ↓ (lines 108-109: candidate_EVIDENCE.md created with HEAD SHA, verdicts, provenance)
Exit Code
   └─ 0 (PASSED), 1 (VERIFICATION_UNAVAILABLE), 2 (CANDIDATE_BLOCKED)
```

### Owning Components Table

| Stage | Owning Function / File | Inputs | Outputs / Persisted Artifact | Runtime State | Failure Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Config & Spec** | `scripts/ai_gate.ps1` (lines 11-16) | `task.json`, `SPEC.md` | In-memory `$config`, `$baseRef` | `$taskDir`, `$specPath` | Terminate script (`throw`) |
| **Snapshots** | `scripts/ai_gate.ps1` (lines 74-75) | `git status`, `git diff $baseRef` | `.runtime/ai_gate/<task>/status.txt`, `diff.patch` | Staging files | Non-zero exit if git fails |
| **Prompts** | `scripts/ai_gate.ps1` (lines 78-87) | Snapshots, `$baseRef`, agent role | `.runtime/ai_gate/<task>/prompt_<role>.txt` | Staging files | Script error on disk write failure |
| **Reviewer Exec** | `Invoke-BoundedProcess` + `scripts/opencode_structured_review.mjs` | Agent, model, repoRoot, prompt file | Log: `.runtime/.../<role>_<n>.log`<br>Candidate: `.runtime/.../candidate_<role>.md` | Child process, pipes, stopwatches | On crash/timeout/unsafe cleanup: `$unavailable=$true; break` (exit 1) |
| **Focused Tests** | `Invoke-BoundedProcess` (lines 105-107) | Python interpreter, test target | Terminal output | `$testResults` | `$testsPassed = $false` (leads to exit 2) |
| **Evidence** | `scripts/ai_gate.ps1` (lines 108-109) | HEAD commit, verdicts, attempts, test results | `.runtime/.../candidate_EVIDENCE.md` | Staging file | Fails before promotion if write fails |
| **Promotion** | `scripts/ai_gate.ps1` (lines 110-111) | Candidate reviews + candidate evidence | `docs/tasks/<task>/reviews/*`, `EVIDENCE.md` | Backup: `.runtime/.../canonical_backup/*.bak` | Transactional rollback on error; exit 1 |
| **Verdict** | `scripts/ai_gate.ps1` (line 112) | `$accepted`, `$testsPassed` | Process Exit Code (0, 1, 2) | None | Fail-closed |

---

## Reviewer Execution Ownership

Reviewer execution spans two cooperating layers:

1. **PowerShell Coordinator Layer (`scripts/ai_gate.ps1`):**
   - `Invoke-BoundedProcess` ([lines 23-47](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1#L23-L47)): Owns process lifetime, stdout/stderr asynchronous pipe draining via `ReadToEndAsync()`, timeout monitoring via `[Diagnostics.Stopwatch]`, and forceful tree kill via `taskkill.exe /PID $p.Id /T /F`.
   - Candidate routing ([lines 88-101](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1#L88-L101)): Selects models sequentially from `models.review`, checks envelope validity with `Test-Envelope`, and stops fallback immediately on `VALID_PASS`, `VALID_BLOCK`, or unsafe adapter cleanup.

2. **Node.js Adapter Layer (`scripts/opencode_structured_review.mjs`):**
   - `run()` ([lines 186-226](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/opencode_structured_review.mjs#L186-L226)): Spawns `opencode serve --hostname=127.0.0.1 --port=0 < NUL` with `OPENCODE_DB: ":memory:"`.
   - Subscribes to SSE events (`client.event.subscribe`), creates session, submits prompt with JSON schema constraint, and qualifies the result (`qualifyAttempt`).
   - `stopServer()` ([lines 145-168](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/opencode_structured_review.mjs#L145-L168)): Verifies process tree termination and pipe closure on Windows using `taskkill.exe`.
   - Outputs a single-line JSON envelope to stdout ([line 223](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/opencode_structured_review.mjs#L223)).

---

## Parallelization Hazards

Detailed hazard inspection for concurrent execution of `spec-reviewer` and `regression-reviewer`:

| Resource / Mechanism | Current Code Location | Concurrency Hazard Analysis | Risk Level |
| :--- | :--- | :--- | :--- |
| `System.Diagnostics.Process` | `ai_gate.ps1:29` | Thread-safe across independent instances. However, PowerShell script execution is single-threaded; a blocking `while(-not $p.WaitForExit(50))` cannot wait on two processes simultaneously without multi-process coordination. | Low (Manageable via dual-slot loop) |
| `stdout` / `stderr` pipes | `ai_gate.ps1:33` | Captured via `ReadToEndAsync()`. Each child process has its own anonymous OS pipe handles. No collision. | Safe |
| Shared Variables in `ai_gate.ps1` | `ai_gate.ps1:76, 91, 94, 98` | `$attempts += ...`, `$accepted[...] = ...`, `$unavailable = $true`. If two threads or jobs write to shared PowerShell variables without isolation, race conditions will occur. | **High** (Requires slot-scoped state) |
| Environment Variables (`$env:*`) | `opencode_structured_review.mjs:199` | Node passes environment explicitly in `spawn({ env })`. Neither reviewer script modifies process environment. | Safe |
| Current Directory (`cwd`) | `ai_gate.ps1:9, 25` | Set to `$repoRoot`. Read-only usage; neither reviewer changes current working directory. | Safe |
| Prompt & Snapshot Paths | `ai_gate.ps1:78, 87` | Snapshots (`status.txt`, `diff.patch`) are shared read-only. Prompt files are named `prompt_$($target.Agent).txt`, already partitioned by role. | Safe |
| Log File Paths | `ai_gate.ps1:91` | Named `Join-Path $runtimeDir "$($target.Agent)_$($attempts.Count+1).log"`. If `$attempts` is shared or concurrent, log file naming could collide. | **Medium** (Fix: name by role & model attempt) |
| Candidate Staging Paths | `ai_gate.ps1:98` | Staged as `candidate_spec-review.md` and `candidate_regression-review.md`. File paths are completely distinct. | Safe |
| Canonical Review Paths | `ai_gate.ps1:76, 98` | Target paths are `reviews/spec-review.md` and `reviews/regression-review.md`. Distinct files. Promotion must happen at fan-in. | Safe |
| Ephemeral Server Ports | `opencode_structured_review.mjs:170` | Spawns with `--port=0`. Windows kernel assigns unique ephemeral ports. No port collision. | Safe |
| OpenCode Database | `opencode_structured_review.mjs:199` | `OPENCODE_DB: ":memory:"` ensures each daemon has an independent private memory database. No SQLite locking hazard. | Safe |
| Timeout State | `ai_gate.ps1:34-37` | Must maintain independent stopwatches per reviewer. Sibling timeout must not cancel or mark the other reviewer as timed out. | **Medium** (Requires per-slot stopwatch) |
| Process Tree Kill | `ai_gate.ps1:36, 42` | `taskkill.exe /PID $p.Id /T /F`. Kills only the specific PID and its child process tree. Does not affect sibling PID. | Safe |
| Terminal Output Interleaving | `ai_gate.ps1:90` | `Write-Host "Running $($target.Agent)..."`. Concurrent console output may interleave lines. | Low (Acceptable UI artifact) |

---

## Existing Persistence / Resume Mechanisms

### Survey Results

A comprehensive survey of the entire repository for persistence/reuse keywords (`ForceRefresh`, `generation_state`, `prior review`, `cache`) yielded:

1. **`-ForceRefresh`**:
   - Appears **only** in the Draft `SPEC.md` ([docs/tasks/ai-workflow-resume-parallel-gate/SPEC.md:19, 51, 129, 154, 183](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/docs/tasks/ai-workflow-resume-parallel-gate/SPEC.md#L19)).
   - Does **not** exist in `scripts/ai_gate.ps1`, `scripts/ai_scout.ps1`, or any test file.
2. **`generation_state`**:
   - Zero occurrences in any script or test in the repository.
3. **Prior Review Artifact Reuse**:
   - `scripts/ai_gate.ps1` contains **zero** logic to inspect or reuse pre-existing `docs/tasks/<task>/reviews/*.md`. It always regenerates snapshots and runs both reviewers.
4. **Current Preservation Logic**:
   - `scripts/ai_gate.ps1` lines 110-111 creates a temporary `canonical_backup` directory before overwriting canonical files, and rolls back if an exception occurs during promotion.
   - Line 102 leaves canonical files untouched if verification fails or is unavailable.

---

## State Ownership Map

| Mechanism / State | Owner | Persisted Location | Validation Rule | Invalidation Rule | Consumers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Final SPEC** | User + ChatGPT | `docs/tasks/<task>/SPEC.md` | Contains `Status: Final` | User / ChatGPT edit | Implementation writer, Scout, Reviewers, Gate |
| **Task Config** | User + ChatGPT | `docs/tasks/<task>/task.json` | Valid JSON, `id` matches directory | Task creation/edit | Scout, Reviewers, Gate |
| **Scout Context** | OpenCode Scout (`ai_scout.ps1`) | `docs/tasks/<task>/CONTEXT.md` | Structured markdown, non-empty | Fresh scout run | ChatGPT (spec finalization) |
| **Reviewer Prompts** | `ai_gate.ps1` | `.runtime/ai_gate/<task>/prompt_<role>.txt` | Exists on disk | Overwritten on every gate run | OpenCode reviewer child processes |
| **Reviewer Outputs** | Reviewer Adapter (`opencode_structured_review.mjs`) | `.runtime/ai_gate/<task>/candidate_<file>` | `schema_version=1`, `cleanup.safe=true`, valid verdict | Process termination / new run | Gate promotion coordinator |
| **Canonical Reviews**| `ai_gate.ps1` | `docs/tasks/<task>/reviews/<role>.md` | Promoted only from valid envelopes | Stale input revision or force refresh | EVIDENCE generator, ChatGPT final review |
| **Evidence** | `ai_gate.ps1` | `docs/tasks/<task>/EVIDENCE.md` | Contains HEAD SHA, verdicts, provenance | Stale input revision or force refresh | ChatGPT final review, merge gate |
| **Backup on Fail** | `ai_gate.ps1` | `.runtime/ai_gate/<task>/canonical_backup/*.bak`| Copied during promotion | Overwritten during next promotion | Rollback handler in `ai_gate.ps1` |

---

## ForceRefresh Semantics

### Current State
`-ForceRefresh` is currently **unimplemented**. It is a requirement proposed in Draft SPEC.

### Recommended Consistent Contract
When implemented as a switch parameter `[switch]$ForceRefresh` in `scripts/ai_gate.ps1`:
- **When omitted (`$false`):** Gate checks whether valid cached stage results exist for the current input fingerprint. If valid, the stage is skipped and the cached artifact is reused.
- **When specified (`$true`):**
  - Completely bypasses cache lookup for reviewer stages.
  - Clears any existing staged results in `.runtime/ai_gate/<task>/`.
  - Forces fresh execution of `spec-reviewer` and `regression-reviewer`.
  - Forces re-execution of focused tests.
  - Generates fresh `candidate_EVIDENCE.md` with updated timestamp/provenance.
  - Promotes fresh canonical review artifacts.

---

## Partial Resume Analysis

### Scenario:
- **Run 1:** `spec-reviewer` PASSES; `regression-reviewer` encounters an INFRASTRUCTURE FAILURE (e.g. timeout or API socket error).
- Gate exits with code `1 = VERIFICATION_UNAVAILABLE`.
- Canonical files (`reviews/regression-review.md`, `EVIDENCE.md`) were NOT promoted.

### Conflict Analysis with Existing Safety Invariants:
1. *Invariant:* "Canonical review promotion only from valid completed results, and preservation of previous valid canonical evidence across infrastructure failure." ([SPEC.md:45](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/docs/tasks/ai-workflow-resume-parallel-gate/SPEC.md#L45)).
2. If `spec-reviewer`'s valid outcome was promoted to canonical `docs/tasks/<task>/reviews/spec-review.md` on Run 1 while `regression-reviewer` failed, the canonical task directory would hold mismatched artifacts (a new spec review alongside a missing or older regression review and older `EVIDENCE.md`).
3. Conversely, if `spec-reviewer`'s result is kept only in `.runtime/ai_gate/<task>/candidate_spec-review.md` alongside an input fingerprint manifest, canonical artifacts remain untouched on Run 1.
4. **Resolution:**
   On Run 2 (with identical inputs):
   - Gate inspects `.runtime/ai_gate/<task>/` (or stage manifest).
   - `spec-reviewer` matches current input fingerprint -> **REUSED** (no process launched).
   - `regression-reviewer` is missing/stale -> **RERUN**.
   - When `regression-reviewer` succeeds, Gate fans in both results, generates fresh `EVIDENCE.md`, and transactionally promotes both canonical reviews and evidence together.
   - This achieves partial resume while perfectly adhering to fail-closed canonical artifact safety.

---

## Recommended Minimal Architecture

### Concurrency Mechanism: Dual-Slot Process Coordinator
Do not use `Start-Job` (process overhead, object deserialization) or `ThreadJob` (module availability hazard).
Implement a dual-slot coordinator loop directly in `scripts/ai_gate.ps1`:

```text
Initialize Slot 1 (spec-reviewer) and Slot 2 (regression-reviewer)
For each slot:
   If Cached Stage Valid:
      Mark Slot as CACHE_HIT, load accepted envelope
   Else:
      Launch Candidate 1 via [Diagnostics.Process]::Start()
      Initialize Slot Stopwatch

While (any slot is Active):
   For each active slot:
      Check Process.WaitForExit(50)
      If Exited:
         Drain stdout/stderr, evaluate envelope
         If VALID verdict: Mark Slot COMPLETED
         Else If Fallback Candidate Available: Launch next Candidate
         Else: Mark Slot FAILED ($unavailable = $true)
      If Elapsed >= Timeout:
         Kill process tree via taskkill
         If Fallback Candidate Available: Launch next Candidate
         Else: Mark Slot FAILED ($unavailable = $true)
   Start-Sleep -Milliseconds 50

Fan-In:
   Wait for both slots to reach terminal state.
   If either slot FAILED -> exit 1 (VERIFICATION_UNAVAILABLE)
   Proceed to Focused Tests -> Aggregation -> Atomic Promotion -> Exit (0 or 2)
```

Advantages:
- Single PowerShell thread; no multi-threading synchronization hazards.
- Zero external PowerShell module dependencies.
- Bounded, isolated child execution per reviewer.
- Fully compatible with existing test harness seams (`_ReviewerExecutableOverride`).

---

## Stage Identity / Invalidation Proposal

To ensure **responsibility-aware invalidation** without global hash thrashing:

### Stage Fingerprint Models

1. **`spec-reviewer` Fingerprint:**
   - `SHA256(docs/tasks/<task>/SPEC.md)` (spec content)
   - `SHA256(.runtime/ai_gate/<task>/diff.patch)` (implementation diff)
   - Task `base_ref`
   - Reviewer role contract (`.opencode/agents/spec-reviewer.md`)
   - Candidate model name (e.g. `opencode/big-pickle`)

2. **`regression-reviewer` Fingerprint:**
   - `SHA256(.runtime/ai_gate/<task>/diff.patch)` (implementation diff)
   - Task `base_ref`
   - Task `scope` from `task.json`
   - Reviewer role contract (`.opencode/agents/regression-reviewer.md`)
   - Candidate model name (e.g. `opencode/big-pickle`)
   - (Also includes `SHA256(SPEC.md)` since regression reviewer checks against spec scope).

3. **What is Excluded to Prevent Global Invalidation:**
   - Git working tree timestamps or untracked scratch files outside task scope.
   - Commit author, commit timestamp, or commit message (only tree diff/content matters).
   - Unrelated files in other worktrees or other `docs/tasks/*` directories.

### Manifest Storage Location
Store per-stage execution metadata in:
`.runtime/ai_gate/<task>/stage_manifest.json` (runtime cache)
and write the fingerprint into an HTML comment block at the end of the promoted canonical `reviews/<role>.md`:
`<!-- blackfire-gate-fingerprint: {"role":"spec-reviewer","spec_sha":"...","diff_sha":"...","model":"..."} -->`

This ensures that:
- Clean checkouts on fresh worktrees can verify if an existing committed canonical review matches current HEAD/diff.
- Uncommitted local runs can resume from `.runtime/ai_gate/<task>/stage_manifest.json`.

---

## Fan-In Semantics

Current aggregation in [scripts/ai_gate.ps1:112](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/scripts/ai_gate.ps1#L112) is:
```powershell
$blocked = -not $testsPassed -or ($accepted['spec-reviewer'].Envelope.structured.verdict -eq 'BLOCK') -or ($accepted['regression-reviewer'].Envelope.structured.verdict -eq 'BLOCK')
```

Under parallel fan-in, the matrix is:

| `spec-reviewer` | `regression-reviewer` | `focused_tests` | Overall Gate Outcome | Exit Code | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `VALID_PASS` | `VALID_PASS` | `PASS` | **PASSED** | `0` | Promote reviews + evidence |
| `VALID_BLOCK` | `VALID_PASS` | `PASS` | **CANDIDATE_BLOCKED** | `2` | Promote reviews + evidence |
| `VALID_PASS` | `VALID_BLOCK` | `PASS` | **CANDIDATE_BLOCKED** | `2` | Promote reviews + evidence |
| `VALID_PASS` | `VALID_PASS` | `FAIL` | **CANDIDATE_BLOCKED** | `2` | Promote reviews + evidence |
| `INFRASTRUCTURE_FAILED` | `VALID_PASS` | (Skipped/Run) | **VERIFICATION_UNAVAILABLE** | `1` | Do NOT promote; stage sibling PASS |
| `VALID_PASS` | `INFRASTRUCTURE_FAILED` | (Skipped/Run) | **VERIFICATION_UNAVAILABLE** | `1` | Do NOT promote; stage sibling PASS |
| `INFRASTRUCTURE_FAILED` | `INFRASTRUCTURE_FAILED`| (Skipped/Run) | **VERIFICATION_UNAVAILABLE** | `1` | Do NOT promote canonical files |

- Aggregation remains 100% deterministic arithmetic/boolean logic.
- No third LLM judge is added.
- Existing fail-closed semantics are strictly preserved.

---

## Auto-Finalize Interaction

Survey of current workflow scripts and `.agents/skills/branch_completion_workflow/SKILL.md`:
- `ai_gate.ps1` does **not** execute any branch merge, git push, or task finalization.
- On success (`exit 0`), Gate writes terminal message:
  `AI verification gate PASSED. Final ChatGPT/human review is still required.`
- Finalization is owned by ChatGPT + user via GitHub review and branch completion skill.
- Therefore, Gate resume and caching are **idempotent**. Calling Gate multiple times on a passed task produces identical exit code 0 and valid evidence without triggering duplicate side-effects.

---

## Backward Compatibility

- **Historical Tasks:** Existing completed tasks (e.g. `docs/tasks/ai-gate-execution-resilience/`) have legacy `reviews/*.md` without fingerprint comments or stage manifests.
- **Handling Rule:**
  - If an existing review artifact lacks valid fingerprint metadata, Gate treats it as a **cache miss** (stale/unverified).
  - It does **not** crash and does **not** require historical task migration.
  - Closed tasks are historical artifacts and will never be run by Gate again.
  - Zero migration scripts are required.

---

## Exact Files Likely To Change

1. **`scripts/ai_gate.ps1`**:
   - Add parameter `[switch]$ForceRefresh`.
   - Implement stage fingerprint generation (`diff.patch` SHA, `SPEC.md` SHA).
   - Implement stage validity checking and stage manifest loading/saving.
   - Refactor sequential `foreach ($target in $targets)` into a concurrent dual-slot process coordinator with per-slot timeout, log capture, and fallback loop.
   - Update fan-in to handle partial staging and terminal outcome evaluation.
2. **`docs/architecture/ai_development_workflow.md`**:
   - Update Section 8 (Phase D) to document concurrent reviewer fan-out/fan-in and resume semantics.
3. **`docs/tasks/README.md`**:
   - Document `-ForceRefresh` flag and stage validity contract.
4. **`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`**:
   - Add test cases verifying reviewer execution overlap, sibling preservation, partial resume, and cache invalidation.

---

## Deterministic Test Plan

Expand [tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1](file:///E:/Side_Project/Blackfire-CV-Autopilot/worktrees/ai-workflow-resume-parallel-gate/tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1) using the existing `_ReviewerExecutableOverride` seam:

1. **Reviewer Overlap / Concurrency Proof:**
   In `fake-reviewer.py`, when a reviewer starts, write a start timestamp marker file and sleep 500ms. Sibling reviewer checks for that marker. If both were alive concurrently, write `concurrency_proven.marker`. Harness asserts marker exists.
2. **Fan-In Matrix Verification:**
   - Both PASS -> exit 0.
   - One BLOCK (spec-reviewer), one PASS -> exit 2.
   - One PASS, one BLOCK (regression-reviewer) -> exit 2.
   - One INFRASTRUCTURE_FAILED, one PASS -> exit 1.
3. **Sibling Result Preservation & Partial Resume:**
   - Run 1: `regression-reviewer` fails infrastructurally; `spec-reviewer` passes. Gate exits 1. Canonical files remain untouched, but `.runtime` stages valid `spec-reviewer` result.
   - Run 2: Inputs unchanged. `spec-reviewer` is skipped (verify via invocation marker that fake reviewer was not called for spec-reviewer); `regression-reviewer` runs and passes. Gate exits 0 and promotes both.
4. **Invalidation Verification:**
   - Change `SPEC.md` content -> verify `spec-reviewer` cache misses and reruns.
   - Change implementation code (modify file in repo) -> verify both reviewers rerun.
   - Pass `-ForceRefresh` -> verify both reviewers rerun despite unchanged inputs.
   - Modify unrelated file outside scope -> verify reviewers hit cache.
5. **No Process / Pipe Leakage:**
   - Verify fake reviewer process trees are completely terminated upon timeout or exit.

---

## Draft SPEC Assumptions Confirmed

1. `spec-reviewer` and `regression-reviewer` are independent read-only roles and can execute concurrently without semantic conflict.
2. The current bottleneck is strictly the sequential loop in `scripts/ai_gate.ps1`.
3. OpenCode daemon architecture (`--port=0`, in-memory database) supports parallel execution on Windows.
4. Gate aggregation is purely deterministic and does not require an LLM aggregator.
5. Fail-closed exit codes (0, 1, 2) and atomic promotion with rollback must be preserved.

---

## Draft SPEC Assumptions Rejected / Need Revision

1. **REJECTED: "Existing gate logic already contains narrower reuse concepts..."**
   - *Draft SPEC §Current evidence, item 19*: Claims gate has prior review artifact handling, generation state, implementation revision checks, and `-ForceRefresh`.
   - *Finding*: None of these exist in `scripts/ai_gate.ps1`. The current script is 113 lines and always executes from scratch. The final spec should frame persistence/resume as a clean, new additive subsystem rather than a refactoring of existing caches.
2. **REVISED: "Auto-finalize / duplicate mutation hazard"**
   - *Draft SPEC §target architecture & Q9*: Concerned that resuming a passed gate might trigger duplicate finalization mutations.
   - *Finding*: `ai_gate.ps1` has no finalization mutations. Gate success only outputs exit code 0. Branch closeout and merge remain manual/interactive user actions.
3. **ENVIRONMENT OBSERVATION:**
   - Task worktree `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\ai-workflow-resume-parallel-gate` does not contain `node_modules`. Node ESM imports in `test_workflow_scripts.py` fail if run directly against repo root without `node_modules` resolving `undici` and `@opencode-ai/sdk`. However, PowerShell harness `Invoke-WorkflowScriptHarness.ps1` runs independently via overrides.
   - `docs/architecture/ai_development_workflow.md` was updated in commit `5c9f6f8` to establish the canonical workspace convention, which trimmed text previously asserted by `Invoke-WorkflowScriptHarness.ps1`.

---

## Open Questions

1. **Manifest Location:** Should the stage input fingerprint be stored only in runtime `.runtime/ai_gate/<task>/stage_manifest.json`, or also embedded as a comment in the canonical `reviews/*.md` file? (Embedding in `reviews/*.md` allows cross-worktree or freshly-cloned git checkouts to detect that reviews match HEAD without local `.runtime` state).
2. **Granularity of `-ForceRefresh`:** Is a global `-ForceRefresh` switch sufficient for v1, or is there a genuine requirement for per-reviewer flags (e.g. `-ForceRefreshReviewer spec-reviewer`)? (Recommendation: Keep it a single switch `[switch]$ForceRefresh` for minimal complexity).
