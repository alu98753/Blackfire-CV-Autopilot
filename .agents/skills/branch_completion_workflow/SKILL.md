---
name: branch_completion_workflow
description: 個人開發模式下的分支收尾工作流，負責 regression baseline、maintenance refactor、contract convergence、integration readiness、main sync 與 task cleanup。
usage_scope: solo_development_only
---

# Branch Closeout Gated Workflow 🚀

本 Skill 是 Feature / Fix / Refactor / Docs / Test task 完成後的統一收尾流程。

它負責：

- closeout context audit；
- main vs task regression baseline；
- regression classification；
- behavior-preserving maintenance refactor safety gate；
- contract / TODO / spec convergence；
- PARS story；
- final branch audit；
- integration readiness；
- integration 後 local main sync；
- task branch/worktree cleanup。

它不允許 local AI agent 自行 merge。

## Canonical workspace contract

Workspace SSOT 定義於 `docs/architecture/ai_development_workflow.md`。

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\        <- permanent main + runtime/CV validation home
└─ worktrees\
   └─ <task-id>\                 <- temporary task worktree
```

Canonical shared environment：

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

每個 runnable worktree 透過自己的 `.venv` junction consume 同一環境。

重要：baseline/task 測試都使用「各自 worktree 的」：

```text
.\.venv\Scripts\python.exe
```

不得引用另一個 worktree 的 absolute interpreter path。

Existing active worktrees 可以在目前位置完成既有 task；不得只為整理目錄而搬動 dirty/active worktree。新 task 使用 canonical project-scoped path。

## Usage scope guard

本 Skill 預設為單人開發模式。

若 repository 已進入多人協作、protected branch、強制 PR review/CI 等模式：

- 保留 regression classification、behavior-preserving refactor、contract convergence 等品質 gate；
- integration 必須服從團隊 branch-protection / PR / CI 規則；
- 不得以本地流程繞過遠端治理。

## Trigger identification

以下指令代表「啟動/繼續 closeout」，不是立即 merge：

- `請分支收尾`
- `分支收尾`
- `準備 merge`
- `請 merge`
- `跑 merge`
- `收尾分支`
- `結束分支`

Closeout 是 gated workflow。遇到 user-only full-suite、重大 contract decision、merge authorization 等 gate 時必須停下等待。

## Hard invariants

1. Local Gemini / Antigravity / OpenCode 不執行 merge、push-to-main、branch deletion 或 integration action。
2. ChatGPT 只有在所有 required closeout gates 通過且使用者明確授權後，才能透過 GitHub 執行 merge-commit integration。
3. 使用者可選擇自己手動 integration。
4. GitHub integration 使用 merge commit；不 silent squash/rebase。
5. `BlackfireCrusade_tool` 永久持有 local `main` 並作為 integrated baseline/runtime home。
6. task worktree 保持 task branch ownership，直到 integration 已確認包含該 branch。
7. branch/worktree cleanup 前必須 `git fetch origin` 並以 `git merge-base --is-ancestor` 驗證 integrated ancestry。
8. 不使用 `reset --hard`、`clean -fd`、force checkout 或其他破壞 dirty state 的 shortcut。
9. full regression suite 仍是 user-only；AI 只可跑 project policy 允許的 focused tests。
10. closeout 不得為了測試成功偷偷修改 shared Python environment。

## Closeout phases

### Phase 0 — Context audit

在 task worktree 確認：

```powershell
git status --short
git branch --show-current
git diff main...HEAD --stat
git log main..HEAD --oneline
```

盤點：

- production changes；
- tests；
- architecture/contracts；
- task artifacts；
- temporary docs/logs；
- behavior change vs behavior-preserving refactor boundary。

如果 worktree detached、branch 不符 task、或存在 unrelated dirty changes，停止並先處理 ownership/state 問題。

### Phase 1 — Canonical main baseline preflight

在：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

執行：

```powershell
git status --short
git branch --show-current
git worktree list --porcelain
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

要求：

```text
branch == main
working tree == clean
```

若 HEAD 落後且可 fast-forward：

```powershell
git pull --ff-only
```

若 dirty、diverged、detached 或無法 fast-forward，停止並回報。

### Phase 2 — Regression baseline

目標：比較 task HEAD 與 canonical main 的 test baseline。

AI 不自行跑 full suite；由使用者執行需要的 full regression。

Task worktree 測試使用：

```text
<task-worktree>\.venv\Scripts\python.exe
```

Main baseline 測試使用：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool\.venv\Scripts\python.exe
```

每組測試都必須從各自 worktree working directory 執行，讓 branch-local imports 解析到正確 source tree。

Windows 非互動/redirect command 遵循 project shell policy，使用 `cmd.exe /d /s /c`，並輸出獨立 UTF-8 logs。

如果 task/main 測試會競爭 game process、`user_data/`、固定 screenshot/log 等共享 runtime resource，序列執行，不平行跑。

等待使用者確認 full-suite 完成後才進下一 phase。

### Phase 3 — Regression classification

將 failure 分為：

```text
PRE_EXISTING_FAILURE
EXPECTED_BEHAVIOR_CHANGE
BRANCH_REGRESSION
UNCERTAIN
```

只要存在 `BRANCH_REGRESSION` 或 `UNCERTAIN`，closeout blocked。

不能用「main 也失敗」掩蓋 task 新增的不同 failure path，也不能把沒有 Final SPEC 支持的 behavior change 分成 EXPECTED。

### Phase 4 — Refactor safety-net gate

在做 closeout maintenance refactor 前，確認相關 behavior 已有足夠 tests/evidence 保護。

沒有 safety net 時，不得因「順便清理」大幅改動 production behavior。

### Phase 5 — Behavior-preserving maintenance refactor

只處理能明確證明 behavior-preserving 的 maintenance，例如：

- dead logic；
- duplicate glue；
- stale comments/docstrings；
- ownership boundary clarity；
- testability improvements；
- architecture drift cleanup。

若 Final SPEC 沒要求 behavior change，refactor 不得改變已驗證行為。

Refactor 應與 feature/fix change 有清楚 commit boundary。

### Phase 6 — Post-refactor verification

先跑直接相關 focused tests。

如果 closeout policy 要求 full-suite，停下交由使用者執行。

任何 refactor 造成的新 failure 或 observable behavior change 都會重新 block closeout。

### Phase 7 — Code/doc hygiene

清掉只對 task 過程有意義、會污染 durable code 的暫時名稱、issue wording、debug comment。

但不要把 canonical contract 重複寫進多份文件。

### Phase 8 — Contract convergence

把 durable invariant 收斂到 canonical architecture/workflow SSOT。

Task SPEC / CONTEXT / reviews / EVIDENCE 是 task lifecycle artifact，不應成為永久第二套 architecture authority。

Backlog 中已 promote 的 active task 不保留 duplicate active description。

任何刪除 tracked task/history artifact 的決定若非 Final SPEC 已授權，先列出候選並等待使用者確認。

### Phase 9 — PARS development story

依 repository story convention，紀錄真正值得保留的開發脈絡：Problem / Actions / Results / Significance。

Story 不得取代 architecture SSOT。

### Phase 10 — Final branch audit

在 task worktree 確認：

```powershell
git status --short
git branch --show-current
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

確認：

- branch clean；
- expected commits 已 push；
- Final SPEC / Gate / review evidence 符合 task lifecycle；
- 沒有 unrelated files；
- 沒有未宣告 behavior change；
- canonical docs 已收斂。

### Phase 11 — Integration readiness

Local agent 只交付 readiness report，不自行 merge。

#### Preferred integration

當 GitHub access 可用且 user 明確授權：

1. ChatGPT 重新檢查 expected head/base 沒有漂移。
2. ChatGPT final semantic/architecture review 通過。
3. ChatGPT 使用 merge-commit semantics 整合至 `main`。

#### Manual integration

若使用者選擇手動整合，應在 canonical main worktree：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

先：

```powershell
git status --short
git fetch origin
git pull --ff-only
```

再由使用者執行 repository-approved `git merge --no-ff <branch>` 與 push。

Local AI 只能提供指令/檢查，不代為執行 integration。

## Post-integration synchronization

Remote integration 完成後，在 canonical main worktree：

```powershell
git fetch origin
git pull --ff-only
```

驗證：

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

必須：

```text
branch == main
HEAD == origin/main
working tree == clean
```

## Task branch / worktree cleanup

先從任一有效 repository worktree：

```powershell
git fetch origin
git worktree list --porcelain
git merge-base --is-ancestor <task-branch> origin/main
```

只有 ancestry 驗證成功後才能 cleanup。

### Active task worktree

確認：

- worktree clean；
- branch/HEAD 是預期值；
- 不含未保存的 local-only evidence；
- `.venv` 只是 junction consumer，不是 environment owner。

接著使用正常 `git worktree remove <path>`；不得 `--force` 處理未知 dirty state。

### Branch deletion

worktree 不再持有 branch 後，才允許刪 local branch。

Remote branch 是否刪除依 repository/user policy；若 local safe-delete 失敗，保留 branch，不強制。

### Existing non-canonical active worktree paths

若 task 在非 canonical path 啟動，只要它仍 active 就可原地完成。Closeout 成功後正常 remove；不要先搬到 canonical path 再刪。

## Environment closeout rules

Closeout 中：

- 不 `pip install` / `pip uninstall`；
- 不 recreate shared venv；
- 不修改 shared-env dependency state；
- 不 `pip install -e .`；
- 每個 worktree 只使用自己的 `.venv\Scripts\python.exe` consumer path；
- `.venv` junction 缺失/失效時 fail-fast，而不是 fallback system Python。

若 task 本身需要 dependency mutation，必須使用 repository-level environment operation contract；普通 branch closeout 不自行發明 mutation protocol。

## Closeout report

交付至少包含：

```text
CLOSEOUT REPORT

Task / Branch:
Head:
Main baseline:
Regression classification:
Focused verification:
User full-suite status (if required):
Contract convergence:
Gate evidence:
Final review status:
Integration authority:
Cleanup readiness:
```

## Completion criteria

```text
[ ] task worktree/branch identity verified
[ ] canonical main clean and synced to fetched origin/main
[ ] regression baseline classified
[ ] no BRANCH_REGRESSION / UNCERTAIN blocker
[ ] maintenance refactor preserved behavior
[ ] focused verification passed
[ ] user-only full suite completed when required
[ ] durable contracts converged to SSOT
[ ] final branch audit clean
[ ] candidate pushed and reviewable
[ ] user explicitly authorizes integration before merge
[ ] after integration, canonical main fast-forwards to origin/main
[ ] task ancestry verified before cleanup
[ ] task worktree cleanup preserves local state and shared environment
```

# One-line principle

> Verify task against canonical main, converge durable truth to SSOT, integrate only with explicit authority, then safely remove the temporary task worktree.
