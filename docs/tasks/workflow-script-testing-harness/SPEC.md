# workflow-script-testing-harness

Status: Draft

## Goal

Create a deterministic offline regression-testing harness for the AI workflow scripts so `scripts/ai_gate.ps1` and `scripts/ai_scout.ps1` can be changed safely without invoking live OpenCode models or depending on external AI availability.

This task is a reliability prerequisite. It establishes testability around existing workflow behavior; it does not change that behavior.

## Problem statement

The production pilot and retrospective confirmed that the workflow scripts contain non-trivial process, parser, timeout, fallback, and artifact-promotion logic, while no dedicated repository test harness currently exercises those behaviors offline.

Both scripts already expose explicit internal test seams:

- `scripts/ai_gate.ps1`
  - `_ReviewerExecutableOverride`
  - `_ReviewerArgumentsOverride`
  - `_SpecReviewerArgumentsOverride`
  - `_RegressionReviewerArgumentsOverride`
  - `_ReviewCandidatesOverride`
  - `_PythonExecutableOverride`
  - `_PythonArgumentsOverride`
  - `_FailPromotionOnTarget`
- `scripts/ai_scout.ps1`
  - `_ExecutableOverride`
  - `_ArgumentsOverride`
  - `_ModelCandidatesOverride`

The harness should use these seams to verify current contracts deterministically without live AI calls.

## Initial scope

- Establish a repository-native test entry point for workflow-script regression tests.
- Add deterministic tests for representative existing `ai_gate.ps1` behavior, including as practical:
  - canonical PASS/BLOCK payload classification;
  - malformed/structurally inconsistent reviewer output rejection;
  - normal review candidate selection / configured override behavior;
  - bounded child-process success/failure/timeout behavior;
  - focused-test execution seam behavior;
  - artifact promotion / rollback seam behavior where safely testable.
- Add deterministic tests for representative existing `ai_scout.ps1` behavior, including as practical:
  - model candidate resolution and override behavior;
  - child-process success/failure/timeout behavior;
  - canonical `CONTEXT.md` promotion safety where testable.
- Ensure tests run without network access, OpenCode model inference, or production/game execution.
- Document a stable command that future workflow tasks can run as their focused regression suite.

## Known invariants

- This task is behavior-preserving for the workflow scripts.
- Existing Gate exit-code semantics remain authoritative:
  - `0` = PASS
  - `1` = INFRASTRUCTURE_BLOCKED
  - `2` = CANDIDATE_BLOCKED
- Existing Scout/Gate model-routing and fallback semantics must not change.
- Existing timeout values and kill-confirmation semantics must not change.
- Existing review payload acceptance/rejection rules must not change in this task, including the currently strict Markdown behavior.
- Existing artifact promotion / rollback semantics must not change.
- Tests must not invoke live OpenCode reviewers or require external model/network availability.
- The harness must exercise public script behavior or existing explicit internal test seams rather than duplicating production logic into a second implementation.
- Test-only fixtures/helpers must not become workflow state owners.

## Non-goals

- Do not fix Markdown-wrapped `VERDICT` parsing; that belongs to `gate-payload-robustness-v1`.
- Do not preserve Gate attempt history in this task unless a minimal test fixture is required; behavior change belongs to the later robustness task.
- Do not add task.json schema linting; that belongs to `task-descriptor-schema-linting`.
- Do not change Gate reviewer sequencing after infrastructure failure.
- Do not change model ordering, fallback policy, timeout budgets, reviewer prompts, or step budgets.
- Do not add Semantic Commit Agent, workflow interruptibility, orchestrator behavior, or autonomous repair.
- Do not refactor production/game code.
- Do not introduce a live-AI integration test dependency as the primary regression harness.

## Provisional acceptance criteria

1. A deterministic workflow-script test harness exists in the repository and can be run locally with one documented command.
2. The harness requires no live OpenCode model call, external AI service, or network access.
3. Tests verify representative existing Gate behavior through real script execution and/or existing test seams rather than copied parser/process logic.
4. Tests distinguish valid reviewer PASS, valid reviewer BLOCK, malformed reviewer output, and infrastructure/process failure according to current behavior.
5. Tests cover at least one normal candidate-resolution path and one failure/fallback-related path for Gate or Scout without changing fallback semantics.
6. Tests cover bounded process behavior sufficiently to detect regression in success/failure/timeout classification where feasible without brittle wall-clock assumptions.
7. Tests cover at least one canonical artifact safety property (promotion, preservation, or rollback) without risking real task artifacts.
8. Tests isolate temporary fixtures/task packages so running the harness does not modify canonical repository task evidence.
9. Existing `ai_gate.ps1` / `ai_scout.ps1` production semantics remain unchanged except for strictly necessary testability exposure that is behavior-neutral and justified by the Final SPEC.
10. Future tasks such as `gate-payload-robustness-v1` can add a regression case to this harness before changing parser behavior.
11. The chosen test framework/structure is compatible with the project's Windows PowerShell development environment and does not add an unnecessary heavy dependency.
12. No production/game runtime behavior changes occur.

## Uncertainty to resolve with Scout

- Whether the narrowest harness should use plain PowerShell assertions, Pester, or an existing repository test convention not found in the lightweight survey.
- Whether existing script-level internal seams are sufficient as-is or a tiny behavior-neutral extraction/import seam is needed to make specific functions testable.
- Where workflow-script tests should live (`tests/`, `scripts/tests/`, or another existing convention) without confusing Python `unittest` discovery.
- Which current Gate/Scout behaviors can be tested safely through full script invocation versus function-level/helper-level tests.
- How to create temporary task packages and fake child processes portably on the user's Windows environment.
- Whether timeout/kill-confirmation behavior can be tested deterministically without making the suite slow or flaky.
- Whether artifact-promotion rollback should be covered in v1 of the harness or deferred if it requires invasive test plumbing.

## Scout questions

1. Locate any existing repository conventions for PowerShell/script tests, fixtures, temporary directories, or command wrappers.
2. Map the existing explicit test seams in `ai_gate.ps1` and `ai_scout.ps1` to the narrowest deterministic regression cases.
3. Identify which behaviors require full process invocation and which can be tested through isolated functions without copying production logic.
4. Determine whether Pester is already available/declared; if not, assess whether adding it is justified versus a dependency-free PowerShell harness.
5. Identify the minimal production-script change surface, if any, needed purely for testability while preserving behavior.
6. Propose a focused test command suitable for `task.json` and future workflow tasks.
7. Flag any test design that could accidentally mutate canonical `docs/tasks/*` artifacts or depend on live AI/network state.

## Lifecycle gate

This SPEC remains Draft until OpenCode Scout generates and pushes `CONTEXT.md`, and ChatGPT + user re-evaluate the evidence. Gemini/Antigravity must not implement the harness before the SPEC becomes Final.
