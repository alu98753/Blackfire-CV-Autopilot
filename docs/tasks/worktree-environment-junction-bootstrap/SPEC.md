# worktree-environment-junction-bootstrap

Status: Final

## Goal

Provide one narrow repository-owned bootstrap primitive that makes an existing registered Git worktree a valid Blackfire Python-environment consumer.

Given an explicit worktree path, the primitive validates the canonical shared Python environment, safely reconciles the worktree-local `.venv` into the required exact Windows junction when it is absent, preserves and rejects conflicting filesystem state, and verifies that the interpreter is runnable through the worktree-local consumer path.

This closes the startup-side lifecycle gap exposed by cleanup dogfood where a registered runnable worktree had no `.venv` junction and `worktree_cleanup_safety.ps1` correctly failed closed with `MISSING_VENV`.

## Architecture boundary

The lifecycle remains deliberately split:

```text
task/branch startup orchestration
        |
        v
worktree_environment_bootstrap.ps1
        |
        v
worktree-local .venv -> canonical shared Python environment

...

task cleanup orchestration
        |
        v
worktree_cleanup_safety.ps1
        |
        v
safe .venv junction detach
```

Responsibilities are distinct:

- startup orchestration owns Git fetch/sync, branch resolution, worktree creation/attachment, upstream tracking, and later lifecycle handoff;
- this task owns only Python environment readiness for one explicit already-registered worktree;
- `worktree_cleanup_safety.ps1` remains teardown owner and alone owns cleanup-side junction detach/recovery behavior;
- Node workflow dependency bootstrap remains a separate per-worktree mechanism and is outside this task.

The downstream `task-start-orchestration-wrapper` task may invoke this primitive but must not cause this primitive to absorb orchestration responsibilities.

## Required primitive

Implement:

```powershell
scripts/worktree_environment_bootstrap.ps1 `
    -WorktreePath <path> `
    [-CanonicalEnvironmentPath <path>]
```

`CanonicalEnvironmentPath` defaults to:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

The override exists so deterministic tests can use an isolated fake canonical environment.

Do not add `-Task`, `-Branch`, `-VerifyOnly`, dependency-management, Scout, or cleanup modes to this primitive.

## Required behavior

### 1. Worktree registration boundary

Before filesystem mutation, normalize `WorktreePath` and prove that it resolves to exactly one registered path from:

```text
git worktree list --porcelain
```

An arbitrary unregistered directory must fail closed.

This primitive does not enforce:

- branch identity;
- attached versus detached HEAD;
- working-tree cleanliness;
- upstream tracking;
- fetch/pull freshness;
- whether the worktree is canonical main or a task worktree.

Those are orchestration concerns. Canonical main is allowed because it is also a runnable registered worktree consuming the same environment contract.

### 2. Canonical environment preconditions

Before creating a missing `.venv`, validate that:

- the canonical environment path exists as a directory;
- `<canonical>\Scripts\python.exe` exists as a file.

Missing or invalid canonical state must fail before junction creation.

No bootstrap path may create or repair the physical shared environment.

### 3. `.venv` reconciliation

Let:

```text
<venv> = <WorktreePath>\.venv
```

Required state behavior:

| Existing state | Result | Mutation |
| --- | --- | --- |
| `.venv` safely absent | create exact Windows directory junction to canonical target, then revalidate | create junction only |
| exact supported junction/mount-point targeting canonical environment | success after interpreter verification | none |
| physical directory | fail closed | preserve unchanged |
| junction/reparse targeting another path | fail closed | preserve unchanged |
| unsupported reparse type, including symbolic-link forms not accepted by the existing junction contract | fail closed | preserve unchanged |
| zero or multiple structured targets / ambiguous target | fail closed | preserve unchanged |
| dangling/broken or otherwise unsafe reparse state | fail closed | preserve unchanged |

Path comparison is normalized and case-insensitive according to the existing Windows cleanup contract.

Creation must produce the same junction form accepted by `worktree_cleanup_safety.ps1`. Use a deterministic Windows-compatible junction creation mechanism; do not introduce a second accepted link type merely for bootstrap convenience.

After creation, classify the resulting `.venv` again rather than assuming creation success implies contract compliance.

### 4. Interpreter verification

A successful bootstrap must execute:

```text
<worktree>\.venv\Scripts\python.exe --version
```

through the worktree-local path and require successful process completion.

Do not use system `python`, another worktree's interpreter path, `pip`, project imports, or dependency mutation as verification.

If the junction was safely created but interpreter execution subsequently fails, report failure without deleting/replacing the newly created junction or mutating the canonical environment. The next invocation remains idempotent and can re-verify the resulting state.

## Classification implementation policy

Do not introduce a new shared `worktree_venv_common.ps1` abstraction solely for this task.

The bootstrap must preserve semantic alignment with the existing classification rules in `worktree_cleanup_safety.ps1`, especially:

- Windows path normalization;
- `Get-Item -Force` handling of reparse objects;
- reparse-point detection;
- accepted Junction/MountPoint classification;
- exactly-one structured target requirement;
- normalized case-insensitive exact-target comparison.

Small, local duplication of these safety checks is acceptable at the current code size and is preferred over adding an abstraction layer without demonstrated need.

If implementation reveals a concrete correctness problem that cannot be solved without shared extraction, stop and return that evidence for spec review rather than expanding scope silently.

## Machine contract

The primitive must emit exactly one machine-readable JSON result record on stdout.

Required fields:

```text
ok
code
message
worktree
```

Success must exit `0`; failure must exit non-zero.

Machine `code` values must be stable and distinguish at least:

- ready success;
- unregistered worktree;
- missing/invalid canonical environment;
- missing canonical interpreter;
- physical `.venv` directory;
- wrong target;
- unsupported reparse type;
- ambiguous target;
- junction creation/postcondition failure;
- interpreter execution failure;
- invalid argument/internal failure.

Success metadata must distinguish whether the junction was newly created or already correct, for example through an `action` field such as `CREATED` versus `UNCHANGED`.

Exact non-zero numeric exit values are implementation detail unless an existing repository contract already requires a particular value. Reuse existing cleanup machine-code terminology where semantics genuinely match; do not force bootstrap-specific states into misleading teardown terminology.

## Known invariants

- One repository uses one canonical shared Python environment.
- Canonical physical environment:
  `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- Every runnable worktree consumes it through its own local `.venv` Windows junction.
- No Git worktree owns the physical Python environment.
- The bootstrap is an environment consumer/bootstrap-link operation, not a dependency mutator.
- It must never run `pip install`, `pip uninstall`, recreate a venv, or silently fall back to system Python.
- `pip install -e .` or equivalent worktree-specific editable binding is forbidden in the shared environment.
- Unknown, conflicting, unsupported, or ambiguous `.venv` state fails closed and is preserved.
- `worktree_cleanup_safety.ps1` remains teardown owner; its external behavior and recovery semantics must remain unchanged.
- Windows non-interactive execution policy remains unchanged: repository shell/tool invocations must follow the current `cmd.exe /d /s /c` contract where applicable.
- Node dependencies remain separate: each worktree owns untracked `node_modules`, materialized explicitly through the existing Node bootstrap contract. This task does not manage Node/npm state.

## Non-goals

- No general task-start orchestration.
- No branch creation/resolution or worktree creation/attachment.
- No fetch/pull or upstream tracking management.
- No detached-HEAD repair or branch-policy enforcement.
- No Scout/Gate launch.
- No Node/npm dependency bootstrap or `node_modules` management.
- No Python dependency installation/removal/recreation.
- No shared-environment dependency mutation protocol.
- No cleanup, detach, worktree removal, prune, or branch deletion behavior.
- No automatic repair/replacement of physical `.venv` directories, wrong-target links, unsupported reparses, or ambiguous state.
- No new shared classification abstraction unless new implementation evidence requires spec reconsideration.
- No game runtime behavior changes.

## Deterministic test strategy

Add focused Windows workflow tests, expected at:

```text
tests/test_worktree_environment_bootstrap.py
```

Tests must use isolated temporary filesystem/Git fixtures and must never mutate the real canonical environment or unrelated active worktrees.

Coverage must include at least:

1. registered temporary worktree + absent `.venv` -> exact junction created and success;
2. second invocation on the correct junction -> success, unchanged/idempotent;
3. physical `.venv` directory -> fail closed and preserved;
4. wrong-target junction -> fail closed and preserved;
5. unsupported reparse type where supported by the Windows test environment -> fail closed and preserved;
6. ambiguous/unsafe target classification where deterministically constructible or through a bounded test seam;
7. missing canonical environment -> fail before mutation;
8. missing canonical interpreter -> fail before junction creation;
9. unregistered directory -> fail before mutation;
10. interpreter execution failure -> non-zero failure without dependency mutation;
11. successful interpreter verification occurs through the worktree-local `.venv\Scripts\python.exe` path;
12. existing `worktree_cleanup_safety.ps1` behavior/tests remain green.

Prefer real temporary Git worktrees and real Windows junctions when deterministic and safe. A bounded process/test seam may be used where creating a specific OS-level failure state is impractical, but production behavior must still exercise real Git/worktree and reparse semantics.

Test fixtures may point `CanonicalEnvironmentPath` at an isolated fake environment and may use a controlled executable/launcher sufficient to verify the process contract. They must not depend on or mutate the production shared environment.

## Acceptance criteria

1. `scripts/worktree_environment_bootstrap.ps1 -WorktreePath <registered-path>` creates an exact canonical Windows junction when `.venv` is safely absent.
2. Re-running against an already-correct canonical junction succeeds without replacing or mutating it.
3. The primitive proves the explicit path is a registered Git worktree before filesystem mutation.
4. Missing canonical environment or missing canonical `Scripts\python.exe` fails before junction creation.
5. Physical `.venv`, wrong-target junction/reparse, unsupported reparse, ambiguous target, and unsafe/broken reparse states fail closed and are preserved.
6. After creation, the junction is re-classified and must satisfy the exact same target/type contract before success can continue.
7. Success requires `<worktree>\.venv\Scripts\python.exe --version` to execute successfully through the worktree-local path.
8. No code path performs pip/package installation, uninstall, venv recreation, editable install, system-Python fallback, or shared-environment mutation.
9. The command emits exactly one JSON result record to stdout, exits `0` on success/non-zero on failure, and exposes stable machine failure codes plus created-versus-unchanged success metadata.
10. `worktree_cleanup_safety.ps1` remains teardown owner and its existing external behavior/tests remain unchanged.
11. `branch_start_workflow` is updated so missing/invalid `.venv` uses this finalized repository-owned bootstrap contract rather than informal/manual Python environment repair guidance.
12. Node/npm handling remains outside this primitive.
13. Focused deterministic tests cover creation, idempotency, fail-closed states, registration validation, interpreter verification, and isolation from the real shared environment.
14. `git diff --check` and focused deterministic tests pass.

## Relationship to downstream work

Downstream task:

```text
task-start-orchestration-wrapper
```

After this task is implemented, verified, and merged, the downstream task must re-survey latest `main`, this finalized bootstrap interface, `branch_start_workflow`, and the existing Node bootstrap contract before finalizing its own orchestration rules.

Expected architecture direction only:

```text
task_start.ps1
    -> Git/worktree startup orchestration
    -> worktree_environment_bootstrap.ps1
    -> explicit Node workflow dependency readiness as decided by Task 2
    -> lifecycle handoff
```

Task 2 remains Draft until that re-survey occurs.
