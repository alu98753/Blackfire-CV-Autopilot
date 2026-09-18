# task-start-orchestration-wrapper

Status: Final

## Goal

Provide one repository-owned task-start orchestration command that materializes an **already-approved remote AI task branch** into the canonical local task-worktree namespace and makes that worktree Python-runnable with minimal manual handoff.

This wrapper closes the remaining manual gap between:

```text
ChatGPT/GitHub task creation
  -> remote task branch + Draft SPEC/task.json already exist
  -> remote-to-local handoff
  -> local runnable task worktree
```

and the later explicit lifecycle step:

```text
scripts/ai_scout.ps1 -Task <task-id>
```

The wrapper is intentionally **not** a generic Git branch creator, not a task-spec generator, not a Scout runner, and not a Node dependency installer.

## Upstream dependency

This task consumes the finalized primitive introduced by:

```text
worktree-environment-junction-bootstrap
```

Specifically:

```text
scripts/worktree_environment_bootstrap.ps1
```

The wrapper must delegate Python `.venv` creation/validation to that primitive and must not duplicate junction classification or mutation logic.

## Lifecycle boundary

The formal AI Task Lifecycle remains:

```text
ChatGPT + user define task
        |
        v
remote task branch + Draft SPEC.md + task.json
        |
        v
scripts/task_start.ps1 -Task <task-id>
        |
        +-- validate/sync canonical main
        +-- inspect worktree topology
        +-- resolve approved remote task branch
        +-- create/attach canonical local worktree
        +-- fast-forward local task branch to its remote ref when safe
        +-- invoke worktree_environment_bootstrap.ps1
        |
        v
TASK_READY
        |
        v
explicit Scout / implementation / later verification lifecycle
```

The wrapper's responsibility ends at `TASK_READY`.

## Required interface

Implement:

```powershell
scripts/task_start.ps1 -Task <task-id> [-Branch <branch-name>]
```

### `-Task`

Mandatory.

Expected format:

```text
^[a-z0-9][a-z0-9-]*$
```

It determines:

- task artifact directory: `docs/tasks/<task-id>/`
- canonical task worktree path: `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`
- default branch name when `-Branch` is omitted.

### `-Branch`

Optional.

Default:

```text
<branch-name> = <task-id>
```

This override exists only for an already-approved remote task branch whose name differs from the task id, such as a legacy `task/<task-id>` branch.

The wrapper must not invent or auto-search multiple branch naming conventions.

### Deliberately absent flags

Do not add:

- `-WorktreePath`
- `-CanonicalMain`
- `-Remote`
- `-NoPush`
- `-BootstrapNode`
- `-RunScout`
- cleanup/delete switches

Canonical paths and remote identity are repository contracts, not per-run user choices.

## Canonical workspace contract

Permanent canonical main worktree:

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

Canonical new task worktree:

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

Canonical remote:

```text
origin
```

The wrapper must inspect actual Git worktree topology; it must never assume branch ownership from path conventions alone.

## Preconditions owned by upstream lifecycle

Before `task_start.ps1` is expected to succeed, GitHub must already contain:

```text
origin/<approved-task-branch>
docs/tasks/<task-id>/SPEC.md
docs/tasks/<task-id>/task.json
```

This is deliberate. ChatGPT + user remain task/spec owners.

If the approved remote branch or required task artifacts do not exist, startup fails closed. The wrapper must not create a new task branch, synthesize task artifacts, or silently fall back to a generic local-only workflow.

## Canonical main synchronization contract

Before task-local mutation, inspect the canonical main worktree.

Required order:

1. prove canonical main path exists and is the repository's permanent registered worktree;
2. prove it is attached to branch `main`;
3. prove it is clean;
4. execute `git fetch origin` from the canonical main worktree;
5. inspect `HEAD` versus fetched `origin/main`;
6. if `HEAD == origin/main`, continue;
7. if local `HEAD` is an ancestor of `origin/main`, fast-forward with:

```text
git merge --ff-only origin/main
```

8. otherwise fail closed.

### Main failure states

| Main state | Required behavior |
| --- | --- |
| clean + current | continue |
| clean + behind, fast-forward possible | fast-forward then continue |
| dirty | fail closed |
| detached HEAD | fail closed |
| wrong branch | fail closed |
| diverged / local-only commits relative to `origin/main` | fail closed |
| fetch/origin unavailable | fail closed |

Do not use:

```text
reset --hard
clean -fd
checkout -f
rebase
non-FF merge
```

The wrapper must treat native Git stderr as diagnostic data and native exit status as authoritative, following the existing proven Windows PowerShell pattern in `scripts/task_cleanup.ps1` rather than allowing normal Git stderr to become a terminating `NativeCommandError` accidentally.

## Approved task branch contract

After fetching `origin`, the wrapper must prove:

```text
refs/remotes/origin/<branch>
```

exists.

If missing, fail with a stable machine code such as:

```text
REMOTE_TASK_BRANCH_MISSING
```

The wrapper must **not** create the branch from `origin/main` and must **not** push a replacement branch.

### Fresh-base validation

The approved remote task branch must contain the currently synchronized `origin/main` as an ancestor:

```text
git merge-base --is-ancestor origin/main origin/<branch>
```

If this check fails, return a stable failure such as:

```text
TASK_BRANCH_STALE_BASE
```

and preserve all state.

The wrapper must not automatically merge or rebase latest main into a stale task branch. Updating an already-published task branch is an explicit GitHub/task-lifecycle operation outside this wrapper.

## Task artifact validation

Before creating or attaching the local worktree, prove the approved remote branch contains:

```text
docs/tasks/<task-id>/SPEC.md
docs/tasks/<task-id>/task.json
```

Use Git object/ref inspection or an equivalent non-mutating check against `origin/<branch>`.

After local worktree readiness, verify the checked-out copies still exist and that:

```text
task.json.id == <task-id>
```

Both `Draft` and `Final` task states are valid for startup. Startup must not change task status.

Missing/malformed task artifacts fail closed.

The wrapper never creates or edits `SPEC.md` or `task.json`.

## Branch/worktree state machine

Let:

```text
B = approved local branch name
R = origin/B
W = E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

### State A — remote branch exists, local branch absent, W absent

Action:

```text
git worktree add -b B W R
```

Result:

- local branch materialized from approved remote branch;
- tracking relationship established by Git;
- continue to validation/bootstrap.

### State B — local branch exists, is not checked out anywhere, W absent

Before attaching, compare local branch against `R`.

Allowed:

- local == remote;
- local is strictly behind remote and can be fast-forwarded after attachment.

Action:

```text
git worktree add W B
```

Then, on a clean worktree if behind:

```text
git pull --ff-only
```

Disallowed:

- local ahead of remote;
- local/remote diverged.

Those states fail closed. Remote is the handoff surface; startup must not publish local-only history.

### State C — B is already attached at W

Require:

- exact canonical path `W`;
- attached branch `B`;
- non-detached HEAD;
- clean worktree.

Then compare local branch with `R`:

- equal -> reuse;
- behind and FF possible -> `git pull --ff-only`, then reuse;
- ahead -> fail closed;
- diverged -> fail closed.

This is the idempotent re-run path.

### State D — B is checked out in any other registered worktree

Fail closed.

Do not move, detach, or steal the branch.

This includes legacy active worktrees outside the canonical path. Existing active/dirty legacy worktrees must not be relocated merely to satisfy directory conventions.

### State E — W exists on disk but is not a registered Git worktree

Fail closed and preserve the directory.

Do not delete, rename, overwrite, or adopt it automatically.

### State F — W is registered to another branch

Fail closed.

### State G — W is registered but detached

Fail closed.

Do not attempt detached-HEAD repair inside `task_start.ps1`.

### State H — local branch ahead of remote or local/remote diverged

Fail closed.

Do not push, merge, reset, or rebase automatically.

## Worktree cleanliness

Startup is a pre-development operation.

A reused task worktree must be clean before any fast-forward or environment bootstrap is attempted.

Dirty existing task worktree -> fail closed.

The wrapper is not a general "resume dirty development session" command. Preserving dirty active development is more important than forcing startup reconciliation.

## Python environment integration

Once Git/worktree state is safe, invoke the existing primitive:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\worktree_environment_bootstrap.ps1 -WorktreePath <W>
```

Capture native process stdout/stderr and exit status without contaminating the wrapper's own stdout machine contract.

Required success contract:

- helper exit code == `0`;
- exactly one non-empty stdout line;
- that line is valid JSON;
- `ok == true`;
- `code == "READY"`;
- `action` is `CREATED` or `UNCHANGED`.

On any helper failure or malformed result, `task_start.ps1` fails closed and preserves the already-created/attached worktree for inspection and deterministic retry.

The wrapper must never:

- run `mklink` directly;
- inspect reparse tags itself;
- delete/repair `.venv` itself;
- run `pip install` / `pip uninstall`;
- recreate a venv;
- fall back to system Python;
- use another worktree's `.venv` interpreter.

## Node dependency policy

Node workflow dependency readiness is **out of scope for this startup wrapper**.

Do not:

- inspect `node_modules` during task startup;
- run `npm ci`;
- invoke `bootstrap_node_workflow_deps.ps1`;
- add `-BootstrapNode`.

Reason:

- `ai_scout.ps1` uses the global OpenCode CLI and does not require repo-local `node_modules`;
- Node modules are per-worktree explicit bootstrap state;
- Gate/reviewer workflow is a later lifecycle consumer and is currently not the universal immediate next step;
- adding Node installation to every task start creates unnecessary latency and couples workspace creation to a later verification concern.

When a later lifecycle step actually requires Node dependencies, the existing explicit contract remains:

```text
scripts/bootstrap_node_workflow_deps.ps1
```

## Scout / Gate ownership

`task_start.ps1` must not invoke:

```text
scripts/ai_scout.ps1
scripts/ai_gate.ps1
```

Startup ends at workspace readiness.

Scout remains the next explicit lifecycle operation after successful handoff when required by the AI Task Lifecycle.

This preserves:

- separation of concerns;
- cheap/idempotent startup retries;
- independent Scout retry/fallback behavior;
- deterministic testing of Git/worktree startup without LLM runtime coupling.

## Cleanup ownership

`task_start.ps1` must not detach/remove worktrees or delete branches.

Existing teardown ownership remains:

```text
scripts/task_cleanup.ps1
    -> scripts/worktree_cleanup_safety.ps1
```

No startup failure may automatically call cleanup as rollback.

## Failure / partial-start semantics

The wrapper follows:

```text
fail closed + preserve evidence
```

Examples:

### Worktree creation succeeds, Python bootstrap fails

Preserve the worktree and branch exactly as created.

Return non-zero machine failure containing the bootstrap failure code/diagnostic.

Do not auto-remove the worktree or branch.

### Local branch/worktree attachment succeeds, later validation fails

Preserve it.

Do not reset, delete, detach, or rewrite history.

### Remote/task artifact/main validation fails before local mutation

Do not create a worktree or local branch.

### Wrapper is re-run after a partial start

The normal state machine must inspect current topology and either safely continue from the preserved state or fail closed with an actionable machine code.

## Machine output contract

The wrapper must emit **exactly one non-empty JSON line to stdout** for both success and failure.

Human diagnostics may go to stderr but must not contaminate stdout.

### Success minimum

```json
{
  "ok": true,
  "code": "TASK_READY",
  "message": "...",
  "task": "task-start-orchestration-wrapper",
  "branch": "task-start-orchestration-wrapper",
  "worktree": "E:\\Side_Project\\Blackfire-CV-Autopilot\\worktrees\\task-start-orchestration-wrapper",
  "base_sha": "<synchronized-origin-main-sha>",
  "remote_ref": "origin/task-start-orchestration-wrapper",
  "action": "CREATED|REUSED",
  "python_action": "CREATED|UNCHANGED",
  "python_version": "Python ..."
}
```

Success exits `0`.

### Failure minimum

```json
{
  "ok": false,
  "code": "<stable-machine-code>",
  "message": "...",
  "task": "<task-id>"
}
```

Failure exits non-zero.

Stable machine codes must distinguish at least:

- invalid task/branch arguments;
- canonical main missing/ambiguous;
- canonical main dirty;
- canonical main wrong branch/detached;
- canonical main divergence;
- fetch/origin failure;
- approved remote task branch missing;
- task branch stale relative to latest main;
- required task artifacts missing/malformed;
- branch owned by another worktree;
- canonical task path collision/unregistered directory;
- canonical task path attached to wrong branch;
- detached task worktree;
- dirty reused task worktree;
- local task branch ahead/diverged from remote;
- worktree add/fast-forward failure;
- Python bootstrap process/JSON/readiness failure;
- internal failure.

Exact numeric exit values remain implementation detail unless an existing repository ABI requires specific numbers.

## Implementation policy

Keep `scripts/task_start.ps1` self-contained.

It may locally reproduce small proven helpers from `scripts/task_cleanup.ps1`, including concepts such as:

- native Git invocation with stdout/stderr capture;
- `git worktree list --porcelain` parsing;
- Windows path normalization.

Do **not** extract a new shared `git_topology_utils.ps1` or refactor `task_cleanup.ps1` merely to reduce duplication in this task.

If implementation reveals a concrete correctness problem that requires shared extraction, stop and return evidence for spec reconsideration rather than silently widening scope.

## Deterministic test strategy

Add:

```text
tests/test_task_start_behavioral.py
```

Tests must not mutate the real repository's active worktrees, real canonical main, or production shared Python environment.

Use a mix of:

- isolated temporary Git repositories/worktrees for real Git semantics;
- bounded executable/helper overrides for deterministic failure injection;
- temporary fake task artifacts;
- a fake Python bootstrap helper or controlled helper seam where appropriate.

Recommended production seams may include narrowly scoped environment overrides such as:

```text
TASK_START_GIT_EXE
TASK_START_PYTHON_HELPER
TASK_START_CANONICAL_MAIN_OVERRIDE
TASK_START_WORKTREES_ROOT_OVERRIDE
```

Only add seams actually required by deterministic tests. Defaults must preserve production behavior.

### Required coverage

1. clean/current canonical main succeeds;
2. clean/behind main fast-forwards safely;
3. dirty main fails before task-local mutation;
4. detached/wrong-branch main fails;
5. diverged main fails;
6. fetch failure fails closed;
7. approved remote task branch missing fails and no branch/worktree is created;
8. remote task branch not based on current `origin/main` fails closed;
9. remote task artifacts missing/malformed fail before task-local mutation;
10. remote branch exists + local absent + path absent -> canonical worktree created;
11. existing correct canonical worktree -> idempotent `REUSED`;
12. existing correct local branch behind remote -> safe FF only when worktree clean;
13. local branch ahead/diverged -> fail closed;
14. branch owned by another worktree -> fail closed;
15. canonical path exists but unregistered -> fail closed/preserve;
16. canonical path registered to another branch -> fail closed;
17. detached canonical task worktree -> fail closed;
18. dirty reused task worktree -> fail closed;
19. Python bootstrap `READY` -> `TASK_READY`;
20. Python bootstrap non-zero / malformed JSON / extra stdout lines / non-READY code -> fail closed;
21. partial startup failure preserves created worktree/branch;
22. wrapper stdout contains exactly one non-empty valid JSON line on representative success and failure paths;
23. existing `worktree_environment_bootstrap` tests remain green;
24. `git diff --check` passes.

## Known invariants

- GitHub/remote task artifacts are the handoff SSOT before local startup.
- Canonical permanent main worktree remains `BlackfireCrusade_tool`.
- New task worktrees use `worktrees/<task-id>`.
- Worktree topology is runtime local-machine state and must be inspected.
- Multi-worktree branch exclusivity is never bypassed.
- Startup never force-resets, cleans, rebases, steals, or silently rewrites user state.
- Python environment is consumer-only and delegated to `worktree_environment_bootstrap.ps1`.
- Node dependency bootstrap remains separate and explicit.
- Scout/Gate remain separate lifecycle operations.
- Cleanup/removal remains owned by cleanup scripts.
- Partial startup failures preserve evidence rather than destructively rolling back.

## Non-goals

- No creation of a missing remote task branch.
- No creation or editing of task `SPEC.md` / `task.json`.
- No generic non-AI local-only branch workflow.
- No automatic merge/rebase of latest main into an already-published stale task branch.
- No remote push/publish behavior.
- No detached-HEAD recovery.
- No dirty-worktree resume behavior.
- No Node readiness/bootstrap.
- No Scout launch.
- No Gate launch.
- No cleanup/removal/branch deletion.
- No Python dependency mutation.
- No shared environment mutation protocol.
- No new shared Git helper abstraction unless new implementation evidence requires spec reconsideration.
- No game runtime behavior change.

## Acceptance criteria

1. `scripts/task_start.ps1 -Task <task-id>` resolves the canonical main/worktrees layout and approved remote task branch non-interactively.
2. Canonical main must be registered, attached to `main`, clean, fetched, and synchronized to `origin/main` using fast-forward-only semantics before task-local mutation.
3. Dirty/detached/wrong-branch/diverged canonical main or fetch failure fails closed without task-local mutation.
4. The approved `origin/<branch>` must already exist; the wrapper never creates or pushes a replacement branch.
5. The approved remote task branch must contain synchronized `origin/main` as an ancestor; stale published branches fail closed rather than receiving an automatic merge/rebase.
6. Required remote task artifacts `SPEC.md` and `task.json` must already exist and `task.json.id` must match `-Task`; startup never creates or edits them.
7. A missing local branch/worktree is materialized from the approved remote branch at `worktrees/<task-id>`.
8. An already-correct clean canonical task worktree is reused idempotently.
9. A clean task branch behind its remote may be advanced only through fast-forward-only semantics.
10. Local-ahead/diverged task branches, detached task worktrees, branch ownership conflicts, wrong-branch canonical path registrations, dirty reused worktrees, or unregistered path collisions fail closed and preserve state.
11. Python readiness is delegated exclusively to `worktree_environment_bootstrap.ps1`; success requires helper exit `0`, exactly one JSON stdout line, `ok=true`, and `code=READY`.
12. Startup performs no `.venv` reparse implementation, pip mutation, system-Python fallback, Node/npm bootstrap, Scout/Gate execution, cleanup, or remote branch publication.
13. Partial startup failures preserve created/attached branch/worktree state for inspection and deterministic retry; no destructive auto-rollback occurs.
14. The wrapper emits exactly one non-empty valid JSON line to stdout on success and failure; success returns `TASK_READY` and exit `0`.
15. Deterministic tests cover main sync/failures, remote/artifact preconditions, branch/worktree state machine, Python helper parsing, partial-start preservation, and machine-output invariants without mutating real active worktrees or the production shared environment.
16. Existing Python bootstrap behavior/tests remain green and `git diff --check` passes.

## Relationship to branch-start workflow

`.agents/skills/branch_start_workflow/SKILL.md` should be updated by implementation so the formal AI task-start path uses `scripts/task_start.ps1 -Task <task-id>` for the remote-to-local orchestration now owned by this wrapper.

The skill should continue to document the underlying invariants and manual recovery guidance, but must not maintain a competing second implementation of the same normal-path orchestration.
