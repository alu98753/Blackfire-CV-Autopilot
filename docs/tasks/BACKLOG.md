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
- [ ] `task-start-review-model-preflight`：釐清 formal task startup 是否應在 `task_start.ps1` 提前驗證單一 explicit `models.review` contract，讓文件、startup fail-fast 與 Gate ownership 一致。
- [ ] AI Gate Node workflow dependency bootstrap：目前 `scripts/ai_gate.ps1` 必須通過 worktree-local `node_modules` readiness（含 `undici` / `@opencode-ai/sdk`），但 formal task startup `scripts/task_start.ps1` 不會 bootstrap Node，導致正常流程可能到 Gate 才 fail-fast 要求手動執行 `scripts/bootstrap_node_workflow_deps.ps1`。後續需正式決定 Node bootstrap ownership（例如 task startup、Gate preflight/explicit prepare step，或其他 deterministic orchestration），目標是讓需要 Gate/Node reviewer 的 task 在進 Gate 前自動或明確準備完成，同時維持 worktree-local untracked `node_modules`、`package.json`/`package-lock.json` SSOT、版本檢查與 fail-closed，不做 silent dependency mutation。
- [ ] 思考凌晨與平日戰鬥的策略變化 像是平常要暫停的template,要暫時移到flee的等等
- [ ] ai workflow要調整具體而言不需要archive 的部分(active可以保留),因為archived應該放到docs/architecture 並SSOT, git pr本身就是archived的證據
- [ ] ai workflow 要重新構思 整理,並把測試精簡化
- [ ] venv, npm等架構要思考怎麼可以用腳本build起來, 讓不同"windows"都可以順利安裝
- [ ] user data要思考怎麼可以在不同電腦間同步 首先要想的是 是否能在同一個資料夾下,然後就可以直接複製貼上而不用git
- [ ] 分析兩隻帳號的七星英雄下一隻應該是誰 以及是否可以慢慢玩也就是不用一次到位 可以完很久 來把想玩的7興英雄收集到 或是一開始就要換到(權衡想要的陣容 在打怪 boss是否打得過)