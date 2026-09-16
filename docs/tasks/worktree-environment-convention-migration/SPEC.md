# Worktree Environment Convention Migration

Status: Final

## Decision Summary

This task standardizes Blackfire local development around two deliberately separate lifecycles:

1. **Git lifecycle** — one project-scoped permanent `main` worktree plus temporary task worktrees.
2. **Python environment lifecycle** — one repository-global shared virtual environment stored outside every Git worktree and consumed through worktree-local `.venv` junctions.

The selected convention is now validated on the local machine. This task does **not** design the future shared-environment mutation protocol; that remains deferred to `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`.

## Final Target Convention

```text
E:\Side_Project\
├─ VenvPools\
│  └─ .venvs-Blackfire-CV-Autopilot\      <- single physical canonical Python environment
│
└─ Blackfire-CV-Autopilot\
   ├─ BlackfireCrusade_tool\               <- permanent main worktree + runtime/CV home
   │  └─ .venv -> junction to canonical env
   │
   └─ worktrees\
      └─ <task-id>\                         <- temporary task worktree
         └─ .venv -> junction to canonical env
```

Legacy task worktrees that were already active under `E:\Side_Project\task-*` may remain in place until their own lifecycle completes. They must not be moved merely for cosmetic directory consistency.

## Established Migration Facts

The following are no longer assumptions:

- `temp-main` has been retired and removed.
- `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` is the local `main` worktree and canonical runtime/CV validation home.
- `main` was synchronized to fetched `origin/main` before topology migration.
- existing linked worktrees survived the primary-worktree move through `git worktree repair` with branch, HEAD, and dirty state preserved.
- new task worktrees can be created under `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\`.
- the migration task itself is located under that project-scoped `worktrees` directory.
- one physical Python environment exists at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- main, migration-task, reviewer-task, and watchdog-task `.venv` paths are valid Windows junctions directly targeting that canonical environment.
- Python 3.11.2 starts successfully through the relocated canonical environment.
- Blackfire runtime dependencies validated before relocation (`cv2`, `numpy`, `PIL`, `win32api`) still import successfully after relocation.
- `pytest` was absent before relocation and remains absent; it was not installed as part of this task.
- branch-local source resolution was validated: `config.py` resolves from the current worktree rather than being bound to another worktree through the shared environment.
- `.venv` remains ignored/untracked in all verified worktrees.
- no `pip install`, `pip uninstall`, environment rebuild, or dependency mutation was performed during migration.

## Problem Being Solved

The old workflow encoded two competing canonical locations:

```text
Git/main/integration authority -> E:\Side_Project\temp-main
runtime/CV/development home     -> E:\Side_Project\BlackfireCrusade_tool
```

This split allowed the runtime home to be detached or behind current `main` while another worktree represented Git integration state. Multiple durable workflow documents also encoded that split as policy.

The old environment layout also made the single physical `.venv` belong to one Git worktree path, so linked worktrees depended on that worktree's location. Moving the main worktree broke those legacy junctions and confirmed that environment ownership had to be separated from Git-worktree ownership.

## Architecture Contract

### 1. Exactly one permanent local main worktree

`E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` is the permanent local checkout of `main`.

It is also the canonical integrated runtime/CV validation home.

No `temp-main`, `test-main`, or other second permanent-main convention may coexist as active policy.

### 2. Task worktrees are project-scoped, branch-scoped, and temporary

New task worktrees default to:

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

A task worktree owns only its task branch during active work. Before Scout/Gate/tests/implementation, local state must be validated rather than inferred.

Existing legacy task worktrees may finish in their original `E:\Side_Project\task-*` paths. Dirty or active worktrees must not be moved solely to satisfy the new directory aesthetic.

### 3. One canonical shared Python environment

Canonical physical environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree exposes the conventional local path:

```text
.\.venv\Scripts\python.exe
```

via a direct Windows junction to that canonical environment.

Normal tools should consume the worktree-local `.venv` path and should not need to know the physical VenvPools location.

### 4. Shared environment is intentionally not branch-isolated

The project deliberately accepts one shared environment across worktrees because dependency mutation is currently rare and environment setup is not the current operational bottleneck.

This means dependency mutation must not be treated as an ordinary branch-local action.

A future safe mutation protocol is explicitly deferred to `shared-environment-mutation-protocol`.

### 5. No worktree-specific editable install

The shared environment must not be bound to one worktree through `pip install -e .` or equivalent editable-install/source-binding behavior.

Tests/runtime must resolve project source from the current worktree. The migration validation confirmed this for `config.py` from both main and the migration task worktree.

### 6. Normal workflows consume, not provision, the environment

Scout, Gate, tests, runtime validation, and ordinary source-code tasks are environment consumers.

They must not silently:

- `pip install`;
- `pip uninstall`;
- recreate the venv;
- mutate dependencies merely to make a command pass;
- fall back to unrelated system Python when repository automation is expected to use `.venv`.

Current evidence does not require changes to `scripts/ai_gate.ps1` or `scripts/ai_scout.ps1` for this task.

### 7. Git worktree safety remains mandatory

Before branch switch, migration, cleanup, Scout, or Gate when topology matters:

- inspect `git worktree list --porcelain`;
- respect Git branch exclusivity;
- preserve dirty/staged/untracked state;
- do not use `reset --hard`, `clean -fd`, force deletion, or implicit stash as shortcuts;
- `git fetch origin` must occur before treating `origin/main` as fresh remote truth;
- `main` synchronization uses non-destructive fast-forward semantics where applicable.

### 8. Windows execution policy remains unchanged

Non-interactive agent commands use:

```text
cmd.exe /d /s /c "<command>"
```

Commands must not wait for stdin. PowerShell remains wrapped through `cmd.exe` according to the repository Windows-shell policy.

## Final Implementation Scope

Production implementation for this task is intentionally documentation/skill-only.

### Must change

- `docs/architecture/ai_development_workflow.md`
  - replace the old permanent `temp-main` baseline convention with the new project-scoped topology;
  - define `BlackfireCrusade_tool` as permanent local `main` + runtime/CV home;
  - define the external shared-environment ownership model at the architecture/workflow level;
  - retain GitHub as the primary handoff surface and existing authority boundaries.

- `.agents/skills/branch_start_workflow/SKILL.md`
  - remove the rule reserving `main` for `temp-main`;
  - default new task worktrees to `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`;
  - require worktree-topology validation rather than assuming branch ownership;
  - preserve remote-to-local sync and branch-exclusivity safety.

- `.agents/skills/branch_completion_workflow/SKILL.md`
  - remove permanent dual-worktree assumptions;
  - use `BlackfireCrusade_tool` as local permanent `main`/baseline/runtime surface;
  - stop cross-referencing an interpreter physically owned by another worktree;
  - use the current worktree's `.venv` consumer path;
  - preserve dirty-worktree safety, merge authority, and non-destructive synchronization semantics.

### May change only if wording must be aligned

- `docs/tasks/BACKLOG.md`
  - keep `shared-environment-mutation-protocol` as pending technical debt; do not promote or implement it in this task.

### Explicitly out of scope

- production source code;
- gameplay/runtime/CV behavior;
- `scripts/ai_gate.ps1`;
- `scripts/ai_scout.ps1`;
- `requirements.txt`;
- installing `pytest` or any other package;
- moving active legacy task worktrees;
- implementing environment locking, atomic swap, or mutation orchestration;
- rewriting historical task specs solely to erase historical `temp-main` references.

## Acceptance Criteria

1. Active canonical workflow documentation defines exactly one permanent local main/runtime worktree: `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`.
2. New task worktrees default to `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`.
3. Active branch-start and branch-completion skills no longer assign permanent `main` ownership to `temp-main` or forbid `BlackfireCrusade_tool` from owning `main`.
4. Legacy task worktrees are explicitly allowed to remain at old `E:\Side_Project\task-*` paths until completion; dirty/active worktrees are not moved for cosmetic consistency.
5. The external canonical Python environment is documented at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
6. Runnable worktrees are documented as consumers through their own `.venv` junction; normal commands use worktree-local `.venv\Scripts\python.exe` paths.
7. No active workflow documentation instructs one worktree to execute another worktree's Python interpreter path.
8. No active workflow introduces system-Python fallback, automatic environment creation, or dependency installation as a side effect of Scout/Gate/tests.
9. Worktree-specific `pip install -e .` into the shared environment is explicitly prohibited.
10. `shared-environment-mutation-protocol` remains deferred and is not implemented by this task.
11. Branch-start/branch-completion instructions preserve branch exclusivity, dirty-state protection, remote freshness, and non-destructive synchronization semantics.
12. Historical task specs may retain old topology as history but must not be treated as active canonical authority.
13. The implementation changes only workflow documentation/skills unless a newly discovered contradiction requires explicit contract-owner approval.
14. No production gameplay behavior changes.

## Validation Requirements

Because the final tracked implementation is documentation/skill-only:

- inspect the final diff for obsolete active `temp-main` rules;
- search active workflow/skill surfaces for `temp-main`, old flattened task path assumptions, and cross-worktree interpreter paths;
- verify the three canonical files agree on the same topology and environment ownership;
- verify no production/script/test files changed unexpectedly;
- preserve the already validated local topology/environment evidence recorded in this task.

No full gameplay regression suite is required solely for these documentation/skill changes.

## Deferred Technical Debt: `shared-environment-mutation-protocol`

This future task is triggered when any of the following becomes real work:

- add/remove/upgrade a Python dependency;
- recreate or materially mutate the canonical shared venv;
- concurrent environment mutation becomes necessary;
- environment drift becomes a demonstrated source of failures.

Expected future investigation may compare locking, in-place sync, rebuild + atomic swap, dependency declaration validation, uv/equivalent tooling, or replacing the singleton model. None is preselected here.

## Non-Goals

- per-worktree virtual environments;
- dependency-fingerprint environments;
- uv/Poetry/Conda/container migration for its own sake;
- speculative environment-mutation machinery;
- moving dirty/active legacy worktrees;
- changing OpenCode CLI/provider compatibility;
- changing merge authority;
- rewriting old historical task records purely for cosmetic consistency.
