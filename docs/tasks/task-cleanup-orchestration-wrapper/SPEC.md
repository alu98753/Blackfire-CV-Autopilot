# task-cleanup-orchestration-wrapper

Status: Draft

## Goal

Provide a repository-owned, single-command task cleanup entrypoint so post-merge cleanup no longer requires the user to manually copy a sequence of Git/worktree commands.

The wrapper must orchestrate the existing closeout contract without duplicating or weakening `scripts/worktree_cleanup_safety.ps1`.

Target user experience:

```bat
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\task_cleanup.ps1 -Task <task-id> < NUL"
```

The command should fail closed on ambiguous, dirty, unmerged, stale, or unsafe topology rather than guessing or forcing cleanup.

## Problem / evidence

Current repository contracts are already safety-correct but operationally fragmented:

- `docs/architecture/ai_development_workflow.md` declares branch-completion as cleanup safety owner and requires `worktree_cleanup_safety.ps1` before normal worktree removal.
- `.agents/skills/branch_completion_workflow/SKILL.md` owns ancestry checks, topology/cleanliness validation, helper invocation, normal remove, bounded stale recovery, and branch deletion ordering.
- `scripts/worktree_cleanup_safety.ps1` is intentionally narrow: it classifies/detaches the task worktree's exact canonical `.venv` junction and does not own Git orchestration.
- `scripts/README.md` does not currently expose cleanup tooling as a normal user-facing maintenance command.
- Real usage still requires a human/ChatGPT to assemble multiple commands correctly; recent cleanup guidance accidentally bypassed the existing helper and used direct/forced removal, demonstrating that documentation alone is insufficient UX enforcement.

## Scope

### 1. Add one orchestration wrapper

Add a small PowerShell entrypoint, provisionally:

```text
scripts/task_cleanup.ps1
```

It should accept an explicit task id and orchestrate the canonical closeout cleanup sequence from a valid repository worktree, preferably the permanent main worktree.

The wrapper may own deterministic sequencing of:

1. repository/root discovery and input validation;
2. `git fetch origin`;
3. current `git worktree list --porcelain` inspection;
4. task branch/worktree resolution from actual Git topology;
5. verifying canonical main is usable for orchestration;
6. verifying the task worktree is clean;
7. verifying the task branch is integrated into `origin/main` via ancestry;
8. invoking `scripts/worktree_cleanup_safety.ps1 -WorktreePath <resolved-path> -Detach`;
9. requiring successful `DETACHED` evidence and preserving helper diagnostics;
10. normal `git worktree remove <resolved-path>` without `--force`;
11. re-reading worktree topology and verifying branch ownership disappeared;
12. safe local branch deletion;
13. optional/explicit remote branch deletion according to the finalized CLI contract;
14. final concise cleanup report.

### 2. Preserve existing safety ownership

The new wrapper must call the existing helper for `.venv` classification/detach. It must not reimplement junction target verification, reparse classification, canonical-environment ownership checks, or residual-junction recovery logic.

### 3. User-facing single-command contract

Update `.agents/skills/branch_completion_workflow/SKILL.md` so that, when the wrapper is available, user-facing cleanup instructions prefer the single repository-owned entrypoint instead of manually composing the lower-level sequence.

Manual lower-level commands remain a diagnostic/recovery path when the wrapper fails closed.

### 4. Script index / discoverability

Update `scripts/README.md` to document:

- `worktree_cleanup_safety.ps1` as the narrow safety primitive;
- `task_cleanup.ps1` as the normal user-facing orchestration entrypoint;
- the expected invocation context and fail-closed behavior.

### 5. Focused deterministic tests

Extend existing workflow-script tests rather than creating a new unrelated framework.

Tests must avoid touching real task worktrees, real remote branches, or the real canonical Python environment. Use temporary fixture repositories / injected command seams / fixture scripts as appropriate.

## Known invariants

- Canonical permanent main worktree:
  `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`
- Canonical task worktree root:
  `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>` for new tasks.
- Git worktree topology is runtime machine state; paths/branch ownership must be resolved from `git worktree list --porcelain`, not guessed from conversation memory.
- Cleanup may proceed only after task branch ancestry is proven in fetched `origin/main`.
- Dirty or ambiguous task worktree state fails closed.
- `scripts/worktree_cleanup_safety.ps1` remains the sole `.venv` junction safety primitive.
- Normal cleanup must not use `git worktree remove --force`.
- Branch deletion occurs only after no registered worktree owns the branch.
- Ordinary cleanup must not mutate the shared Python environment or install packages.
- The wrapper is orchestration, not a general Git worktree manager.
- Windows automation remains non-interactive and compatible with `cmd.exe /d /s /c "... < NUL"`.

## Non-goals

- No rewrite of `worktree_cleanup_safety.ps1` safety semantics unless a concrete wrapper integration defect is found.
- No general-purpose worktree manager.
- No automatic merge or push-to-main.
- No `reset --hard`, `clean -fd`, force checkout, or force worktree deletion.
- No automatic cleanup of unrelated/stale worktrees.
- No shared-environment dependency mutation protocol.
- No game runtime changes.
- No Scout/Gate/model-routing changes.

## Provisional acceptance criteria

1. A normal merged, clean task can be cleaned using one user-facing command with only `-Task <task-id>` plus any explicitly finalized optional branch-deletion flag.
2. The wrapper fetches remote state before ancestry/topology decisions.
3. The wrapper resolves the actual task worktree and branch from Git topology and rejects zero/multiple/ambiguous matches.
4. The wrapper rejects cleanup when the task branch is not an ancestor of fetched `origin/main`.
5. The wrapper rejects dirty task worktrees and does not alter their contents.
6. The wrapper invokes `worktree_cleanup_safety.ps1` and continues only on the expected safe detach result.
7. The wrapper performs normal `git worktree remove` only after successful detach evidence; it never adds `--force` as fallback.
8. After removal, it re-reads topology and verifies the intended branch no longer has a worktree owner before branch deletion.
9. Local branch deletion is safe/non-forced and a failed safe-delete leaves the branch intact with a clear result.
10. Remote branch deletion behavior is explicit and deterministic; it must not silently delete an unexpected branch.
11. Failure at any destructive boundary stops subsequent destructive steps and emits actionable diagnostics.
12. Unrelated worktrees/branches remain untouched.
13. The wrapper can be invoked non-interactively through the project Windows shell contract.
14. `scripts/README.md` exposes the normal cleanup entrypoint and the lower-level safety helper without duplicating the full algorithm.
15. `branch_completion_workflow` directs normal user-facing cleanup through the wrapper, with lower-level commands reserved for diagnosis/recovery.
16. Focused deterministic tests cover happy path plus unmerged, dirty, ambiguous topology, helper failure, worktree-remove failure, post-remove ownership verification, and branch deletion boundaries.

## Uncertainty to resolve before Final

1. **Remote branch deletion default**: should normal `-Task` cleanup delete both local and remote task branches automatically, or require an explicit switch such as `-DeleteRemoteBranch`? The current contract says remote deletion follows repository/user policy, so this should be explicit rather than guessed.
2. **Invocation location**: likely require execution from the permanent main worktree (or internally relocate Git command cwd to it) so the wrapper never tries to remove its own current working directory. Confirm the cleanest contract against existing script/test conventions.
3. **Branch naming**: tasks currently use both `<task-id>` and `task/<task-id>` / `task-<task-id>` historical patterns. The wrapper should probably resolve by worktree/task metadata/topology rather than synthesize one naming convention. Confirm bounded resolution rules.
4. **Stale-registration recovery**: initial wrapper should likely fail closed and print the existing bounded recovery path instead of automatically pruning. Confirm whether any stale recovery belongs in v1 of this convenience wrapper.
5. **Main synchronization**: cleanup needs fetched `origin/main` for ancestry, but should it also require local `main == origin/main` / run `pull --ff-only`, or merely use remote ancestry and leave main synchronization as a separate post-integration responsibility?

## Expected implementation surface

Likely minimal surface:

- `scripts/task_cleanup.ps1` (new)
- `tests/test_workflow_scripts.py` and/or existing `tests/workflow_scripts/` fixtures
- `scripts/README.md`
- `.agents/skills/branch_completion_workflow/SKILL.md`
- `docs/architecture/ai_development_workflow.md` only if a small durable cross-reference is required; do not duplicate the orchestration algorithm there
- task package artifacts

No game runtime production files should change.
