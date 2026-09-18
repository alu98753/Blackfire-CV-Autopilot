# Verification Evidence — worktree-shared-venv-cleanup-safety

## Status

Accepted for integration with an explicit verification-infrastructure exception.

The production OpenCode AI Gate did not produce a semantic PASS/BLOCK verdict. It stopped as `VERIFICATION_UNAVAILABLE` because the `spec-reviewer` adapter failed catastrophically before producing a valid reviewer envelope. Canonical Gate artifacts were left untouched. This document does **not** represent that failure as Gate PASS.

The user explicitly authorized integration based on the deterministic focused verification and ChatGPT final semantic / architecture review recorded below.

## Candidate

Final reviewed implementation head before closeout artifact updates:

`0bf06ad77bbe6c4cb1e3668dbc3449ef6e82079a`

Closeout-only task metadata/evidence commits may follow this SHA before merge; they do not change the reviewed cleanup implementation.

## Deterministic verification

### Junction classification smoke

The task worktree `.venv` was created as a Windows junction to:

`E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`

Running `scripts/worktree_cleanup_safety.ps1 -ClassifyOnly` returned:

`EXPECTED_JUNCTION`

with the exact canonical target.

### Cleanup-specific tests

Cleanup-specific tests passed after the final helper contract fixes:

`OK (skipped=5)`

The focused surface covers:

- exact canonical junction classification and detach while preserving the target;
- fail-closed missing / physical / wrong-target / unsupported reparse states;
- partial-removal state requiring explicit stale proof;
- explicit partial-removal recovery with residual canonical junction detach;
- safe residual-absent recovery classification;
- explicit detached-pending-remove retry classification;
- branch-completion ownership boundary for normal remove and stale prune.

Skipped cases are Windows fixture capability skips, not reported failures.

### Diff hygiene

`git diff --check` passed on the final implementation candidate.

## Broader workflow test observation

Running the entire `tests.test_workflow_scripts` module also exercised unrelated OpenCode/reviewer infrastructure tests. That broader module was not used as this task's acceptance surface because it contains failures unrelated to this cleanup change, including Node/OpenCode adapter import/execution failures and pre-existing workflow-harness architecture/version contract drift.

Those failures were not repaired in this task to avoid scope creep. `task.json` now declares the cleanup-specific deterministic tests as the focused verification surface.

## AI Gate

Command:

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\ai_gate.ps1 -Task worktree-shared-venv-cleanup-safety`

Observed result:

`VERIFICATION_UNAVAILABLE: Catastrophic adapter failure without a valid envelope for spec-reviewer candidate opencode/mimo-v2.5-free; fallback stopped.`

Additional observed guarantee:

`Canonical artifacts were left untouched.`

Classification:

- verification infrastructure failure;
- no semantic reviewer BLOCK was produced;
- no Gate PASS is claimed.

## Final semantic / architecture review

ChatGPT final review: **PASS**.

Reviewed dimensions:

- responsibility boundary: PASS — branch completion remains orchestration owner; helper only classifies/detaches the local `.venv` junction and reports deterministic recovery states;
- shared-environment ownership: PASS — canonical physical environment is never recursively removed or mutated;
- fail-closed behavior: PASS — physical directories, wrong targets, unsupported/ambiguous reparse objects, missing targets, and unknown recovery states stop cleanup;
- partial-removal recovery: PASS — stale proof remains caller/workflow responsibility, residual junction safety is handled before bounded `git worktree prune --verbose`;
- retry semantics: PASS — arbitrary missing `.venv` is not treated as safe; `DetachedPendingRemove` requires explicit caller-held evidence from the same cleanup sequence;
- branch deletion boundary: PASS — branch deletion remains after worktree registration removal;
- architecture drift: PASS — durable contract converged into `docs/architecture/ai_development_workflow.md` and `.agents/skills/branch_completion_workflow/SKILL.md` rather than creating a new worktree manager;
- testability: PASS — destructive behavior is covered through deterministic temp fixtures and narrow helper classifications.

## Latest main compatibility

Before integration review, `main` had advanced by one unrelated commit:

`cce3f30ea65c090a40b6d69d73e76455bb7e9b79` — `docs: update template dungeon`

It changes only:

`templates/dungeons/dragon_lair.png`

No overlap with this task's workflow/helper/test/architecture files was identified.

## Integration decision

User decision: accept **Gate infrastructure unavailable + deterministic focused verification PASS + ChatGPT final semantic/architecture review PASS** for this task and proceed with merge-commit integration.

This is an explicit task-local exception to unavailable reviewer infrastructure, not a weakening of the normal Gate contract.
