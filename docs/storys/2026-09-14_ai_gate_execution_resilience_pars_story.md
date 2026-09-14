# 開發故事：AI Verification Gate 執行有界性、三態分類與交易安全產物防護 ⚡

> 日期：2026-09-14  
> 分支：`refactor/ai-gate-execution-resilience`  
> 成果契約：[AI Development Workflow](../architecture/ai_development_workflow.md), [ai-gate-execution-resilience SPEC](../tasks/ai-gate-execution-resilience/SPEC.md), [ai-gate-execution-resilience EVIDENCE](../tasks/ai-gate-execution-resilience/EVIDENCE.md)  
> 關鍵模組：[scripts/ai_gate.ps1](../../scripts/ai_gate.ps1)

---

## 1. Purpose (問題脈絡)

在先前執行 `scout-efficiency-v1` 任務之驗證階段時，`scripts/ai_gate.ps1` 暴露出嚴重的執行可靠性缺陷：

1. **無界限外部行程執行 (Unbounded Execution)**：
   - 舊版 `ai_gate.ps1` 透過同步阻塞管線（`& opencode @args 2>&1 | Out-String`）執行 Reviewer，且在執行 focused tests 時亦缺乏外部超時包裝。當上游模型提供者延遲、伺服器掛起或陷入深度探索時，審查行程曾卡死達 27 分鐘，只能由人工作業強制中止。
2. **終端觀測性完全缺失 (Lack of Real-time Streaming)**：
   - 阻塞讀取使控制台在 Reviewer 執行期間無任何輸出，開發者無從得知 Reviewer 是否存活或正在檢索哪些檔案。
3. **失敗分類混淆與虛假判斷 (Failure Classification Confusion)**：
   - 舊版僅定義 exit 0（PASS）與 exit 2（BLOCK）。當遭遇行程逾時、非零崩潰或模型輸出畸形時，腳本通常直接拋出未處理例外或非預期終止，無法將候選代碼的語意瑕疵（`CANDIDATE_BLOCKED`）與執行基礎設施問題（`INFRASTRUCTURE_BLOCKED`）精確區分。
4. **產物覆寫與非交易式推廣污染 (Partial Promotion & Dirty Canonical Artifacts)**：
   - 舊版 Reviewer 在執行完成後立即直接寫入 canonical `reviews/*.md`，若後續 Reviewer 或測試遭遇 infrastructure failure，會造成 canonical 目錄混合不同驗證嘗試的產物，損毀有效驗證證據。

---

## 2. Action (關鍵架構行動)

針對上述問題，本分支嚴格落實 Final SPEC，於 [scripts/ai_gate.ps1](../../scripts/ai_gate.ps1) 實作最小且可靠的架構升級：

1. **有界行程執行器 (`Invoke-BoundedProcess`)**：
   - 私有包裝 .NET `System.Diagnostics.Process`，透過 `OutputDataReceived` 與 `ErrorDataReceived` 事件進行多執行緒安全的非同步串流輸出，並即時寫入終端。
   - 主執行緒透過 `Stopwatch` 進行獨立 Wall-clock 逾時輪詢，Reviewer 預設 480 秒、Focused tests 預設 60 秒硬性超時。
   - 超時觸發時發送 `Kill()` 訊號，並以 `$proc.WaitForExit(3000)` 與 `$proc.HasExited` 嚴格檢驗 `KillConfirmed` 狀態。終止操作精確鎖定 Client PID，絕不波及背景守護的 `opencode serve`。
2. **明確的三態退出分類 (0 / 1 / 2 Exit Semantics)**：
   - **Exit 0 (`PASS`)**：雙 Reviewer 皆通過且 focused tests 全數綠燈。
   - **Exit 1 (`INFRASTRUCTURE_BLOCKED`)**：包含 Reviewer/Test 超時、非零崩潰、Reviewer 輸出缺少正規標頭（`MALFORMED`）、以及檔案推廣失敗。
   - **Exit 2 (`CANDIDATE_BLOCKED`)**：代碼本身問題，包含任一 Reviewer 判定 `VERDICT: BLOCK`（且 `BLOCKING_FINDINGS >= 1`），或 focused tests 執行失敗（非零退出）。
3. **閘門層級候選暫存與交易安全推廣 (Transaction-Safe Promotion & Rollback)**：
   - Reviewer 報告與 `EVIDENCE.md` 產出時一律先寫入 `.runtime/ai_gate/<task-id>/` 之 `candidate_*.md` 暫存檔。
   - 僅當所有 Reviewer 與 Focused tests 完成且未觸發 `INFRASTRUCTURE_BLOCKED` 時，才啟動推廣交易。
   - 推廣前自動將既有存在之 canonical artifacts 備份至 `.runtime/ai_gate/<task-id>/canonical_backup/`。
   - 推廣過程中若任一步驟失敗，獨立 try/catch 遍歷所有推廣目標，強制 rollback 至 pre-gate 狀態；若 rollback 過程出現異常，於警告中列出詳細失敗項，維持 Exit 1。
4. **非 Python 異動測試豁免**：
   - 本次異動完全集中於 PowerShell 閘門與任務規格，不包含任何 Python 執行期與測試代碼，依收尾規範核准跳過 Python 雙樹全套迴歸測試，專注於專屬探針與 Self-hosting 實機驗證。

---

## 3. Result (驗證結果)

1. **11 項確定性探針 (Deterministic Probes) 100% 通過**：
   - **Probe 1 (Reviewer Success + Promotion + Test Pass)**：Exit 0，產物成功推廣。
   - **Probe 2 (Reviewer Semantic BLOCK)**：Exit 2，產物推廣並記錄 BLOCK 證據。
   - **Probe 3 (Reviewer Silent Timeout & KillConfirmed)**：Exit 1，PID 終止確認，既有產物 100% 保留。
   - **Probe 4 (Reviewer Non-Zero Exit)**：Exit 1，既有產物完好保留。
   - **Probe 5 (Reviewer Malformed Output)**：缺少 `VERDICT` 標頭即時攔截，Exit 1，產物保留。
   - **Probe 6 (Focused Test Failure)**：Exit 2，記錄 FAIL 證據。
   - **Probe 7 (Focused Test Timeout & KillConfirmed)**：Exit 1，PID 終止確認。
   - **Probe 8 (PSEventJob Leak Check)**：工作階段殘留背景事件工作數為 0。
   - **Probe 9 (Persistent Server Status)**：常駐 `opencode serve`（PID 21508）全程存活不受影響。
   - **Probe 10 (Cross-Review Atomicity)**：Reviewer 1 通過但 Reviewer 2 超時，既有 canonical 產物無任何混合污染，全部保持原樣，Exit 1。
   - **Probe 11 (Promotion Rollback)**：模擬第二個檔案寫入後拋出推廣失敗，成功將所有檔案完全 rollback 至舊 sentinel，Exit 1。
2. **真實環境 Self-Hosting 多模型驗證**：
   - **`opencode/nemotron-3.5-lightning-free`**：實測停留於檢索，剛好滿 480 秒準時觸發 hard timeout 終止，成功驗證超時邊界與 PID 清理。
   - **`opencode/ling-3.0-flash-fin-free`**：上游回傳 Invalid API key，即時分類為 `INFRASTRUCTURE_BLOCKED`（Exit 1），既有有效產物完好未受污染。
   - **`opencode/mimo-v2.5-free`**：雙 Reviewer（Spec 與 Regression）依序在約 5 分鐘內收斂，百分之百遵循 `VERDICT: PASS` 與 `BLOCKING_FINDINGS: 0` 標頭契約，完整通過驗證並原子推廣產出 [EVIDENCE.md](../tasks/ai-gate-execution-resilience/EVIDENCE.md)。

---

## 4. Standard / Learning (標準收斂與經驗反思)

1. **外部 Agent 調用必須一律有界 (Bounded-by-Default)**：
   - 不論模型號稱多快，只要涉及多步驟 tool use，就存在模型陷入發散迴圈或服務端卡死的機率。任何包裝外部進程的工具必須在底層提供硬性超時與確實驗證退出的防護網。
2. **失敗分類直接決定工程決策**：
   - 將 Infrastructure failure 與 Candidate failure 拆分後，CI/CD 與開發者可明確區分「需要重試執行」或「需要修改代碼」，大幅降低除錯成本。
3. **推廣交易安全是多階段審查的基石**：
   - 「先暫存、全數無誤再推廣、推廣失敗全數復原」的模式徹底解決了審查產物歷史被髒數據污染的風險。
