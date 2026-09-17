# ai-workflow-roadmap-ssot-convergence

Status: Final

> Document role: this SPEC is the one-time lifecycle contract for converging the AI workflow roadmap into one durable SSOT. It becomes historical task evidence after merge; it is not the permanent roadmap.

## Goal

Create one durable roadmap SSOT for the repository's AI-assisted development workflow, remove stale and duplicated roadmap content from `docs/tasks/BACKLOG.md`, and make the responsibility of each related document explicit.

Permanent ownership:

```text
docs/architecture/ai_development_workflow.md
= current canonical workflow contract: what is true now

docs/architecture/ai_development_workflow_roadmap.md
= roadmap SSOT: what has been completed and what is still planned

docs/tasks/BACKLOG.md
= backlog intake/index: link to the AI workflow roadmap instead of duplicating it
```

## Scope

- Create `docs/architecture/ai_development_workflow_roadmap.md`.
- Rebuild the AI workflow roadmap from current `main`, merged workflow task evidence, canonical architecture contracts, and still-valid future work.
- Keep only two durable categories in the roadmap:
  - completed capabilities that materially define the current workflow foundation;
  - future work that still represents a real unresolved gap, paused task, measurement track, trigger-based debt, or explicitly deferred direction.
- Remove stale lifecycle labels, superseded task proposals, obsolete warnings, duplicated historical explanation, and roadmap items already absorbed by later implementations.
- Replace the large AI workflow roadmap body in `docs/tasks/BACKLOG.md` with a concise link/current pointer to the roadmap SSOT.
- Preserve the existing role statement in `docs/architecture/ai_development_workflow.md`; it already declares itself the canonical current workflow contract. The new roadmap links back to it rather than redefining it.

## Evidence conclusions from lightweight survey

Current `main` proves the roadmap had drifted behind implementation:

- `agent-workflow-pilot-retrospective-v1` is completed, not active.
- `workflow-script-testing-harness` is merged and is no longer future work.
- the old `gate-payload-robustness-v1` proposal has been superseded by the completed reviewer-output reliability and structured-review transport work and should not remain as an active roadmap item.
- OpenCode `1.18.31` + `@opencode-ai/sdk 1.18.31` structured transport is proven.
- the production BigPickle formal reviewer route has been exercised successfully by the merged parallel Gate task.
- worktree Python environment bootstrap, per-worktree Node dependency bootstrap/readiness, task-start orchestration, safe cleanup support, resumable parallel Gate, and closeout contract convergence are all merged foundations.
- `gate-immutable-review-baseline-contract` still exists as a paused Draft task on remote branch `task-gate-immutable-review-baseline-contract` and remains unresolved.
- task-descriptor validation is partially improved by current script checks, but no complete schema-linting contract/task has been merged.
- the current architecture requires base-ref freshness before Gate, but the deeper immutable-baseline contract remains unresolved and belongs to the paused immutable-baseline task rather than a duplicate roadmap item.
- shared Python environment mutation remains trigger-based debt.
- Writer model calibration remains a measurement track.
- semantic commit assistance, interruptibility, and broader orchestration remain future directions.

## Known invariants

1. `docs/architecture/ai_development_workflow.md` remains the SSOT for the current executable/operational workflow contract.
2. `docs/architecture/ai_development_workflow_roadmap.md` is the only durable AI workflow roadmap SSOT.
3. `docs/tasks/BACKLOG.md` remains the canonical intake/index for unspecced work, but must not duplicate the AI workflow roadmap.
4. Completed task packages remain historical evidence; this task does not delete task history.
5. Superseded roadmap proposals may be omitted rather than retained as historical clutter when their intent has already been absorbed by completed work.
6. GitHub `main` is the evidence baseline for completed capabilities.
7. This task is docs-only / GitHub-only by explicit user authorization. No local worktree, Scout, Gate, workflow-script change, or product/runtime test is required.

## Non-goals

- No changes to workflow scripts, adapters, tests, game/runtime code, environment behavior, or model configuration.
- No implementation of any future roadmap item.
- No reopening completed workflow tasks.
- No preservation of obsolete roadmap prose solely for history; Git history and task packages already provide historical traceability.
- No second roadmap copy under `docs/tasks/` or `docs/todos/`.

## Acceptance criteria

1. `docs/architecture/ai_development_workflow_roadmap.md` exists and labels itself as the roadmap SSOT.
2. The roadmap explicitly distinguishes its purpose from `ai_development_workflow.md` and `BACKLOG.md`.
3. `docs/tasks/BACKLOG.md` labels itself as backlog intake/index and contains only a concise AI workflow roadmap link/current pointer rather than a duplicated roadmap.
4. The roadmap contains only completed foundation and still-valid future work.
5. Stale `agent-workflow-pilot-retrospective-v1` Active state is removed.
6. `workflow-script-testing-harness` appears only as completed capability, not future work.
7. Superseded `gate-payload-robustness-v1` planning is omitted.
8. Structured transport and the successfully exercised BigPickle formal reviewer route are represented accurately.
9. Recent merged foundations include worktree Python bootstrap, Node dependency bootstrap/readiness, task-start orchestration, safe cleanup, resumable parallel Gate, and closeout contract convergence.
10. `gate-immutable-review-baseline-contract` remains represented as paused future work and points to the existing Draft task/remote branch context rather than recreating it.
11. Remaining schema-linting work is described as partial hardening only, without pretending current checks equal a complete schema contract.
12. Trigger-based `shared-environment-mutation-protocol`, Writer model measurement, and deferred v2 directions remain only while still valid.
13. No production/script/test files change.

## Verification

GitHub-only documentation audit:

- confirm changed paths are limited to this task package, the new roadmap, and `docs/tasks/BACKLOG.md`;
- confirm no duplicate AI workflow roadmap remains in BACKLOG;
- confirm roadmap statements are grounded in merged `main` evidence or explicit paused/deferred task state;
- no local tests or AI Gate required for this docs-only convergence.
