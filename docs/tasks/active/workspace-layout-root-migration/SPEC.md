# Workspace Layout Root Migration

Status: Draft

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

while preserving Git/worktree safety, the external shared Python environment contract, and local ignored runtime/user data.

The permanent local `main` worktree becomes the repository root itself:

```text
E:\Side_Project\Blackfire-CV-Autopilot
```

New temporary task worktrees become siblings:

```text
E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>
```

## Lightweight Survey Evidence

Current `main` head when this task was created:

```text
c229590aa5ccbe1deea00bb158b69615953c1472
```

Survey confirmed:

- `scripts/task_start.ps1` dynamically discovers canonical main from Git common-dir metadata.
- `scripts/task_cleanup.ps1` likewise resolves canonical main from actual Git topology rather than the literal `BlackfireCrusade_tool` name.
- `scripts/task_start.ps1` currently derives the default task worktree root as `<parent-of-main>\worktrees`; after the proposed main relocation that would incorrectly become `E:\Side_Project\worktrees`.
- `docs/architecture/ai_development_workflow.md`, branch-start skill, branch-completion skill, and older task contracts still name `BlackfireCrusade_tool` and/or the nested `worktrees` namespace.
- focused behavioral coverage already exists in `tests/test_task_start_behavioral.py`, `tests/test_task_cleanup_behavioral.py`, and `tests/test_worktree_environment_bootstrap.py`.
- the canonical shared Python environment remains external at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- `.gitignore` intentionally excludes local runtime/user state such as `user_data/`, `.runtime/`, `scratch/`, `.venv/`, `node_modules/`, and local tooling directories.

## Responsibility Boundary

This task owns the repository contract and deterministic tooling needed for the new local layout.

It does not own general machine bootstrap, dependency installation, gameplay/runtime behavior, or personal-data synchronization between different computers.

## Known Invariants

1. The permanent local `main` worktree remains attached to branch `main`.
2. Git worktree topology is authoritative; branch ownership must not be inferred from stale path memory.
3. Formal task startup remains:
   ```text
   scripts/task_start.ps1 -Task <task-id>
   ```
4. Formal task cleanup remains:
   ```text
   scripts/task_cleanup.ps1 -Task <task-id>
   ```
5. One repository uses one canonical shared Python environment:
   ```text
   E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
   ```
6. Worktree-local `.venv` remains a Windows junction to that canonical environment.
7. No task in this migration may run `pip install`, `pip uninstall`, recreate the environment, or silently fall back to system Python.
8. No destructive Git shortcuts: no `reset --hard`, `clean -fd`, forced worktree removal, or blind prune.
9. Local ignored state inside the current main checkout must be preservable during the physical migration. The migration path should move the existing checkout rather than require a fresh clone that would omit ignored files.
10. Existing `.venv` junction ownership/target semantics must remain valid after relocation; this task must not mutate the canonical environment itself.

## Scope

Expected implementation surface:

- `scripts/task_start.ps1`
- `tests/test_task_start_behavioral.py`
- `docs/architecture/ai_development_workflow.md`
- `.agents/skills/branch_start_workflow/SKILL.md`
- `.agents/skills/branch_completion_workflow/SKILL.md`
- `scripts/README.md`
- this task package under `docs/tasks/active/workspace-layout-root-migration/`

Additional focused workflow tests/docs may be changed if Scout proves they directly encode the old nested layout.

## Non-goals

- gameplay/runtime/CV behavior changes;
- changing the canonical shared Python environment path;
- creating a new venv;
- dependency installation or environment locking;
- Node dependency bootstrap changes;
- syncing personal `user_data` across machines;
- committing ignored runtime/user data;
- redesigning `task_cleanup.ps1` unless an actual path-coupled defect is proven;
- moving active/dirty task worktrees;
- generic cross-platform workspace discovery;
- performing the user's local physical move from GitHub.

## Provisional Acceptance Criteria

1. Repository-owned canonical documentation defines:
   ```text
   E:\Side_Project\Blackfire-CV-Autopilot
   ```
   as permanent local `main` / integrated runtime home.

2. Repository-owned canonical documentation defines:
   ```text
   E:\Side_Project\Blackfire-CV-Autopilot-worktrees\<task-id>
   ```
   as the default namespace for new task worktrees.

3. `task_start.ps1`, without an override, derives the new sibling worktree root from the discovered canonical main path and creates/reuses `<task-id>` there.

4. Existing `TASK_START_WORKTREES_ROOT_OVERRIDE` testability/recovery behavior remains available unless Scout proves removal is required.

5. Main discovery remains topology-driven; `task_start.ps1` must not hardcode `BlackfireCrusade_tool` or assume a fixed drive solely to locate main.

6. Existing startup safety behavior remains unchanged: clean-main checks, fetch/FF-only synchronization, remote task package validation, branch exclusivity, fail-closed reuse rules, and environment bootstrap delegation.

7. `task_cleanup.ps1` remains valid with the new main path and sibling worktree namespace, or receives only the minimal proven correction required.

8. Focused tests prove the new default sibling-worktree derivation and preserve current failure-state behavior.

9. Architecture/skills/scripts documentation no longer presents the nested `BlackfireCrusade_tool` + `worktrees` layout as canonical current state.

10. A documented local migration procedure preserves the existing checkout as a whole, including `.git` and ignored local state, rather than recommending a fresh clone or selective copy.

11. The migration procedure verifies, after physical relocation:
    - `git status`;
    - `git worktree list --porcelain`;
    - local `.venv` junction target/readiness;
    - canonical Python execution;
    - the next task-start path resolves under `Blackfire-CV-Autopilot-worktrees`.

12. No ignored personal data, webhook secret, runtime state, local tools, `.venv`, or `node_modules` is added to Git.

## Uncertainty / Scout Questions

Scout must confirm before Final SPEC:

- whether any repository-owned path contracts outside the files listed in Scope still encode `BlackfireCrusade_tool` or the nested `worktrees` location;
- whether Git primary-worktree relocation with currently empty linked-worktree topology needs any explicit Git metadata repair step on this machine, or whether moving the complete checkout is sufficient;
- whether `task_cleanup.ps1` has any indirect assumption that task paths share the same project parent directory;
- whether existing tests should model the exact new default derivation instead of relying almost entirely on `TASK_START_WORKTREES_ROOT_OVERRIDE`;
- whether documentation should retain the old nested layout only as historical migration context.

Scout is evidence provider only. Draft status blocks production implementation until ChatGPT + user promote this SPEC to Final.
