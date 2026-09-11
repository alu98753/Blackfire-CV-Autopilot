---
name: branch_completion_workflow
description: 個人開發模式下的分支收尾工作流，包含 dual-worktree baseline、regression classification、refactor、contract convergence 與 merge preparation。
usage_scope: solo_development_only
---

# 分支收尾標準工作流 (Branch Closeout Gated Workflow Skill) 🚀

本技能為本專案 Feature / Fix 分支開發完成後的**統一分支收尾 (Branch Closeout) 總編排技能 (Orchestration Skill)**。
負責從雙工作樹迴歸基準線 (Regression Baseline) 驗證開始，引導執行安全網檢驗、保行為維護重構 (Behavior-Preserving Maintenance Refactor)、程式碼與文件契約收斂，直到交付標準 Merge 指令。

---

## 👤 Usage Scope & 協作環境守衛 (Solo vs. Team Guard)

> [!IMPORTANT]
> **本 Skill 預設為「單人開發模式 (Solo Development Mode)」**：
> 假設由單一開發者全權管理 `main`，因此允許以本地 `temp-main` 作為個人 baseline，並在 clean 且可 fast-forward 時由 AI 輔助同步。

### 🛡️ 多人協作防護網 (Multi-Developer Guard)
若出現團隊協作特徵（如有多位活躍貢獻者、強制 PR Review、保護分支或遠端 CI 驗證）：
- 🚫 **禁止套用 Solo-Only 步驟**：不得以本地 `temp-main` 取代團隊整合環境，嚴禁本機直接 `--ff-only` 或繞過 PR/CI/Review 機制。
- ✅ **維持通用收尾步驟**：保留 HEAD baseline 測試、迴歸分類、保行為重構與文件/契約收斂等核心品質閘門。
- 🔀 **改由團隊標準流程整合**：交付物由本機 `--no-ff` 指令轉為提供 PR 描述、CI 檢查指引或協同合併審查。

---

## 🎯 觸發詞識別 (Trigger Identification)

當使用者發出以下任何指令時，一律視為啟動本工作流：
- `請分支收尾` / `分支收尾`
- `準備 merge` / `準備merge`
- `請 merge` / `請merge` / `跑merge`
- `收尾分支` / `結束分支`

> [!CRITICAL]
> **【最高硬性阻斷禁令 (Hard Blocking Invariant)】**
> 1. **「請 merge」代表「啟動分支收尾流程」，絕對不是「立刻輸出 `git merge` 指令」！**
> 2. 本流程為**硬性分段閘門工作流 (Gated Workflow)**，**嚴禁一次跑到底**！
> 3. 每當遇到需要使用者執行全套測試、確認文件清理範圍或確認重大決策的 Gate 時，AI **必須停下來等待使用者回覆，嚴禁擅自推進至下一階段**。

---

## 📁 標準工作區配置 (Worktree Layout)

收尾時標準工作樹配置如下：

```text
E:\Side_Project\
├─ BlackfireCrusade_tool\   ← 日常 Feature/Fix branch worktree (當前開發目錄)
└─ temp-main\               ← 長期保留的 main baseline worktree
```

- `temp-main` 是長期存在的基準線工作樹，**不需要每次重新建立**。
- **嚴禁假設 `temp-main` 一定已同步到最新 main**，在驗證前必須進行狀態檢查與安全同步。

---

## 🚦 11 階段硬性狀態閘門 (The 11-Phase Gated Workflow)

```mermaid
flowchart TD
    Start(["使用者觸發：請分支收尾 / 請 merge"]) --> P0["Phase 0: Closeout Context Audit<br>(審查變更範圍與模組邊界)"]
    P0 --> P1["Phase 1: Dual-Worktree Baseline Verification<br>(AI 先查 temp-main；交付重定向 log 指令；<br>🛑 停下：等待使用者跑完並指示讀取 log 檔)"]
    P1 --> P2{"Phase 2: Regression Classification<br>(讀取 log 檔比對 failures 分類)"}
    
    P2 -- "存在 BRANCH_REGRESSION 或 UNCERTAIN" --> P2_Block["🛑 強制阻斷！<br>先修復測試或程式行為問題"]
    P2_Block -.-> P1
    
    P2 -- "無 Regression (僅 PRE_EXISTING 或 EXPECTED)" --> P3["Phase 3: Refactor Safety-Net Gate<br>(檢查行為測試覆蓋率，不足先補測)"]
    P3 --> P4["Phase 4: Behavior-Preserving Maintenance Refactor<br>(審計與重構：清理 dead code/glue，獨立 commit)"]
    P4 --> P5["Phase 5: Post-Refactor Verification<br>(跑 focused test；🛑 停下：等待使用者重跑 full test 並重定向 log)"]
    
    P5 -- "出現新 Failure 或行為改變" --> P5_Block["🛑 強制阻斷！修復重構問題"]
    P5_Block -.-> P4
    
    P5 -- "確認無新增 Failure" --> P6["Phase 6: Code & Docstring Hygiene<br>(清除臨時 spec/issue 代號，重寫為穩定契約)"]
    P6 --> P7["Phase 7: Contract / TODO / Spec Convergence<br>(🛑 停下：列出候選文件與日誌清單，等待使用者確認刪除範圍)"]
    P7 --> P8["Phase 8: PARS Development Story<br>(撰寫 docs/storys/ 開發故事)"]
    P8 --> P9["Phase 9: Final Branch Audit<br>(核對 git status, log, diff，確認乾淨)"]
    P9 --> P10["Phase 10: Merge Delivery<br>(輸出 Closeout Report 與結構化 Merge 指令)"]
    P10 --> End(["交付完成，等待使用者手動執行 Merge"])
```

---

### Phase 0 — Closeout Context Audit (變更脈絡審計)

**目標**：完整理解本分支實際改動內容與模組邊界，嚴禁直接開始 merge。

1. **執行環境與歷程審查**：
   ```powershell
   git status
   git branch --show-current
   git diff main...HEAD --stat
   git log main..HEAD --oneline
   ```
2. **變更清單盤點**：
   - 本 branch 涉及的 Production Code 檔案。
   - 相關的 Unit / Behavioral Tests。
   - 暫時性 Specs / TODOs / RFCs。
   - 相關的 Canonical Contracts 與 Architecture Docs。
3. **產出**：向使用者簡要回報當前分支名稱、變更檔案規模與核心模組，並準備推進至 Phase 1。

---

### Phase 1 — Dual-Worktree Baseline Verification (雙工作樹基準線驗證)

**目標**：確認 `temp-main` 為乾淨且最新的 main baseline，隨後由使用者分別執行 HEAD 與 main 的完整 test suite。

> [!WARNING]
> **AI 嚴禁自行執行完整 test suite (`python -m unittest discover tests`)！**

#### 1. AI 主動核驗並刷新 main baseline
於 `E:\Side_Project\temp-main`：
- 確認 `git status --short` 為 clean（無未提交修改）。
- 確認 `git branch --show-current` 為 `main`。
- 執行 `git fetch origin`。
- 比較兩者 Commit Hash：
  - `git rev-parse HEAD`
  - `git rev-parse origin/main`

**決策分流**：
- **若兩者相同**：baseline 已為最新狀態，直接進入測試。
- **若兩者不同**：僅在 worktree clean 且可 fast-forward 時執行：
  ```powershell
  git pull --ff-only
  ```
  *(注：baseline worktree 嚴禁產生 merge commit，必須使用 `--ff-only`)*
- **若出現 dirty、diverged 或無法 fast-forward**：
  - 立即停止流程並向使用者回報異常。
  - **嚴禁自行使用 `reset --hard`、`clean`、force checkout 等破壞性操作**。

#### 2. 一次性交付雙 Terminal 測試指令 (重定向至獨立 Log 檔案)
*(注：為徹底防止終端緩衝區字元混疊錯位與截斷，全套測試統一重定向至主專案目錄下的獨立日誌檔)*
*(注：`temp-main` 為 Git worktree，通常無獨立 `.venv`，兩組測試統一共用主專案之 Python 解譯器以保證相依套件環境 100% 一致)*
- **Terminal 1 — Feature HEAD 測試**：
  ```powershell
  cd E:\Side_Project\BlackfireCrusade_tool
  .venv\Scripts\python -m unittest discover tests > head_test_output.log 2>&1
  ```

- **Terminal 2 — Main Baseline 測試**：
  ```powershell
  cd E:\Side_Project\temp-main
  E:\Side_Project\BlackfireCrusade_tool\.venv\Scripts\python.exe -m unittest discover tests > E:\Side_Project\BlackfireCrusade_tool\main_test_output.log 2>&1
  ```

> [!TIP]
> **執行順序守則**：兩組測試可以依序或平行執行；若測試涉及共享之 runtime resources（如遊戲處理序、`user_data/` 狀態檔、固定 debug 截圖/日誌等），**必須依序執行**以防互斥污染。

#### 3. 🛑 阻斷點 (Gate Invariant)
- 停在此處，**等待使用者在兩個 Terminal 執行完畢並回報「已跑完」**。
- AI 收到通知後，直接以 `view_file` 讀取 `head_test_output.log` 與 `main_test_output.log` 進行完整、零截斷之比對分析。
- 收到雙邊測試完成通知前，**絕對不得進入下一階段**。

#### 4. 結構化記錄
```text
HEAD BASELINE
- passed: <數量>
- failed: <數量>
- errors: <數量>
- failing test names: [測試方法名稱清單]

MAIN BASELINE
- passed: <數量>
- failed: <數量>
- errors: <數量>
- failing test names: [測試方法名稱清單]
```

---

### Phase 2 — Regression Classification Gate (迴歸分類閘門)

**目標**：精確比對 `MAIN BASELINE` 與 `HEAD BASELINE`，將所有失敗案例分類並阻斷潛在迴歸。

#### 失敗案例四象限分類：
1. **`PRE_EXISTING_FAILURE`**：main 與 HEAD 均失敗的測試。屬於既有基準線問題，非本次分支引入。
2. **`BRANCH_REGRESSION`**：main 通過但 HEAD 失敗的測試。確定為本分支引入的 regression！
3. **`EXPECTED_BEHAVIOR_CHANGE`**：main 的舊測試預期因本次已確認之業務需求而合法改變。
   - 必須由 Spec、Canonical Contract 或驗收條件佐證。
   - 嚴禁僅因為「現在實作改成這樣」就將失敗歸類於此。
4. **`UNCERTAIN`**：無法立即確定是 Production Bug、過期測試還是需求模糊的案例。

#### Production-vs-Test 修復守則

Regression 分析與修復必須遵循 `project-test-rules` 的
**Test-Induced Production Logic Prohibition**。

特別禁止為了相容 Mock / Fixture 而在 Production Code 新增測試專用 bypass。

> [!CRITICAL]
> **🛑 阻斷點 (Hard Gate)**：
> 若存在任何 **`BRANCH_REGRESSION`** 或 **`UNCERTAIN`**：
> - **絕對禁止進入後續 Refactor 或 Merge Closeout**！
> - 必須停下來深入分析原因，優先修復測試或 Production 程式碼行為，回到 Phase 1 重新取樣。

---

### Phase 3 — Refactor Safety-Net Gate (重構安全網閘門)

**目標**：確保在開始任何重構前，本分支的重要可觀察行為已有足夠的測試保護。

1. **核心自我詰問**：
   > 「如果下一階段修改內部實作時，不小心改壞了目前已通過的合法行為，現有測試是否具備足夠高機率能精確攔截？」
2. **補強防護網**：
   - 若測試網不足，優先提出需要補齊的：
     - Characterization Tests（特徵描摹測試）
     - Behavioral Tests（業務行為測試）
     - Contract-Level Regression Tests（契約層級迴歸測試）
   - 測試撰寫遵循 Google 軟體工程規範：**驗證可觀察行為，不依賴內部私有變數或 private helper**。
3. **提早固化**：補齊測試後，以獨立 commit 提交（依 `precise_git_commit` 白名單 stage），方可推進。

---

### Phase 4 — Behavior-Preserving Maintenance Refactor (保行為維護重構)

**目標**：在不改變任何可觀察行為的前提下，消除 dead code、重複邏輯、過渡膠水與不必要複雜度。

1. **執行 Refactor Audit（審查 `git diff main...HEAD`）**：
   - `Safe dead code removal`：確認無 caller 的死代碼
   - `Safe simplifications`：化簡過深的巢狀分支與流程
   - `Safe duplication removal`：提取超過 3 行的重複邏輯
   - `Temporary glue`：清除開發過程暫時搭建的適配層
   - `Obsolete compatibility paths`：清理已無意義的舊相容路徑
   - `Duplicated state ownership`：釐清狀態歸屬，消除重複維護
   - `Responsibility / boundary issues`：對齊模組單一職責
   - `Compatibility logic that must remain`：明確標註不可動的相容邏輯
   - `Deferred architecture work`：移出本次、記錄至未來工作
   - `Explicitly out of scope`：明確排除的項目
2. **八大硬性限制 (Strict Refactor Invariants)**：
   1. 不新增功能。
   2. 不改變可觀察行為 (Observable Behavior)。
   3. 不順便重寫無關模組。
   4. 不因為「追求漂亮」而增加過度抽象層。
   5. 不修改正確的 tests 來配合重構。
   6. 需要改變行為的問題，移出本次重構。
   7. 涉及重大架構遷移的問題，記錄為後續工作。
   8. 刪除代碼前必須全方位確認不存在：Runtime Caller、Callback、Registry、動態分發、Config 驅動調用、CLI/腳本入口、反射調用。
3. **獨立提交**：重構必須使用獨立 Commit，例如：
   ```powershell
   git commit -m "refactor: simplify <scope> after feature implementation"
   ```

---

### Phase 5 — Post-Refactor Verification (重構後驗證)

**目標**：確認維護重構完全沒有破壞任何行為或引入新錯誤。

1. **AI 執行聚焦測試**：
   - 優先執行與重構模組直接相關的聚焦單元測試，確保快速反饋。
2. **🛑 阻斷點 (Gate Invariant)**：
   - 請使用者在 Feature/Fix 工作樹再次執行全套測試套件並重定向至日誌：
     ```powershell
     cd E:\Side_Project\BlackfireCrusade_tool
     .venv\Scripts\python -m unittest discover tests > post_refactor_test_output.log 2>&1
     ```
   - 停在此處，等待使用者回報執行完畢。
   - AI 讀取 `post_refactor_test_output.log` 比對確認。
3. **比對確認**：
   - 比對 `HEAD BEFORE REFACTOR` vs `HEAD AFTER REFACTOR`。
   - 必須滿足：
     - `New failures introduced: NONE`
     - `Behavior changed: NO`
   - 若產生任何新 failure，**嚴禁進入文件收斂或 merge 階段**，必須立即退回修復重構。

---

### Phase 6 — Code / Documentation Hygiene (程式碼潔淨度審計)

**目標**：徹底消除 Production 代碼中的臨時歷史痕跡。

1. **排查檢核**：
   - 檢查本次異動之 Production Code 中的 docstrings 與註解。
   - 徹底移除暫時性 spec 名稱（如 `nav_slow_bug2`、`bag_bug` 等檔名）、分支名、Task ID、WIP 註記或歷程說明。
2. **契約化改寫**：
   - Production Code 只能保留：穩定的行為語意 (Behavior Semantics)、職責邊界、公開契約。
   - 若確實需要標示架構依據，**僅限引用長效維護的 Canonical Contract**（例如 `Contract: docs/features/navigation/lobby_scene_contract.md`）。

---

### Phase 7 — Contract / TODO / Spec Convergence (契約與文件收斂)

**目標**：調用 [`canonical_contract_archival`](../canonical_contract_archival/SKILL.md) 技能，將完成任務的臨時文件提煉為長期標準，並徹底清理過期文件與暫存測試日誌，防止 Doc/Artifact Drift。

1. **盤點候選文件與暫存測試日誌**：
   - 檢查 `git diff main..HEAD --name-only` 涉及的 `docs/todos/`、臨時 Specs、RFCs、`future_work.md`。
   - 納入收尾過程中產生的全套測試日誌暫存檔：`head_test_output.log`、`main_test_output.log`、`post_refactor_test_output.log`。
2. **🛑 阻斷點 (Mandatory User Scope Confirmation)**：
   - ⚠️ **嚴禁 AI 自行決定清理範圍**！
   - AI 必須先列出候選清單（包含過期文件與暫存測試日誌），主動詢問使用者：
     > 「請問本次分支要收斂／升格／刪除的文件與日誌是否為以下清單？是否有不可刪除或仍未完成的項目？」
   - **停在此處等待使用者確認**，確認前不得動手修改或刪除文件。
3. **執行分類與提煉（依 `canonical_contract_archival` 規範）**：
   - `PROMOTE`：永久不變量升格至 Canonical Contract（`docs/architecture/` 或 `docs/features/`）。
   - `LINK`：程式碼與測試已有者，Contract 僅做參照。
   - `HISTORY`：歷史脈絡留給 PARS 與 Git。
   - `TODO`：搬遷至獨立 `docs/todos/<task>_rfc.md` 或保留於未完成 TODO。
   - `DROP`：**刪除是預設；封存是例外**。原始任務 Spec 提煉後預設刪除；**暫存測試日誌檔（`*.log`）於此階段與過期文件一併徹底清理刪除**，保證工作區無殘留雜檔。
4. **獨立提交**：以 `docs: ...` 進行獨立精確 Commit。

---

### Phase 8 — PARS Development Story (開發故事歸檔)

**目標**：記錄本次開發歷程，供後續回溯複盤。

1. **撰寫 PARS**：
   - 於 `docs/storys/` 建立或更新本次工作之 PARS 文件：
     - **P**urpose (目的與背景問題)
     - **A**ction (採取的關鍵行動與設計決策)
     - **R**esult (驗證結果與測試數據)
     - **S**o What (業務價值與深遠意義)
     - **I**nfluence (架構影響與後續注意事項)
2. **遵約要求**：
   - 調用 [`write_docs`](../write_docs/SKILL.md) 技能，保持客觀中立，文字確定性嚴格受實測證據約束，禁止 AI 味誇飾。
   - ⚠️ **PARS 定性禁令**：PARS 只是歷史敘事紀錄，**絕非系統架構規範，絕不可作為架構約束依據**。寫完 PARS 不等於完成架構收斂！

---

### Phase 9 — Final Branch Audit (最終分支審查)

**目標**：合併前全面複核，確保工作區與提交歷史潔淨無暇。

1. **執行全域檢核指令**：
   ```powershell
   git status
   git log main..HEAD --oneline
   git diff main..HEAD --stat
   git diff main..HEAD --name-only
   ```
2. **確認檢核項目**：
   - [ ] Working tree 保持乾淨 (Clean)。
   - [ ] Commits scope 清楚分離 (feature, test, refactor, docs 獨立可辨)。
   - [ ] 暫時性 Spec 已正確收斂並刪除過期副本。
   - [ ] Canonical Contract 與索引已同步。
   - [ ] 無任何未追蹤或非本次任務的臨時檔案進入分支。

---

### Phase 10 — Merge Delivery (合併指令交付)

> [!CRITICAL]
> **只有當 Phase 0 至 Phase 9 的所有 Gate 均已確實完成後，才允許進入本階段！**
> AI **絕對禁止自行執行 `git merge`**，必須交付編排好的指令給使用者手動執行。

1. **輸出結構化 Closeout 報告**：
   ```markdown
   ### Branch Closeout Report

   - **Branch**: `<feature_branch_name>`
   - **Change summary**: `<本次變更核心摘要>`

   #### Test Baseline & Verification:
   - **Main baseline**: passed <P>, failed <F>, errors <E>
   - **HEAD pre-refactor baseline**: passed <P>, failed <F>, errors <E>
   - **HEAD post-refactor result**: passed <P>, failed <F>, errors <E>

   #### Failure Analysis:
   - **Pre-existing failures**: [清單]
   - **Branch regressions**: NONE
   - **New regressions after refactor**: NONE

   #### Convergence Summary:
   - **Refactor summary**: `<重構要點>`
   - **Contracts updated**: `<升格或更新的契約路徑>`
   - **Specs removed / retained**: `<刪除之 spec 與保留清單>`
   - **TODOs created**: `<建立之後續 TODO>`
   - **PARS story**: `<docs/storys/...>`

   #### Readiness:
   - **Behavior changed during refactor**: NO
   - **New failures introduced**: NONE
   - **Ready to merge**: YES
   ```

2. **生成標準 `--no-ff` 合併指令（感應用戶 OS）**：
   - **Windows (PowerShell / CMD)**：必須使用**多個 `-m` 參數**串聯，避免跨列換行造成 terminal 截斷：
     ```powershell
     git checkout main
     git pull origin main
     git merge --no-ff <branch_name> -m "Merge branch '<branch_name>' into main" -m "<簡短變更摘要>" -m "Verification: All unit tests verified against main baseline (0 regressions)."
     ```
   - **Linux / macOS**：可使用標準多行引號或多個 `-m`。

---

## 🧩 模組化職責邊界與技能引用矩陣 (Skill Matrix)

本工作流作為總編排者，遵循分工原則，嚴禁重疊複製。調用相關技能時維持各技能單一職責：

| 階段 | 職責 | 權威依歸 / 調用技能 |
| :--- | :--- | :--- |
| **Phase 1, 5** | 測試執行政策（AI 不自行跑 full test，提示使用者跑） | [`project-test-rules`](../project-test-rules/SKILL.md) |
| **Phase 3, 4, 7** | 精確 Commit 白名單 stage（嚴禁 `git add .`） | [`precise_git_commit`](../precise_git_commit/SKILL.md) |
| **Phase 7** | 文件與契約分類、提煉不變量、刪除過期 spec | [`canonical_contract_archival`](../canonical_contract_archival/SKILL.md) |
| **Phase 8** | 客觀撰寫 PARS 故事，證據確定性約束 | [`write_docs`](../write_docs/SKILL.md) |
| **Phase 10** | 強制 `--no-ff` 合併與跨平台 Shell 語法 | [`.agents/AGENTS.md`](../../AGENTS.md) 第 1 條 |

