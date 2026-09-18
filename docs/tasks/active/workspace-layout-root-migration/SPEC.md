# Workspace Layout Root Migration

Status: Final

## Goal

Migrate the canonical local workspace convention from:

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\
└─ worktrees\
```

to:

```text
E:\Side_Project\
├─ Blackfire-CV-Autopilot\
├─ Blackfire-CV-Autopilot-worktrees\
└─ VenvPools\
   └─ .venvs-Blackfire-CV-Autopilot\
```

The permanent local `main` worktree becomes the repository root itself:

```text
E:\Side_Project\Blackfire-CV-Autopilot
```

New temporary task worktrees become siblings:

```text
E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>
```

The migration must preserve Git/worktree safety, the external shared Python environment contract, and ignored local runtime/user data already present in the current main checkout.

## Canonical Workspace Topology

The canonical post-migration workspace is:

```text
E:\Side_Project\
├─ Blackfire-CV-Autopilot\
│  └─ .venv -> junction to E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
│
├─ Blackfire-CV-Autopilot-worktrees\
│  └─ <task-id>\
│     └─ .venv -> junction to E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
│
└─ VenvPools\
   └─ .venvs-Blackfire-CV-Autopilot\   <- single physical canonical Python environment
```

Ownership semantics:

- `Blackfire-CV-Autopilot` is the permanent attached `main` worktree and integrated runtime/CV validation home.
- `Blackfire-CV-Autopilot-worktrees\<task-id>` contains temporary branch-scoped task worktrees.
- `VenvPools\.venvs-Blackfire-CV-Autopilot` is external shared Python environment storage, not a Git worktree.
- Each runnable worktree exposes its own local `.venv` junction to the same canonical physical environment.
- `node_modules` is **not** a top-level shared workspace component. When a worktree needs Node workflow tooling, that worktree owns its own untracked `node_modules`, with `package.json` / `package-lock.json` as dependency SSOT and explicit `scripts/bootstrap_node_workflow_deps.ps1` bootstrap.
- This task does not change Node dependency ownership, package metadata, or bootstrap behavior.

## Evidence Summary

Current task branch contains Scout evidence in:

```text
docs/tasks/active/workspace-layout-root-migration/CONTEXT.md
```

Confirmed findings:

- `scripts/task_start.ps1` already discovers canonical main from Git topology/common-dir metadata; it does not hardcode `BlackfireCrusade_tool`.
- Its only path-coupled defect is the default worktree-root derivation:
  ```text
  <parent-of-main>\worktrees
  ```
  which would become `E:\Side_Project\worktrees` after the main checkout moves.
- `scripts/task_cleanup.ps1` is layout-agnostic for this migration and does not require a code change.
- Existing task-start behavioral tests inject `TASK_START_WORKTREES_ROOT_OVERRIDE`; there is no regression test for the default sibling-root derivation.
- Canonical architecture/workflow docs still describe the old nested layout.
- `test_behavior_pause_resume.py` contains `BlackfireCrusade_tool` only inside third-party-window title examples. The rejection contract is not based on that folder name, so this is not a migration blocker and is out of scope.
- The current linked-worktree topology is non-empty only because this task itself is active. The migration therefore uses lifecycle ordering rather than linked-worktree metadata repair.

## Responsibility Boundary

This task owns:

- the repository contract for the new local workspace layout;
- `task_start.ps1` default worktree-root derivation;
- focused regression coverage for that default;
- canonical workflow/documentation alignment;
- a bounded local migration procedure executed only after this task is merged and cleaned up.

This task does not own:

- general machine bootstrap;
- dependency installation or environment mutation;
- gameplay/runtime/CV behavior;
- personal-data synchronization across computers;
- generic Git worktree metadata repair;
- migration of active/dirty linked worktrees.

## Known Invariants

1. Permanent local `main` remains attached to branch `main`.
2. Git worktree topology is authoritative; branch ownership is never inferred from stale path memory.
3. Formal startup remains:
   ```text
   scripts/task_start.ps1 -Task <task-id>
   ```
4. Formal cleanup remains:
   ```text
   scripts/task_cleanup.ps1 -Task <task-id>
   ```
5. One repository uses one canonical shared Python environment:
   ```text
   E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
   ```
6. Runnable worktrees consume that environment through their own `.venv` Windows junction.
7. No `pip install`, `pip uninstall`, venv recreation, or system-Python fallback is permitted in this task.
8. No `reset --hard`, `clean -fd`, forced worktree removal, or blind prune.
9. Ignored local state inside the current main checkout must be preserved by moving the existing checkout as a whole rather than replacing it with a fresh clone.
10. Existing `.venv` junction target semantics must remain unchanged.
11. Physical main-directory migration occurs only after this task is merged to `main` and the task worktree has been safely cleaned up.
12. Before physical migration, there must be no remaining linked task worktrees that depend on the old primary-worktree location.

## Implementation Scope

### Must change

- `scripts/task_start.ps1`
  - keep topology-driven canonical-main discovery;
  - keep `TASK_START_WORKTREES_ROOT_OVERRIDE`;
  - when no override is supplied, derive the sibling worktree root from the discovered canonical main path so:
    ```text
    E:\Side_Project\Blackfire-CV-Autopilot
    ->
    E:\Side_Project\Blackfire-CV-Autopilot-worktrees
    ```
  - do not hardcode `E:\Side_Project` solely to locate main.

- `tests/test_task_start_behavioral.py`
  - add focused coverage for the default, override-free sibling-root derivation;
  - preserve existing override-based fixtures and fail-closed behavior;
  - fixture naming may be normalized away from `BlackfireCrusade_tool` where it improves clarity.

- `docs/architecture/ai_development_workflow.md`
  - define the complete new canonical topology including main, sibling task-worktree root, external `VenvPools`, and worktree-local `.venv` junction ownership;
  - retain old nested layout only as historical migration context if needed;
  - document post-merge cleanup-before-move ordering.

- `.agents/skills/branch_start_workflow/SKILL.md`
  - use the new canonical paths;
  - show `Blackfire-CV-Autopilot`, `Blackfire-CV-Autopilot-worktrees`, and `VenvPools` as siblings under `E:\Side_Project`;
  - preserve per-worktree `.venv` consumer semantics.

- `.agents/skills/branch_completion_workflow/SKILL.md`
  - use the new canonical paths;
  - show `Blackfire-CV-Autopilot`, `Blackfire-CV-Autopilot-worktrees`, and `VenvPools` as siblings under `E:\Side_Project`;
  - preserve per-worktree `.venv` consumer semantics;
  - keep permanent-main and cleanup safety semantics unchanged.

- `scripts/README.md`
  - align any active canonical path guidance affected by this migration.

- `docs/tasks/active/workspace-layout-root-migration/`
  - keep SPEC/task metadata aligned.

### May change only if required by focused evidence

- `tests/test_task_cleanup_behavioral.py`
  - fixture naming only; no cleanup behavior redesign.

### Explicitly unchanged

- `scripts/task_cleanup.ps1`
- `scripts/worktree_environment_bootstrap.ps1`
- gameplay/runtime/CV production code
- `tests/test_behavior_pause_resume.py`
- shared environment path
- Node workflow bootstrap

## Required Default Derivation

Without `TASK_START_WORKTREES_ROOT_OVERRIDE`:

```text
canonical main:
E:\Side_Project\Blackfire-CV-Autopilot

default worktrees root:
E:\Side_Project\Blackfire-CV-Autopilot-worktrees

task:
E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>
```

The derivation must be based on the discovered canonical main directory name/location, not a second independent hardcoded project path.

## Legacy / Active Worktree Policy

Do not move an active or dirty worktree merely to normalize paths.

For this migration task specifically:

1. implement and verify in its current task worktree;
2. merge the task branch to `main`;
3. run normal:
   ```text
   scripts/task_cleanup.ps1 -Task workspace-layout-root-migration
   ```
4. confirm `git worktree list --porcelain` shows no linked task worktrees that depend on the old primary-worktree path;
5. only then perform the physical main-directory migration.

If any linked worktree still exists at step 4, physical migration is blocked until that worktree completes or is safely handled through its own lifecycle. This task does not repair linked-worktree metadata in place.

## Local Physical Migration Procedure

The physical move is an operator step after integration and cleanup, not production implementation performed by Gemini.

Starting state:

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\
└─ worktrees\
```

Target state:

```text
E:\Side_Project\
├─ Blackfire-CV-Autopilot\
├─ Blackfire-CV-Autopilot-worktrees\
└─ VenvPools\
```

Required migration behavior:

- preserve the complete existing `BlackfireCrusade_tool` checkout as a unit, including:
  - `.git`;
  - ignored `user_data/`;
  - ignored `config/local.toml`;
  - ignored `.runtime/`;
  - ignored `scratch/`;
  - ignored local tools;
  - ignored `node_modules/` if present;
  - the `.venv` junction;
- do not replace the checkout with a fresh clone;
- do not selectively copy only tracked files;
- do not mutate the canonical Python environment.

A safe bounded move may temporarily rename the current outer container to free the final `Blackfire-CV-Autopilot` name, then move the complete former `BlackfireCrusade_tool` checkout into that final location.

## Post-Migration Verification

After physical relocation, verify:

1. `git status` succeeds and shows expected cleanliness/state.
2. `git worktree list --porcelain` identifies:
   ```text
   E:\Side_Project\Blackfire-CV-Autopilot
   ```
   as canonical main.
3. main is attached to branch `main`.
4. `.venv` is still the expected junction to:
   ```text
   E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
   ```
5. `.\.venv\Scripts\python.exe` starts successfully.
6. normal runtime/import validation still works from the relocated main checkout.
7. a subsequent formal task start resolves its default path under:
   ```text
   E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>
   ```

## Acceptance Criteria

1. Canonical docs define `E:\Side_Project\Blackfire-CV-Autopilot` as permanent local main/runtime home.
2. Canonical docs define `E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>` as the default new task-worktree namespace.
3. `task_start.ps1` derives that sibling namespace by default from canonical main.
4. `TASK_START_WORKTREES_ROOT_OVERRIDE` remains supported.
5. Main discovery remains topology-driven and does not depend on the historical `BlackfireCrusade_tool` name.
6. Existing startup fail-closed semantics remain unchanged.
7. `task_cleanup.ps1` behavior remains unchanged.
8. Focused tests prove the default sibling-root derivation without relying on the override.
9. Architecture/start/completion workflow docs no longer present the nested layout as canonical current state.
10. The migration procedure preserves the full existing checkout and ignored local state.
11. The migration procedure requires task cleanup / zero relevant linked worktrees before physical main relocation.
12. No linked-worktree metadata repair mechanism is introduced.
13. No ignored personal data, secret, runtime state, local tools, `.venv`, or `node_modules` is committed.
14. No Python environment dependency mutation occurs.
15. Canonical architecture/start/completion documentation shows `VenvPools` as an external sibling of the main repo and task-worktree root, not nested inside either.
16. Canonical documentation shows main/task `.venv` entries as worktree-local junction consumers of the single physical environment at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
17. Node `node_modules` remains per-worktree untracked state and is not redefined as shared workspace infrastructure; no npm/package/bootstrap behavior changes are introduced.

## Focused Verification

Run at minimum:

```text
python -m unittest tests.test_task_start_behavioral
python -m unittest tests.test_task_cleanup_behavioral
python -m unittest tests.test_worktree_environment_bootstrap
```

If repository wrapper policy requires the canonical worktree-local Python path, use the task worktree's own `.venv\Scripts\python.exe`.

Gate/reviewer evidence may be run afterward according to the normal lifecycle.

## Non-goals

- machine bootstrap for arbitrary new computers;
- cross-platform workspace discovery;
- automatic migration of active worktrees;
- generic worktree metadata repair;
- shared-environment rebuild/mutation;
- Node dependency ownership/package/bootstrap changes; existing per-worktree `node_modules` policy remains unchanged;
- personal `user_data` cloud/private-repo synchronization;
- gameplay/runtime/CV behavior changes;
- modifying pause/resume window-focus behavior.

## Final Decision

The implementation is intentionally small:

```text
one default-path derivation change
+ one focused regression test family
+ canonical workflow/docs alignment
+ explicit post-merge physical migration procedure
```

Production implementation may begin.
