# 模式與活動大一統規格書 (Activity Mode Consolidation Spec) 📋

> 狀態：架構提案 (Proposed Architecture RFC)  
> 上位架構：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)  
> 前置條件契約：[Precondition Contracts](../architecture/precondition_contracts.md)  
> 前置實踐：[背包維護與每日子流程解耦規格書](bag_and_daily_subflow_decoupling_spec.md)  
> 追蹤 Issue/TODO：[future_work.md](future_work.md)

---

## 1. 實務背景與現狀代碼審查 (Context & Code Survey)

### 1.1 問題發起與核心疑問
在實機維護與背包解耦過程中，開發者觀察到：
「背包滿溢後的維護流程（血之祭壇獻祭、背包整理、珠寶店出售）既可在長掛機日常流程中自動觸發，也可透過 `--subflow` 單獨測試執行。既然兩種路徑都會做完全相同的事情，為何系統無法抽象為統一的『活動 (Activity)』重複利用？目前的程式碼是否存在兩套重複實作？」

### 1.2 現狀程式碼審查 (No Code Duplication)
經過對狀態機、引導入口與處理器的代碼審查，確認底層業務與處理器 **100% 同源共用，完全沒有重複撰寫兩套代碼**。

1. **日常主模式排程 ([states/state_machine.py](../../states/state_machine.py))**：
   - 每日城鎮速領（`chest`、`hero_draw`、`blood_altar`、`jewelry_workshop`）與魔王討伐（`demon_lords`）在 `evaluate_next_activity()` 中均呼叫共用方法：
     ```python
     self.start_subflow_queue(pending_town)
     ```
   - 探索結束退回城鎮後的延遲背包維護亦是呼叫：
     ```python
     def trigger_bag_maintenance_chain(self):
         order = cfg.get("bag_maintenance_order", get_default_bag_maintenance_order())
         self.start_subflow_queue(order)
     ```
2. **單獨測試啟動入口 ([runtime/bootstrap.py](../../runtime/bootstrap.py))**：
   - 開發者透過 `--subflow` 指定單一或組合流程時，底層直接注入同一佇列：
     ```python
     if hasattr(args, "subflow") and args.subflow:
         state_machine.is_dev_subflow_run = True
         state_machine.start_subflow_queue(args.subflow)
     ```
3. **底層處理器共用 ([states/handlers/](../../states/handlers/))**：
   - 無論由日常流水線觸發還是由 `--subflow` 觸發，最終均由狀態機統一調度至同一個 Handler（`BloodAltarHandler`、`BagTidyHandler`、`JewelryWorkshopHandler`），且進入前一律遵循 [Precondition Contracts](../architecture/precondition_contracts.md) 定義的 `REACH_TOWN` 前置條件判定。

實機執行日誌亦證實兩者呼叫同一套流水線：
```text
2026-09-11 12:30:34,024 [INFO] 🎒 [背包後續維護] 偵測到地下城探索結束退回城鎮，自動補跑延遲的背包維護子流程佇列...
2026-09-11 12:30:34,025 [INFO] 🎒 [背包後續維護] 背包清理完成，構建維護任務佇列: ['blood_sacrifice', 'bag_tidy', 'jewelry_workshop']
2026-09-11 12:30:34,026 [INFO] ============================================================
2026-09-11 12:30:34,026 [INFO] 🏛️ 【城鎮任務流水線 - 任務總覽儀表板】 🏛️
2026-09-11 12:30:34,026 [INFO] ============================================================
  1. [blood_sacrifice] blood_sacrifice : 🟢 待執行 (Enabled)
  2. [bag_tidy] 背包整理         : 🟢 待執行 (Enabled)
  3. [jewelry_workshop] 珠寶加工廠出售      : 🟢 待執行 (Enabled)
============================================================
```

### 1.3 概念割裂的根本成因
雖然底層程式碼共用，但系統在**架構概念、排程模型與啟動參數**上存在歷史遺留的分歧，導致直觀體驗上如同兩套獨立系統：

| 維度 | 目前的「主模式 (Mode)」 | 目前的「城鎮子流程 (Subflow)」 |
| :--- | :--- | :--- |
| **代表功能** | `dungeon` (地下城), `stage` (關卡), `golden_empire` (領地) | `chest`, `blood_altar`, `lord_boss`, `bag_maintenance` |
| **啟動參數** | `--mode <name>` | `--subflow <name>` |
| **排程方式** | 透過 `primary_config` 與導航表路徑跳轉 | 透過 `town_subflow_queue` 依序彈出 |
| **日常整合** | 被視為外層的主循環活動 | 被視為優先插隊的內部子流程 |

在現有機制下，狀態機在 `evaluate_next_activity()` 中必須兼顧兩套調度哲學：一邊用 `start_subflow_queue` 排程城鎮與 Boss，另一邊用覆寫 `self.config` 切換戰鬥場景。這便是推動本規格書「Activity 大一統」的實質動機。

---

## 2. 收斂目標 (Consolidation Goals)

收斂目前散落的 `mix / dungeon / stage / collect_only / golden_empire / subflow ...` 啟動模式。

未來對外只保留兩種 orchestration mode：

### 2.1 `daily`
固定的 24/7 ActivityPlan。啟動時讀取使用者持久化設定，按照系統既有 Scheduler、Priority、cooldown、defer、preemption 規則持續執行。

### 2.2 `custom`
讓使用者 enable / disable 個別 Activity，並設定必要 target。
`custom` 不建立另一套 scheduler；必須與 `daily` 共用相同的 Activity selection、priority、intent lifecycle 與 prerequisite 機制。

`daily` 本質上應只是官方預設的一份 ActivityPlan，`custom` 則是使用者自行組合的 ActivityPlan。

---

## 3. 單一功能執行入口 (Single Activity Execution)

不要把第三類稱為一般 runtime `mode` 或把所有功能都叫 `subflow`。
建立「直接執行單一 Activity」的開發入口，例如：
- `--activity dungeon`
- `--activity stage`
- `--activity golden_empire`
- `--activity chest`
- `--activity bag_maintenance`

其用途是開發、debug、驗證單一 Activity，繞過全域 Scheduler。目前 `--subflow` 可視為此能力的早期版本；未來逐步泛化，而不是把 dungeon、stage 等概念硬塞入 Town Subflow。

---

## 4. 核心語意與架構分層 (Core Semantics & Architecture Layers)

### 4.1 統一名詞定義
- **`Mode`** = 使用者如何建立執行計畫 (`daily` 或 `custom`)。
- **`ActivityPlan`** = 哪些 Activities 啟用以及相關設定。
- **`Activity`** = Scheduler 可以選擇的一個具體工作（如 `dungeon`, `stage`, `chest`, `bag_maintenance`）。
- **`Intent`** = Runtime 目前承諾完成的工作單位。
- **`Handler/FSM`** = Activity 被 dispatch 後的局部執行。

### 4.2 目標依賴方向 (符合 Greenfield-lite)
依賴關係只能單向流動，禁止底層反向耦合：
```text
User Configuration
  → ActivityPlan
    → Scheduler / Intent Selection
      → Prerequisite Satisfaction
        → Activity Handler / FSM
```
底層 Navigation / Handler 不得根據 `mode` 名稱自行選擇其他 Activity。

---

## 5. 漸進演進與先行實踐 (Evolutionary Steps)

### 5.1 背包維護解耦的先行驗證
在 [背包維護與每日子流程解耦規格書](bag_and_daily_subflow_decoupling_spec.md) 中實作的 `bag_maintenance` 巨集（一次執行 `blood_sacrifice` ➔ `bag_tidy` ➔ `jewelry_workshop`），本質上已是將一組維護動作視為「複合 Activity / Macro」的先行實踐。它證明了透過單一命名（`bag_maintenance`）整合多個子步驟，並在日常模式與獨立測試中維持 100% 共用排程的可行性。

### 5.2 特別注意事項與分支策略
1. 目前 `daily` 仍使用 `type="mix"` 作為 runtime compatibility mechanism，此為過渡實作，不應成為未來架構。
2. 禁止新增 `if config["type"] == ...` 補釘來解決跨 Activity 優先級問題。
3. **分支隔離原則**：本大一統重構涉及將戰鬥探索流程（`dungeon`/`stage`）亦納入 Intent Lifecycle，屬於廣義架構遷移，應在獨立之架構分支（如 `arch/unified-activity-plan`）中推行，不與一般日常 bugfix 分支混雜。
