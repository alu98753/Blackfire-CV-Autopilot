# Worktree Environment Convention Migration

Status: Draft

## Goal

Replace the current split-brain local development convention with one canonical, easy-to-reason-about model:

```text
E:\Side_Project\BlackfireCrusade_tool
    = permanent main worktree
    = canonical runtime project home

E:\Side_Project\task-*
    = temporary task worktrees

E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
    = canonical Python environment owned outside every Git worktree
```

Every repository worktree consumes the same canonical Python environment through a local `.venv` junction. No Git worktree owns the environment lifecycle.

The task must also migrate the repository's durable workflow contracts away from the current `temp-main` convention so humans and agents have one unambiguous answer to both "where is main?" and "where is the runtime project home?".

## Observed Problem

The current repository workflow contract explicitly assigns different canonical roles to two directories:

- `E:\Side_Project\temp-main` is documented as the permanent local `main` baseline / integration worktree.
- `E:\Side_Project\BlackfireCrusade_tool` is the real runtime/development home containing the working Python environment and game/runtime context, but is documented as permanently holding feature/fix branches.

This creates two independent notions of "main": Git/integration authority lives in `temp-main`, while real runtime validation naturally happens in `BlackfireCrusade_tool`. The directories can therefore be on different commits while both appear to represent the official project state.

The current branch-completion contract also reaches across worktrees to reuse `BlackfireCrusade_tool\.venv`, coupling the Python environment lifetime to one Git worktree. That makes task worktrees environment consumers of a directory whose Git branch role is unrelated to environment ownership.

Current local evidence supplied at task creation also shows `BlackfireCrusade_tool` detached at commit `ac5d8c9` while `main` is checked out in another worktree, demonstrating that the split-role model can leave the canonical runtime directory detached or behind the latest main.

## Target Convention

```text
E:\Side_Project\
├─ VenvPools\
│  └─ .venvs-Blackfire-CV-Autopilot\   <- canonical shared Python environment
│
├─ BlackfireCrusade_tool\               <- permanent main worktree + runtime home
│  └─ .venv -> junction to canonical env
│
├─ task-foo\                             <- task worktree
│  └─ .venv -> same canonical env
│
└─ task-bar\                             <- task worktree
   └─ .venv -> same canonical env
```

`temp-main` is transitional legacy state. It must not remain a second permanent main authority after migration is complete.

## Known Invariants

1. **Single canonical main worktree**
   - `E:\Side_Project\BlackfireCrusade_tool` is the permanent local worktree that owns checkout of branch `main` after migration.
   - It is also the default place for real runtime / CV validation of the official integrated version.
   - Agents must not infer that another directory represents local main merely because it exists.

2. **Task worktrees are branch-scoped and temporary**
   - Task worktrees hold task branches only.
   - Before Scout, Gate, tests, or implementation commands, the task worktree must be attached to the expected task branch and synchronized with the latest remote task artifacts according to the repository handoff contract.

3. **Python environment ownership is outside Git worktrees**
   - Canonical environment path: `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot` unless Scout finds an existing repository-wide convention that should generalize this name/path.
   - `BlackfireCrusade_tool\.venv` and every task worktree `.venv` are local junctions/links to that canonical environment.
   - Rebuilding, renaming, or deleting a worktree must not destroy the canonical environment.

4. **`.venv` is local-only**
   - `.venv/` remains Git-ignored and must never become a tracked repository artifact.
   - Junction/link creation is local bootstrap state, not branch content.

5. **No worktree-specific editable install into the shared environment**
   - Task worktrees must not run `pip install -e .` (or an equivalent editable install) into the shared canonical environment when that would bind imports to one worktree source tree.
   - Tests and runtime execution must resolve project source from the current worktree, not from another branch through environment metadata.

6. **Dependency mutation is repository-environment state, not branch state**
   - `pip install`, `pip uninstall`, environment recreation, or equivalent dependency mutations against the shared environment must be treated as serialized repository environment operations.
   - Parallel task agents must not mutate the shared environment concurrently.

7. **Scout / Gate / normal tests consume, not provision, the environment**
   - `scripts/ai_scout.ps1`, `scripts/ai_gate.ps1`, and task tests must not silently create, repair, replace, or mutate the Python environment as a side effect of verification.
   - If a required local `.venv` junction / interpreter is absent or invalid, automation should fail fast with an actionable bootstrap message rather than fall back to system Python.
   - Existing OpenCode provisioning remains a separate concern from Python project-environment ownership.

8. **No destructive local migration assumptions**
   - Migration must account for Git's rule that a branch cannot be checked out by two worktrees simultaneously.
   - A detached `BlackfireCrusade_tool` or an existing `main` checkout in `temp-main` must be handled explicitly.
   - No `reset --hard`, `clean -fd`, forced worktree deletion, or loss of uncommitted work may be used as an implicit shortcut.

9. **Windows execution policy remains unchanged**
   - Non-interactive shell/tool commands are executed through `cmd.exe /d /s /c` and must not wait for stdin.
   - PowerShell automation invoked by agents remains wrapped through non-interactive `cmd.exe` execution according to the project Windows shell policy.

## Initial Scope

The lightweight survey identifies at least these likely contract/change surfaces:

- `docs/architecture/ai_development_workflow.md`
  - currently names `temp-main` as the permanent local main baseline and manual integration fallback.
- `.agents/skills/branch_completion_workflow/SKILL.md`
  - currently defines a permanent dual-worktree layout, permanently assigns `main` to `temp-main`, forbids `BlackfireCrusade_tool` from checking out main, and cross-references `BlackfireCrusade_tool\.venv` from baseline tests.
- `.gitignore`
  - verify `.venv` / local runtime artifacts remain correctly ignored.
- `scripts/ai_scout.ps1` and `scripts/ai_gate.ps1`
  - inspect whether interpreter/environment discovery or fallback behavior needs explicit preflight hardening; modify only if Scout shows these scripts currently violate the consumer-only/fail-fast invariant.
- workflow/testing documentation or helper scripts discovered by Scout that encode `temp-main`, cross-worktree interpreter paths, or environment-provisioning assumptions.
- one-time migration/bootstrap documentation or deterministic helper, if needed to make the convention reproducible and safe.

This is not permission to broadly refactor unrelated workflow code.

## Non-Goals

- Changing gameplay/runtime behavior, CV logic, scheduler semantics, or navigation behavior.
- Changing the supported OpenCode CLI/provider contract except where documentation references environment ownership.
- Making Scout or Gate responsible for installing Python dependencies.
- Creating one virtual environment per branch/worktree.
- Introducing containers/Conda/Poetry solely for this migration.
- Automatically deleting `temp-main` before branch ownership and dirty-state safety are verified locally.
- Solving general multi-developer environment isolation; this convention is for the project's current solo multi-worktree workflow unless explicitly generalized later.
- Allowing parallel agents to mutate one shared Python environment without coordination.

## Provisional Acceptance Criteria

1. Canonical documentation gives exactly one permanent local main worktree: `E:\Side_Project\BlackfireCrusade_tool`.
2. `temp-main` is removed from durable architecture/skill text as the permanent baseline authority, except migration/history notes where clearly marked transitional.
3. Canonical documentation defines the external `VenvPools` environment ownership model and `.venv` junction consumer pattern for main and task worktrees.
4. The convention explicitly forbids worktree-specific editable installs into the shared environment and explains the import-source risk.
5. The convention explicitly serializes shared-environment dependency mutation and forbids Scout/Gate from silently provisioning or mutating the Python environment.
6. Missing/invalid task-worktree `.venv` state has a deterministic, actionable bootstrap/fail-fast path; automation does not silently use system Python.
7. Branch-completion/baseline testing no longer relies on `temp-main` or an absolute interpreter path owned by another Git worktree.
8. A safe one-time migration sequence exists for the current state where `BlackfireCrusade_tool` may be detached and `main` is checked out in another worktree. It must preserve uncommitted work and respect multi-worktree branch exclusivity.
9. After migration, running `git branch --show-current` in `BlackfireCrusade_tool` should report `main`, and its HEAD should be synchronized with `origin/main` before official runtime validation.
10. Task worktrees can independently be deleted/recreated without deleting the canonical Python environment; recreating only their `.venv` junction restores environment access.
11. Relevant deterministic workflow tests or validation coverage are added/updated for any executable workflow-script behavior changed by this task. Docs-only changes must still have explicit manual validation steps.
12. No production gameplay behavior changes.

## Forbidden Shortcuts

- Keeping `temp-main` as a hidden second source of truth while merely renaming documentation.
- Moving the existing environment directory under `BlackfireCrusade_tool` and continuing to make task worktrees depend on that worktree path.
- Falling back to globally installed/system Python when `.venv` is absent.
- Auto-running dependency installation from Scout/Gate to make verification pass.
- Using `pip install -e .` in the shared environment as a convenience for branch-local imports.
- Destroying/recreating dirty worktrees to simplify migration.

## Uncertainty / Scout Questions

Scout should localize, within its normal bounded budget:

1. Every durable reference to `temp-main`, the permanent dual-worktree convention, or absolute `BlackfireCrusade_tool\.venv` reuse.
2. Whether any scripts currently discover `.venv`, invoke Python, or fall back to `python` / system PATH in ways that conflict with the target invariant.
3. Whether workflow-script testing infrastructure now exists on latest main and which focused tests should guard executable changes.
4. Whether repository package/import layout makes shared-venv execution from each worktree safe without editable install, and what command form guarantees current-worktree source resolution.
5. Whether a deterministic bootstrap/check helper already exists and should be extended instead of creating another script.
6. Whether `temp-main` has responsibilities beyond baseline/merge that need an explicit replacement after `BlackfireCrusade_tool` becomes permanent main.
7. Which canonical architecture document should permanently own the worktree/environment convention so the branch-completion skill can reference rather than duplicate it.

Scout findings may narrow or correct this Draft. They must not begin production implementation or silently promote the spec to Final.
