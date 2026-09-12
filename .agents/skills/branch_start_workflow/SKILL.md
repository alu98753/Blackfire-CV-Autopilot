---

name: branch_start_workflow
description: >
個人開發模式下的新工作啟動流程。負責在正式開始 Feature / Fix 開發前，
確認工作樹狀態、同步 main baseline、建立語意化本地 branch、
立即建立對應 remote tracking branch，並建立本次開發的最小上下文與驗收邊界。
與 branch_completion_workflow 對稱：本 Skill 僅負責開始，不負責 merge 或收尾。

## usage_scope: solo_development_only

# Branch Start Workflow 🚀

本 Skill 是 Feature / Fix 正式開發前的統一啟動工作流。

其責任終點為：

> 建立一個基於最新 `main`、具有明確名稱、已連接 `origin/<branch>` 的乾淨開發分支。

後續實作、測試與 commit 皆在該 branch 上進行。

完成開發後，改由：

`branch_completion_workflow`

負責 regression baseline、maintenance refactor、contract convergence、merge preparation 與 branch cleanup。

---

# Trigger Identification

當使用者明確表示要正式開始一次新的開發工作時啟動，例如：

* `開始新開發`
* `開始這個功能`
* `開始修這個 bug`
* `開新分支`
* `幫我建立 feature branch`
* `幫我建立 fix branch`
* `正式開始實作`

僅討論設計、brainstorm、code review 或需求分析時，不得自行建立 branch。

---

# Core Invariants

## 1. 一次開發工作 = 一個明確 Branch

正式進入 implementation 前，必須使用獨立 branch。

標準命名：

```text
feat/<short-kebab-name>
fix/<short-kebab-name>
refactor/<short-kebab-name>
docs/<short-kebab-name>
test/<short-kebab-name>
```

Branch name 必須描述「目的」，不得使用：

```text
temp
test2
new
work
branch1
final
```

---

## 2. Local Branch 建立後立即建立 Remote Tracking Branch

建立本地 branch 後，立即：

```powershell
git push -u origin HEAD
```

使 Git 建立：

```text
local:
feat/example

remote:
origin/feat/example
```

並設定 upstream tracking。

目的：

* 允許隨時進行 GitHub remote review。
* 使用者可要求外部 reviewer 比較 `main...<branch>`。
* branch 具備遠端備份。
* 後續僅需 `git push`。
* 不需要等功能完成才建立遠端 branch。

Remote branch 的存在不代表功能完成，也不代表可以 merge。

---

## 3. Branch 必須基於最新 Main

在建立 branch 前，必須確認 branch base 為最新可信任 `main`。

本專案採永久 Dual-Worktree：

```text
E:\Side_Project\

├─ BlackfireCrusade_tool   # Feature/Fix development worktree
└─ temp-main               # permanent main worktree
```

`main` 永久由 `temp-main` checkout。

因此：

> 禁止在 `BlackfireCrusade_tool` 執行 `git switch main` 或 `git checkout main`。

---

# Startup Workflow

## Phase 0 — Development Intent

先確認本次工作的性質：

```text
Type:
- feat
- fix
- refactor
- docs
- test

Goal:
<一句話>

Expected observable outcome:
<使用者完成後可以觀察到什麼>

Explicitly out of scope:
<此次不處理內容>
```

若使用者已經提供足夠資訊，不得重複詢問。

---

## Phase 1 — Current Workspace Safety Check

於：

```text
E:\Side_Project\BlackfireCrusade_tool
```

確認：

```powershell
git status --short
git branch --show-current
```

若存在 unrelated dirty changes：

* 不得自行 discard。
* 不得 `reset --hard`。
* 不得 `git clean`。
* 不得將其混入新 branch 的 commit。
* 必須保留並明確避開。

若目前仍停留在上一個已完成 branch，後續直接從 `main` 建立新 branch，不需要 checkout main。

---

## Phase 2 — Refresh Main Baseline

於：

```text
E:\Side_Project\temp-main
```

執行：

```powershell
git status --short
git branch --show-current
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

要求：

```text
branch == main
working tree == clean
```

若：

```text
HEAD == origin/main
```

直接繼續。

若 `temp-main` 落後且可 fast-forward：

```powershell
git pull --ff-only
```

若：

* dirty
* diverged
* 無法 fast-forward

立即停止。

禁止：

```text
reset --hard
force checkout
clean -fd
```

---

## Phase 3 — Determine Branch Name

依本次工作建立簡潔 branch name。

例如：

```text
feat/daily-status-notifier
fix/discord-webhook-id-extraction
refactor/notification-boundaries
```

命名原則：

```text
<change-type>/<domain-or-behavior>
```

優先描述使用者目的，而不是 implementation detail。

例如優先：

```text
fix/discord-webhook-id-extraction
```

而不是：

```text
fix/change-post-response-code
```

---

## Phase 4 — Create Local Branch from Main

回到：

```text
E:\Side_Project\BlackfireCrusade_tool
```

確認 branch name 尚不存在：

```powershell
git branch --list <branch_name>
```

然後：

```powershell
git switch -c <branch_name> main
```

因 `temp-main` 已刷新 `main` ref，因此新 branch 應直接基於最新 main。

建立後確認：

```powershell
git branch --show-current
git merge-base --is-ancestor main HEAD
```

---

## Phase 5 — Immediately Publish Remote Tracking Branch

本地 branch 建立成功後立即：

```powershell
git push -u origin HEAD
```

確認：

```powershell
git branch -vv
```

應看到類似：

```text
* fix/example abc1234 [origin/fix/example]
```

必要時確認：

```powershell
git ls-remote --heads origin <branch_name>
```

此步驟完成後，remote branch 即成為本次開發的 canonical review surface。

後續修改完成並 commit 後：

```powershell
git push
```

即可更新遠端內容。

---

# Review Availability Invariant

Branch 建立並 publish 後，只要存在新的 commit，使用者即可要求：

```text
審查目前 branch
比較 main 和目前 branch
review main...HEAD
```

Reviewer 應以：

```text
main
vs
origin/<branch>
```

或對應 GitHub refs 為準。

不得要求使用者為了 review 額外建立臨時 branch。

---

# Development Boundary Snapshot

正式 coding 前，建立最小開發邊界：

```text
Branch:
<name>

Base:
main @ <sha>

Goal:
<一句話>

Observable acceptance:
- ...
- ...

Out of scope:
- ...

Remote tracking:
origin/<name>
```

這不是大型 Spec，也不要求建立額外文件。

若任務已有正式 Spec / TODO / Contract，僅引用既有文件，不重複創造第二份 SSOT。

---

# Commit Rules During Development

遵循 `.agents/AGENTS.md`：

* Angular Commit type。
* 禁止 `git add .`
* 禁止 `git add -A`
* 禁止 `git commit -a`
* 每個 commit 必須精確 stage 本次相關檔案。
* 不得混入 unrelated working-tree changes。

本 Skill 不自行定義額外 Commit 規則；Git commit 行為以全域 `AGENTS.md` 與 `precise_git_commit` 為準。

---

# Explicit Non-Responsibilities

本 Skill 不負責：

* Full regression suite
* Behavior-preserving closeout refactor
* Canonical contract archival
* PARS story
* Merge
* Local branch deletion
* Remote branch deletion

上述事項全部交由：

`branch_completion_workflow`

處理。

尤其：

> Branch Start 絕不自行 merge。
> Branch Start 絕不自行刪除既有 branch。

---

# Completion Criteria

Branch Start Workflow 完成必須同時滿足：

```text
[ ] temp-main/main 已確認為最新可信 baseline
[ ] 開發 worktree 未 checkout main
[ ] branch name 符合 change intent
[ ] local branch 建立自 main
[ ] origin/<branch> 已建立
[ ] upstream tracking 已設定
[ ] 使用者後續可直接 git push
[ ] reviewer 可從遠端直接比較 main...branch
[ ] 本次 Goal / Acceptance / Out-of-scope 已簡要確認
```

---

# Final Output

完成後只需簡短回報：

```text
Development branch ready:

Branch: <branch_name>
Base: main @ <sha>
Remote: origin/<branch_name>
Tracking: enabled

之後 commit 完直接 git push 即可；完成整個功能後使用 branch_completion_workflow 收尾。
```

# One-Line Principle

> Create the review surface when development starts, not when development ends.
