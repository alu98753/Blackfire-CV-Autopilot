# worktree-shared-venv-cleanup-safety

Status: Final

## Goal

Make task-worktree closeout safe when each worktree consumes the repository-global Python environment through a local `.venv` Windows junction.

A real closeout demonstrated that the current instruction sequence is unsafe on Windows: `git worktree remove <path>` was invoked while `<worktree>\.venv` still pointed at the canonical shared environment, Git traversed the junction and attempted to unlink files under the external environment, a locked `.pyd` interrupted removal, the worktree was partially deleted (including `.git`), and stale Git worktree metadata continued to own the task branch.

This task must make closeout mechanically preserve the canonical shared environment, prevent this normal-removal hazard, and define bounded recovery for the known stale-registration state.

## Evidence basis

The Final SPEC is based on:

- lightweight survey of current `main` and closeout contracts;
- the real failure observed during `nemesis-user-intervention-lifecycle` cleanup;
- user-authorized Gemini/Antigravity read-only fallback survey in `CONTEXT.md`;
- current workflow test infrastructure in `tests/test_workflow_scripts.py` and `tests/workflow_scripts/`.

Confirmed evidence:

- `docs/architecture/ai_development_workflow.md` is the canonical workspace/environment SSOT.
- `.agents/skills/branch_completion_workflow/SKILL.md` is the closeout orchestration owner.
- There is no existing repository-owned worktree cleanup helper.
- The current closeout contract acknowledges that `.venv` is only a junction consumer but still hands directly to `git worktree remove <path>`.
- Windows reparse evidence from an existing worktree showed the expected `.venv` as mount-point/junction tag `0xA0000003` targeting `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- The existing workflow script test harness is the nearest deterministic test owner for a small helper.

## Architectural decision

This task will add a **small deterministic cleanup helper plus tests plus contract updates**.

Documentation-only enforcement is insufficient because junction classification, target verification, fail-closed destructive handoff, and stale-registration recovery are mechanical safety invariants that should not depend on a human remembering command ordering.

The branch-completion workflow remains the orchestration owner. The helper is a narrow filesystem/worktree-safety primitive and must not become a general worktree manager.

## Scope

### 1. Narrow cleanup helper

Add a repository-owned helper under `scripts/` with a narrow responsibility:

- inspect one explicit task worktree path;
- classify `<worktree>\.venv` without following it as proof of ownership;
- verify that the local `.venv` is the expected Windows junction/mount-point reparse object;
- verify its normalized target equals the canonical external environment;
- unlink only the verified local junction itself;
- verify the local `.venv` is gone and the canonical environment still exists;
- report deterministic success/failure suitable for branch-completion orchestration;
- support bounded classification of the known stale-registration recovery state.

The exact filename/API may be chosen during implementation, but it should be small, non-interactive, and independently testable.

### 2. Safe normal cleanup order

Canonical normal closeout becomes:

```text
verify integration ancestry / clean worktree / branch ownership
    -> verify .venv is exact canonical junction
    -> detach local .venv junction only
    -> verify canonical environment still exists
    -> git worktree remove <path>
    -> re-read git worktree list --porcelain
    -> only after branch no longer has a worktree owner may branch deletion proceed
```

`git worktree remove --force` remains forbidden for unknown/dirty state.

### 3. Bounded stale-registration recovery

Define recovery for the known partial-removal state:

```text
worktree removal already failed
+ worktree registration still exists
+ worktree path / .git administrative marker is demonstrably absent or invalid
+ no live/dirty worktree state remains to preserve
    -> classify registration as stale
    -> git worktree prune --verbose
    -> re-read git worktree list --porcelain
    -> verify intended stale registration is gone
    -> only then allow branch deletion
```

`git worktree prune` is not a general cleanup command. It is permitted only after explicit stale proof.

### 4. Contract convergence

Update durable workflow wording so the same safe order is not contradicted elsewhere.

At minimum inspect/update as needed:

- `.agents/skills/branch_completion_workflow/SKILL.md` — detailed closeout owner and command/order contract;
- `docs/architecture/ai_development_workflow.md` — durable workspace/environment invariant and cross-reference to safe cleanup;
- `.agents/skills/branch_start_workflow/SKILL.md` — only if needed to keep junction lifecycle wording consistent; startup must not duplicate closeout logic.

Avoid creating multiple independent cleanup algorithms in docs.

## Junction verification contract

Automatic unlink is permitted only when all of the following are proven:

1. `<worktree>\.venv` exists as a directory-like reparse object.
2. Reparse metadata identifies the object as a Windows junction / mount point, not an ordinary directory and not an unsupported/unknown reparse type.
3. The junction target is obtained from reparse/link metadata rather than by following the path and guessing ownership from the resolved contents.
4. After normalization, the target is exactly the canonical environment path:
   `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
5. The canonical target exists before detach.
6. The detach operation addresses the link path itself only and is non-recursive with respect to the target.
7. After detach, `<worktree>\.venv` is absent and the canonical environment still exists.

Implementation may use PowerShell/.NET/Windows filesystem metadata or another repository-available structured mechanism. `fsutil reparsepoint query` may be used as diagnostic evidence but must not be accepted via loose substring parsing as the sole ownership proof. `Resolve-Path` alone is insufficient because it follows the junction.

Path comparison must be strict and normalized for Windows semantics, including case-insensitivity and trailing separators. If extended/UNC forms or metadata fields cannot be normalized unambiguously, fail closed rather than infer equivalence.

## Cleanup decision tree

### A. `.venv` is the expected canonical junction

Proceed:

- detach local junction only;
- verify canonical target survived;
- then perform normal `git worktree remove`.

### B. `.venv` is missing on an otherwise normal, registered, runnable task worktree

Fail fast.

Rationale: runnable task worktrees are required to consume the canonical environment through their local `.venv`. Missing junction is not silently treated as successful cleanup because doing so would hide topology drift or an earlier partial-removal event.

If surrounding evidence instead proves the worktree is already partially removed/stale, classify under stale-recovery rules rather than normal cleanup.

### C. `.venv` is a normal physical directory

Fail closed and preserve it. Do not recursively remove it and do not continue with worktree removal automatically.

### D. `.venv` is a junction/reparse object with an unexpected target or unsupported reparse type

Fail closed and preserve it. Ownership is not proven.

### E. Worktree path or `.git` is already missing / partial removal suspected

Do not retry normal removal and do not use `--force`.

Inspect Git registration and filesystem state. Only transition to stale-registration recovery after proving no live/dirty worktree state remains to preserve.

### F. Registration proven stale

Run bounded `git worktree prune --verbose`, then re-read `git worktree list --porcelain` and verify the intended registration disappeared while unrelated registrations remain.

### G. Live or dirty registered worktree

Stop. No prune, reset, clean, force removal, or recursive deletion.

## Helper responsibility boundary

The helper may own:

- `.venv` classification;
- exact canonical-target verification;
- safe local junction detach;
- postcondition verification;
- structured diagnostics/result codes for normal-vs-stale cleanup decisions.

The helper must not own:

- merge or push to `main`;
- task ancestry policy beyond consuming explicit preconditions supplied by the closeout workflow;
- task branch deletion;
- remote branch deletion;
- broad worktree creation/removal orchestration;
- recursive deletion of unknown directories;
- shared environment mutation;
- package installation;
- `git worktree remove --force`;
- automatic pruning of ambiguous/live registrations.

The branch-completion workflow remains responsible for sequencing, integration checks, worktree removal, prune authorization after stale proof, and branch deletion.

## Known invariants

- Canonical physical environment:
  `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- No Git worktree owns the physical environment.
- A task worktree owns only its local `.venv` junction.
- Cleanup must never recursively delete or mutate the canonical environment target.
- Ordinary closeout is an environment-consumer operation: no `pip install`, `pip uninstall`, venv recreation, editable install, or dependency mutation.
- Cleanup inspects current `git worktree list --porcelain`; remembered paths/branch ownership are not authoritative.
- Task ancestry in `origin/main` is verified before cleanup.
- Dirty or ambiguous state fails closed.
- Local branch deletion is allowed only after no registered worktree owns the branch.
- Legacy/non-canonical worktree paths may be cleaned in place, but they do not weaken junction verification or stale-state safety.
- `shared-environment-mutation-protocol` remains out of scope.

## Non-goals

- No redesign of shared Python environment topology.
- No dependency mutation/locking/rebuild/package-management protocol.
- No general Git worktree manager.
- No automatic deletion of unknown `.venv` directories/reparse points.
- No `git worktree remove --force` fallback.
- No automatic `git worktree prune` on merely suspicious state.
- No unrelated Scout/Gate/model-routing/game-runtime changes.

## Tests / validation strategy

Use deterministic filesystem/control-flow tests. Never target the real canonical environment in automated tests.

Use temporary fixture directories and the existing workflow test harness where practical. If actual junction creation is reliable in the test environment, create temporary junctions only to temporary targets. Otherwise provide an injectable/classification seam so reparse metadata and command results can be simulated without privileges.

Focused coverage must include at least:

1. expected canonical junction is accepted and detached while target remains intact;
2. missing `.venv` on normal registered worktree fails closed;
3. ordinary physical directory fails closed and remains untouched;
4. wrong-target junction fails closed and remains untouched;
5. unsupported/unknown reparse type fails closed;
6. normal worktree removal is only handed off after successful junction detach + target-survival verification;
7. helper never recursively deletes the canonical target;
8. partial-removal state does not trigger force removal;
9. stale registration can be pruned only after explicit stale proof;
10. post-prune verification confirms intended registration is gone and unrelated registrations remain;
11. live/dirty registered worktree blocks prune/cleanup;
12. path normalization is case-insensitive and trailing-separator safe without accepting an actually different target.

Focused tests must be non-interactive and must not require mutation of the real shared environment.

## Acceptance criteria

1. Canonical closeout no longer invokes `git worktree remove` while a verified canonical `.venv` junction remains attached.
2. Automatic `.venv` unlink is possible only after structured proof that it is the exact canonical Windows junction/mount point.
3. Detach removes only the link object; canonical shared environment remains present and usable.
4. Missing `.venv` in a normal registered runnable worktree fails fast rather than silently continuing.
5. Physical directory, wrong-target junction, unsupported reparse type, ambiguous target, or target-verification failure all fail closed without recursive deletion.
6. Normal `git worktree remove` is attempted only after successful junction detach and postcondition verification.
7. `git worktree remove --force`, `reset --hard`, and `clean -fd` are not introduced as recovery shortcuts.
8. Partial-removal/missing-`.git` state does not cause blind retry of normal remove.
9. `git worktree prune --verbose` is used only after explicit stale-registration proof and is followed by registry re-verification.
10. Unrelated live worktree registrations are preserved.
11. Branch deletion remains blocked until the branch is no longer owned by any registered worktree.
12. Branch-completion workflow remains the orchestration owner; the helper stays narrowly scoped to junction/stale-state safety.
13. Durable architecture/skill wording converges on one safe closeout order and does not duplicate contradictory lifecycle logic.
14. Deterministic focused tests cover the normal junction path, fail-closed classifications, partial/stale recovery boundaries, and target-preservation invariant without touching the real canonical environment.
15. Existing shared-environment mutation policy remains unchanged and out of scope.

## Implementation surface

Expected minimal surface:

- one narrow helper under `scripts/` for Windows task-worktree `.venv` cleanup safety;
- focused deterministic tests under existing workflow test infrastructure;
- `.agents/skills/branch_completion_workflow/SKILL.md` update;
- `docs/architecture/ai_development_workflow.md` small durable invariant/cross-reference update;
- `.agents/skills/branch_start_workflow/SKILL.md` only if needed for wording consistency;
- this task package/evidence.

No game runtime production files should change.

## Completion gate

This SPEC is **Final**.

Gemini/Antigravity may now implement the Final contract on `task-worktree-shared-venv-cleanup-safety`. OpenCode Scout/reviewers remain read-only when used. After implementation, run focused deterministic tests and the repository Gate if available, then perform ChatGPT final semantic/architecture review before integration.