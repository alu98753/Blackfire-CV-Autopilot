# Worktree Environment Convention Migration

Status: Final

## Decision Summary

Blackfire local development uses two separate lifecycles:

1. **Git lifecycle** — one project-scoped permanent `main` worktree plus temporary task worktrees.
2. **Python environment lifecycle** — one repository-global shared virtual environment stored outside all Git worktrees and consumed through worktree-local `.venv` junctions.

The local machine has already validated this convention. Safe mutation of the shared Python environment remains deferred to `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`.

## Canonical Topology

```text
E:\Side_Project\
├─ VenvPools\
│  └─ .venvs-Blackfire-CV-Autopilot\      <- single physical canonical Python environment
│
└─ Blackfire-CV-Autopilot\
   ├─ BlackfireCrusade_tool\               <- permanent main + runtime/CV home
   │  └─ .venv -> junction to canonical env
   │
   └─ worktrees\
      └─ <task-id>\                         <- temporary task worktree
         └─ .venv -> junction to canonical env
```

Existing active task worktrees may remain at their current paths until their task lifecycle completes. New task worktrees use the canonical project-scoped namespace.

## Verified Local Facts

- `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` is the local `main` worktree and canonical runtime/CV validation home.
- `main` was synchronized to fetched `origin/main` before topology migration.
- linked worktree metadata was repaired after the primary-worktree path change while preserving branch, HEAD, and dirty state.
- new task worktrees can be created under `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\`.
- this task worktree is located under that project-scoped `worktrees` directory.
- one physical Python environment exists at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- verified runnable worktrees expose valid Windows `.venv` junctions directly targeting that canonical environment.
- Python 3.11.2 starts successfully through the relocated canonical environment.
- Blackfire runtime dependencies validated before relocation (`cv2`, `numpy`, `PIL`, `win32api`) still import successfully after relocation.
- branch-local source resolution was validated: `config.py` resolves from the current worktree rather than another worktree.
- `.venv` remains ignored/untracked in verified worktrees.
- no `pip install`, `pip uninstall`, environment rebuild, or dependency mutation was performed during migration.

## Architecture Contract

### 1. One permanent local main worktree

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

is the permanent local checkout of `main` and the canonical integrated runtime/CV validation home.

### 2. Task worktrees are project-scoped and temporary

New task worktrees default to:

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

Each task worktree owns its task branch during active work. Before Scout, Gate, tests, implementation, branch switch, or cleanup, inspect actual worktree ownership instead of inferring it from path memory.

Active worktrees are not moved solely for directory aesthetics.

### 3. One canonical shared Python environment

Canonical physical environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree exposes:

```text
.\.venv\Scripts\python.exe
```

through a direct Windows junction to that environment.

Normal tools consume the worktree-local `.venv` path rather than another worktree's interpreter path.

### 4. Shared environment is intentionally repository-global

The project accepts one shared dependency state across worktrees because dependency mutation is rare and repeated provisioning is not the current operational goal.

Dependency mutation is therefore a repository-level environment operation, not ordinary branch-local work.

### 5. No worktree-specific editable install

The shared environment must not be bound to one worktree through `pip install -e .` or equivalent editable/source-binding behavior.

Tests/runtime resolve project source from the current worktree.

### 6. Normal workflows consume, not provision, the environment

Scout, Gate, tests, runtime validation, and ordinary source-code tasks are environment consumers.

They must not silently:

- install/uninstall dependencies;
- recreate the venv;
- mutate dependencies merely to make commands succeed;
- fall back to unrelated system Python when repository automation expects `.venv`.

Current evidence does not require executable changes to `scripts/ai_gate.ps1` or `scripts/ai_scout.ps1`.

### 7. Git worktree safety

When topology matters:

- inspect `git worktree list --porcelain`;
- respect branch exclusivity;
- preserve dirty/staged/untracked state;
- do not use `reset --hard`, `clean -fd`, force deletion, or implicit stash as shortcuts;
- `git fetch origin` before treating `origin/main` as fresh remote truth;
- use non-destructive fast-forward synchronization where applicable.

### 8. Windows execution policy

Non-interactive agent commands use:

```text
cmd.exe /d /s /c "<command>"
```

Commands must not wait for stdin. PowerShell automation remains wrapped through `cmd.exe` according to repository policy.

## Final Implementation Scope

### Must change

- `docs/architecture/ai_development_workflow.md`
  - own the canonical workspace topology, environment ownership, task lifecycle, and authority boundaries.

- `.agents/skills/branch_start_workflow/SKILL.md`
  - create/sync new task worktrees under the project-scoped namespace;
  - validate worktree ownership before branch operations;
  - use worktree-local `.venv` consumer paths.

- `.agents/skills/branch_completion_workflow/SKILL.md`
  - use `BlackfireCrusade_tool` as permanent local `main`/baseline/runtime surface;
  - execute each baseline through that worktree's own `.venv` consumer path;
  - preserve dirty-state safety, merge authority, non-destructive synchronization, and safe cleanup semantics.

### May change only for SSOT wording alignment

- `docs/tasks/BACKLOG.md`
  - retain `shared-environment-mutation-protocol` as pending technical debt.

### Explicitly out of scope

- production source code;
- gameplay/runtime/CV behavior;
- `scripts/ai_gate.ps1`;
- `scripts/ai_scout.ps1`;
- `requirements.txt`;
- dependency installation;
- moving active task worktrees;
- environment locking, atomic swap, or mutation orchestration;
- OpenCode compatibility/provider changes.

## Acceptance Criteria

1. Canonical workflow documentation defines exactly one permanent local main/runtime worktree: `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`.
2. New task worktrees default to `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`.
3. `branch_start_workflow` and `branch_completion_workflow` agree with the architecture SSOT.
4. Existing active worktrees may finish at their current paths without forced relocation.
5. The external canonical Python environment is documented at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
6. Runnable worktrees are documented as consumers through their own `.venv` junction.
7. No canonical workflow instructs one worktree to execute another worktree's interpreter path.
8. No canonical workflow introduces system-Python fallback, automatic environment creation, or dependency installation as a normal Scout/Gate/test side effect.
9. `pip install -e .` into the shared environment is explicitly prohibited.
10. `shared-environment-mutation-protocol` remains deferred.
11. Branch lifecycle instructions preserve branch exclusivity, dirty-state protection, remote freshness, and non-destructive synchronization.
12. Tracked implementation remains workflow documentation/skills only unless contract-owner approval expands scope.
13. No production gameplay behavior changes.

## Validation Requirements

Because tracked implementation is documentation/skill-only:

- verify the three canonical workflow files describe one consistent topology and environment model;
- verify no cross-worktree interpreter references remain in canonical workflow surfaces;
- verify new task-worktree paths are project-scoped;
- verify no production/script/test files changed unexpectedly;
- preserve the already validated local topology/environment evidence recorded in this task.

No full gameplay regression suite is required solely for these documentation/skill changes.

## Deferred Technical Debt: `shared-environment-mutation-protocol`

Trigger this future task when any of the following becomes real work:

- add/remove/upgrade a Python dependency;
- recreate or materially mutate the canonical shared venv;
- concurrent environment mutation becomes necessary;
- environment drift becomes a demonstrated failure source.

Future investigation may compare locking, in-place sync, rebuild + atomic swap, dependency declaration validation, uv/equivalent tooling, or replacing the singleton model. None is preselected here.

## Non-Goals

- per-worktree virtual environments;
- dependency-fingerprint environments;
- environment-tool migration for its own sake;
- speculative mutation machinery;
- moving dirty/active worktrees;
- changing merge authority;
- changing production behavior.
