---
name: canonical_contract_archival
description: 當 Feature/Fix/Spec/TODO 已完成，準備把已驗證且應長期約束未來開發的內容提煉成 canonical contract、避免文件漂移、並清理舊 spec / future work 時使用。適用於 merge 前後的文件收斂；不負責功能重構或建立新框架。
---

# Canonical Contract Archival

## 目的

把「完成一次任務的開發文件」收斂成「未來開發者應遵守的長期標準」。

**Canonical contract（權威契約）**：只針對一個明確 concern，記錄未來修改仍必須維持的行為、不變量、責任邊界與禁止事項。  
它不是目前 code 的逐行說明，也不是歷史開發日記。

## 先建立 Source of Truth 邊界

不要宣稱一份文件是全專案唯一真相。不同問題有不同權威來源：

| 問題 | 權威來源 |
| --- | --- |
| 未來「應該」遵守什麼行為／架構約束 | Canonical Contract (`docs/architecture/` 或 `docs/features/`) |
| 現在「實際怎麼做」、精確參數／模板／資料結構 | Production code / config |
| 關鍵行為是否仍被自動驗證 | Focused behavior / contract tests |
| 當初為什麼做這個決策、取捨與歷史過程 | ADR / PARS story (`docs/storys/`) / archived spec |
| 還沒做、尚待決定的工作 | TODO / RFC |

> [!CRITICAL]
> **【PARS 開發故事定性禁令：非架構文件，不可當作證據】**
> - **PARS 開發故事 (`docs/storys/`) 僅為開發歷程的敘事故事 (Narrative Log)**：記錄當時問題脈絡、執行的修復行動與除錯統計，供團隊複盤回溯。
> - **PARS 故事不是架構規範，絕不可作為未來開發或架構設計的依據或證據**。
> - **嚴禁以「PARS 已記載」為由略過契約升格**：Spec 中只要含有「行為不變量、排程階梯、責任邊界、禁止模式」，**必須且只能**提煉升格至 `docs/architecture/` 或 `docs/features/<domain>/` 的 Canonical Contract。若未完成升格，原始 Spec 絕不可視為「已被承接」，更嚴禁直接刪除！

Tests 是 **executable verification**，不是天然的絕對 SSOT；測試也可能不完整或寫錯。

## 升格為 Canonical Contract 的門檻

一條內容只有在下列問題大致都回答「是」時才升格：

1. **已落地**：目前 production behavior 已實作，不只是提案。
2. **有證據**：有直接相關測試、可觀察行為或其他驗證支持。
3. **未來仍要成立**：重構內部實作後，這條規則仍應保留。
4. **違反它算 regression**：不是單純換一個等價實作方式。
5. **屬於行為／邊界／ownership**：不是 private helper、暫時檔名或某次 debugging 細節。
6. **範圍清楚**：知道此契約約束誰、不約束誰。

任何一項不確定時，**不要自行把它宣告成永久標準**；先保留為現況說明、TODO 或待決策項。

## 如何分類完成 Spec 的內容

### 放進 Contract

優先提煉：

- 穩定的不變量（Invariant）
- Observable behavior / failure semantics
- 唯一 owner 與跨模組責任邊界
- Dispatch / completion / recovery 等重要語意
- 必須保留的 acceptance criteria
- 明確禁止的捷徑與 anti-pattern
- 對未來相容性真正有約束力的資料契約

### 只連結，不重複抄寫

通常不要在 Contract 複製：

- private function / class 的實作流程
- 行號
- 完整 template 清單
- calibration threshold / timeout / magic value
- config 的目前預設值
- 內部資料結構細節

若某個數值本身就是刻意承諾的安全／相容性要求，才可成為契約；否則以 code/config 為精確來源，Contract 只描述語意並連到 owner。

### 移出 Contract

- 問題發生經過、root cause、commit 統計 → PARS story / archived spec
- rejected alternatives 與重大架構取捨 → ADR 或歷史設計文件
- 尚未實作的 refactor → TODO / RFC
- 測試數量、commit SHA、一次性的 debug artifact → 歷史紀錄
- 已過時或與新 contract 重複的說明 → 刪除或標註 superseded

## 工作流程

1. **讀完整上下文並核對實作 (Read Context & Verify against Implementation)**
   - 盤點本次分支涉及的 Spec / TODO / RFC。
      - 原始 spec / TODO
      - 對應 production code / config
      - 直接相關 focused tests
      - 上位 architecture / contract
      - 必要時查看 branch diff，確認哪些確實已交付
   - 審視其提出的架構假設、職責邊界與後置條件。
   - **以當前 Production 代碼與測試實作為唯一定本標準 (Implementation as Ground Truth)**：逐一核驗該不變量是否與實際代碼行為 100% 一致，嚴禁將初期過時假設或未落地的設計寫入 Contract。

2. **五分流分類與實作仲裁 (Five-Bucket Classification & Arbitration)**
   依據上述規範，將 Spec 與文件內容逐項對照當前代碼實作進行結構化分類：
   - `PROMOTE`：長效架構不變量 (Invariants)、職責邊界、後置條件驗證契約、異常自癒機制，升格至 Canonical Contract（`docs/architecture/` 或 `docs/features/`）。
   - `LINK`：程式碼、常數與測試已有具體實作者，Contract 僅做參照，不複製貼上代碼細節。
   - `HISTORY`：歷史脈絡留給 PARS 與 Git。
   - `TODO`：尚未完成的工作或後續規劃，搬遷至獨立 `docs/todos/<task>_rfc.md` 或保留於未完成 TODO 清單。
   - `DROP`：過期或重複內容，提煉後預設刪除；暫存測試日誌檔（`*.log`）亦於收尾時一併徹底清理刪除。

   **仲裁與升格執行**：
   - **遇矛盾以實作為準**：spec、code、tests 衝突時，以目前 executable behavior 為準，不得盲目複製未落地的提案。
   - **建立／更新 Contract 規範**：針對 `PROMOTE` 項目主動建立或更新 Contract。Contract 優先保持短、穩定、可掃讀，建議只含：
     - Status / Scope / Document responsibility
     - Canonical invariants
     - Ownership / boundaries
     - Observable behavior / evidence semantics
     - Acceptance criteria
     - 明確不採用的捷徑 / Non-goals
     - Executable verification links
     - Change / supersession rule
   - **若有 PROMOTE 項目**：主動更新/建立對應的 Canonical Contract（`docs/architecture/` 或 `docs/features/`），並同步更新 `future_work.md` 中指向舊 spec 的超連結與狀態。
   - **若無 PROMOTE 項目**（或已完整涵蓋）：確認無遺漏後記錄「經審查無新增長效不變量」。

3. **顯式確認清理範圍 (Mandatory User Scope Confirmation)**
   > [!CRITICAL]
   > **嚴禁 AI 自行決定清理範圍**：完成契約升格與實作核對後，AI 必須停下來向使用者顯式呈報：
   > 1. 【已升格更新之 Canonical Contract 清單與章節】（或說明經核對無需更新）；
   > 2. 【已萃取完畢、建請刪除 (DROP) 的過期 Spec 清單與暫存測試日誌 (`*.log`)】（遵循「刪除是預設；封存是例外」原則）；
   > 3. 【仍未完成需保留 (RETAIN) 的 TODO 清單】。
   > **經使用者明確確認同意後，方可執行檔案刪除 (`git rm`)**。

4. **退休原始 Spec：刪除是預設；封存是例外 (Default to DELETE, Archive as EXCEPTION)**
   - **核心理念**：完成的任務 Spec 通常由三部分組成：
     ```text
     已成立的規則 ───────> Canonical Contract (長期約束)
     尚未完成的工作 ─────> 獨立 TODO / RFC (後續排期)
     開發過程/commit/測試 ─> PARS 開發故事 / Git log (歷史留存)
     ```
     當這三者都已經有正式去處時，原始 Spec 只剩下重複資訊；保留過期的完成 Spec 反而會造成嚴重的 **Doc Drift**！
   - **黃金決策原則**：
     > **Default to delete completed task specs after their durable knowledge has been promoted or relocated. Archive only when the original document itself retains unique historical/design value not adequately preserved by ADR, PARS, or Git history.**
   - **決策分流**：
     ```text
     原始完成 Spec
     │
     ├─ 還包含無法在其他地方保存的獨特歷史／設計演進價值？
     │      └─ YES ──> ARCHIVED / SUPERSEDED (標註後封存)
     │
     └─ 不變量已升格至 Contract、未完成事項已移至 TODO、歷史過程已留存於 PARS/Git？
            └─ YES (預設 Default) ──> DELETE (果斷刪除，不留過期副本)
     ```

6. **同步索引與相關文件**
   - 更新 `future_work.md` / TODO index / architecture links。
   - 若此次只是 docs-only，依專案既有測試政策處理，不自行擴大 runtime 工作範圍。

## 防止 Doc Drift

- Contract 描述「不可改歪的語意」，不要描述「今天剛好怎麼實作」。
- 測試以 public / observable behavior 為主，不綁 private implementation。
- 行為或架構契約若被**刻意改變**，code + tests + contract 應在同一 branch / PR 同步修改。
- 重大決策理由改變時，新增或 supersede ADR；不要偷偷改寫歷史理由。
- Agent skill 本身只定義工作流程；專案實際標準應連到 canonical contract，而不是複製一份進 skill。

## 快速判斷句

問自己：

> 「如果六個月後把底層實作整個 refactor，但外部語意不變，這句話還必須成立嗎？」

- **是** → 很可能是 Contract 候選。
- **否，只是目前實作方式** → 留在 code/config 或歷史文件。
- **還沒做／還沒決定** → TODO / RFC。

## Lobby Scene Spec 的示範分類

可升格的方向：
- Active scene 必須有足夠正向 evidence，不能只因相似模板達 threshold 就猜中。
- 多候選無法可靠消歧時必須採保守結果，不盲猜。
- 已確認 Lobby 時，navigation 不得把 Town door 當合法 Lobby routing action。
- `SceneId` 是 canonical scene identity；領域 scene contract 不依賴 CV engine。
- 驗收條件與「明確不採用的捷徑」應保留。

通常不要永久凍結：
- `0.02 / 0.05 / 0.88` 等目前 calibration 數值，除非已明確決定它本身就是契約。
- 10 張 template 的完整檔名清單。
- 某次 commit SHA、測試通過數量。
- `SceneType = SceneId` 這類遷移期 compatibility mechanism。
- 尚未完成的「徹底移除 SceneType」工作；它應留在 TODO / RFC。
