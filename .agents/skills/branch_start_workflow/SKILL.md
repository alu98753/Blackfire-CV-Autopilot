---
name: branch_start_workflow
description: >
  Formal AI task startup and branch/worktree startup guidance. Formal AI tasks use
  scripts/task_start.ps1 as the normal path; low-level Git/worktree steps are recovery/manual fallback only.
usage_scope: solo_development_only
---

# Branch Start Workflow

This skill defines the start boundary for Feature / Fix / Refactor / Docs / Test work.

The canonical workflow contract lives in `docs/architecture/ai_development_workflow.md`.

## 1. Normal path for formal AI tasks

A formal AI task is expected to already have on GitHub:

```text
origin/<approved-task-branch>
docs/tasks/active/<task-id>/SPEC.md
docs/tasks/active/<task-id>/task.json
```

Those artifacts are created by ChatGPT/user before local task execution.

For this case, the user should not manually reconstruct fetch / worktree-add / branch-switch / `.venv` bootstrap steps. Use the repository wrapper:

```powershell
.\scripts\task_start.ps1 -Task <task-id>
```

For an approved legacy/nonstandard branch name:

```powershell
.\scripts\task_start.ps1 -Task <task-id> -Branch <branch-name>
```

A successful result is one machine-readable JSON record with:

```text
code = TASK_READY
```

At `TASK_READY`, the task worktree is attached to the expected branch at the canonical path and its worktree-local Python consumer is runnable.

The next AI lifecycle step, when required, is explicit Scout execution; `task_start.ps1` does not run Scout itself.

## 2. What `task_start.ps1` owns

For formal AI tasks, the wrapper owns the mechanical startup sequence:

- discovers/validates the canonical permanent main worktree;
- inspects actual Git worktree topology;
- requires canonical main to be attached to `main` and clean;
- fetches `origin`;
- safely fast-forwards canonical main when possible;
- validates that the approved remote task branch exists;
- validates that current `origin/main` is an ancestor of that remote task branch;
- validates remote `SPEC.md` and `task.json` and matching task id;
- requires every formal task `task.json` to contain one explicit `models.review` provider/model string (canonical default: `opencode/big-pickle`); null, missing, empty, array, or locally configured defaults are invalid;
- creates or safely reuses the canonical task worktree;
- respects Git multi-worktree branch exclusivity;
- safely fast-forwards a clean local task branch to the remote when allowed;
- invokes `scripts/worktree_environment_bootstrap.ps1`;
- verifies the bootstrap helper machine contract;
- returns `TASK_READY` or a stable fail-closed code.

The wrapper intentionally does **not**:

- create an unapproved new task branch;
- synthesize task artifacts;
- merge/rebase a stale task branch with latest main;
- repair detached/dirty/diverged states;
- install Python dependencies;
- bootstrap Node dependencies;
- launch Scout or Gate;
- perform cleanup or branch deletion.

## 3. Canonical workspace contract

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\        <- permanent attached main + runtime/CV home
└─ worktrees\
   └─ <task-id>\                 <- branch-scoped task worktree
```

Canonical shared Python environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree uses its own local consumer path:

```text
.\.venv\Scripts\python.exe
```

The `.venv` entry is a junction to the canonical shared environment. No worktree owns the physical environment.

New formal task worktrees use the project-scoped path above. Existing active legacy worktrees may remain where they are until closeout; do not relocate dirty/active worktrees merely for tidiness.

## 4. Trigger identification

Use this workflow when the user explicitly starts implementation lifecycle work, for example:

- `開始 XXX task`
- `正式開始 XXX`
- `建立 XXX task`
- `開始這個功能`
- `開始修這個 bug`

Discussion, brainstorming, design review, and code review alone do not create a local worktree.

## 5. Formal AI task lifecycle boundary

The formal sequence is:

```text
ChatGPT + user define task
        |
        v
GitHub remote branch + Draft SPEC.md + task.json
        |
        v
task_start.ps1
        |
        v
TASK_READY
        |
        v
Scout (explicit next step when required)
        |
        v
ChatGPT + user Final SPEC
        |
        v
Gemini/Antigravity implementation
```

The user-facing handoff should therefore normally be one command, not a copied list of internal Git/worktree operations.

## 6. Failure behavior

`task_start.ps1` deliberately fails closed rather than guessing or repairing ambiguous state.

Typical blockers include:

- canonical main dirty, detached, wrong branch, or diverged;
- remote task branch missing;
- task branch stale relative to current `origin/main`;
- required task artifacts missing/malformed;
- branch already owned by another worktree;
- canonical task path occupied by an unregistered directory or another branch;
- detached task worktree;
- task local/remote branch ahead/diverged state;
- Python bootstrap failure.

On failure, preserve state and report the machine code. Do not immediately substitute destructive commands.

## 7. Recovery / manual diagnostics

Low-level commands are diagnostic/recovery tools, not the normal formal-AI-task path.

Useful read-only inspection:

```powershell
git worktree list --porcelain
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git branch -vv
```

Before giving any recovery mutation command, confirm current topology and branch ownership. Never assume a branch can be checked out just because the expected directory exists.

Forbidden shortcuts:

```text
git reset --hard
git clean -fd
force checkout
force worktree removal
```

If a stale task branch must be updated with latest main, that is an explicit Git/task-lifecycle operation outside `task_start.ps1`; do not silently merge/rebase it as startup recovery.

## 8. Manual / non-AI task fallback

The wrapper is intentionally optimized for formal AI tasks whose remote branch and task package already exist.

For a genuinely manual/non-AI branch that is outside this contract, normal Git worktree operations may still be used after topology inspection. Such a workflow must still obey:

- canonical permanent main ownership;
- `git fetch origin` before branch decisions;
- clean main before synchronization;
- `git worktree list --porcelain` before checkout/add;
- no branch stealing from another worktree;
- project-scoped worktree path for new work;
- no silent Python environment mutation.

Do not disguise a formal AI task as a generic branch merely to bypass `task_start.ps1` safety checks.

## 9. Python environment ownership

For formal AI tasks, `task_start.ps1` invokes:

```text
scripts/worktree_environment_bootstrap.ps1
```

Users normally do not need to call the primitive themselves.

Direct primitive use is reserved for bounded diagnostics/recovery or non-standard workflows:

```powershell
.\scripts\worktree_environment_bootstrap.ps1 -WorktreePath <worktree>
```

Never run `pip install`, `pip uninstall`, recreate the shared environment, use system Python fallback, or use another worktree's interpreter to make startup succeed.

## 10. Node workflow dependencies

Node readiness is intentionally outside `task_start.ps1`.

If a later consumer such as Gate/reviewer tooling requires repository-local Node packages and the worktree is not bootstrapped, use the explicit repository operation:

```powershell
.\scripts\bootstrap_node_workflow_deps.ps1
```

Scout uses the global OpenCode CLI and does not require repository `node_modules`.

## 11. Remote tracking

For formal AI tasks, the approved remote branch already exists before `task_start.ps1` runs. The wrapper materializes/tracks that handoff; the user does not need to run `git push -u origin HEAD` as part of normal formal task startup.

For generic/manual branches outside the formal AI task lifecycle, publishing an intended review branch remains an explicit Git operation.

## 12. Development boundary snapshot

The authoritative scope comes from `docs/tasks/active/<task-id>/SPEC.md` when present. Do not create a second local spec.

Useful snapshot:

```text
Task / Branch: <name>
Worktree: E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
Base: origin/main @ <sha>
Goal: <from SPEC>
Remote: origin/<branch>
Environment: worktree-local .venv consumer ready
```

## 13. Commit rules during development

Follow `.agents/AGENTS.md`:

- Angular/conventional commit type;
- no `git add .`;
- no `git add -A`;
- no `git commit -a`;
- precisely stage task-related files only;
- do not mix unrelated working-tree changes.

## 14. Explicit non-responsibilities

Branch start does not own:

- semantic task/spec authority;
- production implementation;
- full regression suite;
- Gate/reviewer verdicts;
- merge/integration;
- task cleanup;
- branch deletion;
- Python dependency mutation;
- Node dependency mutation except an explicit later bootstrap operation.

## 15. Completion criteria

For a formal AI task, `TASK_READY` is the mechanical completion signal. It means the wrapper has already validated/synchronized the relevant startup mechanics and Python worktree consumer.

Do not ask the user to repeat the internal worktree/bootstrap checks after a successful `TASK_READY` unless new evidence indicates state changed after the wrapper completed.

# One-line principle

> Formal AI task startup is one repository command; low-level Git/worktree/environment commands are recovery tools, not routine user choreography.
