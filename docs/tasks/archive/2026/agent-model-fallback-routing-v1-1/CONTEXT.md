Now let me inspect the primary implementation files and architecture documentation referenced in the scope.
Now let me check the agent contract files and any existing test infrastructure referenced by the scripts.
I've reached the maximum tool-use steps. Here is the complete scout report based on the files already inspected (6 files read):

---

# Scout Context

## Relevant files and symbols

1. **`scripts/ai_scout.ps1` (236 lines)** ??Primary Scout invocation script. Currently accepts a single `$Model` parameter, resolves it from `task.json` or CLI override, builds one OpenCode `run --standalone --agent scout --model $Model` invocation, and runs it through an inline process lifecycle (start ??wait ??timeout check ??structural validation ??atomic promotion to `CONTEXT.md`). No fallback, retry, or multi-model logic exists today.

2. **`scripts/ai_gate.ps1` (713 lines)** ??Primary Gate script. Contains `Invoke-BoundedProcess` (reusable bounded process wrapper with kill-confirm, elapsed tracking), `Get-OpenCodeInvocation` (builds OpenCode args from a single `$ReviewModel`), `Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`. The main loop at line 412 iterates over two review targets (spec-reviewer, regression-reviewer) and on any infra failure sets `$infraBlocked = $true` and `break`s immediately ??no fallback path. Key failure classification branches: timeout (line 441), non-zero exit (451), malformed structured JSON (460), canonical payload extraction failure (469), invalid verdict structure (476). After reviewers, focused tests run, then transactional promotion with backup/rollback (lines 627??91).

3. **`docs/architecture/ai_development_workflow.md` (351 lines)** ??Architecture contract. Section 10 ("Model selection") states model choice comes from `task.json` or PowerShell arguments, models are not hard-coded, and provider credentials stay local. No fallback mechanism is documented. Exit codes 0/1/2 and their semantics are defined in Section 6 Phase D.

4. **`docs/tasks/agent-model-fallback-routing-v1-1/SPEC.md` (121 lines)** ??Draft spec. Defines: ordered model-candidate routing for Scout and review roles; fallback only on infrastructure failures (never after semantic terminal results); bounded total time budget; attempt provenance; backward compatibility with single-model config.

5. **`docs/tasks/agent-model-fallback-routing-v1-1/task.json` (15 lines)** ??Task descriptor. Scope includes `ai_scout.ps1`, `ai_gate.ps1`, and `ai_development_workflow.md`. Current models: `"scout": "opencode/mimo-v2.5-free"`, `"review": "opencode/mimo-v2.5-free"`.

6. **`docs/tasks/ai-gate-execution-resilience/task.json` (14 lines)** ??Checked for schema comparison. All existing task.json files use the same scalar `models.scout` / `models.review` pattern; no array or ordered-candidate form exists anywhere.

## Current control flow

**Scout (`ai_scout.ps1`):**
1. Parse params, resolve `$Model` from CLI or `config.models.scout` (scalar string).
2. Build a single OpenCode invocation with that one model.
3. Start process via `System.Diagnostics.Process`, redirect stdout/stderr, close stdin.
4. Poll loop with 50ms waits; check wall-clock timeout against `$TimeoutSeconds` (default 480s).
5. On timeout: kill process, confirm exit within 3s, `throw`.
6. On non-zero exit: `throw`.
7. On empty or structurally invalid output: `throw`.
8. On success: atomic `Set-Content` ??`Move-Item` promotion to `CONTEXT.md`.
9. Any failure leaves pre-existing `CONTEXT.md` untouched.

**Gate (`ai_gate.ps1`):**
1. Parse params, resolve `$ReviewModel` from CLI or `config.models.review` (scalar string).
2. Snapshot git status/diff into `.runtime/` directory.
3. Sequential loop over `spec-reviewer` ??`regression-reviewer`:
   - `Get-OpenCodeInvocation` builds args with the single `$ReviewModel`.
   - `Invoke-BoundedProcess` runs with `$ReviewTimeoutSeconds` (default 480s).
   - Failure classification: timeout ??`break`, non-zero exit ??`break`, malformed structured output ??`break`, missing canonical payload ??`break`, invalid verdict structure ??`break`.
   - Any `break` sets `$infraBlocked = true` and exits the reviewer loop entirely.
   - Valid result: stage candidate, record verdict.
4. If not infra-blocked, run focused tests via `Invoke-BoundedProcess` with Python.
5. If all pass: transactional promotion (backup ??copy ??simulated-failure seam ??rollback on failure).
6. Exit code: `0` = PASS, `1` = INFRASTRUCTURE_BLOCKED, `2` = CANDIDATE_BLOCKED.

**Key architectural fact:** Both scripts are currently single-invocation, single-model. There is no loop, no model list, no fallback branching, no per-attempt timing budget, and no provenance tracking beyond a single raw log file.

## Existing safety mechanisms

- **`Invoke-BoundedProcess`** in `ai_gate.ps1` (line 73): Reusable function returning `ExitCode`, `TimedOut`, `KillConfirmed`, `ElapsedSeconds`, `StdOut`, `StdErr`. Already has kill-confirmation with 3-second WaitForExit. This is the strongest candidate for reuse inside a fallback loop.
- **Kill-confirmation pattern** (lines 155??68 in `ai_gate.ps1`): Process killed ??3s WaitForExit ??warning if unconfirmed. Present in both scripts.
- **Structural validation**: `Test-ReviewVerdictStructure` (line 372) and `Get-CanonicalReviewPayload` (line 330) already distinguish malformed output from valid semantic results. This classification boundary is exactly where fallback eligibility decisions should be made.
- **Transactional promotion with backup/rollback** (lines 627??91 in `ai_gate.ps1`): Backs up existing canonical artifacts, promotes, rolls back on failure. Must not be broken by fallback changes.
- **Test seams**: `$_ExecutableOverride`, `$_ReviewerExecutableOverride`, `$_SpecReviewerArgumentsOverride`, `$_RegressionReviewerArgumentsOverride` in `ai_gate.ps1`; `$_ExecutableOverride`, `$_ArgumentsOverride` in `ai_scout.ps1`. These allow deterministic testing without live OpenCode.
- **Process isolation**: Both scripts use `--standalone`, explicit repo working directory, closed stdin, no shared shell state.

## Existing tests

No dedicated test files were found for these scripts within the repository. The `focused_tests` field is empty for this task. The scripts contain built-in test seams (override parameters) that imply external test harnesses may exist or be planned. This is a gap: fallback routing must be verifiable with deterministic probes.

## Regression and architecture risks

1. **Single-model assumption is deeply embedded**: `$Model` in `ai_scout.ps1` and `$ReviewModel` in `ai_gate.ps1` are scalar strings passed directly to `--model` args. Fallback requires iterating over multiple models while preserving all downstream logic (timeout, classification, promotion).
2. **`break` semantics in gate reviewer loop**: The current `break` on infra failure exits the entire reviewer loop. With fallback, this must become "try next model for the same agent" rather than "abort all reviewers."
3. **Per-attempt vs. total time budget**: Current `ReviewTimeoutSeconds = 480` is per-attempt. The spec asks whether 480s should be total or per-attempt-within-a-total. This design decision is explicitly uncertain (SPEC uncertainty item 4).
4. **`task.json` schema backward compatibility**: All 5 existing task.json files use scalar `models.scout`/`models.review`. Any schema change (array form, new field) must be backward-compatible or have a migration path (spec acceptance criterion 9).
5. **Gemini degradation rule (SPEC section 3)**: Gemini as fallback for its own implementation review creates a logical conflict. This is flagged as explicit uncertainty (spec item 6) and is not resolved by the current code.
6. **Provenance tracking**: No attempt-identity, attempt-count, or per-attempt timing exists. Failed raw logs go to `.runtime/` but are not structured for multi-attempt auditability.
7. **Scout script is not restructured as a function**: Unlike `ai_gate.ps1` which has `Invoke-BoundedProcess`, `ai_scout.ps1` has inline process management. A fallback loop in Scout would need refactoring to avoid duplicating the process lifecycle.

## Uncertainty

1. **Schema extension design**: Whether `models.scout`/`models.review` should accept both scalar and array (backward-compatible), or a new field like `models.scout_candidates` / `models.review_candidates` should be introduced. Current code does scalar `.models.scout` string cast (line 40 of `ai_scout.ps1`, line 50 of `ai_gate.ps1`).
2. **CLI override semantics**: What `-Model` / `-ReviewModel` means when a fallback chain exists (strict single-model override? first-candidate override? full chain override?). Currently these are simple scalar overrides.
3. **Fallback loop boundary in `ai_gate.ps1`**: The infra-failure `break` at lines 448/454/463/472/479 currently aborts the entire reviewer loop. The cleanest fallback insertion point needs to be within the `foreach ($rev in $reviewTargets)` loop but around the `Invoke-BoundedProcess` call for each individual agent, not wrapping the entire reviewer sequence.
4. **Total time budget architecture**: Whether to make 480s a total role budget with per-attempt sub-budgets, or keep per-attempt at 480s with a separate total cap. This directly affects the `Invoke-BoundedProcess` call and stopwatch logic.
5. **Gemini degraded fallback terminal behavior**: Not resolvable from current code ??requires spec-level design decision.
6. **No existing tests for fallback routing**: Whether the current test seams are sufficient for multi-attempt verification or if a new seam (e.g., model-candidate-list override parameter) is needed.

## Minimal proposed change surface

**`scripts/ai_scout.ps1`:**
- Refactor inline process management into a `Invoke-ScoutAttempt` function (similar to `Invoke-BoundedProcess`).
- Add fallback loop: resolve ordered candidate list from task.json (backward-compatible: scalar ??single-item list), iterate candidates, break on valid result, aggregate timing.
- Add per-attempt and total-time budget enforcement.
- Add structured provenance logging (attempt index, model name, failure classification, elapsed time).

**`scripts/ai_gate.ps1`:**
- Modify `Get-OpenCodeInvocation` to accept a model name parameter (currently captures `$ReviewModel` from script scope).
- Add fallback loop around `Invoke-BoundedProcess` within the reviewer iteration: on infra failure, try next candidate for same agent before moving to next reviewer.
- Add total-time budget tracking across all reviewer attempts.
- Add structured provenance to `EVIDENCE.md` output.
- Preserve: `break` on valid semantic result, existing promotion/rollback, exit code semantics.

**`docs/architecture/ai_development_workflow.md`:**
- Update Section 10 (Model selection) and Section 6 Phase B/D to document fallback behavior, exit code preservation, and provenance.

**`task.json` schema:**
- Backward-compatible extension for ordered candidates (exact shape to be determined by Final SPEC).

## Recommendation

**GO WITH SPEC CHANGES**

The implementation surface is well-scoped: two PowerShell scripts and one architecture doc. The scripts already have clean function decomposition (`Invoke-BoundedProcess`, `Test-ReviewVerdictStructure`, `Get-CanonicalReviewPayload`) that provides natural insertion points for a fallback loop. The `break` on infra failure is a clean boundary ??it just needs to become "continue to next model candidate" instead of "abort all reviewers."

However, the SPEC requires resolution of several explicit uncertainties before Final SPEC can be written: (a) `task.json` schema extension shape (scalar+array polymorphism vs. new field), (b) CLI override semantics in fallback context, (c) total vs. per-attempt time budget architecture, (d) Gemini degraded fallback terminal behavior, and (e) whether existing test seams are sufficient or one additional seam is needed. These are spec-level design decisions that the current repository cannot answer. The implementation plan itself is clear and low-risk once these decisions are made.
