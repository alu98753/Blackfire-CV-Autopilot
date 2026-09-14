# Workflow Merge Authority

Status: Draft

## Goal

Clarify merge authority in the AI-assisted development workflow so local implementation/review agents remain unable to integrate branches, while the user and ChatGPT remote orchestrator may merge after all closeout gates pass and the user has explicitly authorized integration.

## Problem statement

The current repository contracts use broad language such as "AI must never merge" and define Phase 10 primarily as delivery of a local `git merge --no-ff` command. That no longer matches the intended operating model:

- Gemini/Antigravity and OpenCode are local implementation/review agents and must never merge.
- ChatGPT is the remote contract owner/final reviewer and normally performs GitHub integration once closeout is complete and the user has explicitly requested/authorized merge.
- The user remains the ultimate integration authority and may merge manually.

The contract must distinguish these roles instead of using the undifferentiated term "AI".

## Scope

Update only workflow/governance documentation and agent rules required to make merge authority unambiguous, primarily:

- `.agents/AGENTS.md`
- `.agents/skills/branch_completion_workflow/SKILL.md`
- `docs/architecture/ai_development_workflow.md`

Additional directly related documentation may be updated only if Scout evidence shows a contradictory merge-authority contract that would otherwise remain active.

No production/runtime code, tests, scripts, or configuration behavior should change.

## Known invariants

1. Closeout remains gated. A user saying `merge` / `請 merge` starts or continues closeout; it must not bypass unfinished gates.
2. Local implementation/review agents (Gemini/Antigravity/OpenCode) never execute merge, push-to-main integration, branch deletion, force push, or equivalent integration actions.
3. ChatGPT may integrate only after all required closeout gates are satisfied and the user has explicitly authorized merge/integration.
4. The user may always perform integration manually.
5. GitHub integration must preserve a merge commit. Squash/rebase merge must not silently replace the repository's merge-commit history policy.
6. `temp-main` remains the local permanent `main` worktree and baseline/test surface. Remote ChatGPT integration does not convert the feature worktree into a `main` worktree.
7. After remote merge, local worktrees must safely synchronize from `origin/main`; destructive reset/clean remains forbidden.
8. This task changes governance semantics only. No game behavior may change.

## Provisional target behavior

After all closeout gates pass:

- Preferred integration path when ChatGPT GitHub access is available:
  1. ChatGPT performs final GitHub audit against the exact expected head/base.
  2. ChatGPT confirms the PR/head has not moved since final review.
  3. With explicit user merge authorization, ChatGPT integrates using GitHub's merge-commit method.
  4. Local agents do not perform the integration.
  5. Local `temp-main` later fast-forwards to `origin/main`; the feature worktree is safely parked/cleaned according to the multi-worktree rules.

- Fallback path when ChatGPT GitHub integration is unavailable or the user chooses manual integration:
  - the workflow delivers the existing safe local `temp-main` `git merge --no-ff` path to the user;
  - local AI agents may prepare/report instructions but still must not execute the merge themselves.

## Provisional acceptance criteria

1. Repository rules explicitly distinguish `local coding/review agent` from `ChatGPT remote orchestrator` and `user` merge authority.
2. No remaining active contract says all AI are categorically forbidden to merge in a way that unintentionally includes ChatGPT.
3. Phase 10 defines ChatGPT remote merge as the preferred path when GitHub integration is available and the user has explicitly authorized merge.
4. Phase 10 retains a safe user-manual fallback path.
5. GitHub merge uses merge-commit semantics, not squash/rebase, and should guard against stale/moved head where supported.
6. Earlier closeout gates remain mandatory; this task must not create an authorization shortcut.
7. Local Gemini/Antigravity/OpenCode remain prohibited from merge/integration actions.
8. Multi-worktree cleanup/synchronization instructions remain valid after either integration path.
9. The final diff contains documentation/rule changes only; no runtime/test/script behavior changes.

## Non-goals

- Do not add automatic or scheduled merging.
- Do not grant Gemini/Antigravity/OpenCode merge permission.
- Do not bypass full-suite/user gates or final semantic review.
- Do not change branch protection or GitHub repository settings.
- Do not redesign the entire branch completion lifecycle.
- Do not modify game/runtime behavior.
- Do not start `intent-routing-observability` in this branch.

## Uncertainty / Scout questions

Scout should verify before this spec becomes Final:

1. Are there other active repository contracts that broadly prohibit all AI merge actions and must be updated for consistency?
2. Does any current branch-start/branch-completion rule assume local `temp-main` must always perform the merge rather than simply remain the local `main` owner/baseline?
3. What exact post-remote-merge cleanup sequence best preserves the permanent dual-worktree invariant?
4. Are there existing PR/merge-method assumptions that require wording changes for GitHub merge-commit integration?
5. Can this remain a docs/rules-only task with no script changes?
