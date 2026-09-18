# task-cleanup-orchestration-wrapper

Status: Final

## Goal

Provide a repository-owned, single-command task cleanup entrypoint so post-merge cleanup no longer requires the user to manually copy a sequence of Git/worktree commands.

The wrapper must orchestrate the existing closeout contract without duplicating or weakening `scripts/worktree_cleanup_safety.ps1`.

Target user experience:

```bat
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\task_cleanup.ps1 -Task <task-id> < NUL"
```

Normal `-Task <task-id>` performs local cleanup only. Remote branch deletion is opt-in through an explicit switch such as `-DeleteRemoteBranch`.

The command must fail closed on ambiguous, dirty, unmerged, stale, partial, detached, or otherwise unsafe topology rather than guessing, pruning, forcing, or mutating unrelated state.

## Problem / evidence

Current repository contracts are safety-correct but operationally fragmented:

- `docs/architecture/ai_development_workflow.md` declares branch-completion as cleanup safety owner and requires `worktree_cleanup_safety.ps1` before normal worktree removal.
- `.agents/skills/branch_completion_workflow/SKILL.md` owns ancestry checks, topology/cleanliness validation, helper invocation, normal remove, bounded stale recovery, and branch deletion ordering.
- `scripts/worktree_cleanup_safety.ps1` is intentionally narrow: it classifies/detaches the task worktree's exact canonical `.venv` junction and does not own Git orchestration.
- `scripts/README.md` does not currently expose cleanup tooling as a normal user-facing maintenance command.
- Real usage still requires a human/ChatGPT to assemble multiple commands correctly; recent cleanup guidance accidentally bypassed the existing helper and used direct/forced removal, demonstrating that documentation alone is insufficient UX enforcement.

The read-only Gemini survey confirmed that repository history contains multiple branch naming styles and that current authoritative runtime ownership comes from `git worktree list --porcelain`, not branch-name synthesis. It also confirmed that v1 stale/partial-removal recovery should remain explicit and fail closed rather than becoming automatic convenience behavior.

## Architectural decision

Add `scripts/task_cleanup.ps1` as a thin orchestration wrapper.

Responsibility split remains:

```text
branch_completion_workflow
    = durable closeout orchestration contract

scripts/task_cleanup.ps1
    = normal user-facing deterministic orchestration entrypoint

scripts/worktree_cleanup_safety.ps1
    = narrow .venv junction classification/detach safety primitive
```

The wrapper must not become a second cleanup algorithm. It sequences existing invariants, validates evidence between phases, stops on failure, and emits actionable diagnostics.

## Scope

### 1. Add one orchestration wrapper

Add:

```text
scripts/task_cleanup.ps1
```

Required interface:

```powershell
scripts\task_cleanup.ps1 -Task <task-id>
```

Optional explicit remote deletion:

```powershell
scripts\task_cleanup.ps1 -Task <task-id> -DeleteRemoteBranch
```

The wrapper may be launched from any valid repository worktree, but all destructive Git operations must execute with the canonical permanent `main` worktree as cwd.

It must never remove the process/current working worktree.

### 2. Canonical orchestration sequence

Normal cleanup sequence:

1. validate `-Task`;
2. discover repository / worktree topology;
3. identify the canonical permanent `main` worktree from actual Git topology and canonical path expectations;
4. require canonical main to be attached to `main`, clean, non-detached, and usable as destructive-command cwd;
5. run `git fetch origin`;
6. resolve the task worktree deterministically from actual `git worktree list --porcelain` data using task identity/path evidence;
7. require exactly one resolved task worktree and one attached local branch;
8. require the task worktree to be clean;
9. verify the resolved task branch is an ancestor of fetched `origin/main`;
10. invoke `scripts/worktree_cleanup_safety.ps1 -WorktreePath <resolved-path> -Detach`;
11. capture helper stdout and validate exactly one JSON result;
12. continue only when helper result is valid and `code == "DETACHED"`;
13. run normal `git worktree remove <resolved-path>` without `--force`;
14. re-read `git worktree list --porcelain`;
15. verify the removed path is no longer registered and the resolved branch is no longer owned by any worktree;
16. delete the local branch using safe/non-forced deletion;
17. if and only if `-DeleteRemoteBranch` was supplied, delete the exact resolved remote branch after successful local cleanup;
18. emit a concise per-phase result report.

Every destructive phase is a hard boundary: failure stops all later destructive steps.

### 3. Task / branch resolution contract

Branch names are not synthesized from historical naming conventions.

Historical forms such as:

```text
<task-id>
task/<task-id>
task-<task-id>
```

are evidence of inconsistency, not a resolution algorithm.

Resolution must be topology-first:

```text
explicit task id
    -> canonical task-worktree identity / normalized registered path
    -> actual attached branch from git worktree list --porcelain
```

Requirements:

- resolve exactly one registered task worktree;
- take branch ownership from its porcelain record;
- require non-detached branch state;
- require the corresponding local branch ref to exist before branch deletion;
- zero, multiple, ambiguous, detached, or mismatched candidates fail closed;
- do not probe branch-name variants until one happens to exist.

### 4. Invocation / cwd contract

The wrapper may be launched from any valid repository worktree for user convenience.

Before destructive operations it must resolve the canonical permanent main worktree:

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

and require:

```text
branch == main
working tree == clean
not detached
registered in current git worktree topology
```

All destructive Git commands execute from canonical main cwd.

The wrapper must reject any topology where the target task worktree equals the current process/cwd worktree or canonical main worktree.

### 5. Remote branch deletion policy

Default:

```powershell
-Task <task-id>
```

performs local cleanup only.

Remote branch deletion is opt-in:

```powershell
-DeleteRemoteBranch
```

Rules:

- delete only the exact branch resolved from authoritative topology;
- perform remote deletion only after successful worktree removal, topology re-verification, and local branch deletion;
- a remote-delete failure must not roll back already completed local cleanup;
- final report must distinguish local-cleanup success from remote-delete success/failure.

### 6. Main synchronization boundary

The wrapper must run:

```text
git fetch origin
```

before ancestry decisions.

It must verify integration against fetched:

```text
origin/main
```

using ancestry.

It must not run `git pull --ff-only` as part of cleanup orchestration. Updating local main remains the branch-completion / post-integration synchronization responsibility, not cleanup-wrapper responsibility.

Canonical main must still be clean and attached so it is a safe command cwd.

### 7. Preserve existing `.venv` safety ownership

The wrapper must invoke the existing:

```text
scripts/worktree_cleanup_safety.ps1
```

for normal `.venv` classification/detach.

It must not reimplement:

- junction/reparse classification;
- canonical target validation;
- canonical environment survival checks;
- residual junction recovery logic.

Helper stdout is machine evidence, not free-form success text.

Wrapper must:

- capture helper stdout separately from diagnostics;
- require one parseable JSON object;
- require expected fields including `code`;
- accept only `DETACHED` for normal cleanup continuation;
- reject mixed, malformed, multiple, or non-JSON output as failure.

### 8. Stale / partial-removal recovery boundary

V1 normal wrapper does not automatically invoke:

```text
-PartialRemovalRecovery
-DetachedPendingRemove
git worktree prune --verbose
```

and does not infer stale proof.

If the helper, Git topology, or worktree removal indicates stale / partial / detached-pending-remove conditions, the wrapper must stop and emit bounded recovery guidance pointing to the existing `branch_completion_workflow` recovery contract.

No automatic prune is permitted in v1.

### 9. User-facing closeout contract

Update `.agents/skills/branch_completion_workflow/SKILL.md` so normal user-facing cleanup prefers the single wrapper command.

The detailed manual sequence remains authoritative for:

- diagnosis;
- wrapper fail-closed cases;
- stale/partial-removal recovery;
- exceptional topology.

The wrapper does not replace the closeout workflow's architecture authority.

### 10. Script discoverability

Update `scripts/README.md` to expose:

- `task_cleanup.ps1` as the normal user-facing task cleanup entrypoint;
- `worktree_cleanup_safety.ps1` as the narrow low-level safety primitive;
- normal invocation examples;
- `-DeleteRemoteBranch` opt-in semantics;
- fail-closed behavior and recovery handoff.

### 11. Focused deterministic tests

Extend existing workflow-script tests rather than creating an unrelated framework.

Use Python `unittest` + subprocess/temporary fixture repositories or command seams as appropriate.

Tests must never touch:

- real repository task worktrees;
- real remote branches;
- the real canonical shared Python environment.

## Known invariants

- Canonical permanent main worktree:
  `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`
- Canonical task worktree root:
  `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>` for new tasks.
- Git worktree topology is runtime machine state; paths/branch ownership must be resolved from `git worktree list --porcelain`, not conversation memory or branch-name guessing.
- Cleanup may proceed only after task branch ancestry is proven in fetched `origin/main`.
- Dirty, detached, stale, partial, or ambiguous state fails closed.
- `scripts/worktree_cleanup_safety.ps1` remains the sole `.venv` junction safety primitive.
- Normal cleanup continues only on validated helper `DETACHED` evidence.
- Normal cleanup must not use `git worktree remove --force`.
- Branch deletion occurs only after no registered worktree owns the branch.
- Remote deletion is explicit opt-in.
- Ordinary cleanup must not mutate the shared Python environment or install packages.
- The wrapper is orchestration, not a general Git worktree manager.
- Windows automation remains non-interactive and compatible with `cmd.exe /d /s /c "... < NUL"`.
- Any destructive-step failure stops subsequent destructive actions.
- Unrelated worktrees and branches remain untouched.

## Non-goals

- No rewrite of `worktree_cleanup_safety.ps1` safety semantics unless a concrete wrapper integration defect is discovered and separately justified.
- No general-purpose worktree manager.
- No automatic merge or push-to-main.
- No automatic `git pull --ff-only`.
- No automatic stale-registration pruning or recovery escalation.
- No `reset --hard`, `clean -fd`, force checkout, or force worktree deletion.
- No automatic cleanup of unrelated/stale worktrees.
- No shared-environment dependency mutation protocol.
- No game runtime changes.
- No Scout/Gate/model-routing changes.

## Acceptance criteria

1. A normal merged, clean task can be cleaned using one user-facing command with `-Task <task-id>`.
2. Default cleanup removes the task worktree and safe local branch only; remote deletion requires explicit `-DeleteRemoteBranch`.
3. The wrapper may be launched from any valid repository worktree but runs destructive Git commands from validated canonical main cwd.
4. The wrapper rejects attempts to remove its current/canonical-main worktree.
5. The wrapper fetches remote state before ancestry/topology decisions and does not perform `pull`.
6. The wrapper resolves the actual task worktree and branch from Git topology and rejects zero/multiple/ambiguous/detached matches.
7. Historical branch naming patterns are not used as guess-and-try resolution fallbacks.
8. The wrapper rejects cleanup when the resolved task branch is not an ancestor of fetched `origin/main`.
9. The wrapper rejects dirty task worktrees and does not alter their contents.
10. The wrapper invokes `worktree_cleanup_safety.ps1` and continues only on strict, single-object JSON evidence with `code == "DETACHED"`.
11. Malformed, mixed, missing, or unexpected helper output fails closed.
12. The wrapper performs normal `git worktree remove` only after successful detach evidence and never uses `--force` fallback.
13. After removal, it re-reads topology and verifies the intended worktree path and branch ownership are gone before branch deletion.
14. Local branch deletion is safe/non-forced; safe-delete failure leaves the branch intact and stops remote deletion.
15. Remote deletion deletes only the exact resolved branch and occurs only after successful local cleanup when explicitly requested.
16. Remote-delete failure is reported independently without misreporting local cleanup as failed/rolled back.
17. Any failure at a destructive boundary stops all later destructive actions.
18. Stale/partial-removal conditions do not trigger automatic prune, `-PartialRemovalRecovery`, or `-DetachedPendingRemove`; wrapper stops with bounded recovery guidance.
19. Unrelated worktrees/branches remain untouched.
20. The wrapper can be invoked non-interactively through the project Windows shell contract.
21. `scripts/README.md` exposes the wrapper and lower-level helper without duplicating the full algorithm.
22. `branch_completion_workflow` directs normal user-facing cleanup through the wrapper while retaining manual recovery semantics.
23. Focused deterministic tests cover happy path plus dirty, unmerged, ambiguous topology, invocation/cwd protection, helper parsing/failure, worktree-remove failure, post-remove ownership verification, local branch deletion, explicit remote deletion, and stop-on-failure boundaries.
24. Existing workflow-script tests remain green.
25. No game runtime production files change.

## Test strategy

At minimum cover:

1. happy-path local cleanup;
2. happy path with explicit remote deletion;
3. remote deletion omitted by default;
4. launch from main worktree;
5. launch from non-main repository worktree while destructive commands relocate to canonical main;
6. current/canonical-main worktree target protection;
7. exact task-worktree resolution;
8. zero/multiple/ambiguous topology;
9. detached task worktree;
10. representative historical branch names through actual fixture topology rather than synthetic guessing;
11. dirty task worktree;
12. unmerged task branch;
13. fetch failure;
14. malformed/multiple/mixed helper output;
15. helper result other than `DETACHED`;
16. normal worktree-remove failure after detach;
17. post-remove topology still reports the target or branch ownership;
18. safe local branch deletion failure;
19. remote delete attempted only after local cleanup and only with explicit flag;
20. no later destructive command after any failure;
21. absence of `--force`, `reset --hard`, `clean -fd`, automatic prune, automatic recovery escalation, and `git pull` in normal wrapper behavior.

Tests should use isolated temporary Git repositories / fake remotes / command seams and must not mutate the real shared environment.

## Expected implementation surface

Expected minimal surface:

- `scripts/task_cleanup.ps1` — new orchestration wrapper;
- `tests/test_workflow_scripts.py` — focused contract/subprocess tests;
- small test fixtures/seams only if required by existing test organization;
- `scripts/README.md` — discoverability and invocation;
- `.agents/skills/branch_completion_workflow/SKILL.md` — normal user-facing wrapper preference + recovery handoff;
- `docs/tasks/task-cleanup-orchestration-wrapper/SPEC.md` / task metadata.

`docs/architecture/ai_development_workflow.md` should remain unchanged unless implementation exposes a genuinely new durable architectural invariant. Do not duplicate wrapper sequencing there.

`scripts/worktree_cleanup_safety.ps1` should remain unchanged unless a concrete integration defect is proven; convenience refactoring is out of scope.

No game runtime production files should change.

## Completion gate

This SPEC is Final.

Gemini/Antigravity may now implement this contract. The implementation must preserve the existing cleanup safety primitive and fail-closed semantics. After implementation, run focused deterministic workflow-script tests, review the final diff, push the branch, and return commit/test evidence for ChatGPT final semantic/architecture review.
