# 開發故事：AI 協同驗證閘門與標準工作流程落地 🤖

> 日期：2026-09-14  
> 分支：`feat/ai-verification-gate-v1`  
> 成果契約：[AI Development Workflow](../architecture/ai_development_workflow.md), [Task Management Layout](../tasks/README.md), [Verification Rule](../../.agents/rules/ai-verification-gate.md)  
> 關鍵模組：[scripts/ai_gate.ps1](../../scripts/ai_gate.ps1), [scripts/ai_scout.ps1](../../scripts/ai_scout.ps1), [scripts/bootstrap_opencode.ps1](../../scripts/bootstrap_opencode.ps1), [.opencode/agents/](../../.opencode/agents/)

---

## 1. Purpose (問題脈絡)

在引入外部 AI 代理（如 OpenCode、Claude Code 或其他自動化協同代理）參與程式碼維護與功能實作的過程中，既有開發流程面臨了幾個關鍵挑戰：

1. **缺乏客觀機器驗收標準**：
   - AI 代理在實作完代碼後，往往僅依賴自我描述或非結構化的回應，缺乏由專案本身主導的剛性驗證閘門。
   - 實作前欠缺標準化規格檢驗，實作後欠缺自動化回歸分析，容易引入隱性缺陷或非預期的行為漂移。
2. **多重任務命名空間混淆**：
   - 專案曾並存 `.ai/tasks/` 與 `docs/todos/` 等不同目錄結構，導致任務契約缺乏單一真相源（Single Source of Truth）。
   - 臨時性 TODO 與具備結構化驗證需求的正式 Task Package 邊界模糊。
3. **本機工具鏈安裝與協同環境孤立**：
   - 外部協同代理工具（OpenCode CLI）缺乏統一且具備幂等性的本機安裝與引導腳本，導致環境配置繁瑣且容易因套件名稱更迭產生分歧。

---

## 2. Action (關鍵架構行動)

為建立透明、可重複且受專案本身約束的 AI 協同開發體系，本分支完成了一套標準驗證架構：

1. **確立單一任務真相源（Canonical Task Package Layout）**：
   - 將正式任務契約統一定義於 `docs/tasks/<task-id>/`，並建立 [docs/tasks/README.md](../tasks/README.md) 與 [docs/tasks/BACKLOG.md](../tasks/BACKLOG.md)。
   - 每個任務包以 `task.json` 作為機器可讀的宣告清單（定義任務狀態、聚焦測試清單、相依規格與審查產出路徑），並以 `spec.md` 與 `reviews/` 形成完整驗收閉環。
   - 正式凍結既有 `docs/todos/` 目錄，將其重定義為過渡性與封存待辦專用，消除架構冗餘。
2. **建構三階段 AI 工作流程（Draft ➔ Scout ➔ Final）**：
   - 在 [docs/architecture/ai_development_workflow.md](../architecture/ai_development_workflow.md) 中正式定義生命週期：
     - **Draft**：建立任務初稿與規格骨架。
     - **Scout**：調用專屬偵察代理（`scout`）針對現有程式碼、不變量與架構現況進行唯讀上下文審計，產生 `context-audit.md`。
     - **Final**：整合偵察反饋，由 Reviewer 確認邊界後鎖定實作契約。
   - 嚴格建立「Draft 階段禁止實作」守則，確保未經架構審查前不得動手修改生產程式碼。
3. **自動化驗證腳本與 AST 語法安全保障**：
   - 實作 [scripts/ai_scout.ps1](../../scripts/ai_scout.ps1)：自動化派發偵察任務並產出結構化稽核檔案。
   - 實作 [scripts/ai_gate.ps1](../../scripts/ai_gate.ps1)：作為 Merge 前的硬性自動化閘門，自動化檢驗 task package 完整性、呼叫 OpenCode 執行 `spec-reviewer` 與 `regression-reviewer` 獨立代理審查、自動執行聚焦測試並生成 `evidence.md`。
   - 完成 PowerShell AST 解析器驗證，解決字串引號轉義導致的解析異常，確保在 Windows 原生環境中高可靠執行。
4. **本機 OpenCode 引導與角色規範**：
   - 建立 [scripts/bootstrap_opencode.ps1](../../scripts/bootstrap_opencode.ps1)，使用官方 `opencode-ai` npm 套件進行本機安裝檢測與版本核驗。
   - 建立 `.opencode/agents/` 專屬角色提示檔案（`scout.md`、`spec-reviewer.md`、`regression-reviewer.md`），並於 [.agents/rules/ai-verification-gate.md](../../.agents/rules/ai-verification-gate.md) 確立協同代理人的行為準則。

---

## 3. Result (驗證結果)

1. **腳本安全性與 Smoke Verification**：
   - `docs/tasks/README.md` 存在且正確解析，`.ai/tasks` 目錄已完全清除。
   - `scripts/ai_scout.ps1 -Task no-such-task` 與 `scripts/ai_gate.ps1 -Task no-such-task -SkipTests` 均能在目標任務不存在時，以客觀訊息安全中斷並退出（exit code 1），無任何未捕獲例外或語法解析錯誤。
   - `scripts/bootstrap_opencode.ps1` 與 `opencode --version` 驗證成功（`opencode v2.0.3`）。
2. **全套測試迴歸驗證**：
   - 本地全套測試（1165 測項）執行結果：
     ```text
     Ran 1165 tests in 240.992s
     OK (skipped=14)
     ```
   - 與 Main Baseline 比對，Genuine Regression 數量為 0。
3. **代碼與文件潔淨度**：
   - 產出檔案均符合客觀敘事與確定性約束，無情緒化修飾，標準相對超連結正確對齊。

---

## 4. Side Effects & Next Steps (後續規劃)

1. **試點任務選定**：
   - 依據工作流程規劃，首個試點項目為 `intent-routing-observability`（因其變更範疇小、不涉及排程政策改變、可獨立驗證日誌契約）。
2. **流程推進**：
   - 本分支收尾完成並合併至 `main` 後，將以本架構為基礎正式啟動後續日常任務與狀態機重構之實作流程。
