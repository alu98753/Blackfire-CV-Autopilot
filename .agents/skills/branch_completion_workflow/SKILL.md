---
name: branch_completion_workflow
description: 當一個 Feature/Fix 分支開發結束、準備收尾或準備合併至 main 時觸發此技能。引導 AI 自動執行代碼驗證、文件同步(docs)、PARS開發故事撰寫、測試全綠燈檢查，並生成標準 --no-ff 合併指令與詳細日誌。
---

# 分支收尾與合併標準工作流 (Branch Completion & Merge Workflow Skill) 🚀

本技能定義當本專案任何 Feature / Fix 分支開發結束、準備收尾或準備進行 Merge 時，必須按順序執行的 4 大標準步驟與檢核清單。

---

## 🎯 4 大收尾步驟 (Completion Checklist)

### 步驟 1：最小聚焦單元測試與全套手動提醒 (Focused Test Verification & Manual Full Suite Prompt)
- **原則**：AI 僅執行本次分支修改直接相關之最小單元測試檔案或方法，確保改動邏輯通過。
- **全套測試提醒**：AI 嚴禁自行執行耗時的全套測試 (`.venv\Scripts\python -m unittest discover tests`)。在完成分支收尾與報告時，AI 必須主動生成全套測試指令，提醒使用者手動執行並回報任何剩餘失敗。

### 步驟 2：文件收斂、契約升格與開發故事同步 (Contract Archival, Docs & PARS)
分支開發若涉及新增規則、架構重構或在 `docs/todos/` 建立了開發規格，應於收尾時執行文件收斂：
1. **觸發 `canonical_contract_archival` 前置交互守則**：
   - ⚠️ **嚴禁 AI 自行決定清理範圍**：AI 絕對禁止自行挑選檔案擅自執行文件收斂或刪除。
   - **顯式提問機制**：AI 必須先盤點本次分支修改或產生的 Spec/TODO 候選清單，主動向使用者提問：
     > 「請問本次分支要收斂與清理的文件清單是否為以下項目？是否有遺漏、或是否有不可清理/不可刪除的 TODO？」
   - **必須等待使用者顯式確認或提供最終清單後**，方可調用 `canonical_contract_archival` 執行建立 Canonical Contract、搬遷 TODO/RFC 與刪除過期 spec。
2. **依標準分類提煉**：
   - 永久約束不變量 ➔ 升格至 `docs/features/<domain>/` 或 `docs/architecture/`。
   - 未完成工作 ➔ 搬遷至獨立 `docs/todos/<task>_rfc.md`。
   - 原始完成 spec ➔ 依「刪除是預設；封存是例外 (Default to DELETE, Archive as EXCEPTION)」原則果斷清理，防止 Doc Drift。
3. **撰寫 PARS 框架開發故事**：依據 `AGENTS.md` 第 3 條規範，於 `docs/storys/` 建立包含 Purpose, Action, Result, So What, Influence 的 PARS 文檔。
4. **領域特定文檔同步**：
   - 懸賞對照規則：若改動 `QuestMapper`，同步更新 [docs/daily_task/quest_mapping_rules_report.md](../../../docs/features/daily_task/quest_mapping_rules_report.md)。
   - 體力退避與狀態機：若改動退避邏輯，更新 [docs/stamina_retreat_feature.md](../../../docs/features/stamina_retreat_feature.md)。
   - 背包與品質：若改動裝備銷毀與分解品質，更新 [docs/bag_color_classification.md](../../../docs/features/bag_color_classification.md)。

### 步驟 3：分支變更比對與統計 (Branch Diff Audit)
進行分支差異分析以彙整異動細節：
- **比對指令**：
  ```bash
  git log main..HEAD --oneline
  git diff main..HEAD --stat
  ```
- **檢核重點**：統計 Commit 總數、修改檔案總數、新增/刪除行數，並按子模組分類整理（如酒館、血之祭壇、懸賞任務、背包整理、狀態機防呆等）。

### 步驟 4：生成 --no-ff 合併指令與結構化 Merge Commit 日誌 (Merge Generation)
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
- ⚠️ **分支合併限制**：AI 絕對禁止自行執行 `git merge`，必須提供編排好的 `git merge --no-ff ...` 指令給使用者，或待使用者明確指示「可以進行 merge」後方可執行。
