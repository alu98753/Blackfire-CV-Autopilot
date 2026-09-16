# Worktree Environment Convention Migration

Status: Draft

## Decision Summary

This task standardizes the local development topology around two separate lifecycles:

1. **Git lifecycle** — one project-scoped permanent `main` worktree plus temporary task worktrees.
2. **Python environment lifecycle** — one repository-global shared virtual environment stored outside all Git worktrees and consumed through worktree-local `.venv` junctions.

A complete shared-environment mutation protocol is intentionally deferred to the backlog item `shared-environment-mutation-protocol`. Dependency mutation is rare and is not the present pain point.

## Goal

Eliminate the current split-brain local convention where `temp-main` owns Git `main` while `BlackfireCrusade_tool` is the real runtime/CV home.

Target topology:

```text
E:\Side_Project\
├─ VenvPools\
│  └─ .venvs-Blackfire-CV-Autopilot\      <- single canonical shared Python environment
│
└─ Blackfire-CV-Autopilot\                <- project namespace
   ├─ BlackfireCrusade_tool\               <- permanent main worktree + runtime home
   │  └─ .venv -> junction to shared env
   │
   └─ worktrees\
      ├─ task-foo\
      │  └─ .venv -> same shared env
      └─ task-bar\
         └─ .venv -> same shared env
```

After migration there must be exactly one obvious answer to both:

- "Where is local main?" -> `BlackfireCrusade_tool`
- "Where is official integrated runtime validation performed?" -> `BlackfireCrusade_tool`

## Survey Evidence

A manual read-only Gemini survey was used in place of Scout for this draft refinement.

### Current local worktree state

At survey time:

- previous `main` holder: `E:\Side_Project\temp-main`
- previous holder: clean, branch `main`, HEAD `ac5d8c9`
- `temp-main` was safely switched to detached HEAD to release `main`
- `BlackfireCrusade_tool` remained detached at `ac5d8c9384195a3a2ae6c19e852a26364b55025f`
- known local `origin/main`: `a537eac18bd177282105d99c0366cfa338d63ca3`
- `BlackfireCrusade_tool` was dirty: 1 modified file + 3 untracked files
- therefore no `fetch`, `switch main`, or `pull --ff-only` was performed in `BlackfireCrusade_tool`

The dirty state was correctly preserved. No reset, clean, stash, or forced checkout was used.

### Confirmed old-topology contracts

The old permanent dual-worktree model is encoded in multiple durable surfaces:

- `docs/architecture/ai_development_workflow.md`
  - defines `temp-main` as the permanent local main/baseline surface.
- `.agents/skills/branch_start_workflow/SKILL.md`
  - defines `BlackfireCrusade_tool` as the feature/fix development worktree and `temp-main` as permanent main owner.
  - explicitly forbids switching `BlackfireCrusade_tool` to `main`.
- `.agents/skills/branch_completion_workflow/SKILL.md`
  - depends on the permanent dual-worktree layout and forbids the development worktree from owning `main`.
- `docs/tasks/workflow-merge-authority/SPEC.md`
  - historical/task-level contract also records `temp-main` as the permanent main/baseline surface.

`test-main` was not found as a durable convention.

### Environment evidence

The survey found:

- README and most scripts use worktree-relative `.venv\Scripts\python.exe`.
- `scripts/ai_gate.ps1` already resolves the current repository root's `.venv\Scripts\python.exe` and infrastructure-blocks when absent.
- no automated `pip install` / `pip uninstall` behavior was found.
- README contains manual `.venv` creation and `pip install -r requirements.txt` instructions.
- existing `.venv` directories in inspected worktrees are physical directories, not junction/reparse points.
- both inspected `pyvenv.cfg` files use Python 3.11.2.
- matching `python.exe` file identity/content does not prove that the whole environment/package tree is already shared.

Therefore the target shared-junction layout is a **migration target**, not a description of current state.

## Architecture Decision

### A. Project-scoped Git lifecycle

For Blackfire:

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\       <- permanent main
└─ worktrees\
   ├─ task-a\
   ├─ task-b\
   └─ task-c\
```

Task worktrees must no longer be globally flattened alongside unrelated side projects.

### B. One shared canonical venv

Blackfire intentionally uses one repository-global virtual environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree exposes:

```text
.\.venv\Scripts\python.exe
```

via a Windows junction to the canonical environment.

The stable local `.venv` path is the consumer contract. Agents/scripts should not need to know the physical pool path during normal operation.

### C. Deliberate trade-off

A repository-global shared mutable environment does not isolate dependency state across branches. This is accepted for now because dependency changes are rare and the active problem is Git/worktree/runtime identity, not environment mutation.

Safe dependency mutation remains deferred to `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`.

## Known Invariants

1. **Exactly one permanent local main worktree**
   - After migration, `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` owns checkout of `main`.
   - It is also the canonical integrated runtime/CV validation home.
   - No second permanent main authority remains.

2. **Task worktrees are project-scoped and temporary**
   - task worktrees live under `Blackfire-CV-Autopilot\worktrees\`.
   - each holds its task branch only.
   - local branch/worktree state must be validated before task commands.

3. **Canonical environment is outside all Git worktrees**
   - target path: `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
   - deleting/recreating a worktree must not delete the canonical environment.

4. **`.venv` is a local junction contract after migration**
   - every runnable worktree exposes `.venv` as a local junction to the same canonical environment.
   - `.venv/` remains ignored and untracked.
   - current physical `.venv` directories must not be mistaken for already-completed migration.

5. **Normal workflows consume, not mutate, the environment**
   - Scout/Gate/tests/runtime validation must not install/uninstall dependencies merely to succeed.
   - where repository automation owns interpreter discovery, absent/invalid `.venv` must fail closed rather than silently use system Python.

6. **No worktree-specific editable install into the shared environment**
   - `pip install -e .` or equivalent source binding to one worktree is forbidden for the shared environment.

7. **Shared-environment mutation is deferred**
   - dependency add/remove/upgrade, venv recreation, locking, atomic swap, and synchronization are not part of this task.
   - promote `shared-environment-mutation-protocol` when a real mutation need appears.

8. **Dirty worktree preservation is mandatory**
   - dirty/untracked/staged state must never be silently reset, cleaned, stashed, overwritten, or moved merely to complete migration.

9. **Remote freshness must be explicit**
   - local `origin/main` cannot be treated as current remote truth until `git fetch origin` succeeds.
   - before official runtime validation, `BlackfireCrusade_tool` must be clean enough for safe branch attachment and synchronized with fetched `origin/main` using non-destructive fast-forward semantics.

10. **Git worktree branch exclusivity remains authoritative**
   - `main` cannot be checked out in two linked worktrees simultaneously.
   - migration must release any previous `main` holder before attaching `BlackfireCrusade_tool` to `main`.

11. **GitHub remains the handoff surface**
   - tracked task artifacts remain authoritative for task intent and evidence.
   - local machine topology is validated, not guessed.

12. **Windows non-interactive execution policy remains unchanged**
   - commands invoked by agents use `cmd.exe /d /s /c`, do not wait for stdin, and preserve repository working directory.

## Scope

### Must change

- `docs/architecture/ai_development_workflow.md`
  - remove `temp-main` as permanent main/baseline authority and document the new project-scoped topology.
- `.agents/skills/branch_start_workflow/SKILL.md`
  - replace the old rule that permanently reserves `main` for `temp-main`.
  - establish safe creation of task worktrees under the project-scoped `worktrees\` namespace.
- `.agents/skills/branch_completion_workflow/SKILL.md`
  - remove permanent dual-worktree assumptions and cross-worktree Python interpreter assumptions.
  - align closeout/synchronization with `BlackfireCrusade_tool` as permanent `main`.
- `docs/tasks/BACKLOG.md`
  - retain the deferred `shared-environment-mutation-protocol` technical debt.
- migration/runbook documentation
  - provide a safe one-time sequence including dirty-state preservation, remote fetch freshness, branch exclusivity, environment migration, validation, rollback, and legacy `temp-main` retirement.

### Likely change only if directly referenced by old topology

- `scripts/README.md`
- README/developer setup documentation
- `.gitignore` only if current ignore rules are insufficient
- other workflow docs discovered to encode `temp-main`, flattened task-worktree paths, or cross-worktree interpreter paths

### Explicitly not required by current evidence

- `scripts/ai_gate.ps1`
  - current evidence already shows worktree-relative `.venv` discovery with fail-closed behavior.
- `scripts/ai_scout.ps1`
  - no evidence yet requires executable behavior changes.
- production source code
- gameplay/runtime code
- product tests unrelated to workflow documentation
- `requirements.txt`

Executable script changes must not be introduced without new evidence.

## Non-Goals

- changing gameplay/runtime/CV/navigation/state-machine behavior.
- designing one venv per worktree.
- dependency-fingerprint environments.
- migrating to uv/Poetry/Conda/containers solely for this task.
- implementing shared-environment locking, atomic swap, or dependency sync.
- automatically destroying or force-cleaning `temp-main`.
- making Scout/Gate environment managers.
- changing OpenCode compatibility/provider policy.
- rewriting historical task records merely to erase history. Historical task specs may retain old topology as historical evidence when clearly non-authoritative.

## Migration Safety Requirements

The one-time migration/runbook must use this safety order:

1. enumerate all worktrees and record path, branch/detached state, HEAD, and dirty/untracked/staged state.
2. fetch `origin` before claiming remote freshness.
3. preserve all dirty worktrees; no reset/clean/stash/force checkout shortcuts.
4. identify the sole current `main` holder and safely release it only when its worktree is clean and expected.
5. confirm ancestry/fast-forward safety between local `main` and fetched `origin/main`.
6. attach `BlackfireCrusade_tool` to `main` only when its current dirty state has been intentionally resolved by the user or otherwise preserved through an explicitly approved non-destructive procedure.
7. synchronize `BlackfireCrusade_tool` with `origin/main` using fast-forward-only semantics.
8. inventory the existing physical `.venv` directories before moving/replacing anything; record interpreter version and enough package/environment evidence to validate equivalence.
9. create the external canonical shared environment using a procedure with an explicit rollback path; do not assume current `.venv` directories are already junctions/shared environments.
10. replace each worktree-local `.venv` with a junction only after the canonical environment is validated.
11. validate junction/reparse-point identity and interpreter target explicitly.
12. validate imports and an appropriate focused test/smoke command from both main and at least one task worktree using the worktree-local `.venv` path.
13. retire/remove legacy `temp-main` only after the new main ownership, environment access, and workflow contracts are validated.

The runbook must define rollback for environment migration before any original environment directory is irreversibly removed.

## Provisional Acceptance Criteria

1. `BlackfireCrusade_tool` is the only documented permanent local `main` worktree and integrated runtime home.
2. task worktrees are documented under `Blackfire-CV-Autopilot\worktrees\<task>`.
3. active workflow/skill contracts no longer assign permanent main ownership to `temp-main`.
4. `branch_start_workflow` and `branch_completion_workflow` both implement the new topology consistently.
5. historical task material is not treated as canonical authority; historical references may remain when clearly contextual.
6. one shared Python environment is documented outside all Git worktrees.
7. every runnable worktree uses a local `.venv` junction to that canonical environment after migration.
8. migration validation explicitly checks junction/reparse-point identity and interpreter target rather than inferring sharing from identical `python.exe` files.
9. normal workflow commands use worktree-local `.venv` paths and do not cross-reference another worktree's interpreter.
10. no new system-Python fallback is introduced.
11. shared-environment mutation remains deferred and cross-referenced to backlog.
12. migration handles dirty worktree preservation, remote-ref freshness, detached HEAD, branch exclusivity, and fast-forward-only synchronization.
13. migration includes a documented environment rollback path.
14. official runtime validation from `BlackfireCrusade_tool` occurs only after fetched `origin/main` synchronization.
15. environment migration is verified from main and at least one task worktree before legacy topology retirement.
16. no production gameplay behavior changes.

## Forbidden Shortcuts

- treating local `origin/main` as freshly verified without fetching.
- switching a dirty `BlackfireCrusade_tool` to `main` by reset/clean/stash/force.
- keeping `temp-main` as a hidden second permanent main authority.
- claiming current physical `.venv` directories are already shared/junction-based without explicit reparse-point validation.
- inferring whole-environment sharing only from identical Python executable identity.
- keeping the physical canonical environment under a Git worktree.
- using another worktree's absolute `.venv\Scripts\python.exe` path.
- using `pip install -e .` in the shared environment.
- adding speculative environment mutation machinery to this task.
- modifying Gate/Scout executable behavior without evidence of a real incompatibility.
- deleting original venv/worktree state before rollback is possible.

## Deferred Technical Debt

### `shared-environment-mutation-protocol`

Canonical backlog: `docs/tasks/BACKLOG.md#shared-environment-mutation-protocol`

Trigger for promotion:

- a Python dependency must be added, removed, or upgraded;
- the canonical venv must be recreated/migrated after this one-time topology migration;
- concurrent mutation becomes necessary;
- environment drift becomes a demonstrated failure source.

Expected future investigation may include locking, in-place sync, rebuild + atomic swap, dependency declaration validation, and uv or equivalent tooling. None of these are preselected by this task.

## Remaining Uncertainty Before Final

1. exact contents of the dirty `BlackfireCrusade_tool` files and whether they belong to another active task/user state.
2. actual current remote `origin/main` after a fresh fetch.
3. exact physical `.venv` package/layout relationship between existing worktrees beyond the Python executable evidence.
4. whether an existing repository helper is suitable for the one-time migration/runbook or whether documentation-only migration is safer.
5. which permanent section of `ai_development_workflow.md` should own the topology contract so branch skills reference it rather than duplicate architecture intent.

These uncertainties affect migration execution details, not the selected target topology.