# 城鎮任務流水線佇列 (Town Subflow Pipeline) 🏛️

## 概述

**城鎮任務流水線佇列 (Town Subflow Pipeline)** 是專門為城鎮內多建築物子流程設計的動態連動調度架構。

當腳本在自動掛機（如 `mix` 混合模式、`stage` 推圖模式、`dungeon` 地城模式）過程中遇到 **背包已滿** 並完成 **背包清理與分解 (`BAG_CLEANING`)** 後，腳本將自動退回城鎮，並依序鏈式執行所有啟用的城鎮建築物任務（如：血之祭壇獻祭 ➔ 珠寶加工廠出售 ➔ 未來新建築）。流程全部完成後，系統會自動清理所有狀態標記，並無縫切換回 `STATE_NAVIGATING` 恢復原本的掛機導航。

---

## 🏛️ 架構設計理念 (Clean Code & 開閉原則)

本架構嚴格遵守 **開閉原則 (Open-Closed Principle)** 與 **單一職責原則 (Single Responsibility Principle)**：

1. **流水線集中調度**：
   `GameStateMachine` 管理 `town_subflow_queue` 佇列與彈出消費方法 `pop_and_next_town_subflow()`。
2. **Handlers 完全解耦**：
   各個城鎮建築物 Handler（如 `BloodAltarHandler`、`JewelryWorkshopHandler`）只專注於處理自身的內建邏輯與離場。離開建築物時只需呼叫 `self.machine.pop_and_next_town_subflow()`，完全不需要知道下一個建築是誰，也不硬編碼下游跳轉。
3. **無限擴充性**：
   未來若需加入第 3、第 4 個城鎮建築（如：鍛造廠 `blacksmith`、藥水店 `potion_shop`），只需在狀態機註冊 Handler 並將名稱放入佇列，**現有的所有 Handler 完全不需要修改任何一行程式碼**。

---

## 🔄 流程與運作原理

```
                           [ 背包滿 BAG_CLEANING 完成 ]
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │ GameStateMachine              │
                       │ trigger_town_subflow_chain()  │
                       └───────────────┬───────────────┘
                                       │ (生成任務佇列: ["blood_altar", "jewelry_workshop"])
                                       ▼
                           [ pop_and_next_town_subflow() ]
                                       │
                     ┌─────────────────┴─────────────────┐
                     │                                   │
                     ▼ (佇列有任務 1)                    ▼ (佇列已空)
          ┌─────────────────────┐             ┌─────────────────────┐
          │ STATE_BLOOD_ALTAR   │             │ STATE_NAVIGATING    │
          └──────────┬──────────┘             │ (恢復 mix/stage/    │
                     │ (完成獻祭離場)          │  dungeon 主導航)    │
                     ▼                        └─────────────────────┘
          [ pop_and_next_town_subflow() ]
                     │
                     ▼ (佇列有任務 2)
          ┌─────────────────────────┐
          │ STATE_JEWELRY_WORKSHOP  │
          └──────────┬──────────────┘
                     │ (完成出售離場)
                     ▼
          [ pop_and_next_town_subflow() ] ➔ 佇列已空 ➔ STATE_NAVIGATING (回復主導航)
```

---

## ⚙️ 組態配置 (Configuration)

可在 [config.py](file:///e:/Side_Project/BlackfireCrusade_tool/config.py) 的 `GLOBAL_SETTINGS` 或特定模式設定中自訂執行順序與項目：

```python
GLOBAL_SETTINGS = {
    # 預設背包清理後連動的城鎮建築順序
    "default_town_subflow_order": ["blood_altar", "jewelry_workshop"],
}
```

若欲關閉某一子流程或調整優先順序，只需修改 `town_subflow_order` 陣列即可。

---

## 🚀 未來新增城鎮建築步驟 (Developer Guide)

當未來欲擴充新城鎮建築時，請遵循以下步驟：

1. **建立 Handler**：於 `states/handlers/` 建立新建築 Handler，傳承 `BaseStateHandler`。
2. **實作離場消費**：於完成離場判定處呼叫 `self.machine.pop_and_next_town_subflow()`。
3. **註冊狀態與佇列**：於 `GameStateMachine` 註冊新狀態，並將名稱加入 `town_subflow_order`。
