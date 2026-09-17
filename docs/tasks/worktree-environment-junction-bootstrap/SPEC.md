# worktree-environment-junction-bootstrap

Status: Draft

## Goal

Provide a repository-owned, deterministic bootstrap path that makes a newly created or already registered task worktree a valid Blackfire Python environment consumer by creating and validating its worktree-local `.venv` Windows junction to the canonical shared environment.

This task closes the startup-side lifecycle gap exposed by real cleanup dogfood, where a registered task worktree had no `.venv` junction and `worktree_cleanup_safety.ps1` correctly failed closed with `MISSING_VENV`.

## Scope

- Add a narrow bootstrap primitive for a single explicit worktree path.
- Validate the target worktree exists and is a registered Git worktree before mutation.
- Validate the canonical shared Python environment exists at:
  `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- If `<worktree>\.venv` is safely absent, create a Windows junction to the canonical environment.
- If `.venv` already exists, classify it and succeed only when it is the expected junction/mount-point targeting the canonical environment exactly.
- Reject physical directories, wrong targets, unsupported reparse points, ambiguous targets, missing canonical environment, or unsafe/ambiguous worktree state.
- Verify the resulting `.venv` resolves to the canonical environment and that `.venv\Scripts\python.exe` is runnable.
- Keep the shared environment consumer-only: no package installation, removal, recreation, editable install, or dependency mutation.
- Add deterministic tests that never touch the real shared environment or real active worktrees.
- Update the branch-start workflow so environment readiness is an explicit startup invariant rather than an informal manual step.

## Known invariants

- One repository uses one canonical shared Python environment.
- Canonical physical environment:
  `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- Each runnable worktree consumes it through its own `.venv` Windows junction.
- A task worktree does not own a physical Python environment.
- Ordinary Scout/Gate/tests/runtime tasks are environment consumers and must never silently `pip install`, `pip uninstall`, recreate the venv, or fall back to system Python.
- `pip install -e .` is forbidden in the shared environment.
- `scripts/worktree_cleanup_safety.ps1` remains cleanup-side ownership for validating/detaching `.venv`; bootstrap must not weaken or duplicate teardown semantics unnecessarily.
- Unknown, conflicting, or unsafe `.venv` state fails closed.
- Windows non-interactive shell policy remains unchanged.

## Non-goals

- No general task-start orchestration in this task.
- No branch creation, fetch/pull orchestration, worktree creation, Scout launch, or remote tracking management.
- No shared-environment dependency mutation protocol.
- No Python package installation or lockfile changes unless later evidence proves they are required for the bootstrap script itself.
- No cleanup/removal behavior changes.
- No automatic repair of physical `.venv` directories or wrong-target links.
- No game runtime changes.

## Provisional acceptance criteria

1. A valid registered task worktree with no `.venv` can be bootstrapped to an exact canonical junction using one repository-owned command.
2. Re-running the bootstrap on an already-correct junction is idempotent and succeeds without replacing it.
3. A physical `.venv` directory fails closed and is preserved.
4. A reparse point targeting anything other than the canonical environment fails closed and is preserved.
5. Missing canonical environment fails before junction creation.
6. The resulting `.venv\Scripts\python.exe` is verified runnable.
7. The bootstrap performs no pip/dependency mutation and no system-Python fallback.
8. Real shared environment and unrelated worktrees are not mutated by tests.
9. Branch-start workflow references the bootstrap/readiness contract.
10. `git diff --check` and focused deterministic tests pass.

## Uncertainty

- Final script name/interface is not yet locked; likely forms include `scripts/worktree_environment_bootstrap.ps1` or a similarly narrow repository-owned primitive.
- Whether classification logic should reuse/extract a shared helper from `worktree_cleanup_safety.ps1` or remain separately implemented must be decided after reviewing nearby code/tests to avoid duplicated safety ownership.
- Exact Git registration/topology checks and test seam design should be confirmed before Final SPEC.

## Relationship to downstream work

Downstream task:

`task-start-orchestration-wrapper`

That task is expected to consume this bootstrap primitive after worktree creation/attachment. This task must therefore expose a small deterministic contract suitable for orchestration, but must not absorb the higher-level task-start workflow itself.
