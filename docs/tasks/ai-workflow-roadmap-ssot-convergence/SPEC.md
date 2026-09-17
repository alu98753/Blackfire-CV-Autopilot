# ai-workflow-roadmap-ssot-convergence

Status: Draft

> Document role: this SPEC defines the one-time docs-only convergence task that creates a single AI development workflow roadmap SSOT. It is a task lifecycle artifact, not the permanent roadmap itself.

## Goal

Create one durable roadmap SSOT for the repository's AI-assisted development workflow, remove stale/duplicated roadmap content from `docs/tasks/BACKLOG.md`, and make the responsibility of each related document explicit.

The permanent split should be:

```text
docs/architecture/ai_development_workflow.md
= current canonical workflow contract: what is true now

docs/architecture/ai_development_workflow_roadmap.md
= roadmap SSOT: what has been completed and what is still planned

docs/tasks/BACKLOG.md
= backlog intake/index: link to the roadmap instead of duplicating it
```

## Scope

- Create `docs/architecture/ai_development_workflow_roadmap.md`.
- Rebuild the AI workflow roadmap from current `main`, completed workflow task evidence, architecture contracts, and still-valid future work.
- Keep only:
  - completed capabilities that materially define the current workflow foundation;
  - future work that still represents a real unresolved gap, paused task, measurement track, trigger-based debt, or explicitly deferred v2 direction.
- Remove stale lifecycle labels, superseded task proposals, obsolete warnings, duplicated historical explanation, and roadmap items already absorbed by later implementations.
- Replace the large AI workflow roadmap body in `docs/tasks/BACKLOG.md` with a concise link/current pointer to the roadmap SSOT.
- Add/strengthen file-purpose notes so readers can tell which document owns current contract, roadmap, and backlog intake.
- Add a short roadmap link from `docs/architecture/ai_development_workflow.md` without duplicating roadmap content.

## Known invariants

1. `docs/architecture/ai_development_workflow.md` remains the SSOT for the current executable/operational workflow contract.
2. The new roadmap is not allowed to redefine current operational behavior; current behavior belongs in the architecture contract.
3. `docs/tasks/BACKLOG.md` remains the canonical intake for new unspecced work, but must not duplicate the AI workflow roadmap.
4. Completed task packages remain historical evidence; this task does not delete task history.
5. Superseded roadmap proposals may be omitted rather than retained as historical clutter when their intent has already been absorbed by completed work.
6. GitHub `main` is the evidence baseline for completed capabilities.
7. This task is docs-only / GitHub-only by explicit user authorization. No local worktree, Scout, Gate, workflow script change, or product/runtime test is required.

## Non-goals

- No changes to `scripts/*.ps1`, Node adapters, tests, game/runtime code, environment contracts, or model configuration.
- No implementation of any future roadmap item.
- No reopening completed workflow tasks.
- No preservation of obsolete roadmap prose solely for history; Git history and task packages already provide historical traceability.
- No new competing roadmap copy under `docs/tasks/` or `docs/todos/`.

## Provisional acceptance criteria

1. A new `docs/architecture/ai_development_workflow_roadmap.md` exists and clearly labels itself as the roadmap SSOT.
2. `docs/architecture/ai_development_workflow.md` clearly labels itself as the current architecture/workflow contract and points to the roadmap for evolution/progress.
3. `docs/tasks/BACKLOG.md` clearly labels itself as backlog intake/index and contains only a concise AI workflow roadmap link/current pointer rather than a duplicated roadmap.
4. The roadmap contains a concise completed-foundation section reflecting actual merged capabilities through current `main`.
5. The roadmap contains only future items that remain materially unresolved.
6. `agent-workflow-pilot-retrospective-v1` is not shown as active.
7. `workflow-script-testing-harness` is not shown as future work.
8. Superseded `gate-payload-robustness-v1` planning is removed rather than carried as active work.
9. The pinned OpenCode structured transport and the successfully exercised BigPickle formal reviewer route are represented accurately.
10. Completed recent foundations include worktree Python bootstrap, Node dependency bootstrap/readiness, task-start orchestration, safe cleanup support, resumable parallel Gate, and closeout contract convergence.
11. `gate-immutable-review-baseline-contract` remains represented as paused future work and links to its existing remote Draft task branch/package context rather than recreating it.
12. Remaining schema linting/base-ref preflight/diagnostic wording debt is described only to the extent it is still real after current implementations.
13. Trigger-based `shared-environment-mutation-protocol`, Writer model measurement, and explicitly deferred v2 directions remain only if still valid.
14. No production/script/test files change.

## Uncertainty resolved by lightweight survey

Before Final status, verify from current `main` and existing task evidence:

- which roadmap items are already completed or superseded;
- which future items still have a real responsibility boundary;
- whether `task-descriptor-schema-linting` is fully unresolved or partially addressed;
- which completed workflow capabilities deserve durable roadmap entries rather than historical task-level detail.
