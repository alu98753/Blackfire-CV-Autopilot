# Worktree Environment Convention Migration

Status: Draft

## Decision Summary

This task standardizes the local development topology around two deliberately separate lifecycles:

1. **Git lifecycle** — project-scoped worktrees with one permanent `main` worktree and temporary task worktrees.
2. **Python environment lifecycle** — one repository-global shared virtual environment stored outside all Git worktrees and consumed through local `.venv` junctions.

The task intentionally does **not** design a complete concurrent mutation protocol for the shared environment. Dependency mutation is currently rare and is deferred to the backlog item `shared-environment-mutation-protocol`, to be activated when a real dependency change or concurrent-mutation need occurs.

## Goal

Eliminate the current split-brain local development convention in which Git/integration authority and runtime authority live in different permanent directories.

After migration, there must be one obvious canonical project structure:

```text
E:\Side_Project\
├─ VenvPools\
│  └─ .venvs-Blackfire-CV-Autopilot\      <- single canonical shared Python environment
│
└─ Blackfire-CV-Autopilot\                <- project container / namespace
   ├─ BlackfireCrusade_tool\               <- permanent main worktree + canonical runtime home
   │  └─ .venv -> junction to shared env
   │
   └─ worktrees\
      ├─ task-foo\                         <- temporary task worktree
      │  └─ .venv -> same shared env
      └─ task-bar\                         <- temporary task worktree
         └─ .venv -> same shared env
```

The intended human/agent mental model is:

```text
Blackfire-CV-Autopilot\BlackfireCrusade_tool
    = official local main
    = official integrated runtime validation home

Blackfire-CV-Autopilot\worktrees\<task>
    = task branch only
    = temporary

VenvPools\.venvs-Blackfire-CV-Autopilot
    = one shared repository environment
    = not owned by any Git worktree
```

## Observed Problem

The current repository contract explicitly assigns different canonical roles to two directories:

- `E:\Side_Project\temp-main` is documented as the permanent local `main` baseline / integration worktree.
- `E:\Side_Project\BlackfireCrusade_tool` is the actual runtime/development home but is documented as permanently holding feature/fix branches.

That produces two competing notions of "official project state":

```text
Git / merge main authority
        = temp-main

runtime / real CV validation authority
        = BlackfireCrusade_tool
```

These directories may point at different commits while both appear canonical for different activities. This is especially unsafe in a multi-agent / multi-worktree workflow because instructions such as "test latest main" or "sync main" require extra path-specific interpretation.

Current local evidence supplied at task creation showed `BlackfireCrusade_tool` detached at commit `ac5d8c9` while branch `main` was checked out by another worktree. That is a concrete example of the runtime home not necessarily representing current main.

The current branch-completion contract also reaches across worktrees to reuse `BlackfireCrusade_tool\.venv`, which couples environment availability to one Git worktree even though that worktree is not the documented owner of `main`.

## Architecture Decision

### A. Git lifecycle: project-scoped worktree hierarchy

Each side project owns its own directory namespace. For Blackfire:

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\       <- permanent main
└─ worktrees\
   ├─ task-a\
   ├─ task-b\
   └─ task-c\
```

This prevents task worktrees from all unrelated side projects being flattened into one global `E:\Side_Project` namespace.

`temp-main` is transitional legacy state and must not remain a second permanent `main` authority after migration.

### B. Environment lifecycle: one shared canonical venv

Blackfire intentionally uses one shared canonical Python virtual environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every worktree exposes a conventional local path:

```text
.\.venv\Scripts\python.exe
```

through a Windows junction to the same external environment.

Therefore agents and scripts may use the stable worktree-local `.venv` path without knowing the physical pool location.

### C. Deliberate trade-off

This task explicitly accepts that a repository-global shared mutable environment does **not** provide dependency isolation between concurrent branches.

That trade-off is currently acceptable because dependency mutation is rare and is not the user's present pain point. The architecture optimizes for:

- one stable Python environment;
- zero repeated dependency provisioning for ordinary task worktrees;
- fast task-worktree creation;
- a uniform `.venv` path for humans, IDEs, Scout, Gate, and tests;
- decoupling environment storage from any individual Git worktree.

The risk is not ignored. Safe shared-environment mutation is tracked separately in `docs/tasks/BACKLOG.md` under `shared-environment-mutation-protocol`.

## Known Invariants

1. **Exactly one permanent local main worktree**
   - `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` is the permanent local checkout of branch `main` after migration.
   - It is also the canonical runtime/CV validation home for the integrated version.
   - No second directory may remain a hidden or documented permanent main authority.

2. **Task worktrees are project-scoped, branch-scoped, and temporary**
   - Task worktrees live under `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\`.
   - Each task worktree holds its task branch only during active work.
   - Before Scout, Gate, tests, or implementation commands, the task worktree must be attached to the expected branch and synchronized with current remote task artifacts.

3. **One canonical Python environment exists outside Git worktrees**
   - Canonical path: `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot` unless Scout finds a pre-existing machine-wide naming convention that materially requires a naming adjustment.
   - Main and task worktrees consume that same environment.
   - Rebuilding, renaming, moving, or deleting a Git worktree must not implicitly destroy the canonical environment.

4. **`.venv` is a local junction contract**
   - Every runnable Blackfire worktree should expose `.venv` as a local junction/link to the canonical shared environment.
   - `.venv/` remains Git-ignored and is never tracked.
   - Junction creation is local bootstrap state, not branch content.

5. **Normal workflows consume the environment; they do not mutate it**
   - Scout, Gate, normal tests, normal runtime validation, and ordinary source-code tasks treat the shared environment as pre-existing infrastructure.
   - They must not install/uninstall dependencies merely to make a command succeed.
   - Missing/invalid `.venv` state must not silently fall back to system Python.

6. **No worktree-specific editable install into the shared environment**
   - Task worktrees must not run `pip install -e .` or equivalent mechanisms that bind the shared environment to one worktree's source tree.
   - Project imports during tests/runtime must resolve from the current worktree rather than environment metadata pointing at another worktree.

7. **Shared-environment mutation is recognized but deferred**
   - Adding/removing/upgrading Python dependencies, recreating the canonical venv, or otherwise mutating it is a repository-environment operation rather than an ordinary branch-local action.
   - A complete safe mutation/locking/atomic-rebuild protocol is **not part of this task**.
   - When a real dependency mutation is next required, the backlog task `shared-environment-mutation-protocol` should be promoted before introducing ad-hoc concurrent mutation behavior.

8. **No destructive migration shortcuts**
   - Migration must respect Git worktree branch exclusivity.
   - A detached `BlackfireCrusade_tool`, dirty worktree, or `main` currently checked out in `temp-main` must be handled explicitly.
   - Do not use `reset --hard`, `clean -fd`, force deletion, or loss of uncommitted work as implicit migration steps.

9. **GitHub remains the handoff surface**
   - Task artifacts remain tracked under `docs/tasks/<task-id>/`.
   - Local worktree topology is machine state, not something inferred from stale assumptions.

10. **Windows non-interactive execution policy remains unchanged**
   - Agent shell/tool commands run through `cmd.exe /d /s /c`.
   - Commands must be non-interactive and close stdin where appropriate.
   - PowerShell automation remains wrapped through `cmd.exe` according to project policy.

## Initial Scope

The lightweight survey identifies these likely change surfaces. Scout must narrow them before Final SPEC:

- `docs/architecture/ai_development_workflow.md`
  - currently names `temp-main` as the permanent local baseline/integration worktree.
- `.agents/skills/branch_completion_workflow/SKILL.md`
  - currently encodes a permanent dual-worktree model, assigns `main` to `temp-main`, forbids `BlackfireCrusade_tool` from owning `main`, and uses cross-worktree absolute Python paths.
- `docs/tasks/BACKLOG.md`
  - must retain the deferred `shared-environment-mutation-protocol` technical debt.
- `.gitignore`
  - verify `.venv` and local workflow/runtime artifacts remain ignored.
- `scripts/ai_scout.ps1` / `scripts/ai_gate.ps1`
  - inspect only for environment discovery/fallback assumptions that directly conflict with the new convention; executable changes require evidence from Scout rather than assumption.
- `scripts/README.md`, `docs/testing/`, or other workflow docs/helpers discovered by Scout
  - update only when they encode obsolete `temp-main`, flattened worktree paths, cross-worktree interpreter paths, or system-Python fallback assumptions.
- one-time migration/bootstrap documentation or deterministic helper
  - include only if needed to make the migration repeatable and safe.

This is not permission to broadly refactor workflow automation.

## Non-Goals

- Changing gameplay/runtime behavior, CV logic, navigation, scheduler semantics, or state-machine behavior.
- Designing per-worktree virtual environments.
- Designing dependency-fingerprint environments.
- Migrating to uv/Poetry/Conda/containers solely for environment management.
- Solving shared-environment concurrent mutation, locking, atomic swap, or dependency synchronization in this task.
- Automatically deleting `temp-main` before dirty-state and branch ownership are safely verified locally.
- Making Scout or Gate environment managers.
- Changing OpenCode CLI/provider compatibility except where documentation refers to local topology.
- Generalizing the convention to team/multi-developer workflows beyond what is required for the current solo multi-worktree setup.

## Provisional Acceptance Criteria

1. Canonical workflow documentation defines exactly one permanent local main worktree: `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`.
2. Task worktrees are documented under `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task>` rather than flattened beside unrelated side projects.
3. `temp-main` is removed from durable workflow/skill contracts as a permanent baseline authority, except clearly marked migration/history references.
4. Canonical documentation defines exactly one shared Python environment outside all Git worktrees at the agreed `VenvPools` location.
5. Main and task worktrees expose `.venv` as local junction consumers of the same shared environment.
6. Normal Agent/Scout/Gate/test instructions consistently use the worktree-local `.venv` path where Python execution is required and do not depend on another worktree's absolute interpreter path.
7. Missing or invalid `.venv` access does not silently degrade to system Python where repository automation controls interpreter selection.
8. The convention explicitly forbids worktree-specific editable installs into the shared environment.
9. Shared-environment mutation safety is explicitly deferred and cross-referenced to `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`; this task does not grow into a dependency-management redesign.
10. A safe one-time migration sequence exists for the current local state, including the case where `BlackfireCrusade_tool` is detached and `main` is held by `temp-main`.
11. Migration instructions preserve dirty/uncommitted work and respect Git's one-branch-per-worktree checkout constraint.
12. After migration, `git branch --show-current` in `BlackfireCrusade_tool` reports `main`, and official runtime validation begins only after it is synchronized with `origin/main`.
13. Creating/deleting a task worktree does not create/delete the canonical shared Python environment; recreating the local `.venv` junction restores access.
14. Any executable workflow-script changes introduced by this task receive deterministic focused regression coverage appropriate to the changed behavior.
15. No production gameplay behavior changes.

## Forbidden Shortcuts

- Keeping `temp-main` as a hidden second source of truth while changing only names in documentation.
- Leaving task worktrees globally flattened when the canonical convention claims project-scoped hierarchy.
- Keeping the physical canonical environment under `BlackfireCrusade_tool` and calling it worktree-independent.
- Falling back to globally installed/system Python when `.venv` is missing where repository automation is expected to enforce interpreter choice.
- Auto-running `pip install`, `pip uninstall`, or environment recreation from Scout/Gate.
- Using `pip install -e .` in the shared environment for branch-local convenience.
- Expanding this task into speculative environment locking/atomic-swap machinery without an actual dependency-mutation requirement.
- Destroying or force-cleaning dirty worktrees to simplify migration.

## Deferred Technical Debt

### `shared-environment-mutation-protocol`

Canonical backlog: `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`

Reason for deferral:

- Blackfire intentionally chooses a single shared venv for current operational simplicity.
- Dependency changes are currently rare.
- The present pain point is ambiguous worktree/main/runtime ownership, not dependency mutation.
- Implementing locking, rebuild/swap, or dependency synchronization now would add workflow complexity without current evidence that it is needed.

Trigger for promotion:

- a Python dependency must be added, removed, or upgraded;
- the canonical venv must be recreated/migrated;
- two agents/processes need to mutate environment state concurrently;
- environment drift becomes a demonstrated source of failures.

Until triggered, ordinary workflows consume the shared environment without mutating it.

## Uncertainty / Scout Questions

Scout should localize, within its normal bounded budget:

1. Every durable reference to `temp-main`, the permanent dual-worktree convention, flattened task-worktree paths, or absolute `BlackfireCrusade_tool\.venv` reuse.
2. Whether scripts currently discover `.venv`, invoke Python, or fall back to `python` / PATH in ways that conflict with the target convention.
3. Whether workflow-script testing infrastructure on current main is sufficient to protect any required executable changes.
4. Whether the current package/import layout already guarantees current-worktree source resolution when using the shared venv without editable install.
5. Whether a deterministic worktree/bootstrap helper already exists and should be extended instead of introducing another helper.
6. Whether `temp-main` currently owns responsibilities beyond baseline testing / manual merge fallback that need an explicit replacement.
7. Which canonical architecture document should permanently own the worktree/environment convention so task-specific specs and branch-completion skills can reference one durable authority instead of duplicating it.
8. Whether nesting linked worktrees under the project container introduces any existing script/path assumptions that must be migrated.

Scout may narrow or correct this Draft using repository evidence. Scout must not begin production implementation or promote the spec to Final.