---
name: branch_completion_workflow
description: >
  Solo-development branch closeout workflow. Owns regression/classification, contract convergence,
  integration readiness, post-integration synchronization guidance, and repository-owned task cleanup.
usage_scope: solo_development_only
---

# Branch Closeout Gated Workflow

This skill defines task closeout. It does not grant local agents integration authority.

The canonical workflow contract lives in `docs/architecture/ai_development_workflow.md`.

## 1. Core responsibility

Closeout owns:

- final task/branch context audit;
- regression baseline/classification;
- behavior-preserving maintenance cleanup when justified;
- contract/document convergence;
- final semantic/architecture readiness;
- user-authorized integration handoff;
- post-integration task cleanup through repository automation.

It does not allow local Gemini/Antigravity/OpenCode agents to merge to `main`.

## 2. Canonical workspace

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\        <- permanent attached main + runtime/CV validation home
└─ worktrees\
   └─ <task-id>\                 <- temporary task worktree
```

Canonical shared Python environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Each runnable worktree consumes that environment through its own local:

```text
.\.venv\Scripts\python.exe
```

Do not use another worktree's absolute interpreter path.

The old permanent temp-main / detached-main convention is retired. `BlackfireCrusade_tool` permanently owns local `main`.

## 3. Integration authority

1. Local Gemini / Antigravity / OpenCode do not merge, push to `main`, delete branches, or perform equivalent integration actions.
2. ChatGPT may integrate through GitHub only after applicable closeout requirements pass and the user explicitly authorizes integration.
3. The user may choose manual integration instead.
4. GitHub integration uses merge-commit semantics; do not silently squash/rebase.
5. Cleanup never runs before integrated ancestry is proven.

## 4. Closeout phases

### Phase 0 — Context audit

From the task worktree, inspect:

```powershell
git status --short
git branch --show-current
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

Confirm:

- expected task branch/worktree identity;
- no unrelated dirty changes;
- expected production/tests/docs/task artifacts;
- behavior change vs behavior-preserving refactor boundary.

Detached/wrong-branch/unrelated dirty state blocks closeout.

### Phase 1 — Canonical main baseline preflight

Canonical main is:

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

For regression/baseline work, main must be attached to `main` and clean. Fetch `origin`; if local main is behind and safely fast-forwardable, synchronize with fast-forward semantics. Dirty/diverged/detached/wrong-branch state blocks baseline use.

The task branch must also be current relative to the configured `base_ref` before formal Gate or final candidate review. After fetching, require the current `base_ref` (normally `origin/main`) to be an ancestor of task `HEAD`. If it is not, stop verification and reconcile the latest baseline into the task branch through repository-approved non-destructive merge semantics. Re-run affected deterministic/focused verification after reconciliation before formal Gate.

Do not run Gate against a stale long-lived branch where newer-main files can be misread as task-owned deletions or unrelated changes.

Do not use reset/clean/force checkout shortcuts.

### Phase 2 — Regression baseline

AI agents run only the smallest directly relevant focused tests allowed by project policy. Full-suite execution remains user-only when required.

Task tests use:

```text
<task-worktree>\.venv\Scripts\python.exe
```

Main baseline tests use:

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool\.venv\Scripts\python.exe
```

Each command runs from its own worktree root so source imports resolve to the correct tree.

If tests share game/runtime/user-data resources, run them serially.

### Phase 3 — Regression classification

Classify failures as:

```text
PRE_EXISTING_FAILURE
EXPECTED_BEHAVIOR_CHANGE
BRANCH_REGRESSION
UNCERTAIN
```

`BRANCH_REGRESSION` or `UNCERTAIN` blocks closeout.

### Phase 4 — Refactor safety gate

Do not perform opportunistic maintenance refactors without tests/evidence protecting the relevant behavior.

### Phase 5 — Behavior-preserving maintenance refactor

Allowed only when clearly behavior-preserving, for example:

- dead logic;
- duplicate glue;
- stale comments/docstrings;
- responsibility-boundary clarity;
- testability improvements;
- architecture drift cleanup.

If Final SPEC did not authorize behavior change, closeout refactor must not introduce one.

### Phase 6 — Post-refactor verification

Run the smallest directly relevant focused tests. Any new failure/observable behavior change re-blocks closeout.

### Phase 7 — Code/doc hygiene

Remove task-local/transient wording from durable production code where appropriate. Do not duplicate canonical architecture contracts across many files.

### Phase 8 — Contract convergence

Converge durable invariants into canonical architecture/workflow SSOT. Task SPEC/CONTEXT/reviews/EVIDENCE remain task lifecycle/history artifacts, not a permanent second architecture authority.

Tracked-history deletion or archival outside the Final SPEC requires explicit user agreement. Local worktree cleanup does not imply deletion of tracked task-history artifacts.

### Phase 9 — Development story

When project convention calls for it, record a concise PARS development story. The story is historical narrative, not architecture authority.

### Phase 10 — Final branch audit and verification handoff

Confirm:

```powershell
git fetch origin
git status --short
git branch --show-current
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git merge-base --is-ancestor <base-ref> HEAD
```

Verify:

- task branch clean;
- current configured `base_ref` is an ancestor of task `HEAD`;
- expected commits pushed;
- no unrelated files;
- Final SPEC/current implementation/evidence align;
- no undeclared behavior change;
- canonical docs converged.

If formal AI Gate is applicable, run it only after this baseline-freshness check and any required post-reconciliation verification. Gate meanings remain:

```text
0 = trusted verification PASS
2 = CANDIDATE_BLOCKED
1 = VERIFICATION_UNAVAILABLE
```

`2` or `1` blocks integration and returns to bounded diagnosis/correction/verification.

After a successful formal Gate, canonical `docs/tasks/<task-id>/reviews/*.md` and `EVIDENCE.md` required for remote final review must be committed and pushed to the task branch. Local-only Gate evidence is not a complete GitHub handoff.

### Phase 11 — Integration readiness

Local agents deliver readiness; they do not merge.

Preferred path:

1. Candidate HEAD and applicable canonical Gate evidence are pushed and reviewable on GitHub.
2. ChatGPT re-checks current expected head/base on GitHub.
3. ChatGPT performs final semantic/architecture review.
4. User explicitly authorizes integration.
5. ChatGPT integrates through GitHub with merge-commit semantics.

Manual fallback is allowed when the user prefers it, but it uses the canonical permanent `main` worktree—not temp-main—and must preserve repository merge policy.

## 5. Post-integration synchronization

After remote integration, local permanent main may be synchronized when immediate local runtime/baseline use is needed:

```powershell
git fetch origin
git pull --ff-only
```

This is a main synchronization operation, not task cleanup internals.

If no immediate local-main use is needed, the next formal `task_start.ps1` will validate/fetch/safely synchronize canonical main before materializing another task.

## 6. Normal task cleanup: one high-level command

After integration is confirmed, users should **not** manually reconstruct `.venv` detach + `git worktree remove` + branch deletion.

Normal cleanup is:

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id>
```

If policy/user intent also requires deleting the remote task branch:

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id> -DeleteRemoteBranch
```

Run the command from a valid repository worktree outside the task worktree being removed; canonical main is the normal operator location.

### What `task_cleanup.ps1` owns

The wrapper owns the normal teardown mechanics:

- discovers canonical repository/main through Git common-dir state;
- validates canonical main exists and is clean;
- fetches `origin`;
- re-reads actual worktree topology;
- resolves the intended attached task worktree/branch;
- refuses to remove the current or canonical main worktree;
- requires the task worktree to be clean;
- proves task branch ancestry in `origin/main`;
- invokes `worktree_cleanup_safety.ps1 -Detach`;
- requires the helper's exact `DETACHED` machine result;
- runs normal `git worktree remove`;
- verifies branch/path ownership disappeared from topology;
- safely deletes the local branch;
- optionally deletes the remote branch when explicitly requested.

It fails closed rather than forcing unknown state.

This cleanup removes local task execution/worktree state. It does not delete tracked task-history files from repository history.

## 7. What users should no longer do during normal cleanup

When `task_cleanup.ps1` can own the operation, do not ask users to manually perform:

```text
worktree_cleanup_safety.ps1 -Detach
git worktree remove <task-path>
git branch -d <task-branch>
git worktree prune
manual .venv junction deletion
```

Those are implementation/recovery-level operations, not routine user choreography.

The normal user interaction should be:

```text
ChatGPT: task is integrated; run this one cleanup command.
User: runs task_cleanup.ps1.
Script: returns success or a bounded fail-closed reason.
```

## 8. Cleanup failure / recovery policy

If `task_cleanup.ps1` fails, preserve the filesystem/Git state and inspect the reported reason before issuing any low-level recovery command.

Typical blockers:

- canonical main dirty;
- task worktree missing/ambiguous;
- task worktree dirty;
- branch not integrated into fetched `origin/main`;
- unsafe `.venv` state;
- worktree removal failure;
- local branch safe-delete failure.

Do not respond to a fail-closed result with `--force`, `reset --hard`, `clean -fd`, or blind prune.

### Low-level cleanup primitive

`scripts/worktree_cleanup_safety.ps1` is a narrow internal/recovery primitive. It owns only `.venv` classification/detachment safety. It does not own ancestry, cleanliness, branch deletion, remote deletion, or normal operator sequencing.

Partial-removal recovery modes (`-PartialRemovalRecovery`, `-DetachedPendingRemove`) are bounded recovery evidence paths. They are not normal task cleanup commands and should only be used after the corresponding state has been proven.

Only after a specific stale-registration recovery proof may `git worktree prune --verbose` be considered, followed by topology re-read. Do not make prune routine.

## 9. Environment closeout rules

Closeout does not:

- `pip install` / `pip uninstall`;
- recreate the shared venv;
- modify shared-env dependency state;
- use `pip install -e .`;
- use another worktree's interpreter;
- silently repair a missing/unsafe `.venv`.

Normal cleanup delegates junction safety to repository scripts.

## 10. Gate / verification note

Gate/reviewer policy remains a separate verification concern. A user-authorized temporary decision not to run Gate for workflow-infrastructure work does not silently rewrite the canonical Gate contract.

Closeout must accurately state which verification evidence actually exists and whether that evidence has been pushed to GitHub when remote final review depends on it.

## 11. Closeout report

A closeout report should include at least:

```text
Task / Branch:
Head:
Main/base_ref baseline:
Base-ref ancestry current: yes/no
Regression classification:
Focused verification:
User full-suite status (if required):
Contract convergence:
Gate / reviewer evidence actually available:
Gate evidence pushed to GitHub: yes/no/not-applicable
Final semantic review status:
Integration authority:
Cleanup readiness:
```

## 12. Completion criteria

```text
[ ] task worktree/branch identity verified
[ ] canonical main baseline state valid when needed
[ ] configured base_ref is an ancestor of task HEAD before formal Gate/final candidate review
[ ] regression baseline classified
[ ] no BRANCH_REGRESSION / UNCERTAIN blocker
[ ] maintenance changes preserve declared behavior
[ ] focused verification passed
[ ] full suite completed by user when required
[ ] durable contracts converged
[ ] final branch audit clean
[ ] candidate pushed and reviewable
[ ] applicable canonical Gate reviews/EVIDENCE pushed before remote final review
[ ] explicit user authorization obtained before integration
[ ] integration confirmed in origin/main
[ ] normal cleanup delegated to task_cleanup.ps1
```

# One-line principle

> Review and integration remain gated human/ChatGPT decisions; once integrated, routine task-worktree teardown is one repository cleanup command, not a manual sequence of Git and junction operations.
