# AI Workflow Closeout Contract Convergence

Status: Final

## Goal

Converge the AI workflow documentation after `ai-workflow-resume-parallel-gate` so future task closeout has one clear, non-contradictory path from a current task branch through formal Gate, GitHub evidence handoff, ChatGPT final review, user-authorized merge, and repository-owned cleanup.

## Scope

Primary change surface:

- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md`
- `.agents/skills/branch_completion_workflow/SKILL.md`
- this task package

This is a documentation/contract convergence task only.

## Known invariants

- GitHub-tracked artifacts are the handoff surface and GitHub is the remote SSOT.
- `SPEC.md` remains the normative task contract; reviews/EVIDENCE are evidence.
- Formal Gate uses current `base_ref` snapshots and must not review a stale long-lived task branch as though newer-main files were task deletions.
- Reviewer artifacts are stage-level durable results; `EVIDENCE.md` is completed-Gate aggregate evidence.
- A trusted sibling review may be promoted during partial verification failure; the failed reviewer's canonical artifact is not overwritten and completed `EVIDENCE.md` is not promoted.
- ChatGPT performs the final semantic/architecture review from GitHub.
- Integration requires explicit user authorization and uses merge-commit semantics.
- `task_cleanup.ps1` owns normal local task cleanup after integrated ancestry is proven.

## Non-goals

- No changes to `scripts/ai_gate.ps1` or any production/workflow script.
- No changes to game runtime behavior.
- No new Gate preflight implementation in this task.
- No fingerprint algorithm redesign.
- No new deterministic tests.
- No broad rewrite of `.agents/AGENTS.md` or branch-start behavior unless a direct contradiction is discovered.
- No automatic deletion/archive policy for tracked task history.

## Acceptance criteria

1. The architecture contract states that, before formal Gate/final closeout review, current `base_ref` (normally `origin/main`) must be incorporated into the task branch; stale/diverged task branches are reconciled before Gate rather than reviewed against a misleading diff.
2. Gate exit meanings `0/2/1` live under verification (Phase D), not under final review/integration (Phase E).
3. Phase E explicitly states: successful Gate evidence is committed/pushed -> ChatGPT GitHub final semantic/architecture review -> explicit user authorization -> merge-commit integration -> repository-owned cleanup.
4. Partial Gate artifact semantics are consistent everywhere: trusted sibling review may persist; failed reviewer canonical is untouched; `EVIDENCE.md` remains completed-Gate-only evidence.
5. `docs/tasks/README.md` no longer claims that all `reviews/*` remain untouched on any infrastructure failure.
6. Tracked task-history retention is distinguished from local `task_cleanup.ps1` worktree/branch cleanup; local cleanup does not imply deleting tracked task artifacts.
7. Duplicate/ambiguous StructuredOutput wording is cleaned up without changing reviewer semantics.
8. Canonical ownership stays narrow: architecture owns lifecycle/authority, branch-completion skill owns operational closeout procedure, task README owns task-artifact semantics.
9. No script/code/runtime file changes.

## Deferred follow-up

- The Gate's current human-facing partial-failure warning is slightly inaccurate under sibling promotion, but fixing that text requires a script change and is intentionally deferred.
- A future implementation task may add a fail-fast Gate preflight for stale `base_ref` ancestry; this task only documents the invariant.

## Execution note

The user explicitly authorized this docs-only convergence to be completed remotely on GitHub without local worktree materialization or Scout. Evidence comes from the current merged workflow contracts and the tracked advisory findings from `ai-workflow-resume-parallel-gate`.
