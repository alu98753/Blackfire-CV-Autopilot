# Scout Context — Worktree Shared `.venv` Cleanup Safety

## Status

Scout evidence only. The task `SPEC.md` remains **Draft**; this document does not promote it to Final and does not authorize implementation.

## Survey scope

Inspected the task SPEC and task metadata, the branch-start and branch-completion workflow instructions, the AI development architecture, the existing workflow scripts/tests, the repository worktree topology, and the configured Windows Python environment paths. No production code, workflow instruction, test, or shared environment was modified.

## Confirmed topology and environment evidence

- The canonical repository is `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`.
- The canonical external environment is `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- The architecture and branch-start workflow describe each runnable worktree's local `.venv` as a Windows junction to that external environment; commands must use the current worktree's `.venv\Scripts\python.exe`.
- `git worktree list --porcelain` showed the main worktree, the existing `ai-workflow-resume-parallel-gate` worktree, and this task worktree. The requested task worktree is attached to `task-worktree-shared-venv-cleanup-safety` and is clean.
- The requested task worktree currently has no `.venv`. This is evidence that this docs-only worktree is not presently a runnable environment consumer; it is not evidence that a future runnable worktree may safely omit the junction.
- In the existing active worktree, `fsutil reparsepoint query` reported reparse tag `0xA0000003` (Mount Point) and the exact substitute/print target `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`. The canonical target exists and contains the expected environment layout.

## Current ownership and unsafe handoff

There is no existing repository-owned worktree cleanup helper. The closeout owner is `.agents/skills/branch_completion_workflow/SKILL.md`; the architecture document is the durable environment/worktree contract. The branch-start workflow owns startup and environment preflight, not closeout.

The current completion instruction verifies that `.venv` is the only junction consumer and then hands off directly to normal `git worktree remove <path>`. The reported incident demonstrates that this is insufficient: Git removal can traverse the junction and attempt to unlink files from the canonical environment. A locked file can leave a partial worktree removal while the Git administrative registration remains stale.

The existing scripts are oriented to Scout/Gate/contract checks. No current script owns junction verification, safe detachment, or stale worktree registration recovery. The existing workflow-script harness is the closest test owner if a narrow helper is added.

## Evidence-bound safety contract recommendation

Before normal worktree removal, a closeout helper or equivalent explicit procedure should:

1. Inspect the exact worktree registration with `git worktree list --porcelain` and verify branch/ownership, ancestry, cleanliness, and remote synchronization using the existing closeout preflight.
2. Inspect `<worktree>\.venv` without following it as the sole proof. Require a directory reparse point whose tag is a junction/mount point and whose normalized target is exactly the configured canonical environment.
3. Fail closed for a missing path, ordinary directory, symlink/other reparse type, malformed or ambiguous target, or wrong target. It must never recursively remove any of these cases.
4. Detach only the verified local junction, then verify that the local `.venv` is absent and the canonical environment still exists. Only after that hand off to ordinary `git worktree remove <path>`; do not use `--force` to bypass unknown dirty state.
5. Re-run `git worktree list --porcelain` after removal and verify that the task branch is no longer owned by a worktree before any separately authorized branch deletion.

The verification implementation should use Windows reparse metadata and exact normalized path comparison. `fsutil reparsepoint query` is a useful native diagnostic and exposes the tag plus substitute/print names, but text parsing is version/localization-sensitive. PowerShell `Get-Item` exposes reparse attributes and link metadata, but target fields vary by PowerShell version. A helper should combine stable metadata/API inspection with strict normalization, fail closed on unavailable fields, and not rely on `Resolve-Path` alone because it follows the junction. Any `cmd dir /AL` or `fsutil` output used for diagnostics must not be treated as a substring-based ownership proof.

The detach operation must address the link path itself (for example, a non-recursive junction removal), never the canonical target path and never a recursive operation rooted at the junction. The helper should make the target and operation explicit so spaces and reparse semantics cannot be lost to shell quoting.

## Decision tree for exceptional states

- **Expected canonical junction:** detach the local junction, verify the target survived, then perform normal worktree removal.
- **Missing `.venv`:** the startup contract treats a missing/invalid environment as fail-fast. The Final SPEC must explicitly decide whether a legacy/non-runnable closeout is allowed; absent that decision, stop rather than silently remove.
- **Ordinary directory:** stop and require manual review. It may contain a private or copied environment; do not delete it.
- **Wrong-target junction or unknown reparse point:** stop and preserve it. Ownership is not proven.
- **Partial removal / missing `.git`:** do not retry normal removal or use force. Inspect the path, Git registration, and administrative marker. Only classify it as stale after proving the path/marker is absent or invalid and there is no live or dirty worktree state.
- **Stale registration:** after the proof above, a narrowly scoped `git worktree prune --verbose` may remove stale administrative metadata. Re-run `git worktree list --porcelain` and verify the intended branch registration is gone. Do not prune while any state is ambiguous, and do not use prune as a general cleanup command.
- **Live or dirty registered worktree:** stop. No prune, force removal, reset, clean, or recursive deletion.

The task should define postconditions for each branch of this tree, especially missing `.venv` and partial-removal recovery. It should also require a second verification after detachment to reduce the time-of-check/time-of-use risk.

## Recommended minimal implementation surface

The evidence supports a narrow helper under `scripts/`, owned by the branch-completion workflow, because junction verification and fail-closed destructive handoff are mechanical safety invariants. Its responsibility should be limited to one named worktree: classify/verify `.venv`, detach only an exact canonical junction, and report structured outcomes for stale-registration handling.

It should not own merge, push to main, branch deletion, recursive deletion, environment mutation, or broad worktree management. The completion workflow should remain the orchestration owner. Any architecture/skill edits should be limited to one converged closeout sequence and a cross-reference, avoiding a second lifecycle implementation in the startup workflow.

If the Final SPEC chooses documentation-only enforcement instead, it must still specify the exact verification evidence, detach command semantics, fail-closed cases, and stale-registration proof; the current prose-only handoff is not sufficient for the incident class.

## Deterministic validation strategy

The existing `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` and `tests/test_workflow_scripts.py` provide the closest test surface for a PowerShell/script helper. Tests should use temporary fixture directories outside the canonical environment and injected/mock command or metadata seams where junction creation privileges are unavailable. They must never point cleanup at the real canonical environment.

The Final SPEC should cover at least:

- exact canonical junction accepted and detached without changing the target;
- missing `.venv` fails according to the chosen legacy policy;
- ordinary directory, wrong target, and unknown reparse type fail closed;
- normal removal is offered only after local detach and postcondition checks;
- locked/partial removal does not trigger force cleanup;
- stale registration is pruned only after explicit stale proof and is absent afterward;
- unrelated worktree registrations are preserved.

These are filesystem/control-flow tests, so no long sleeps or shared-environment mutation is needed. Existing docs-only Scout work requires no test execution at this stage.

## Risks and unresolved decisions for Final SPEC

- Exact Windows API/PowerShell mechanism and stable structured result/exit-code contract are not yet selected.
- The policy for a missing `.venv` in legacy or already-partially-removed worktrees is unspecified.
- The proof boundary for `git worktree prune` needs to distinguish a stale administrative entry from a live path with a missing `.git` marker.
- Junction target normalization must cover case, trailing separators, extended/UNC forms, and target disappearance without accepting an equivalent-looking but different path.
- File locks, antivirus/indexer activity, concurrent agents, and a verification-to-detach race need explicit fail-closed handling.
- The durable completion workflow and architecture document must converge on one owner and one order of operations; the separate shared-environment mutation protocol backlog item remains out of scope.

## Recommendation

**GO WITH SPEC CHANGES.** The task is technically justified and the incident is reproducible in principle, but implementation should wait for a Final SPEC decision on helper versus instruction-only enforcement, exact reparse verification, missing-`.venv` policy, and stale-registration proof/postconditions.
