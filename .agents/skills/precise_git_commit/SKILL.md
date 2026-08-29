---
name: precise_git_commit
description: 規範 AI 在執行 Git 提交時必須嚴格精確指定本次任務修改的檔案，嚴禁盲目使用 git add . 或 git add -A，防止誤提交非本次任務修改之檔案或使用者未完成的代碼。
---

# 精確 Git 提交範疇規範 (Precise Git Commit Scope Skill) 🎯

本技能定義 AI 協同開發人員在任何代碼修改、修復或功能開發收尾進行 Git 提交時，必須遵守的**檔案精確 Stage 與 Commit 規範**。

---

## 核心原則 💡

1. **嚴禁全域 Stage（Zero Tolerance for Bulk Add）**：
   - 🚫 **絕對禁止** 執行 `git add .`、`git add -A` 或 `git add --all`。
   - 任何提交前，必須先執行 `git status` 與 `git diff` 審查變更清單。

2. **精確白名單 Stage（Explicit Whitelist Only）**：
   - ✅ 僅能以明確、具體的檔案路徑執行 `git add <file1> <file2> ...`。
   - **判定標準**：唯有「本次任務中由 AI 依據需求或修復目的明確修改/新增的檔案」才可被加入暫存區（Staged）。
   - **非本次修改檔案絕不 Stage**：使用者進行中的實驗代碼、無關的暫存檔、未經請求的其他模組修改，一律保留在 Working Tree，嚴禁誤打包進 Commit。

3. **雙重審核確認流程（Pre-Commit Status Verification）**：
   - Stage 後必須再次執行 `git status`，確認 `Changes to be committed:` 列表中的檔案 100% 均屬於本次任務範疇，且 `Changes not staged for commit:` 中無誤入項目。

---

## 標準操作流程 🛠️

### 步驟 1：審查工作區狀態
```powershell
git status
```
檢視哪些檔案為本次任務所修改，哪些為使用者未提交的工作區檔案。

### 步驟 2：精確 Stage 指定檔案
```powershell
git add path/to/exact_file1.py path/to/exact_file2.py
```

### 步驟 3：二次核對 Staged 清單
```powershell
git status --short
```
確認綠色（`A` / `M`）僅包含本次任務的檔案。

### 步驟 4：執行標準 Angular Commit
依據 `AGENTS.md` 跨平台規範使用多個 `-m` 參數提交：
```powershell
git commit -m "fix(scope): 簡明標題" -m "1. 具體修改點說明。" -m "2. 測試驗證結果。"
```
