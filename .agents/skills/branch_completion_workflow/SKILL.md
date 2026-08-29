---
name: branch_completion_workflow
description: 當一個 Feature/Fix 分支開發結束、準備收尾或準備合併至 main 時觸發此技能。引導 AI 自動執行代碼驗證、文件同步(docs)、PARS開發故事撰寫、測試全綠燈檢查，並生成標準 --no-ff 合併指令與詳細日誌。
---

# 分支收尾與合併標準工作流 (Branch Completion & Merge Workflow Skill) 🚀

本技能定義當本專案任何 Feature / Fix 分支開發結束、準備收尾或準備進行 Merge 時，必須按順序執行的 4 大標準步驟與檢核清單。

---

## 🎯 4 大收尾步驟 (Completion Checklist)

### 步驟 1：全域單元測試與驗證 (Full Test Verification)
- **原則**：任何分支在收尾前，必須執行全套單元測試，確保全域無 Regression。
- **執行指令**：
  ```bash
  .venv\Scripts\python -m unittest discover tests
  ```
- **檢核標準**：測試結果必須呈現 `OK` 且 100% 通過。若有任何失敗，須依據 `AGENTS.md` 第 6 條測試規範精確修復至全綠。

### 步驟 2：技術文檔與故事同步 (Docs & PARS Story Sync)
分支開發過程中若有涉及配置、規則、架構或新增功能的改動，必須審查並更新 `docs/` 下的技術文檔：
1. **懸賞對照規則**：若改動 `QuestMapper`，必須同步更新 [docs/daily_task/quest_mapping_rules_report.md](../../../docs/features/daily_task/quest_mapping_rules_report.md)。
2. **體力退避與狀態機**：若改動退避或 `has_available_dungeon` 邏輯，更新 [docs/stamina_retreat_feature.md](../../../docs/features/stamina_retreat_feature.md)。
3. **背包與品質**：若改動裝備銷毀與分解品質，更新 [docs/bag_color_classification.md](../../../docs/features/bag_color_classification.md)。
4. **撰寫 PARS 框架開發故事**：依據 `AGENTS.md` 第 3 條規範，於 `docs/storys/` 建立包含以下 5 項要素的 PARS Markdown 文檔：
   - **Purpose (目的)**: 描述需求或痛點。
   - **Action (行動)**: 具體改進措施與細節。
   - **Result (結果)**: 成效與測試驗證結果。
   - **So What (核心價值)**: 提煉出最核心的工程價值。
   - **Influence (影響)**: 對後續架構與其他模組的借鑑。

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
