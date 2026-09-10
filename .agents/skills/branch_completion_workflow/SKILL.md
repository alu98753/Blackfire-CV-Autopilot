---
name: branch_completion_workflow
description: 當一個 Feature/Fix 分支開發結束、準備收尾或準備合併至 main 時觸發此技能。引導 AI 自動執行代碼驗證、文件同步(docs)、PARS開發故事撰寫、測試全綠燈檢查，並生成標準 --no-ff 合併指令與詳細日誌。
---

# 分支收尾與合併標準工作流 (Branch Completion & Merge Workflow Skill) 🚀

# 分支收尾與合併標準工作流 (Branch Completion & Merge Workflow Skill) 🚀

本技能定義當本專案任何 Feature / Fix 分支開發結束、準備收尾或準備進行 Merge 時，必須按順序執行的**三階段硬性狀態閘門 (Three-Phase Gated Workflow)** 與檢核清單。

---

## 🎯 觸發詞識別 (Trigger Identification)
當使用者發出以下任何指令時，即視為啟動本工作流：
- `跑merge` / `跑 merge`
- `準備merge` / `可以merge了` / `請提供merge指令`
- `收尾分支` / `結束分支` / `收尾`

> [!CRITICAL]
> **【最高硬性阻斷禁令 (Hard Blocking Invariant)】**
> 當使用者說「跑merge」時，AI **絕對禁止直接輸出 `git merge` 指令**！
> 必須依序通過 **Phase 1 (程式碼潔淨度與 Docstring 閘門)** 與 **Phase 2 (收尾驗證與文件收斂閘門)**。
> 若本次分支涉及任何 `docs/todos/`、開發 Spec 或核心契約變更，AI **必須停在 Phase 2 向使用者提問候選收斂清單，等待使用者確認後完成契約升格與過期 Spec 清理**。
> 未完成 Phase 1 程式碼 Docstring 清理與 Phase 2 文件收斂之前，輸出任何 `git merge` 指令均視為嚴重流程違規（Process Regression）！

---

## 🚦 三階段硬性狀態閘門 (Three-Phase Gated Workflow)

```text
使用者輸入：「跑merge / 收尾 / 準備merge」
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ 【Phase 1: 程式碼潔淨度與 Docstring 審計閘門 (Code Hygiene)】 │
├─────────────────────────────────────────────────────────────┤
│ 1. 審查本次異動之 production code 中的 docstrings 與註解。   │
│ 2. 禁令排除：徹底移除暫時性 spec 名稱、issue id、分支名。   │
│ 3. 重寫為穩定行為/架構語意，必要時僅引用長效 Canonical Contract。│
└──────────────────────────────┬──────────────────────────────┘
                               │ (Phase 1 檢查無誤後推進)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 【Phase 2: 收尾驗證與文件契約收斂閘門 (Archival & Docs Gate)】 │
├─────────────────────────────────────────────────────────────┤
│ 4. 執行最小聚焦單元測試，確保改動邏輯 100% 通過。            │
│ 5. 撰寫 PARS 框架開發故事 (docs/storys/)。                  │
│ 6. 檢查 git diff main..HEAD 是否有 docs/todos/ 或 Spec？    │
│    ├─ 有 ──> 🛑 強制阻斷！向使用者列出候選清單提問。          │
│    │         等待使用者確認後，執行契約升格與 Spec 清理。      │
│    └─ 無（或已確認收斂完成） ──> 解鎖 Phase 3                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Phase 2 完成解鎖)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 【Phase 3: 分支審計與合併指令交付 (Merge Command Delivery)】  │
├─────────────────────────────────────────────────────────────┤
│ 7. 執行 git log / git diff 彙整異動統計與模組細節。         │
│ 8. 生成 Windows/Linux 相容之標準 --no-ff 合併指令。        │
│ 9. 提醒使用者手動執行全套單元測試。                         │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 1：程式碼潔淨度與 Docstring 審計 (Code Hygiene & Docstring Cleanliness Gate)

#### 核心原則：暫時 Spec 不得成為 Production Code 的永久依賴
> [!IMPORTANT]
> **Pre-Merge Cleanup Acceptance Criterion**：
> Temporary issue/spec names (e.g. `nav_slow_bug2`, phase numbers, branch names, task IDs) may be used during implementation, but **MUST NOT remain in production docstrings/comments after the branch is completed**. Before merge, rewrite them into stable behavioral/architectural descriptions, or reference a canonical long-lived contract only when necessary.

#### 審查與清理檢核表：
1. **Docstring 本質是穩定契約 (Stable Semantic Contract)**：
   - Docstring 的首要職責是向未來的維護者解釋該 function / class / module 的**職責邊界、輸入輸出、副作用與狀態轉移保證**。
   - 嚴禁出現一次性 issue 代號（例如「遵循規格 nav_slow_bug2 第 4 節」），因為半年後 spec 可能被刪除、章節改動，會使 production code 遺留幽靈歷史包袱。
2. **長效契約引用原則 (Canonical Contract Reference)**：
   - 程式碼內部若確實需要標示架構依據，**僅允許引用長效維護的 Canonical Contract**（例如 `Contract: docs/features/navigation/lobby_scene_contract.md`）。
   - 能以清楚的行為語意自我解釋時，優先自足描述，避免不必要的外部文件連結。
3. **查核動作**：
   - 使用 `git diff main..HEAD` 或針對本次修改檔案進行關鍵字掃描，排查是否遺留暫時性標籤、WIP 標記或一次性 Spec 代號。

---

### Phase 2：收尾驗證與文件契約收斂 (Archival & Docs Gate)

#### 步驟 1：最小聚焦單元測試驗證 (Focused Test Verification)
- **原則**：AI 僅執行本次分支修改直接相關之最小單元測試檔案或方法，確保改動邏輯通過。
- **禁令**：AI 嚴禁自行執行全套測試 (`.venv\Scripts\python -m unittest discover tests`)。

#### 步驟 2：撰寫 PARS 框架開發故事 (PARS Story Archival)
- 依據 `AGENTS.md` 第 3 條規範，於 `docs/storys/` 建立包含 Purpose, Action, Result, So What, Influence 的 PARS 文檔。
- ⚠️ **PARS 定性紅線**：PARS 是開發歷程的敘事故事 (Narrative Log)，**絕非系統架構規範，絕不能作為行為約束或架構證據**。寫完 PARS 不等於完成架構收斂！

#### 步驟 3：文件收斂、契約升格與過期 Spec 清理 (Contract Archival)
- ⚠️ **嚴禁以「PARS 已記載」為由略過契約升格**：Spec 中只要含有「行為不變量、排程階梯、責任邊界、禁止模式」，**必須且只能**提煉升格至 `docs/architecture/` 或 `docs/features/<domain>/` 的 Canonical Contract。若未完成升格，原始 Spec 絕不可視為「已被承接」，更嚴禁直接刪除！
檢查 `git diff main..HEAD --name-only`，若包含 `docs/todos/`、新架構規格或核心約束：
1. **前置交互守則（強制提問）**：
   - ⚠️ **嚴禁 AI 自行決定清理範圍**：AI 絕對禁止自行挑選檔案擅自執行文件收斂或刪除。
   - **顯式提問機制**：AI 必須先盤點本次分支修改或產生的 Spec/TODO 候選清單，主動向使用者提問：
     > 「請問本次分支要收斂與清理的文件清單是否為以下項目？是否有遺漏、或是否有不可清理/不可刪除的 TODO？」
   - **🛑 停在此處等待回覆**：在使用者確認清單前，**絕對不得輸出 Phase 3 的 git merge 指令**！
2. **調用 `canonical_contract_archival` 執行提煉**：
   - 永久約束不變量 ➔ 升格至 `docs/features/<domain>/` 或 `docs/architecture/`。
   - 未完成工作 ➔ 搬遷至獨立 `docs/todos/<task>_rfc.md` 或保留於未完成 TODO。
   - 原始完成 spec ➔ 依「刪除是預設；封存是例外」原則果斷清理，防止 Doc Drift。
   - 精確 Stage 本次收斂修改之檔案並進行 Commit。

---

### Phase 3：分支審計與合併指令交付 (Merge Command Delivery)
*（僅當 Phase 1 程式碼 Docstring 清理完畢且 Phase 2 文件收斂已確認完成時，方可進入本階段）*

#### 步驟 4：分支變更比對與統計 (Branch Diff Audit)
- **比對指令**：
  ```bash
  git log main..HEAD --oneline
  git diff main..HEAD --stat
  ```
- **檢核重點**：統計 Commit 總數、修改檔案總數、新增/刪除行數，按模組分類梳理變更摘要。

#### 步驟 5：生成 --no-ff 合併指令與結構化 Merge Commit 日誌
- 依據 `AGENTS.md` 第 1 條規範，分支合併至 `main` **必須強制使用 `--no-ff`**。
- **Merge 訊息結構範本**：
  ```markdown
  Merge branch '<branch_name>' into main

  [<type>/<scope>] 簡短摘要說明

  Summary of Changes (<commits_count> commits, +<added_lines> / -<deleted_lines> lines across <files_count> files):

  1. <模組 A>:
     - 改動 1
     - 改動 2
  2. <模組 B>:
     - 改動 1

  Verification:
  - All unit tests passed cleanly (OK).
  ```

---

## 📌 注意事項與安全防守
- ⚠️ **禁止自行合併**：AI 絕對禁止自行執行 `git merge`，必須提供編排好的 `git merge --no-ff ...` 指令給使用者。
- ⚠️ **嚴格順序性**：Phase 1 與 Phase 2 未確認完成前，絕不可輸出 Phase 3 的 merge 指令。


