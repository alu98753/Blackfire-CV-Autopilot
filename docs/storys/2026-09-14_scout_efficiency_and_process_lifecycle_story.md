# 開發故事：Scout 執行效能、非同步輸出串流與有界行程生命週期收斂 ⚡

> 日期：2026-09-14  
> 分支：`refactor/scout-efficiency-v1`  
> 成果契約：[AI Development Workflow](../architecture/ai_development_workflow.md), [scout-efficiency-v1 SPEC](../tasks/scout-efficiency-v1/SPEC.md), [scout-efficiency-v1 CONTEXT](../tasks/scout-efficiency-v1/CONTEXT.md)  
> 關鍵模組：[scripts/ai_scout.ps1](../../scripts/ai_scout.ps1), [.opencode/agents/scout.md](../../.opencode/agents/scout.md)

---

## 1. Purpose (問題脈絡)

在執行 `scout-efficiency-v1` 任務之初，針對既有 `scripts/ai_scout.ps1` 進行實測觀察，發現協同代理人在 Scout 階段存在顯著的可靠性與觀測性缺陷：

1. **無界限執行時間與預算超限**：
   - 預設 Scout 代理人在缺乏明確檔案檢索上限時，容易在大型專案中盲目展開全面性稽核，導致單次執行時間遠超可接受之 8 分鐘上限（實測觀察超過 8 分鐘仍未完成）。
2. **終端觀測性完全缺失 (Lack of Streaming)**：
   - 原先腳本內部或管線中若使用 `Out-String` 或同步阻塞讀取，會導致子程序在執行期間無法即時將 stdout/stderr 輸出至終端機，使用者無從得知 Scout 目前進度，造成「假死」疑惑。
3. **靜默無輸出下的超時機制失效風險**：
   - 若採用同步 `StandardOutput.Peek()` / `ReadLine()` 進行輪詢，當子行程存活但長時期無任何 stream 輸出時，`Peek()` 本身可能造成呼叫端執行緒阻塞，使主迴圈無法回到計時器判定，導致 hard timeout 機制在最關鍵的 hung/silent child 情境下失效。
4. **行程殘留與事件工作累積**：
   - 超時強制 kill 後若未確認退出狀態即進行清理，可能誤報終止成功；在 PowerShell 中註冊的 `Register-ObjectEvent` 若未主動清理其產生的背景 `PSEventJob`，會在長生命週期的 PowerShell session 中持續累積。

---

## 2. Action (關鍵架構行動)

針對上述問題，本分支嚴格依據 Final SPEC 實作最小且可靠的架構修正：

1. **非同步行程輸出與執行緒安全設計 (Async Streams & Thread Safety)**：
   - 在 [scripts/ai_scout.ps1](../../scripts/ai_scout.ps1) 中移除所有同步 `Peek()` 與 `ReadLine()` polling。
   - 改用 .NET `System.Diagnostics.Process` 的 `OutputDataReceived` 與 `ErrorDataReceived` 事件監聽，並呼叫 `BeginOutputReadLine()` 與 `BeginErrorReadLine()`。
   - 所有事件回調在寫入捕獲串列時，統一透過 `[System.Threading.Monitor]` 互斥鎖保證多執行緒安全。
2. **主執行緒獨立 Wall-Clock 超時控制與退出核驗**：
   - 超時判定完全保留在主執行緒，透過短週期 `WaitForExit(50)` 輪詢迴圈與 `Stopwatch` 進行檢查，完全不依賴子行程的串流活躍度。
   - 當觸發超時時，向子程序發送 `Kill()` 訊號，並透過 `$proc.WaitForExit(3000)` 與 `$proc.HasExited` 明確核驗子行程是否確實退出；若無法確認則明確回報 `termination failure`，禁止偽稱 PID 已 terminated。
   - 確保終止操作僅作用於 client PID，絕不影響背景常駐的 `opencode serve` 守護行程。
3. **全生命週期資源清理 (Event & Job Cleanup)**：
   - 在 `finally` 區塊中除了調用 `Unregister-Event` 註銷事件來源外，同時使用 `Get-Job -Name ... | Remove-Job -Force` 徹底移除 `Register-ObjectEvent` 所產生的 `PSEventJob`，防止工作區 session 資源洩漏。
4. **原子推廣與防覆寫保護 (Atomic Promotion)**：
   - 子程序產出先寫入暫存候選檔案，必須同時滿足「Exit code == 0」、「未超時」、「非空輸出」且「具備 `# Scout Context` 結構」四項條件，方能透過原子操作推廣至 canonical `CONTEXT.md`。
   - 若發生超時、非零 exit code 或驗證失敗，既有 canonical `CONTEXT.md` 100% 保持原樣不被覆寫。
5. **軟性檔案預算約束 (Soft File Budget)**：
   - 在 [.opencode/agents/scout.md](../../.opencode/agents/scout.md) 與調用 Prompt 中確立軟性邊界：限定至多檢視 10 個直接相關檔案，報告規模控制在 1500 字以內，達標即停並記錄不確定性。

---

## 3. Result (驗證結果)

1. **確定性探針驗證 (Deterministic Probes)**：
   - **Silent Child Timeout**：完全靜默之子行程在 2s 超時後被強制終止（耗時 2822ms），確認退出並安全保留原始 `CONTEXT.md`。
   - **Streaming Output**：子程序分段輸出即時呈現於終端機，無緩衝延遲（耗時 3060ms）。
   - **Success + Promotion**：結構驗證與隨機 Token 檢查通過，原子推廣至 `CONTEXT.md`。
   - **Non-zero Exit Protection**：子程序 exit code 42 失敗，既有哨兵內容完整保留未被覆寫。
   - **Timeout Overwrite Protection**：超時情境下哨兵內容確認 100% 保留。
   - **Event Jobs Cleanup**：確認 session 中殘留 `PSEventJob` 數量為 0。
   - **Persistent Server Status**：背景常駐 `opencode serve --service` (PID 21508) 全程存活且不受任何影響。
2. **全套測試雙工作樹迴歸驗證 (Full Test Baseline)**：
   - **HEAD Baseline** (`refactor/scout-efficiency-v1`)：1165 測試全數通過（1151 passed, 0 failures, 0 errors, 14 skipped，耗時 237.359s）。
   - **Main Baseline** (`temp-main`)：1161 測試（1144 passed, 1 failure, 1 error, 15 skipped）。
   - **迴歸分類判定**：`BRANCH_REGRESSION = 0`，本分支無任何引入迴歸。

---

## 4. Influence & Architecture Invariant (影響與架構不變量)

1. **子程序管線可靠性模型**：
   - 確立 PowerShell 呼叫外部協同 AI 代理時的標準範式：主執行緒獨立計時 + 非同步串流收集 + 互斥鎖安全 + 明確退出核驗 + 雙重資源清理。
2. **Scout 任務定位界限**：
   - Scout 代理人定位確立為「輕量任務局部化定位工具」，而非全庫漫遊審計者，有效防範長延遲與 token 浪費。
