# 城鎮任務流水線佇列 (Town Subflow Pipeline) 🏛️

## 概述

**城鎮任務流水線佇列 (Town Subflow Pipeline)** 是專門為城鎮內多建築物子流程設計的動態連動調度架構。

當腳本在自動掛機（如 `mix` 混合模式、`stage` 推圖模式、`dungeon` 地城模式）過程中遇到 **背包已滿** 並完成 **背包清理與分解 (`BAG_CLEANING`)** 後，腳本將自動退回城鎮，並依序鏈式執行所有啟用的資源維護任務（血之祭壇獻祭 ➔ 背包整理 ➔ 珠寶加工廠出售）。流程全部完成後，系統會自動清理所有狀態標記，並無縫切換回 `STATE_NAVIGATING` 恢復原本的掛機導航。

---

## 🏛️ 架構設計理念 (Clean Code & 雙軌解耦)

本架構嚴格遵守 **開閉原則 (Open-Closed Principle)**、**單一職責原則 (Single Responsibility Principle)** 與 **每日福利／資源維護雙軌解耦契約**：

1. **流水線集中調度**：
   `GameStateMachine` 管理 `town_subflow_queue` 佇列與彈出消費方法 `pop_and_next_town_subflow()`。
2. **Handlers 完全解耦**：
   各個城鎮建築物 Handler（如 `BloodAltarHandler`、`BagTidyHandler`、`JewelryWorkshopHandler`）只專注於處理自身的內建邏輯與離場。離開建築物時只需呼叫 `self.machine.pop_and_next_town_subflow()`，完全不需要知道下一個建築是誰，也不硬編碼下游跳轉。
3. **每日福利與背包維護雙軌解耦契約**：
   系統嚴格區分「每日領取福利」與「背包滿資源維護」，避免兩者相互干擾：

| 特性比較 | `blood_altar` (Daily 每日福利) | `blood_sacrifice` (背包維護流水線) |
| :--- | :--- | :--- |
| **調度來源** | 每日活動排程 `DailyManager` (Tier 1 任務) | 背包清理完成後 `trigger_bag_maintenance_chain()` |
| **紅點門禁** | `requires_red_dot = True`（無紅點則跳過並標記完成） | `requires_red_dot = False`（無需紅點，無條件進入獻祭） |
| **完成簽核** | 呼叫 `record_subflow_completed("blood_altar")` | **不簽核** DailyManager，嚴禁污染每日領血紀錄 |

4. **獨立背包整理子流程 (`bag_tidy`)**：
   背包整理不再由 `JewelryWorkshopHandler` 私自內嵌持有，改由獨立的 `BagTidyHandler` 承擔，並作為獨立子流程依序調度，具備獨立後置條件驗證 (Postcondition Verification)。

### 5. `BagCleaningHandler` 與 `BagTidyHandler` 職責邊界契約

| 維度 | `BagCleaningHandler` (背包滿清理與分解) | `BagTidyHandler` (背包純排序與整理) |
| :--- | :--- | :--- |
| **領域性質** | **破壞性空間釋放**：將背包中的白/綠/藍裝備大量分解銷毀以騰出格子。 | **非破壞性純排序**：僅點擊「整理」按鈕排齊格子，無任何物品銷毀。 |
| **執行流程** | 開包 ➔ 大量分解 ➔ 全選 ➔ 反選貴重裝備 ➔ 執行分解 ➔ 整理 ➔ 退出關閉。 | 開包 ➔ 點擊整理按鈕 ➔ 退出關閉並執行後置條件驗證。 |
| **排他防護** | 珠寶店進店前**嚴禁**呼叫本處理器，防止將待售首飾與裝備誤分解。 | 珠寶店進店前由本處理器排齊格子，確保商品整齊排列在左上角便於出售。 |

### 6. 後置條件驗證契約 (Postcondition Verification)

依據 [Precondition Contracts](../../architecture/precondition_contracts.md)，動作點擊不等於完成，必須透過物理畫面特徵證明結果成立：
- **背包退出閉環**：`BagTidyHandler` 點擊 `common/quit.png` 時，必須調用 `click_and_wait_until_gone` 確認關閉按鈕消失。
- **三項後置條件驗證**：重新採集畫面，驗證 `common/quit.png` 為 None、`common/tidy.png` 為 None、且 `common/door.png` 成立（畫面已回到純淨城鎮大門且無任何遮罩覆蓋層）。三項條件全數成立後，方可調用 `pop_and_next_town_subflow()` 交棒至下一流程。

### 7. 覆蓋層清理與場景守護契約 (Overlay Dismissal & Scene Guard)

- **進店與整理前置清理**：各 Handler 於 `INIT` 階段若偵測到殘留的關閉按鈕 (`common/quit.png` 可見但非城鎮大門)，優先透過 `click_and_wait_until_gone` 消除覆蓋層，避免點擊被前景遮罩吸收。
- **進店點擊遺失自癒**：`JewelryWorkshopHandler` 進入 `ENTERED_BUILDING` 階段後，若超過 4 秒畫面依然看見城門 (`common/door.png`) 且無店內特徵，判定為進店點擊遺失，自癒退回 `INIT` 重新點擊進店，防止原地死鎖。

### 8. 懸賞告示牌子流程契約 (Bulletin Board Subflow Contract)

懸賞告示牌子流程負責每日懸賞任務之開窗、重置與接取，依循 [Precondition Contracts](../../architecture/precondition_contracts.md) 嚴格落實以下不變量：

本節是 `Precondition Contracts` 對告示牌流程的領域特化。它約束可觀測的感知、決策與復原行為；ROI 尺寸、沉澱時間、重試次數、模板路徑與診斷輸出均為實作或執行期策略，不構成不變量。術語判讀見 [Canonical Invariant Registry](../../architecture/canonical_invariant_registry.md)。

#### 8.1 告示牌特有的決策語意 (Domain Decision Semantics)

告示牌動作的 Click／postcondition／bounded retry／defer／recovery 義務由 [Precondition Contracts](../../architecture/precondition_contracts.md) 擁有，本節不重新定義。

1. **Perception Classification**：證據不足 MUST NOT 被視為已知干擾層。目標動作剛產生的新彈窗，在缺乏反向證據前 MUST NOT 僅因目標特徵尚未就緒而被關閉；領域推進 MUST 由正向或排他證據支撐。
2. **Decision Evidence Scope**：決策證據 MUST 遵守其宣告的感知範圍。診斷證據 MAY 使用較廣的搜尋範圍，但 MUST NOT 改寫或決定狀態轉移語意。

#### 8.2 領域契約 (Domain Contracts)
1. **開窗四互斥語意分流**：
   - 彈窗狀態必須可明確區分為：目標確認（Confirmed Target）、已知衝突遮擋（Known Conflicting Overlay）、未知/證據不足遮擋（Unknown / Evidence-Insufficient Overlay）與無視窗（No Overlay）。
   - 未知／證據不足狀態不得直接被轉譯為已知衝突遮擋。
2. **背包排他判定正交性**：
   - 背包排他判定必須使用經驗證為背包專屬的正交特徵，嚴禁使用會跨其他介面出現的共享圖示（如重新整理按鈕）作為單一排他證據。
   - *(實作參考：目前以 `common/Disassembly.png` 作為背包專屬排他特徵；`common/tidy.png` 因可能於其他功能介面重疊出現，不得作為全域背包鑑別特徵)*。
3. **重置的領域結果**：
   - 重置成功的後置條件是告示牌進入可安全繼續任務接取的可觀測狀態。
   - 若無法建立該後置條件，流程的領域結果 MUST 是未完成；後續處理依 Precondition Contracts 的 defer／recovery 規則進行。

---

## 🔄 流程與運作原理

```
                           [ 背包滿 BAG_CLEANING 完成 ]
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │ GameStateMachine              │
                       │ trigger_bag_maintenance_chain()│
                       └───────────────┬───────────────┘
                                       │ (展開預設佇列: ["blood_sacrifice", "bag_tidy", "jewelry_workshop"])
                                       ▼
                           [ pop_and_next_town_subflow() ]
                                       │
                     ┌─────────────────┴─────────────────┐
                     │                                   │
                     ▼ (任務 1: blood_sacrifice)          ▼ (佇列已空)
          ┌─────────────────────┐             ┌─────────────────────┐
          │ STATE_BLOOD_ALTAR   │             │ STATE_NAVIGATING    │
          └──────────┬──────────┘             │ (恢復 mix/stage/    │
                     │ (完成獻祭離場)          │  dungeon 主導航)    │
                     ▼                        └─────────────────────┘
          [ pop_and_next_town_subflow() ]
                     │
                     ▼ (任務 2: bag_tidy)
          ┌─────────────────────┐
          │ STATE_BAG_TIDY      │
          └──────────┬──────────┘
                     │ (完成整理與後置驗證離場)
                     ▼
          [ pop_and_next_town_subflow() ]
                     │
                     ▼ (任務 3: jewelry_workshop)
          ┌─────────────────────────┐
          │ STATE_JEWELRY_WORKSHOP  │
          └──────────┬──────────────┘
                     │ (完成出售離場)

---

## 🔄 流程與運作原理

```
                           [ 背包滿 BAG_CLEANING 完成 ]
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │ GameStateMachine              │
                       │ trigger_bag_maintenance_chain()│
                       └───────────────┬───────────────┘
                                       │ (展開預設佇列: ["blood_sacrifice", "bag_tidy", "jewelry_workshop"])
                                       ▼
                           [ pop_and_next_town_subflow() ]
                                       │
                     ┌─────────────────┴─────────────────┐
                     │                                   │
                     ▼ (任務 1: blood_sacrifice)          ▼ (佇列已空)
          ┌─────────────────────┐             ┌─────────────────────┐
          │ STATE_BLOOD_ALTAR   │             │ STATE_NAVIGATING    │
          └──────────┬──────────┘             │ (恢復 mix/stage/    │
                     │ (完成獻祭離場)          │  dungeon 主導航)    │
                     ▼                        └─────────────────────┘
          [ pop_and_next_town_subflow() ]
                     │
                     ▼ (任務 2: bag_tidy)
          ┌─────────────────────┐
          │ STATE_BAG_TIDY      │
          └──────────┬──────────┘
                     │ (完成整理與後置驗證離場)
                     ▼
          [ pop_and_next_town_subflow() ]
                     │
                     ▼ (任務 3: jewelry_workshop)
          ┌─────────────────────────┐
          │ STATE_JEWELRY_WORKSHOP  │
          └──────────┬──────────────┘
                     │ (完成出售離場)
                     ▼
          [ pop_and_next_town_subflow() ] ➔ 佇列已空 ➔ STATE_NAVIGATING (回復主導航)
```

---

### 9. 城鎮實體正規化與互動就緒契約 (Town Egress Normalization & Interaction Readiness)

本節是 [Precondition Contracts](../../architecture/precondition_contracts.md) 在城鎮場景與建築進出轉換的領域特化。

#### Invariant 9.1: Town Physical Location vs. Interaction Readiness Separation
- **Scope**: 全系統所有進入城鎮或依賴城鎮環境之子流程與排程器。
- **Rule**:
  1. 系統 MUST 將「處於城鎮物理環境 (Physical Location)」與「具備城鎮互動就緒性 (Interaction Readiness)」區分為兩個獨立閘門。
  2. 單一城鎮門戶特徵可見，僅能確立物理位置處於城鎮；在缺乏正向城鎮無遮擋前景特徵（Clear Anchor）或多幀穩定確認前，系統 MUST NOT 判定為具備互動就緒性：
     - `TOWN + positive clear anchor + no blocker` ➔ 判定為 `READY`，方可派發業務控制權。
     - `TOWN + no blocker + no clear anchor` ➔ 判定為 `UNKNOWN`，進入有界重新觀測 (bounded re-observe)。
  3. **Intent Protection**: 當城鎮就緒性處於 `UNKNOWN` 或正規化逾時失敗時，系統 **MUST NOT** 懲罰性 defer、pop 或 complete 業務 Intent。
  4. 未達城鎮互動就緒狀態前，狀態機 MUST NOT 向依賴城鎮之業務 Handler 派發實體控制權。
- **Observable consequence**: 退出戰鬥或建築後，若畫面仍處於半透明淡入、過渡載入或殘留彈窗未消退狀態，系統維持在安全導航前置等待，絕不引發過早點擊或偽完成。
- **Allowed variation**: 前景驗證所採用之具體錨點模板、驗證演算法與多幀防抖次數可隨遊戲更新動態調整。
- **Verification**: `tests/test_behavior_reach_town_normalization.py`

#### Invariant 9.2: Building Egress Multi-Frame Verification Lifecycle
- **Scope**: 所有具備進入或退出城鎮建築生命週期之 Handlers。
- **Rule**:
  1. 點擊建築退出特徵 MUST 僅視為退出動作之發起，MUST NOT 視為退出完成。
  2. 建築 Handler 在發起退出點擊後，MUST 將生命週期轉移至退出驗證階段，唯有在後續畫面觀測到正向城鎮環境特徵時，方可判定退出完成並推進或交棒。
- **Observable consequence**: 退出建築動作因點擊丟失或過渡延遲未生效時，Handler 絕不會同幀誤判退出成功而呼叫完成或銷毀。
- **Allowed variation**: 內部狀態機階段名稱（如 `VERIFY_EXIT`）與超時重試預算可自由重構。
- **Verification**: `tests/test_behavior_town_scenarios.py`

#### Invariant 9.3: Login World-Ready Boundary
- **Scope**: 登入、重啟重開與初始化生命週期 (`login_handler.py`, `relaunch`, `supervisor`) 及城鎮正規化控制器。
- **Rule**:
  1. 系統登入與重啟驗證完成之基準契約為 `WORLD_READY`，絕非 `TOWN_READY`。登入與恢復流程 MUST 將任何已驗證之已知遊戲世界場景（如 `IN_DUNGEON`、`TOWN`、`TOWN_BUILDING`、`LOBBY`）視為登入就緒。
  2. 登入與重啟流程 MUST NOT 強制將實體位置正規化回城鎮。
  3. 若登入或重啟後實體位置落在地下城 (`IN_DUNGEON`)，系統 MUST 保留地下城探索之所有權與接續性，嚴禁強制回城或退場。
  4. 城鎮實體正規化 (`REACH_TOWN`) 唯有在下游業務消費者（Downstream Consumer，如城鎮福利領取、日常維護子流程）明確需要城鎮環境時，方由該消費者發起請求。
- **Observable consequence**: 遊戲重開後若玩家落在地下城戰鬥或探索中，自動戰鬥與副本探索順暢接續，絕不會因為系統盲目尋找城門而觸發錯誤退場或狀態死鎖。
- **Allowed variation**: `WORLD_READY` 具體支援之場景種類、識別順序與特徵比對演算法可隨世界地圖擴充。
- **Verification**: `tests/test_behavior_login_and_town_boundary_regression.py`

---

### 10. 錯位讓渡協定與業務意圖保護 (Committed Handler Mislocation Relinquishment Protocol)

#### Invariant 10.1: Generic Building Evidence Semantics
- **Scope**: 全專案建築物特徵比對與內部判斷。
- **Rule**:
  1. 建築物共用之退出或回城按鈕（如 `exitfromhouse_and_to_town.png`）屬於「通用建築內部特徵 (Generic Building-Internal Evidence)」，MUST NOT 作為任何特定建築物之自身專屬正向特徵。
  2. 各業務 Handler 進入其專屬業務邏輯前，MUST 依賴該建築之「自身專屬特徵 (Own-Specific Evidence)」確認身分。
- **Observable consequence**: 誤入其他建築物時，Handler 不會因為看到通用退出按鈕而誤認為已成功進入正確房間。
- **Allowed variation**: 具體模板檔名與特徵比對門檻屬可調策略。
- **Verification**: `tests/test_phase_transition_stability.py`

#### Invariant 10.2: Bounded Mislocation Relinquishment without Intent Mutation
- **Scope**: 所有城鎮子流程 Handlers（Chest, HeroDraw, BloodAltar, BagTidy, BulletinBoard, JewelryWorkshop）。
- **Rule**:
  1. 當 Handler 處於運行中但觀測到通用建築內部特徵可見、且自身專屬特徵不存在時，MUST 透過有界連續幀確認（連續 2 幀）判定錯位成立。
  2. 錯位確認成立後，Handler MUST 主動讓渡（Relinquish）實體控制權交還給 shared `REACH_TOWN` 正規化路徑，由 shared controller 執行實體退場回城。
  3. **Strict Prohibition (懲罰性消耗禁令)**：錯位讓渡期間，系統與 Handler **MUST NOT** 觸發 defer（冷卻退避）、pop（彈出佇列）或 mark completed（標記完成）！業務 Intent 必須 100% 完整保留，待回城達到 Interaction Readiness 後重新派發。
- **Observable consequence**: 當因點擊偏移誤入錯誤建築時，系統自動退出並回到城鎮重新點擊正確建築，絕不吃掉今日任務、絕不使意圖陷入 180s 冷卻、亦不破壞日常流水線契約。
- **Allowed variation**: 讓渡防抖幀數、實體讓渡內部訊號機制（如 Token 或 Transition）可自由演進。
- **Verification**: `tests/test_behavior_handler_mislocation_relinquish.py`

---

## ⚙️ 組態配置 (Configuration)

可在 [config.py](../../../config.py) 或 `config/defaults.toml` 的 `GLOBAL_SETTINGS` 中自訂背包清理後連動的維護順序：

```python
GLOBAL_SETTINGS = {
    # 預設背包清理後連動的資源維護子流程順序（獻祭 ➔ 整理 ➔ 出售）
    "default_bag_maintenance_order": ["blood_sacrifice", "bag_tidy", "jewelry_workshop"],
}
```

若欲調整個別 Profile 的維護順序，可在 Profile TOML 中指定 `bag_maintenance_order` 陣列進行覆寫。

---

## 🚀 未來新增城鎮建築步驟 (Developer Guide)

當未來欲擴充新城鎮建築時，請遵循以下步驟：

1. **建立 Handler**：於 `states/handlers/` 建立新建築 Handler，傳承 `BaseStateHandler`，並內嵌 `MislocationGuard` 實作錯位讓渡。
2. **實作離場消費**：於完成離場判定處呼叫 `self.machine.pop_and_next_town_subflow()`。
3. **註冊狀態與佇列**：於 `GameStateMachine` 註冊新狀態，並在 `states/town_subflow_registry.py` 與 `config.py` 中配置該子流程。
