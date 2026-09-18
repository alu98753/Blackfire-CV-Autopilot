# Task Lifecycle Active / Archive

Status: Draft

## Goal

Separate currently active development tasks from completed task history without losing tracked task evidence, while making task-package lookup a single repository-owned responsibility instead of duplicating path construction across workflow scripts.

Target direction:

```text
docs/tasks/
├─ README.md
├─ BACKLOG.md
├─ active/
│  └─ <task-id>/
└─ archive/
   └─ <year>/
      └─ <task-id>/
```

Active workflow commands must operate only on active task packages. Archived packages remain durable repository history and must not be silently treated as active work.

## Problem confirmed by lightweight survey

Current repository contract puts both active and completed task packages directly under:

```text
docs/tasks/<task-id>/
```

The current README explicitly states that tracked task packages remain in repository history until an archival policy exists, so local cleanup and repository-history closeout are presently separate but the archive half is undefined.

Direct path ownership is also duplicated today:

- `scripts/task_start.ps1` validates remote `docs/tasks/$Task/SPEC.md` and `task.json` directly.
- `scripts/ai_scout.ps1` builds `docs\tasks\$Task` directly.
- `scripts/ai_gate.ps1` builds `docs\tasks\$Task` directly and embeds those paths in prompts/excludes/evidence handling.
- `docs/tasks/README.md` documents the flat-path convention.
- `tests/test_task_start_behavioral.py` asserts the flat layout directly.
- `tests/test_workflow_scripts.py` and related workflow tests cover cleanup/gate contracts and are nearby regression surfaces.
- `scripts/task_cleanup.ps1` primarily owns local worktree/branch cleanup; it must remain distinct from repository archival.

This creates a known future drift risk if active/archive layout is introduced by editing each caller independently.

## Architecture boundary

Introduce one task-package resolution boundary used by active workflow scripts.

Conceptual contract:

```text
Resolve active task package by task id
    -> docs/tasks/active/<task-id>/

Inspect historical task package
    -> docs/tasks/archive/<year>/<task-id>/
```

Exact helper filename/API is implementation detail to confirm after Scout, but path interpretation must have one canonical implementation.

Repository archival is a repository-history concern. Local worktree/branch cleanup remains owned by `task_cleanup.ps1`; do not fold archival behavior into that wrapper.

## Known invariants

1. GitHub remains the task/history SSOT.
2. `SPEC.md` remains the normative behavioral contract; `task.json` remains automation metadata and must not become a second lifecycle SSOT.
3. Task id must still match its package directory name.
4. Active workflow commands must fail closed when a requested task exists only in archive.
5. Archived task packages remain tracked history; archival is a move/closeout operation, not deletion.
6. No global `current-task` marker.
7. `task_cleanup.ps1` continues to mean local execution/worktree cleanup only.
8. Existing worktree, shared-Python-environment, Gate, and branch-safety contracts must not be weakened.
9. No silent fallback from active lookup to archive lookup.
10. Path construction for active task packages must not remain duplicated across `task_start.ps1`, `ai_scout.ps1`, and `ai_gate.ps1`.
11. Legacy `docs/todos/` remains frozen legacy storage.
12. This task is repository task-lifecycle infrastructure, not an AI-workflow-roadmap task; do not modify the AI workflow roadmap unless a concrete contract dependency is discovered and surfaced.

## Scope

Expected implementation surface, subject to Scout localization:

- `docs/tasks/README.md`
- `docs/tasks/BACKLOG.md` if intake/promote wording needs path updates
- new shared task-package resolver/helper under `scripts/`
- `scripts/task_start.ps1`
- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `scripts/task_cleanup.ps1` only where documentation/boundary checks are needed; do not transfer archive ownership into it
- new explicit task archival command/helper under `scripts/`
- `tests/test_task_start_behavioral.py`
- `tests/test_workflow_scripts.py`
- `tests/test_task_cleanup_behavioral.py` if cleanup-boundary assertions are required
- new focused tests for resolver/archive behavior
- migration of existing tracked task packages only after the migration rule is explicit and mechanically safe

## Required behavior

### 1. Active / archive separation

The canonical active package location becomes:

```text
docs/tasks/active/<task-id>/
```

The canonical historical location becomes:

```text
docs/tasks/archive/<year>/<task-id>/
```

The archive year must be deterministic. Prefer the closeout/integration year rather than guessing from file timestamps; Scout should identify what repository evidence is available for this safely.

### 2. Single resolver ownership

Active workflow consumers must obtain the active task package path through one shared resolver contract rather than each constructing `docs/tasks/.../$Task` independently.

At minimum the resolver must distinguish:

- active package exists and is valid;
- task exists only in archive;
- task does not exist;
- duplicate/ambiguous archive matches;
- malformed package / id mismatch where applicable.

Active commands must not silently search archive as a fallback.

### 3. Archive command

Provide an explicit repository-history closeout command, tentatively:

```powershell
scripts/task_archive.ps1 -Task <task-id>
```

Its responsibility is moving a completed tracked package from active storage to canonical archive storage while preserving history.

It must fail closed on unsafe/ambiguous state and must not perform destructive cleanup.

The exact point in the integration sequence at which archival occurs is intentionally Draft uncertainty; Scout must inspect current merge/cleanup contracts and recommend the safest ordering that does not create a state where Gate/review unexpectedly loses access to an active package.

### 4. Completed-task migration

Do not classify historical packages as completed based only on folder age, naming, or presence of `EVIDENCE.md`.

Migration must use explicit, auditable criteria. If completion cannot be proven safely for a package, leave it unarchived rather than guessing.

The implementation may stage migration separately from resolver introduction if that reduces risk.

### 5. Fail-closed active commands

After migration, an archived task passed to active lifecycle commands such as start/scout/gate must not be treated as active.

Expected semantic outcome:

```text
TASK_ARCHIVED / equivalent explicit error
```

Exact error vocabulary may follow existing script conventions.

### 6. Documentation

Update task lifecycle documentation to distinguish:

```text
backlog -> active -> final review/integration -> archive
```

and separately:

```text
task_cleanup.ps1 = local execution closeout
task_archive.ps1 = tracked repository-history closeout
```

## Non-goals

- Redesigning Scout/Gate model routing or reviewer workflow.
- Changing production game/runtime behavior.
- Replacing `task_start.ps1` worktree orchestration.
- Changing shared Python environment ownership.
- Deleting completed task history.
- Introducing database/state-service tracking for tasks.
- Making `task.json.status` the lifecycle SSOT.
- Reorganizing `docs/todos/`.
- Automatically inferring every legacy task's completion status without evidence.

## Provisional acceptance criteria

1. Active task packages have one canonical path under `docs/tasks/active/<task-id>/`.
2. Archived packages have one canonical path under `docs/tasks/archive/<year>/<task-id>/`.
3. Start, Scout, and Gate use one shared active-task resolver/path contract.
4. There is an explicit archive operation separate from `task_cleanup.ps1`.
5. Active commands fail closed for archived-only task ids.
6. Resolver tests cover active, missing, archived-only, malformed/id mismatch, and ambiguous historical cases where applicable.
7. Archive tests cover successful move plus at least destination collision, missing active task, unsafe/incomplete closeout state, and no-deletion behavior.
8. Existing `task_start.ps1` behavioral guarantees remain covered after path migration.
9. Existing Gate artifact/review path behavior remains valid under the resolved active package.
10. Existing cleanup behavior remains unchanged except for explicit boundary/documentation updates.
11. README/BACKLOG examples no longer teach the old flat active-task layout.
12. Existing task-package migration is deterministic and leaves uncertain packages untouched.
13. No caller independently reintroduces active package path concatenation that bypasses the resolver.
14. Focused tests pass without dependency/environment mutation.

## Scout questions / uncertainty

Gemini Scout should answer these before this SPEC becomes Final:

1. What exact files currently construct or assume `docs/tasks/<task-id>` directly, including tests, prompts, exclusion paths, helper scripts, and docs?
2. Is there already a reusable PowerShell helper/module pattern suitable for a shared task resolver?
3. What is the safest archive ordering relative to Gate, final GitHub review, merge, and `task_cleanup.ps1`?
4. Can archival safely happen before merge, or does correctness require a post-integration closeout commit/path?
5. What existing repository evidence can mechanically prove that an old task is completed/integrated?
6. Which existing task directories can be proven safe to migrate, and which should remain untouched?
7. Do any scripts outside start/scout/gate depend on the flat path?
8. Which focused deterministic tests are the minimum sufficient coverage for resolver + archive semantics?
9. Does moving the current task package itself during implementation create a bootstrap/Gate edge case, and what migration order avoids it?

## Implementation constraint

Do not begin production implementation while this SPEC is Draft.

Gemini Scout is authorized for one read-only repository survey. It must not edit files, become spec owner, or upgrade this SPEC to Final. ChatGPT + user will finalize the contract after reviewing the Scout evidence.
