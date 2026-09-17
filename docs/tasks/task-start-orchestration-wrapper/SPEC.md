# task-start-orchestration-wrapper

Status: Draft

## Goal

Provide a repository-owned user-facing task-start orchestration entrypoint that turns an approved task branch into a correctly attached, canonical project-scoped, runnable task worktree with minimal manual handoff steps.

## Dependency

Upstream prerequisite:

`worktree-environment-junction-bootstrap`

This task must consume the finalized bootstrap contract rather than reimplement `.venv` junction creation or validation.

## Known boundary

This task is higher-level orchestration. It is expected to own sequencing around task-start operations such as repository/worktree discovery, branch/worktree attachment, startup validation, and environment-bootstrap invocation.

The exact interface, phase ordering, branch-resolution rules, failure/recovery behavior, and integration with existing branch-start workflow are intentionally TBD until the upstream bootstrap task is finalized and the surrounding startup implementation/contracts are surveyed.

## Known invariants

- Canonical permanent main worktree:
  `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool`.
- New task worktrees default to:
  `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`.
- Git worktree topology is runtime machine state and must be inspected rather than guessed.
- Startup must respect multi-worktree branch exclusivity and detached-HEAD safety.
- Canonical main must be synchronized through normal safe fetch / fast-forward semantics before creating a new task worktree.
- Task worktrees are Python-environment consumers, not environment owners.
- `.venv` bootstrap ownership belongs to `worktree-environment-junction-bootstrap` once finalized.
- No force checkout/reset/clean or silent dependency mutation.

## Non-goals

- No implementation before this Draft is converged to Final.
- No duplication of cleanup orchestration (`task_cleanup.ps1`).
- No reimplementation of environment junction safety/bootstrap primitives.
- No shared Python dependency mutation protocol.

## Provisional acceptance criteria

TBD after upstream `worktree-environment-junction-bootstrap` is Final and startup contracts/nearby implementation are reviewed.

## Uncertainty

- User-facing command/interface.
- Exact branch resolution and remote/local attachment behavior.
- Whether the wrapper creates a worktree, attaches an existing one, or supports both.
- Exact synchronization boundary with canonical main.
- Integration point with branch-start workflow and task artifacts.
- Failure/recovery semantics for stale paths, branch ownership conflicts, and partial startup.
- Whether Scout launch belongs inside this wrapper or remains a separate handoff step.
