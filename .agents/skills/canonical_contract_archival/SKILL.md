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
| 未來「應該」遵守什麼行為／架構約束 (SHOULD behavior) | Canonical Contract (`docs/architecture/` 或 `docs/features/`) |
| 現在「實際怎麼做」、精確參數／模板／資料結構 (AS-IS behavior) | Production code / config |
| 關鍵行為是否仍被自動驗證 | Focused behavior / contract tests |
| 當初為什麼做這個決策、取捨與歷史過程 | ADR / PARS story (`docs/storys/`) / archived spec |
| 還沒做、尚待決定的工作 | TODO / RFC |

> [!IMPORTANT]
> **【AS-IS 與 SHOULD 的本質區別】**
> - **Production code 是 AS-IS behavior 的主要證據，但不是 SHOULD behavior 的自動權威來源**。
> - **Canonical invariant 必須是**：`implemented + verified + intentionally designed + refactor-stable`。
> - **衝突處理守則**：若 existing canonical contract、accepted design intent、production code、tests 或 runtime evidence 發生實質衝突，**不得自動 PROMOTE**，必須分類為 **`CONFLICT_REQUIRES_REVIEW`** 並向使用者確認。
> - **禁止將可能的 bug、偶然 implementation behavior 或錯誤測試直接制度化為 Contract**。

> [!CRITICAL]
> **【PARS 開發故事定性禁令：非架構文件，不可當作證據】**
> - **PARS 開發故事 (`docs/storys/`) 僅為開發歷程的敘事故事 (Narrative Log)**：記錄當時問題脈絡、執行的修復行動與除錯統計，供團隊複盤回溯。
> - **PARS 故事不是架構規範，絕不可作為未來開發或架構設計的依據或證據**。
> - **嚴禁以「PARS 已記載」為由略過契約升格**：Spec 中只要含有「行為不變量、排程階梯、責任邊界、禁止模式」，**必須且只能**提煉升格至 `docs/architecture/` 或 `docs/features/<domain>/` 的 Canonical Contract。若未完成升格，原始 Spec 絕不可視為「已被承接」，更嚴禁直接刪除！

Tests 是 **executable verification**，不是天然的絕對 SSOT；測試也可能不完整或寫錯。

## 語意分層架構 (Semantic Layer Classification)

在評估任何 Candidate 之前，必須先進行**語意分層分類**：

| 語意層級 (Semantic Layer) | 定義與範疇 | 處理動作 |
| --- | --- | --- |
| **`ARCHITECTURE_INVARIANT`** | 跨領域、全系統層級不可妥協的長效設計原則與行為不變量（如 Click ≠ Completion、Bounded Retry、Recovery 不得偽裝進度、決策 evidence 與診斷 evidence 分離）。 | **可 PROMOTE** 進入 Canonical Contract |
| **`DOMAIN_CONTRACT`** | 特定業務領域中由需求與遊戲領域規則決定的持久行為契約（如 懸賞看板目標/干擾/未確認四分類語意、背包排他判定需專屬正交特徵）。 | **可 PROMOTE** 進入 Canonical Contract |
| **`RUNTIME_POLICY`** | 執行時期的調校政策、逾時上限、重試預算、冷卻等待與退避時間（如 2.5s、重試 3 次、退避 180s）。可依環境動態調整，非永恆真理。 | **禁止 PROMOTE**。留在 Config / Code / Docstring |
| **`IMPLEMENTATION_DETAIL`** | 具體函式/類別名稱、ROI 局部座標、模板圖片檔名、狀態機私有 phase 名稱、內部資料結構細節。 | **禁止 PROMOTE**。僅做 LINK，不寫入規範 |
| **`DIAGNOSTIC_DETAIL`** | 因果診斷標籤（如 `SUSPECTED_TARGET_OVERLAY`）、debug artifact 輸出格式、除錯日誌層級。 | **禁止 PROMOTE**。留在 Code / History / Test |
| **`HISTORY`** | 問題發生經過、root cause、commit SHA、測試數量、除錯過程。 | **移至 PARS / ADR / Git** |
| **`TODO`** | 尚未實作的重構、未來擴充、待定決策。 | **移至獨立 TODO / RFC** |

> [!WARNING]
> **只有 `ARCHITECTURE_INVARIANT` 與 `DOMAIN_CONTRACT` 允許進入 Canonical Contract 的規範性章節 (Normative Section)**。其他內容一律降級或移出！

## 強制 Invariant 語意壓縮 (Invariant Compression)

任何被標記為 `PROMOTE` 的 Candidate，**必須從具體實作改寫為最小穩定語意**。

### 🚫 Normative Invariant 絕對禁止清單
Canonical Invariant 原則上**嚴禁**包含以下 implementation vocabulary：
- timeout / settle 秒數（如 `2.5s`）
- retry / attempt 次數（如 `3 次`）
- cooldown 秒數（如 `180s`）
- similarity / diff threshold（如 `0.90`）
- ROI 絕對/相對像素座標（如 `(800, 200, 300, 100)`）
- template 圖片完整檔名（如 `Disassembly.png`、`tidy.png`，應抽象為「背包專屬排他特徵」）
- private class / function 名稱（如 `_detect_overlay()`）
- debug artifact 檔名（如 `debug_board.png`）
- log tag 或 temporary enum / tag vocabulary（如 `SUSPECTED_TARGET_OVERLAY`、`BOARD_CONFIRMED`）
- implementation algorithm（如特定矩陣比對演算法）
- current default config（如當前預設值）

> [!NOTE]
> **唯一例外**：只有當該數值本身是外部相容性（External Protocol/Safety Requirement），且未來任意修改該數值都應視為 Breaking Change 時，才可例外成為 Normative Invariant。其餘均屬可調 Policy。

## 反事實重構自檢閘門 (Refactor Counterfactual Gate)

每個準備 PROMOTE 的 Candidate，必須逐一通過以下 5 大反事實提問：

1. **Rename**：若底層 class / function / phase 改名，這條規則仍成立嗎？
2. **Policy**：若 timeout / retry budget / config default 改變，這條規則仍成立嗎？
3. **Algorithm**：若 detector / CV 比對演算法被替換，這條規則仍成立嗎？
4. **Telemetry**：若 logging / diagnostic format / tag 被替換，這條規則仍成立嗎？
5. **Structure**：若 FSM 內部狀態機結構或執行順序被重構，這條規則仍成立嗎？

> **若任一問題答案為「否」**，代表該條款尚未充分抽象化，或本質屬於 Policy / Implementation Detail，**嚴禁 PROMOTE**，必須再抽象化或降級！

## 每條 Invariant 必須描述 Allowed Degrees of Freedom

為防止 Canonical Contract 僵化並明確表達「哪些內容不是不變量」，Normative Invariant 統一採用以下標準結構：

```markdown
### Invariant: <語意名稱，如 Bounded Action Retry>

Scope:
<此契約約束的模組或領域，如 Bulletin Board Subflow>

Rule:
<使用 MUST / MUST NOT 描述的核心語意約束>

Observable consequence:
<外部模組、狀態機或驗收測試可觀察到的結果>

Allowed variation:
- timeout / retry budget 可依遊戲更新調校
- 具體比對模板與檢測演算法可獨立置換
- 內部 phase 狀態名稱可自由重構

Verification:
<驗證此行為的 focused behavior / contract tests>
```

> [!IMPORTANT]
> **`Allowed variation` 是必要欄位**，用於向未來的維護者明確宣示自由度，避免未來僅是調整 config 參數就被誤判為「違反架構契約」。

## 上位契約層級與去重閘門 (Canonical Hierarchy & Dedup Gate)

在新增任何 Invariant 前，**必須先檢索既有上位 Canonical Contract**（如 `docs/architecture/precondition_contracts.md` 等）。

若上位 Contract 已明確定義基礎原則：
- `Click ≠ Completion`
- `Bounded Retry / Wait`
- `DEFER ≠ Completion`
- `Recovery 不得偽裝成業務成功`
- `Perception 與 Decision 職責分離`

**Domain Contract 嚴禁全文重複複製上位鐵律！**  
Domain Contract 只能記錄 **Domain Specialization**，例如：
> 「Bulletin Board reset 遵循上位 Action/Postcondition Invariant；其 domain postcondition 為 reset 按鈕消失且目標面板可見；其 recovery escalation 為重試耗盡時觸發 DEFER 退避，不得強行推進接任務。」

Canonical 文件應形成有層次的樹狀體系，杜絕複製貼上。

## 契約寫作風格 (Contract Writing Style)

Canonical Contract 必須保持：
- **短、中性、可掃讀、Refactor-resistant**。
- **嚴格使用 RFC 2119 關鍵字**（MUST / MUST NOT / MAY）描述 semantic obligation。
- **剔除情緒化與偽權威詞彙**：禁用「不可動搖」、「永久鐵律」、「唯一法定」、「徹底杜絕」、「100%」等誇飾字眼（除非真的是外部通訊協定絕對限制）。
- **排除歷程敘事**：嚴禁將 root cause、開發故事、commit SHA、除錯步驟寫進 Normative Contract（這些屬於 PARS / ADR）。

---

## 升格為 Canonical Contract 的門檻

一條內容只有在下列條件全部滿足時才允許升格：

1. **已落地 (Implemented)**：目前 production behavior 已實作，不只是提案。
2. **有證據 (Verified)**：有直接相關測試、可觀察行為或其他驗證支持。
3. **刻意設計 (Intentionally Designed)**：經過架構意圖審查，非隨機或偶然之副作用。
4. **耐重構 (Refactor-Stable)**：通過反事實自檢，重構內部實作後仍必須成立。
5. **違規即迴歸 (Regression-Bound)**：違反它代表破壞系統承諾，而不僅僅是換一個實作方式。
6. **範圍清楚 (Clear Scope)**：明確標記誰受約束、誰不受約束，並定義 Allowed variation。

任何一項不確定時，**不要自行把它宣告成永久標準**；先保留為現況說明、TODO 或標記為 `CONFLICT_REQUIRES_REVIEW`。

---

## 工作流程

1. **讀完整上下文與衝突審查 (Read Context & Conflict Review)**
   - 盤點本次分支涉及的原始 Spec / TODO、對應 code / config、focused tests 與上位 architecture contract。
   - 審視其提出的架構假設、職責邊界與後置條件。
   - **AS-IS 與 SHOULD 衝突審查**：核對 production code 現況 (AS-IS) 與設計意圖 (SHOULD)。若發現現有契約、代碼行為或測試存在矛盾，**標記為 `CONFLICT_REQUIRES_REVIEW`，嚴禁將 bug 或偶然行為就地合法化**。

2. **語意分層與 Invariant 壓縮 (Classification & Invariant Compression)**
   - 將所有候選項目分類至 7 大語意層級。
   - 僅將 `ARCHITECTURE_INVARIANT` 與 `DOMAIN_CONTRACT` 列為 `PROMOTE` 候選。
   - 執行 **Invariant Compression**：剝離 timeout 秒數、retry 次數、模板檔名等實作細節，改寫為語意規則。
   - 通過 **Refactor Counterfactual Gate** 5 大提問檢驗。
   - 執行 **Parent-Contract Dedup**：上位已規範者僅寫 domain 具體化。
   - 補齊 **Allowed variation** 自由度描述。

3. **顯式確認清理範圍 (Mandatory User Scope Confirmation)**
   > [!CRITICAL]
   > **嚴禁 AI 自行決定清理範圍**：完成契約升格與審查後，AI 必須停下來向使用者顯式呈報：
   > 1. 【已升格更新之 Canonical Contract 清單與章節】（或說明經核對「經審查無新增長效不變量」）；
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

5. **同步索引與相關文件**
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
