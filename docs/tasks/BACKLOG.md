# Development Backlog

> Document role: **backlog intake/index** for new ideas, unresolved bugs, future work, and tasks that are not yet ready for a full `SPEC.md`. This file is not the AI workflow roadmap and must not duplicate that roadmap.

When an item becomes active development work, promote it into:

```text
docs/tasks/active/<task-id>/SPEC.md
docs/tasks/active/<task-id>/task.json
```

Do not keep two active SSOT descriptions for the same task. Historical task detail belongs in the task package and Git history.

Existing material under `docs/todos/` predates this workflow and remains legacy until touched. New backlog items belong here unless another canonical roadmap explicitly owns that domain.

## AI development workflow

Canonical roadmap SSOT:

[`docs/architecture/ai_development_workflow_roadmap.md`](../architecture/ai_development_workflow_roadmap.md)

Use that roadmap for:

- completed AI workflow capabilities;
- current/paused workflow work;
- still-valid reliability/debt items;
- Writer measurement track;
- deferred workflow v2 directions.

Current pointer: `gate-immutable-review-baseline-contract` remains a **paused Draft task** on remote branch `task-gate-immutable-review-baseline-contract`. Do not recreate or resume it until the user explicitly unpauses it.

Do not duplicate the AI workflow roadmap in this backlog. New workflow ideas may be captured here briefly only until they are either promoted into a task or incorporated into the roadmap SSOT.

## Task todo

- [ ] 觀察 `NemesisIntervention` 是否需要與 process-external Supervisor daily restart 協作／延後重啟；本 task 先維持既有每日重啟語意，不保證 intervention hold 跨 process 持久化。
- [ ] prompt 太長了 需要縮減(GPT給scout 的)
- [ ] config 位置統一任務