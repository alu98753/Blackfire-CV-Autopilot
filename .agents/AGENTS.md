# Project Global Guidelines & Rules (AGENTS.md) 🤖

本文件包含所有 AI 協同開發人員在維護本專案時必須遵守的全域行為規範。

---

## Mandatory AI Test Execution Policy

- AI agents must never run the complete test suite, including `python -m unittest discover tests`.
- During implementation, AI agents may run only the smallest directly relevant test method, test class, or test file for the changed behavior.
- After focused work is complete, AI may ask the user to run the complete suite when project policy requires it.
- These rules supersede older instructions that ask an AI agent to run a full-suite, pre-merge, branch-completion, or coverage-union verification.
- Docs-only changes do not require unit/full-suite execution; scope must still be audited before commit.

## 核心原則：AI Agent 5 大極簡原則 💡

1. **「感知」與「決策」分離 + 分層禁止反向依賴**：`Detector` 只負責觀察畫面並輸出狀態 (`SceneInfo`)，絕不觸發點擊；`Handler` 只根據狀態做決策，絕不現場比對畫面。
   - 依賴方向：`main` → `state_machine` → `handlers` → `actions/mouse`。
   - 底層模組嚴禁持有上層物件直接引用；跨層通知使用 callback 注入。
2. **單一職責與架構警示 (Smell vs Goal)**：一檔一主要職責。LOC 是 smell，不是拆分目標。
   - Production code 約 300 行、方法約 60 行、巢狀約 3 層是審查觸發線，不是硬上限。
   - 優先檢查 change reason、dependency direction、cohesion、testability，再看大小。
   - 禁止 LOC-driven refactor、code golf、無語意 helper/part1/part2 拆檔。
   - Tools / CLI / Tests 不套用 production LOC 觸發線；依責任與可導航性判斷。
3. **狀態驅動，拒絕補釘**：新需求/彈窗優先建立獨立 State 或子狀態機，不在主流程堆 `if is_special_case`。
4. **全局審視優先於局部編寫**：寫 code 前先審視既有架構與 ownership boundary。
5. **零容忍三害：Magic Number、Dead Code、DRY 違規**：
   - 業務邏輯中的 magic number/string 要有語意命名。
   - 重構後 dead code 當次清除。
   - 重複邏輯應抽取共用責任，但不得為 DRY 建立錯誤抽象。

---

## 研發與維護實務規範 🛠️

### 1. Git 分支、Task Start 與 Commit 規範 🔀

> [!CRITICAL]
> **合併權限分工 (Merge Authority Rules)**
>
> 1. **本機實作/審查代理人（Gemini / Antigravity / OpenCode）**：禁止 merge、push to `main`、刪 branch 或進行等價 integration action。
> 2. **ChatGPT Remote Orchestrator**：只有在 applicable closeout requirements 通過、且使用者明確授權後，才能透過 GitHub 以 merge-commit semantics 整合。
> 3. **User**：最終 integration authority，可選擇自行手動整合。

#### Canonical local ownership

Permanent local main worktree：

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
```

它永久 attached to `main`，同時是 integrated runtime/CV validation home。

新 task worktree：

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

**舊的 permanent temp-main / detached-main parking convention 已淘汰。** 不得再把 `BlackfireCrusade_tool` 當作 detached `origin/main` 停泊區。

#### Formal AI Task Start Routing Rule

當使用者明確說「開始 XXX task」、「正式開始 XXX」、「建立 XXX task」等正式 AI Task Lifecycle 指令時：

1. ChatGPT 先在 GitHub 建立/更新 approved remote task branch、Draft `SPEC.md`、`task.json`。
2. Local startup normal path 統一使用 repository-owned wrapper：

```powershell
.\scripts\task_start.ps1 -Task <task-id>
```

legacy/nonstandard approved branch name 才使用：

```powershell
.\scripts\task_start.ps1 -Task <task-id> -Branch <branch-name>
```

`task_start.ps1` 自行負責 canonical main validation/safe FF、fetch、worktree topology/branch exclusivity、remote task branch + artifacts validation、canonical task worktree create/reuse、safe task-branch FF，以及 `.venv` bootstrap。

**正常 formal AI task 啟動時，不再要求使用者手動逐條執行：**

```text
git fetch origin
git worktree list --porcelain
git worktree add ...
git checkout/switch ...
git pull --ff-only
mklink /J ...
worktree_environment_bootstrap.ps1
```

低階 Git/worktree/bootstrap command 只在 `task_start.ps1` fail closed 後作為 bounded diagnosis/recovery 使用。

`TASK_READY` 後才進入後續 Scout/Final SPEC/implementation lifecycle。`task_start.ps1` 不執行 Scout、Gate、Node bootstrap 或 cleanup。

#### Manual/non-AI branches

真正不屬於 formal AI task lifecycle 的一般 branch 可遵循 `branch_start_workflow` manual fallback，但仍必須先檢查 actual worktree topology、不得搶占其他 worktree branch、不得用 force/reset/clean 掩蓋 dirty/diverged state。

#### Commit rules

- Commit format：Angular / Conventional (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, etc.).
- 禁止 `git add .`、`git add -A`、`git commit -a`。
- 每次只精確 stage 本次 task 相關檔案。
- 不得混入 unrelated working-tree changes。
- Merge to `main` 採 merge-commit semantics；不得 silent squash/rebase。

#### Windows shell rule

Automation/non-interactive commands 使用：

```text
cmd.exe /d /s /c "<command>"
```

PowerShell automation 包在 non-interactive `cmd.exe` execution 中，避免 child CLI 等待 stdin；保留正確 repository working directory。

---

### 2. 分支收尾、整合與 Cleanup 規範 📝

當使用者表示「分支收尾」、「準備 merge」、「請 merge」等，啟動 `branch_completion_workflow` gated closeout，不代表直接 merge。

Closeout 依實際 task 執行 context audit、regression classification、contract convergence、final semantic/architecture review、integration readiness。任何 `BRANCH_REGRESSION` / `UNCERTAIN` 均 block closeout。

Local AI agent 不自行 integration。User 明確授權後，ChatGPT 可透過 GitHub merge-commit 整合；或 user 選擇在 canonical permanent main 手動整合。

#### Normal post-integration cleanup

Task 已確認整合進 `origin/main` 後，normal cleanup 只交付 repository wrapper：

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id>
```

若 user/repository policy 要連 remote branch 一起刪：

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id> -DeleteRemoteBranch
```

`task_cleanup.ps1` 已負責 fetch、topology、cleanliness、integrated ancestry、`.venv` safety detach、normal worktree removal、postcondition verification、local branch safe-delete，以及 optional remote delete。

**正常 cleanup 時，不再要求使用者手動逐條執行：**

```text
worktree_cleanup_safety.ps1 -Detach
git worktree remove ...
git branch -d ...
git worktree prune
手動刪 .venv junction
```

`worktree_cleanup_safety.ps1` 是 task cleanup 的低階 safety primitive / recovery tool，不是 normal operator entrypoint。

如果 `task_cleanup.ps1` fail closed，先依 machine/result evidence 診斷，再提供 bounded recovery。禁止直接用：

```text
git worktree remove --force
git reset --hard
git clean -fd
blind git worktree prune
```

Canonical cleanup 細節以 `branch_completion_workflow` 與 `docs/architecture/ai_development_workflow.md` 為準。

---

### 3. Python / Node Environment Ownership

Canonical shared Python environment：

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

每個 runnable worktree 透過自己的 `.venv` junction consume 同一 physical environment。

- Main baseline 使用 main worktree 自己的 `.venv\Scripts\python.exe`。
- Task tests 使用 task worktree 自己的 `.venv\Scripts\python.exe`。
- 不引用另一 worktree 的 interpreter absolute path。
- Consumer task/Scout/Gate/tests/runtime validation 不 `pip install` / `pip uninstall` / recreate venv。
- 不 silent fallback 到 system Python。
- 不在 shared env 執行 `pip install -e .`。

Formal task startup 的 `.venv` readiness 由 `task_start.ps1 -> worktree_environment_bootstrap.ps1` 負責；user 不需要自行建立 junction。

Node dependencies 維持 per-worktree `node_modules`，由 tracked `package.json` + `package-lock.json` 管理。Node materialization 僅在 later consumer 需要時透過：

```powershell
.\scripts\bootstrap_node_workflow_deps.ps1
```

Scout/Gate/tests 不 silent `npm install` / `npm ci`。`task_start.ps1` 不 bootstrap Node。

---

### 4. 極速掛機與延遲規範 ⚡

- `pyautogui.PAUSE = 0.002` (2ms)。
- `mouseDown`/`mouseUp` 間隔 `40ms` (`time.sleep(0.04)`)，釋放後至少等 `40ms`。
- 主迴圈 `--interval` 預設 `0.05` 秒 (50ms)；常規按鈕點擊後等待 `30ms`，跨場景/下樓等待 `40ms`。

### 5. 局部比對與 Scale 視務規範 🎯

- **Scoped Crop Only**：卡片/彈窗內部比對禁止全螢幕掃描，必須先切割 `crop` 區域。
- **Scale 自適應**：以 `scale_x = w / base_w` 縮放範本；卡片發射前先核驗無冷卻木牌。

### 6. 懸賞任務對應規範 📋

- 集中於 `utils/quest_mapper.py` 的 `QuestMapper`。
- 優先級：`確定性` > `僅彈窗`；`地下城` > `關卡`；`關卡層數`大者優先。
- 未知任務記錄至 `user_data/daily_status.json`。

### 7. 測試架構設計與執行規範 🧪

#### Docs-only exemption

當異動只有 Markdown / documentation contract（例如 `docs/**/*.md`、`.agents/AGENTS.md`、`.agents/skills/**/*.md`），且未修改 runtime/build/test/script/config 資產，不需要執行 unit/full suite。

仍需核對 changed-file scope，並回報：`未執行測試（純文件變更）`。

#### Test public behavior, not private implementation

測試優先驗證外部可觀察 behavior/state transition，而非 private helper 或中間變數。架構重構不應迫使 behavior tests 跟著 implementation details 改寫。

#### Behavioral domain slicing

大型測試依 behavior/subsystem 分檔，不依 LOC 機械拆分。

#### Execution policy

1. 日常開發只執行 smallest directly relevant test method/class/file。
2. 修 test failure 時只跑該 failure target，通過後再擴到必要 focused scope。
3. Full test suite 只能由 user 執行。
4. 若 AI 要求 user 跑 full suite，使用 project root + worktree-local `.venv`，並在 Windows 使用 UTF-8/log redirection 以便後續診斷。

Example user-only full suite command：

```powershell
cmd.exe /d /s /c "chcp 65001 >nul && .venv\Scripts\python.exe -X utf8 -m unittest discover tests > test_run.log 2>&1"
```

Current pytest test entrypoints use the Python 3.11.2 clean environment:

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -m "not ai_workflow" -v
```

AI workflow, OpenCode, task orchestration, and worktree contract modules are marked `pytest.mark.ai_workflow`. The normal game-logic suite excludes them with `-m "not ai_workflow"`; test files should not be moved only to separate these domains. The complete suite is user-only and includes AI workflow tests:

```powershell
.\.venv\Scripts\python.exe -X utf8 -u -m pytest -v
```

若 task/main tests 競爭 game process、`user_data/`、固定 screenshot/log 等 shared resource，序列執行。

### 8. Markdown 文檔客觀寫作規範 📄

全專案 Markdown 遵循 Evidence-Bound Natural Writing：

1. 確定性不得超過證據強度。
2. 整理/改寫不得擅自升級斷言或填補未證實空白。
3. 避免 AI 味修飾、情緒化黑話與無效標籤。
4. 優先連貫短段落；只有真正平行項目/步驟使用 list。
5. 保留具體數值、變數、公式、符號與路徑。
6. `docs/` Markdown 不使用 `file:///` absolute link；使用 repository-relative links。

### 9. MetaData 腳本與資料庫維護規範 🗃️

- 長期可重用核心工具/生成器要規範命名並 track。
- 一次性 exploration script 優先放 scratch/ignored location，或 task 結束前清理。
- 分析/文件維護做到資料解析 → 文件更新 → 工具分類/臨時檔清理 → 狀態核驗後再回報。

### 10. 座標體系一致性與共用工具規範 📐

- 全鏈路統一 Client 座標系 (`GetClientRect` + `ClientToScreen`)；避免混用 `GetWindowRect`。
- 視窗控制 handle 查詢統一走 `utils/window.py` 的 `WindowHandle`。
- 跨模組共用常數集中於 `config.py` 或合適 canonical contract。

### 11. 日誌分級與終端潔淨規範 📜

- 預設 `logging.INFO`。
- 每幀/高頻 telemetry 用 `DEBUG`。
- 關鍵 decision/state transition/業務完成用 `INFO`。
- 可自癒異常/退避用 `WARNING`。
- 超限、不可逆中斷、未捕獲例外用 `ERROR`。
- 禁止在 INFO 反覆輸出每秒高頻診斷造成 terminal 洗屏。

### 12. 提交前自審清單 ✅

1. ☐ 是否有 magic number/string 應抽取語意常數？
2. ☐ 是否有真正可共用的重複邏輯或錯誤抽象？
3. ☐ Responsibility / dependency / cohesion / testability 是否合理？
4. ☐ 底層是否直接引用上層物件？
5. ☐ 是否留下 dead code？
6. ☐ 座標是否統一 Client 座標系？
7. ☐ 高頻 telemetry 是否放在 DEBUG？
8. ☐ Production code/docstring/comment 是否殘留暫時 task/issue wording？
9. ☐ Markdown 斷言是否符合 evidence strength？
10. ☐ Formal AI task startup/cleanup 是否使用 repository wrapper，而不是要求 user 手動重做 wrapper 已擁有的低階步驟？
