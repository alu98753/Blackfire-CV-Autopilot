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

1. **建立 Handler**：於 `states/handlers/` 建立新建築 Handler，傳承 `BaseStateHandler`。
2. **實作離場消費**：於完成離場判定處呼叫 `self.machine.pop_and_next_town_subflow()`。
3. **註冊狀態與佇列**：於 `GameStateMachine` 註冊新狀態，並在 `states/town_subflow_registry.py` 與 `config.py` 中配置該子流程。

