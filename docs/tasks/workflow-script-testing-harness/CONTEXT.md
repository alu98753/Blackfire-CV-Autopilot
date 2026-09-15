# Scout Context

## Relevant files and symbols

| File | Why it matters |
| `docs/tasks/workflow-script-testing-harness/task.json` | Task descriptor declaring scope: `scripts/ai_gate.ps1`, `scripts/ai_scout.ps1`, `tests/`, and the task docs directory. |
|---|---|
| `docs/tasks/workflow-script-testing-harness/SPEC.md` | Canonical spec defining goal (offline deterministic regression harness), invariants, non-goals, acceptance criteria, and 7 open Scout questions. |
| `scripts/ai_scout.ps1` (412 lines) | Secondary target. Contains 3 internal test seams (`_ExecutableOverride`, `_ArgumentsOverride`, `_ModelCandidatesOverride`), key functions (`Resolve-NormalModelList`, `Invoke-ScoutProcessAttempt`), and atomic CONTEXT.md promotion. |
| `tests/` (directory) | Existing test location ??contains ~30+ Python `unittest`/`pytest` files (`test_behavior_*.py`, `test_*.py`). No PowerShell `.Tests.ps1` files exist anywhere in the repo. No `conftest.py`, `pytest.ini`, or `pyproject.toml` found. |
| `scripts/ai_gate.ps1` (889 lines) | Primary target. Contains 8 internal test seams (`_ReviewerExecutableOverride`, `_ReviewerArgumentsOverride`, `_SpecReviewerArgumentsOverride`, `_RegressionReviewerArgumentsOverride`, `_ReviewCandidatesOverride`, `_PythonExecutableOverride`, `_PythonArgumentsOverride`, `_FailPromotionOnTarget`), key functions (`Resolve-ReviewCandidates`, `Invoke-BoundedProcess`, `Get-OpenCodeInvocation`, `Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`), and transaction-safe promotion with rollback. |
| `scripts/` (directory) | Contains only 4 `.ps1` files (`ai_gate.ps1`, `ai_scout.ps1`, `bootstrap_opencode.ps1`, `run_crop_tool.ps1`). No `scripts/tests/` subdirectory exists. |
## Current control flow

**ai_gate.ps1** flow:

1. Param block accepts `$Task` (mandatory) plus 8 underscore-prefixed test seams.
2. Reads `docs/tasks/$Task/task.json` and `SPEC.md`, validates `base_ref`.
3. Resolves review candidates via `Resolve-ReviewCandidates` (override ??CLI ??config fallback).
4. Creates `.runtime/ai_gate/$Task/` for status/diff snapshots; runs `git status` and `git diff`.
5. Iterates over two review targets (spec-reviewer, regression-reviewer). For each, iterates candidates: invokes `Invoke-BoundedProcess` ??extracts structured JSON via `Get-FinalAssistantMessageFromStructuredJson` ??extracts payload via `Get-CanonicalReviewPayload` ??validates via `Test-ReviewVerdictStructure`. First valid verdict wins; infra failures cascade to `INFRASTRUCTURE_BLOCKED` (exit 1).
6. Runs focused Python tests if configured (via `$_PythonExecutableOverride` seam).
7. Promotes candidate artifacts to canonical paths with backup/rollback; any promotion failure triggers rollback and exit 1.
8. Final exit codes: 0 = PASS, 1 = INFRASTRUCTURE_BLOCKED, 2 = CANDIDATE_BLOCKED.

1. Param block accepts `$Task` (mandatory) plus 3 underscore-prefixed test seams.
**ai_scout.ps1** flow:
2. Reads task.json, resolves model candidates via `Resolve-NormalModelList` (override ??CLI ??config fallback).
3. Iterates candidates via `Invoke-ScoutProcessAttempt`: processes timeout, kill-confirmation, non-zero exit, empty output, malformed output (missing `# Scout Context` heading).
4. First structurally valid output wins; promotes atomically via `Set-Content` ??`Move-Item` to canonical `CONTEXT.md`.

## Existing safety mechanisms

- **Process timeout + kill-confirmation**: Both scripts use `System.Diagnostics.Stopwatch` polling loop with `Kill()` + `WaitForExit(3000)` confirmation. Gate returns `TIMEOUT_UNCONFIRMED_KILL` ??`INFRASTRUCTURE_BLOCKED`. Scout throws on unconfirmed kill.
- **Transaction-safe artifact promotion (Gate only)**: Backup ??copy ??simulated-failure seam ??rollback on any failure. Each rollback item independently try/catched.
- **`$_FailPromotionOnTarget` seam**: Allows tests to inject a promotion failure at a named target to exercise rollback paths.
- **`$ErrorActionPreference = "Stop"`**: Both scripts enforce strict error propagation.
- **Candidate validation pipeline (Gate)**: `Get-CanonicalReviewPayload` ??`Test-ReviewVerdictStructure` with strict line-1 regex, PASS/BLOCK mutual consistency checks.
- **Malformed output detection (Scout)**: Regex check for `# Scout Context` or `## Relevant files` heading.
- **Test isolation**: `.runtime/` directories are git-ignored; canonical paths are only written after successful validation.

## Existing tests

- **No PowerShell tests exist anywhere in the repository.** Zero `.Tests.ps1` files. No Pester references found in any file.
- **No PowerShell test framework conventions** ??no `Install-Module Pester`, no `Invoke-Pester` calls, no PowerShell test helpers.
- **Existing test suite is 100% Python** (~30+ files in `tests/`), using `unittest`/`pytest` patterns. No `conftest.py` or pytest configuration files found at repo root.
- The `tests/` directory convention is Python-only and would conflict with Pester test discovery if PowerShell tests were placed there without care.

## Regression and architecture risks

1. **No existing PowerShell test convention**: The harness must establish a new pattern. Risk of inconsistent placement if not thoughtfully located.
2. **`tests/` directory collision**: Existing Python `unittest` discovery may pick up PowerShell test files if placed in `tests/` without file-type filtering. Best to isolate in `tests/workflow_scripts/` or `scripts/tests/`.
3. **Process-level testing is inherently timing-sensitive**: Both scripts use wall-clock `Stopwatch` + `WaitForExit(50)` polling. Tests that exercise timeout paths need fake executables with controllable sleep behavior, not real timeouts.
4. **Gate git operations at top-level**: `git status` and `git diff` run against `$baseRef` before any seam injection ??test fixtures must be in a git-tracked context or the test must override these steps (no seam for git commands currently).
5. **Duplicate process-spawning logic**: `ai_gate.ps1` has `Invoke-BoundedProcess` (shared utility function); `ai_scout.ps1` has its own inline `Invoke-ScoutProcessAttempt`. Any extraction of shared test helpers must not alter production flow.
6. **Stdin close pattern**: Both scripts close stdin immediately (`$proc.StandardInput.Close()`). Fake executables used in tests must not block on stdin.
7. **Artifact promotion side effects**: Gate's promotion writes to `docs/tasks/$Task/reviews/` and `docs/tasks/$Task/EVIDENCE.md`. Tests must use temporary task directories, not real task evidence.

## Uncertainty

1. **Pester availability**: Pester is not installed or referenced in the repo. Whether to use Pester (requires `Install-Module Pester`) vs. plain PowerShell assertion scripts (`Assert-` + `throw`) is unresolved. The spec asks the Scout to recommend; plain PowerShell is zero-dependency and simpler for this repo.
2. **Git operation seam**: `ai_gate.ps1` has no test seam for `git status` / `git diff` at the top. Tests either need to run in a real git context with appropriate fixtures, or accept these as non-testable without a behavior-neutral extraction. This is a significant gap for fully offline deterministic testing.
3. **Shared function extraction**: `Invoke-BoundedProcess` in `ai_gate.ps1` and the equivalent in `ai_scout.ps1` could be shared, but the spec says behavior must not change. Whether a tiny `.ps1` dot-source helper is justified is uncertain.
4. **Timeout test determinism**: The spec uncertainty about wall-clock timeout tests remains ??a fake executable with `Start-Sleep` of controlled duration can work, but flakiness risk is real on slow CI.
5. **Focused test execution seam**: The Gate's focused-test path uses `$_PythonExecutableOverride` + `$_PythonArgumentsOverride`, which is sufficient for testing the test-execution logic itself.

## Minimal proposed change surface

- `tests/workflow_scripts/` ??new subdirectory for PowerShell test files (or `scripts/tests/` if preferred to avoid Python discovery collision)
**New files (harness):**
- `tests/workflow_scripts/Invoke-GateHarness.ps1` ??single documented entry-point script that runs all workflow script regression tests
- `tests/workflow_scripts/Test-AiGate.Tests.ps1` ??Pester test file for ai_gate.ps1 behavior
- `tests/workflow_scripts/Test-AiScout.Tests.ps1` ??Pester test file for ai_scout.ps1 behavior
- `tests/workflow_scripts/Fixtures/` ??fake executables, fake task.json/SPEC.md, fake reviewer output payloads

**Existing files (minimal or no changes expected):**
- `scripts/ai_gate.ps1` ??**no production changes** (all seams already exist)
- `scripts/ai_scout.ps1` ??**no production changes** (all seams already exist)
- Possibly a small `.psm1` helper module if shared process/parsing utilities are extracted (behavior-neutral only)

## Recommendation

**GO WITH SPEC CHANGES**

**Reason:** The repository already has all 11 required internal test seams across both scripts. The spec's behavior-preserving constraint is fully satisfiable without modifying `ai_gate.ps1` or `ai_scout.ps1`. The primary risk is the unresolved question of test framework choice (Pester vs. plain PowerShell assertions) and the `git status`/`git diff` seam gap in `ai_gate.ps1`. These are spec-level decisions that should be resolved before implementation: (a) recommend plain PowerShell assertions with a thin harness runner to avoid Pester dependency, (b) scope v1 harness to test paths reachable through existing seams (skip the un-seamed git operations at top of Gate), and (c) place tests in `tests/workflow_scripts/` to avoid Python unittest discovery collision. With these spec adjustments, the task is well-scoped and implementable.
