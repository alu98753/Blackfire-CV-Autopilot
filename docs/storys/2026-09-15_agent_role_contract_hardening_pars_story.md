# Agent Role Contract Hardening & Transport Boundary PARS Story

## 1. Purpose (背景與問題)

在先前的 AI 驗證閘門（`ai_gate.ps1`）運行中，OpenCode 代理人（`spec-reviewer` 與 `regression-reviewer`）多次出現審查邏輯完全成立且給予 PASS 判定，但 Gate 卻判定為 `INFRASTRUCTURE_BLOCKED` 的問題。

其根本成因為傳輸邊界混淆（Transport Boundary Mismatch）：
- **審查契約意圖**：規範的是模型最後提交的正式審查產物（Final Review Payload），其第一行必須是嚴格的機器可讀標頭（`VERDICT: PASS|BLOCK` 與 `BLOCKING_FINDINGS: <count>`）。
- **舊版閘門實作**：直接將 OpenCode 在終端輸出的「整場人類可讀 transcript」（包含前置中間推理、檔案閱讀進度、思考過渡句等）傳入嚴格驗證器 `Test-ReviewVerdictStructure`。
- **無效的 Prompt 微調循環**：為迎合舊版驗證器「整個 output 字元 0 必須是 V」的要求，開發過程中嘗試了多種負面 Prompt 約束（如「不要輸出前言」、「第一回合/第二回合拆分」等）。然而 LLM 容易產生負向提示效應（Negative Priming），往往在最後交卷時仍輸出簡短轉場語句（例如 "I have read all evidence. Let me finalize."），導致 Gate 持續因格式誤判而阻斷。

---

## 2. Action (關鍵行動與設計決策)

本次改動的核心原則是：**停止針對 LLM 的無效 Prompt 調優，改由系統建立嚴格的傳輸邊界層（Transport Boundary Layer），將「辨識正式答案邊界」與「驗收正式答案合規性」徹底解耦**。

### 2.1 結構化 JSON 傳輸邊界

在 `scripts/ai_gate.ps1` 中，將真實 OpenCode 調用加上 `--standalone --format json`：
- 將代理人執行的中間推理、工具調用（`call`）、工具執行結果（`tool`）與回答（`text`）作為結構化 JSONL 接收。
- 完整原始 JSONL 留存於 `.runtime/ai_gate/<Task>/<agent>.jsonl`，確保黑盒除錯線索完整保留。

### 2.2 三層式有效負載邊界架構 (Three-Layer Payload Architecture)

將驗證管線明確切分為三層責任：

```text
OpenCode JSONL 串流
        ↓
① 提取最終 Assistant 訊息 (Get-FinalAssistantMessageFromStructuredJson)
   - 依據最後一筆 text 事件的 messageID，聚合最後一輪助手的完整輸出。
   - 徹底排除所有前置回合、工具呼叫與中間推理雜訊。
        ↓
② 提取規範審查有效負載 (Get-CanonicalReviewPayload)
   - 僅在已隔離的最終 Assistant 訊息中搜尋開頭行對齊的 VERDICT/BLOCKING_FINDINGS 標頭。
   - 嚴格校驗：僅允許恰好 1 處合法標頭；0 處或多於 1 處皆視為基礎架構異常。
   - 從該唯一標頭索引處切出後續文字，作為 Canonical Review Payload。
        ↓
③ 嚴格機器驗證器 (Test-ReviewVerdictStructure)
   - 保持 \A 錨點，嚴格要求輸入字元 0 必須是 VERDICT 標頭，並校驗語意一致性。
   - 驗證成功後，僅將純淨 Payload 晉升寫入 docs/tasks/<Task>/reviews/*.md。
```

### 2.3 代理人契約與 Prompt 潔淨化

- 移除 `.opencode/agents/spec-reviewer.md` 與 `regression-reviewer.md` 中的實驗性「Turn 1/Turn 2」假性分段、負向提示詞與恐嚇性警示。
- 恢復為清晰、精確的正向格式規範：具備 bounded-blocker-detector 語意、明確 early-stop 機制與 positive output-format 要求。
- 將 `ai_gate.ps1` 的 diff snapshot 產生方式由 `--unified=80` 回復為標準預設 context，消除 reviewer 單次閱讀分頁過長消耗 tool step 預算的問題。

---

## 3. Result (驗證結果與測試數據)

### 3.1 確定性探針 (Deterministic Probes A~G)

實作專用單元探針驗證邊界層行為：
- **Probe A**：最終訊息直接以合法標頭開始 $\rightarrow$ 完整保留，Validator 通過。
- **Probe B**：前置包含對話雜訊但存在合法標頭 $\rightarrow$ 精確自標頭截取，前言徹底消除，Validator 通過。
- **Probe C**：無標頭 $\rightarrow$ Extractor 報錯並阻斷。
- **Probe D**：重複標頭 $\rightarrow$ 識別歧義並阻斷。
- **Probe E**：粗體/Markdown 標頭 $\rightarrow$ 拒絕非正規格式。
- **Probe F**：PASS 搭配非零 blocking $\rightarrow$ Extractor 成功切出，Validator 拒絕。
- **Probe G**：中間工具輸出與思考雜訊 $\rightarrow$ Extractor 僅接收最終訊息，完全不干擾。

### 3.2 雙工作樹全套單元測試與 Formal Gate

1. **正式 AI Gate**：
   - 執行命令：`powershell.exe -File .\scripts\ai_gate.ps1 -Task agent-role-contract-hardening-v1-1`
   - **Exit Code: 0 (PASS)**。
   - `spec-reviewer` 耗時 146.0s，`regression-reviewer` 耗時 82.8s。
   - 產出的 `reviews/spec-review.md` 與 `regression-review.md` 第 1 行皆為嚴格乾淨的 `VERDICT: PASS`，零前言殘留。
2. **全套單元測試 (Unit Test Suite)**：
   - `HEAD BASELINE`：執行 1165 項測試，**100% 通過（0 失敗、0 錯誤、14 略過）**，無任何 regression。

---

## 4. So What (業務價值與架構意義)

本改動的核心價值在於**不再依賴 LLM 的隨機行為來保證 Infrastructure 的穩定性**：
- **驗收標準未放寬**：正式產物的審查標準完全沒有退讓，依然要求第 1 行為嚴格機器標頭；改變的是由系統在傳輸層精確圈定「哪裡才是正式報告」。
- **職責分離**：
  - `.runtime/*.jsonl` 負責完整黑盒軌跡留存，供開發除錯與審計。
  - `reviews/*.md` 負責純淨的 Canonical 契約產物，杜絕對話雜訊晉升進版本庫。
- **大幅縮短除錯耗損**：避免因為模型多輸出一句「我讀完了」就讓長達數分鐘的 Gate 歸零重跑，顯著提升自動化開發工作流的迭代收斂速度。

---

## 5. Influence (權衡與相容性假設)

### 5.1 架構權衡 (Trade-off)

- **複雜度微幅上升**：相較於過去直接將字串餵給正則表達式，現在增加了 JSONL 解析、訊息 ID 聚合與有效負載切片的邏輯。
- **評估判定**：此處新增的解析邏輯均為具備明確契約的傳輸適配層（Transport Adapter），相較於 prompt 試錯的不確定性，代價完全可控且符合工程邊界隔離原則。

### 5.2 執行環境相容性假設 (Compatibility Assumption)

- **現行依據**：在 OpenCode 2.0.3 下，實證顯示 JSONL 串流中最後出現的 assistant `text` 訊息即代表最終結論回覆（Final Assistant Turn）。
- **邊界警示**：此項機制屬於**已驗證之相容性假設 (Verified Compatibility Assumption)，非長效不變量 (Permanent Architecture Invariant)**。未來若 OpenCode 升級（如 2.1+）調整事件結構時，應主動重跑結構化探針進行校準，而非假定其 schema 永不變更。
