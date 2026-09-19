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
    - [ ] task 開起來要限制ai只能看該資料夾 不准看其他worktree的, 做serach ...任何事情都一樣
    - [ ] Task artifact path convention 漂移：一開始我把 task 建到舊的 docs/tasks/<task>，但現行 contract 已是 docs/tasks/active/<task>；task_start.ps1 才 fail-closed 抓出來。

    - [ ] Task schema 沒有單一建立入口：修完路徑後，task.json 又缺 models，還用了舊欄位 base_branch 而非 base_ref。代表「建立 task」仍靠 AI 手刻 JSON，容易 schema drift。

    - [ ] task_start 與 ai_scout invocation context 不一致/不直覺：一開始從 canonical main 跑 Scout 得 TASK_MISSING，切到 task worktree 才進下一階段。使用者需要知道「哪條 command 要在哪裡跑」。

    - [ ] Scout failure 太晚才發現 malformed metadata：task_start 能驗證「SPEC/task.json 存在 + id 正確」，但沒有驗證 ai_scout 真正需要的完整 schema；結果 TASK_READY 後 Scout 才因 .models 爆掉。

    - [ ] Scout output 有 artifact hygiene 問題：CONTEXT.md 混入 Now let me look...、maximum steps 等 agent scratch text，還有 ?? encoding 字元；不影響本次判斷，但 evidence 不乾淨。

    - [ ] Final SPEC 更新需要多段人工 orchestration：Scout 完成後仍是「你貼 SHA → 我審查 → 我修改 SPEC/task.json → 你再同步 worktree」。中間 handoff 次數偏多。

    - [ ] Implementation handoff 還需要人工 prompt：Final 後還要我另外產一段「只能待在這個 worktree、只能看 SPEC、不得擴 scope、記得 push」的 prompt；這些其實都是 deterministic workflow policy。

    - [ ] Node dependencies 不在 task readiness 定義內：Implementation 完、要 Gate 時才發現 task worktree 沒有 node_modules；必須額外執行 bootstrap_node_workflow_deps.ps1。也就是 TASK_READY ≠ REVIEW_READY。

    - [ ] Node bootstrap 是額外人工階段：雖然「不 silent install」這個設計是合理的，但使用者還是要記得何時跑 bootstrap；Gate 只能 fail-fast 再告訴你。

    - [ ] 使用者誤執行 helper/contract script 的可能性高：Gate 報錯後你還直接執行了 node_workflow_contract.ps1；代表錯誤訊息與 workflow UX 還可以更明確地只給唯一 recovery command。

    - [ ] Gate → ChatGPT final review 又一次人工 SHA handoff：你貼 c752805...，我再查 GitHub。既然 GitHub 是 SSOT，理論上 task identity 本身就足以找到 latest Gate evidence。

    - [ ] Merge 還需要臨時建立 PR：task branch 本身已 Gate PASS + final review PASS，但 integration 還是另外 create PR → merge；可以考慮把這變成正式 lifecycle command/contract。

    - [ ] Merge ≠ lifecycle 完成：合併後還有 archive → archive integration → cleanup，目前仍需要你繼續跑 command、貼結果。Task 的「完成」被切成很多人工 checkpoint。
- [ ] venv, npm等架構要思考怎麼可以用腳本build起來, 讓不同"windows"都可以順利安裝
- [ ] user data要思考怎麼可以在不同電腦間同步 首先要想的是 是否能在同一個資料夾下,然後就可以直接複製貼上而不用git
- [ ] 分析兩隻帳號的七星英雄下一隻應該是誰 以及是否可以慢慢玩也就是不用一次到位 可以完很久 來把想玩的7興英雄收集到 或是一開始就要換到(權衡想要的陣容 在打怪 boss是否打得過)
- []