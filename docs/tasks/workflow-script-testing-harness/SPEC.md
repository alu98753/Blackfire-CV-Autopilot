# workflow-script-testing-harness

Status: Final

## Goal

Create a deterministic, offline, repository-native regression harness for `scripts/ai_gate.ps1` and `scripts/ai_scout.ps1` so later workflow changes can be made against a known behavioral baseline without invoking live OpenCode models, external AI services, or network access.

This is a reliability prerequisite. It establishes testability around existing workflow behavior; it does not change that behavior.

## Evidence basis

Scout confirmed:

- no PowerShell test harness or Pester convention currently exists in the repository;
- `tests/` is currently Python-oriented;
- `ai_gate.ps1` already exposes eight explicit internal test seams;
- `ai_scout.ps1` already exposes three explicit internal test seams;
- those seams are sufficient for a useful v1 harness without production-script modification;
- Gate has an un-seamed top-level `git status` / `git diff` phase, so v1 should run script-level tests inside the real repository rather than introduce a new git-command seam;
- timeout tests can become flaky if they depend on large real wall-clock windows;
- canonical task artifacts must never be used as mutable test fixtures.

## Scope

### New test structure

Create a dedicated PowerShell harness under:

```text
tests/workflow_scripts/
```

Use a dependency-free plain PowerShell runner rather than introducing Pester in v1.

Required stable entry point:

```powershell
.\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1
```

The runner must:

- execute all workflow-script regression cases;
- return exit code `0` only when every case passes;
- return non-zero on any failed assertion, unexpected script exit, fixture leak, or cleanup failure;
- print concise per-case PASS/FAIL output suitable for local debugging;
- require no OpenCode installation when executable overrides are used;
- require no network access or live AI inference.

### Fixture isolation

Tests may create temporary task packages only under uniquely named disposable paths matching the scripts' current `docs/tasks/<task-id>/` contract. Temporary task directories and `.runtime` artifacts must be cleaned in `finally`-style cleanup.

Tests must never modify or reuse canonical evidence belonging to a real task.

### `ai_gate.ps1` baseline behaviors to cover

At minimum, the harness must lock the current behavior of:

1. valid canonical reviewer `PASS` -> Gate accepts the verdict;
2. valid canonical reviewer `BLOCK` with blocking findings -> Gate classifies candidate blocked according to current exit semantics;
3. malformed or structurally inconsistent reviewer output -> infrastructure failure;
4. currently unsupported Markdown-wrapped verdict headers remain rejected in this task;
5. configured/override review candidate selection through existing seams;
6. at least one infrastructure/fallback-related candidate path using fake child processes;
7. focused-test execution through `_PythonExecutableOverride` / `_PythonArgumentsOverride` without running production tests;
8. at least one artifact-safety path using existing promotion/rollback seams, if reachable without changing production code;
9. Gate exit-code contract remains:
   - `0` = PASS
   - `1` = INFRASTRUCTURE_BLOCKED
   - `2` = CANDIDATE_BLOCKED.

### `ai_scout.ps1` baseline behaviors to cover

At minimum, the harness must lock the current behavior of:

1. normal candidate resolution / override selection;
2. successful fake Scout output containing the required Scout structure -> canonical promotion for the disposable fixture task;
3. malformed Scout output -> failure and no invalid canonical promotion;
4. non-zero child-process failure and/or candidate fallback through existing seams;
5. bounded-process timeout behavior where it can be exercised with a short, controlled fake process without making the suite materially flaky;
6. existing canonical `CONTEXT.md` preservation on failed Scout execution where safely testable.

## Known invariants

- This task is behavior-preserving for both workflow scripts.
- Existing Gate exit-code semantics remain authoritative.
- Existing Scout/Gate model-routing and fallback semantics must not change.
- Existing timeout values and kill-confirmation semantics must not change.
- Existing review payload acceptance/rejection rules must not change, including current rejection of Markdown-wrapped verdict headers.
- Existing artifact promotion / rollback semantics must not change.
- Tests must not invoke live OpenCode reviewers or require external model/network availability.
- Tests must exercise real script behavior through public invocation and existing explicit test seams; they must not copy parser, routing, timeout, or promotion logic into a second implementation.
- Test-only helpers/fixtures must not become workflow state owners.
- No production/game runtime behavior may change.

## Test architecture decisions

### Framework

Use plain PowerShell assertions/helpers in v1.

Rationale:

- Pester is not currently installed, declared, or used by the repository;
- adding a framework dependency is unnecessary to establish the first deterministic safety net;
- the harness should remain runnable on the user's current Windows PowerShell environment with no bootstrap step beyond the repository itself.

A future task may migrate the harness to Pester if evidence shows material maintainability value.

### Location

Use `tests/workflow_scripts/`.

This keeps tests under the canonical repository test tree while isolating `.ps1` files from Python test discovery by extension and subdirectory convention.

### Production-script modification

Default expectation: **no changes** to `scripts/ai_gate.ps1` or `scripts/ai_scout.ps1`.

A production-script edit is allowed only if implementation proves an existing behavior cannot be tested through current seams and the change is strictly testability-only, behavior-neutral, and smaller than duplicating production logic. Such a change must be explicitly justified in the implementation evidence and reviewed as a potential architecture regression.

### Timeout testing

Prefer controlled short-lived fake child processes. Do not build tests around the normal 480-second production timeout. Timeout assertions must use small override timeout values and tolerate normal scheduler jitter; they must not assert millisecond-precise elapsed time.

## Non-goals

- Do not fix Markdown-wrapped `VERDICT` parsing; that belongs to `gate-payload-robustness-v1`.
- Do not preserve Gate attempt history as a behavior change.
- Do not add task.json schema linting; that belongs to `task-descriptor-schema-linting`.
- Do not change Gate reviewer sequencing after infrastructure failure.
- Do not change model ordering, fallback policy, timeout budgets, reviewer prompts, or step budgets.
- Do not add a git-command override seam merely to simplify this test task unless absolutely required by an otherwise untestable acceptance criterion.
- Do not extract/shared-refactor process logic between Gate and Scout in this task merely for cleanliness.
- Do not introduce Pester or another external test framework dependency in v1.
- Do not add Semantic Commit Agent, workflow interruptibility, orchestrator behavior, or autonomous repair.
- Do not refactor production/game code.
- Do not make live-AI integration tests part of the required regression suite.

## Acceptance criteria

1. `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` exists as the stable one-command entry point.
2. Running the harness requires no network access, live OpenCode model invocation, or external AI availability.
3. The harness returns `0` only when all cases pass and non-zero on any failure.
4. Gate tests distinguish canonical PASS, canonical BLOCK, malformed/inconsistent output, and infrastructure/process failure under current behavior.
5. Gate tests explicitly preserve the current strict rejection of Markdown-wrapped verdict headers, creating the red/green baseline for `gate-payload-robustness-v1`.
6. At least one Gate candidate-selection/fallback path is exercised through existing overrides.
7. Gate focused-test execution is exercised through the existing Python executable/argument override seams without running production tests.
8. At least one Gate artifact-safety behavior (promotion, preservation, or rollback) is tested using disposable fixtures if reachable without production behavior changes.
9. Scout tests cover successful structured output promotion, malformed output rejection, and at least one failure/fallback path.
10. Scout failure testing demonstrates invalid output does not replace valid canonical context where safely reachable.
11. Timeout/process bounding is covered with short controlled fake processes if stable; exact elapsed-time assertions are forbidden.
12. All disposable `docs/tasks/<fixture-id>/` directories and test-created runtime artifacts are removed after the suite, including on assertion failure.
13. No real task's `SPEC.md`, `CONTEXT.md`, `EVIDENCE.md`, or `reviews/*` is modified by the harness.
14. No production/game code changes occur.
15. `ai_gate.ps1` and `ai_scout.ps1` behavior remains unchanged; production-script edits, if any, are limited to strictly necessary behavior-neutral testability exposure and require explicit justification.
16. The command below passes on the implementation candidate:

```powershell
.\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1
```

17. Future workflow tasks can add regression cases to this harness without live model calls.

## Verification contract

The workflow harness is not placed in `task.json.focused_tests` because the current Gate focused-test runner is Python-oriented. Changing Gate test execution semantics is outside this task.

Therefore the Writer must, before running AI Gate:

```powershell
.\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1
```

and record the command/result in the implementation handoff or tracked task evidence as appropriate.

Then run the normal independent Gate:

```powershell
.\scripts\ai_gate.ps1 -Task workflow-script-testing-harness
```

The Gate reviewers verify the harness implementation and behavior-preservation contract; they do not replace execution of the harness itself.

## Regression risks

- tests accidentally touching canonical real-task artifacts;
- tests silently calling real OpenCode because an override was omitted;
- flaky timeout assertions tied to wall-clock precision;
- helper code duplicating production parser/process logic and drifting independently;
- using the P0 task to smuggle in parser/schema/fallback behavior changes;
- leaving temporary task directories or `.runtime` fixtures after failed tests;
- making the harness dependent on a globally installed PowerShell testing framework.

## Expected change surface

Expected:

```text
tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1
tests/workflow_scripts/... case/helper/fixture files as needed
docs/tasks/workflow-script-testing-harness/* task evidence
```

Expected unchanged:

```text
scripts/ai_gate.ps1
scripts/ai_scout.ps1
production/game code
```

Any deviation must be justified against this Final SPEC.
