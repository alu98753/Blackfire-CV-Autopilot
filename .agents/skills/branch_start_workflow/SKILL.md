---
name: branch_start_workflow
description: >
  個人開發模式下的新工作啟動流程。負責確認 canonical main、檢查 worktree ownership、
  建立 project-scoped task worktree、發布 remote tracking branch，並建立最小開發邊界。
  本 Skill 僅負責開始，不負責 merge 或收尾。
usage_scope: solo_development_only
---

# Branch Start Workflow 🚀

本 Skill 是 Feature / Fix / Refactor / Docs / Test 正式開發前的統一啟動流程。

責任終點：

> 建立一個基於最新可信 `main`、位於 canonical task-worktree namespace、具有明確 branch 名稱且已連接 `origin/<branch>` 的乾淨 task worktree。

完成開發後交由 `branch_completion_workflow` 收尾。

## Canonical workspace contract

Workspace SSOT 定義於 `docs/architecture/ai_development_workflow.md`。

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\        <- permanent main + runtime/CV home
└─ worktrees\
   └─ <task-id>\                 <- branch-scoped task worktree
```

每個 runnable worktree 的：

```text
.venv\Scripts\python.exe
```

都透過 worktree-local `.venv` junction consume：

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

新 task 一律使用 project-scoped worktree path。既有 active worktree 若位於其他位置，在該 task 完成前可原地保留；不得只為了整理目錄而移動 dirty / active worktree。

## Trigger identification

使用者明確表示正式開始一次新的開發工作時啟動，例如：

- `開始新開發`
- `開始這個功能`
- `開始修這個 bug`
- `建立 XXX task`
- `正式開始實作`

僅討論設計、brainstorm、review 或需求分析時，不自行建立 branch/worktree。

## Core invariants

### 1. 一個 task 對應一個明確 branch/worktree

正式 implementation 前使用獨立 task branch。

Branch 名稱描述目的，不使用 `temp`、`test2`、`new`、`work`、`branch1`、`final` 等無語意名稱。

### 2. Branch 建立後立即發布 remote tracking branch

建立成功後：

```powershell
git push -u origin HEAD
```

Remote branch 是 canonical review/handoff surface；它的存在不代表功能完成或可 merge。

### 3. Branch 必須基於最新可信 main

Canonical main worktree：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

開始 task 前必須先 `git fetch origin`，確認 main worktree clean、attached to `main`，並以 `git pull --ff-only` 同步到 fetched `origin/main`。

不得用 reset/clean/force checkout 掩蓋 dirty/diverged 狀態。

### 4. Worktree ownership 必須先查再動

建立/switch branch 前先執行：

```powershell
git worktree list --porcelain
```

不得假設 branch 沒有被其他 worktree 使用。

### 5. Environment 是 consumer-only

Task startup 不建立或修改 Python dependencies。

若 task worktree 缺少有效 `.venv` junction，應 fail-fast 並提供 bootstrap guidance；不得 silent fallback system Python。

不得在 shared environment 執行 `pip install -e .`。

Node workflow dependencies 採用 per-worktree untracked `node_modules`。若 task 需要執行 Node tooling（如 AI Gate 或 Node workflow tests），worktree 必須具備本機 `node_modules`。Normal consumers 嚴禁自動安裝套件；若未 bootstrap 應 fail-fast。

## Startup workflow

### Phase 0 — Development intent

確認最小邊界：

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
<完成後可觀察到什麼>

Explicitly out of scope:
<此次不處理內容>
```

若使用者已提供足夠資訊，不重複詢問。

### Phase 1 — Canonical main preflight

在：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

先執行：

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

若 dirty、diverged、detached 或無法 fast-forward，立即停止並回報。

禁止：

```text
reset --hard
clean -fd
force checkout
```

### Phase 2 — Determine task id / branch name

優先遵循正式 task id。一般 branch 命名以目的為主，例如：

```text
feat/daily-status-notifier
fix/discord-webhook-id-extraction
refactor/notification-boundaries
```

若 AI Task Lifecycle 已建立 `task-<task-id>` remote branch，直接使用該 branch contract，不再另造第二個 branch identity。

### Phase 3 — Determine canonical task path

新 task worktree 預設：

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

建立前確認：

```powershell
git worktree list --porcelain
git branch --list <branch>
git branch -r --list origin/<branch>
```

不得覆蓋既有目錄或搶占已被其他 worktree checkout 的 branch。

### Phase 4 — Create / attach task worktree

若 remote task branch 已存在、本地 branch 尚不存在：

```powershell
git worktree add -b <branch> E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id> origin/<branch>
```

若本地 branch 已存在且未被其他 worktree 使用：

```powershell
git worktree add E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id> <branch>
```

若是一般新 branch，從 fetched `origin/main` 建立，再立即 publish upstream。

### Phase 5 — Remote-to-local handoff

進入 task worktree 後確認：

```powershell
git status --short
git branch --show-current
git pull --ff-only
```

若 task worktree detached，先恢復到正確 task branch；不得在 detached HEAD 上執行 Scout/Gate/implementation。

### Phase 6 — Environment preflight

#### 6.1 Python environment preflight

確認：

```text
<task-worktree>\.venv
```

存在且可解析到 canonical shared environment。

正常執行只使用：

```text
.\.venv\Scripts\python.exe
```

不得引用其他 worktree 的 interpreter absolute path。

若 `.venv` 缺失或需要 bootstrap，執行 repository-owned bootstrap primitive：

```powershell
.\scripts\worktree_environment_bootstrap.ps1 -WorktreePath <task-worktree>
```

本 primitive 會安全驗證 worktree 註冊狀態、檢查 canonical 環境與 interpreter、建立 exact Windows junction 並驗證本機 python 執行能力；若遇到 physical directory、wrong target 或 unsupported reparse 則會 fail closed。本 Skill 嚴禁自行 pip install、pip uninstall 或 recreate venv。

#### 6.2 Node workflow dependency preflight

若該 task 涉及 AI Gate、reviewer adapter、或 Node workflow scripts，確認本 worktree 具備可用的 Node workflow dependencies。

若 `node_modules` 缺失或未完成 bootstrap，執行明確 bootstrap 指令：

```powershell
.\scripts\bootstrap_node_workflow_deps.ps1
```

（或由操作者在 worktree root 執行 `npm ci`）。

注意：
- 每個 runnable worktree 擁有獨立 untracked `node_modules`，不透過 junction 共享。
- Gate、Scout 與 tests 僅作為 consumer；若套件缺失會 fail-fast，絕不自動執行 `npm install` / `npm ci`。

### Phase 7 — Publish remote tracking branch

若 branch 尚未設定 upstream：

```powershell
git push -u origin HEAD
```

確認：

```powershell
git branch -vv
```

後續 commit 完成後直接 `git push`。

## Development boundary snapshot

正式 coding 前保留最小邊界：

```text
Task / Branch:
<name>

Worktree:
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>

Base:
main @ <sha>

Goal:
<一句話>

Observable acceptance:
- ...

Out of scope:
- ...

Remote:
origin/<branch>
```

若已有正式 `docs/tasks/<task-id>/SPEC.md`，引用該 SSOT，不建立第二份 spec。

## Commit rules during development

遵循 `.agents/AGENTS.md`：

- Angular Commit type。
- 禁止 `git add .`
- 禁止 `git add -A`
- 禁止 `git commit -a`
- 精確 stage 本次相關檔案。
- 不混入 unrelated working-tree changes。

## Explicit non-responsibilities

本 Skill 不負責：

- full regression suite
- behavior-preserving closeout refactor
- contract archival/convergence
- PARS story
- merge
- task worktree cleanup
- local/remote branch deletion
- Python dependency mutation

上述事項由 `branch_completion_workflow` 或專門的 environment task 處理。

## Completion criteria

```text
[ ] canonical main 已 fetch 並同步到最新可信 origin/main
[ ] git worktree ownership 已確認
[ ] task branch 名稱符合 change intent / task contract
[ ] task worktree 位於 canonical project-scoped path
[ ] task worktree attached to expected branch
[ ] origin/<branch> 已建立或已存在
[ ] upstream tracking 已設定
[ ] worktree-local .venv 可用
[ ] Goal / Acceptance / Out-of-scope 已確認
```

## Final output

```text
Task worktree ready:

Task: <task-id>
Branch: <branch>
Worktree: E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
Base: main @ <sha>
Remote: origin/<branch>
Environment: .venv consumer ready
```

# One-line principle

> Validate canonical main and worktree ownership first; then create one task, one branch, one worktree, one remote review surface.
