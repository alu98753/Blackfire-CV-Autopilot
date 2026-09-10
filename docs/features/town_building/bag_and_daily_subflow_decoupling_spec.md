# 背包維護與每日子流程解耦規格書 (Bag Maintenance & Daily Subflow Decoupling Spec) 📋

> 狀態：正式規格提案 (Proposed Specification)  
> 上位架構：[Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md)  
> 前置條件契約：[Precondition Contracts](../../architecture/precondition_contracts.md)  
> 關聯契約：[REACH_TOWN Contract](../navigation/reach_town_contract.md)、[Lobby Scene Contract](../navigation/lobby_scene_contract.md)  
> 追蹤 Issue/TODO：[future_work.md](../../todos/future_work.md)、[bag_bug.md](../../todos/bag_bug.md)、[bag_jewelry_workshop_bug.md](../../todos/bag_jewelry_workshop_bug.md)

---

## 1. 背景與問題定義 (Problem Statement)

近期在長掛機與自動背包清理過程中，密集觀察到以下兩項嚴重影響無人值守穩定性的卡死與邏輯異常現象：

1. **背包滿後觸發珠寶店/血之祭壇時，背包未關閉即跳轉懸賞導致全域卡死**：
   - 背包清理後觸發城鎮流水線，但在進入珠寶店時打開背包，畫面邊緣因暗化背景仍穿透匹配到城鎮大門 `common/door.png`（相似度 0.9403），觸發珠寶店內部的「Scene Guard 防護攔截」，結束出售並退出；
   - 此時背包視窗仍停留在螢幕上未關閉，狀態機強行轉移至 `NAVIGATING` 去執行懸賞任務；
   - 導航層在城鎮畫面嘗試點擊城門 `common/door.png`，因前景被未關閉的背包模態遮罩阻擋，點擊無效且無法跳轉場景，連續重試 15 次逾時，全域陷入死鎖卡死。
2. **懸賞告示牌尚未進入建築（還在背包/其他過渡畫面）就開始誤判任務**：
   - 懸賞告示牌處理器 (`BulletinBoardHandler`) 僅依賴 `common/quit.png` 作為「已成功進入告示牌」的憑據；
   - 當畫面上殘留未關閉的背包或其他彈窗時，因這些視窗右上角同樣具備 `quit.png`，告示牌處理器誤判已在告示牌內部，跳過建築進入直接發起任務 OCR 掃描；
   - 因當前畫面實為背包而非告示牌，OCR 未匹配到任何任務，系統直接誤判定為「今日所有任務均已接滿」，將告示牌標記為今日完成並退出，造成當日懸賞任務全數被吞噬遺漏。

---

## 2. 同源性深度分析 (Root Cause & Commonality Analysis)

經過對程式碼、日誌及除錯截圖的跨層審查，**確認這兩個問題本質上 100% 同源 (Common Root Cause)**，由以下三大架構缺陷交織而成：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        【架構根因 1：流水線語意混淆】                    │
│    背包清理完成後，錯誤借用 Daily 每日速領佇列 (town_subflow_order)        │
│    導致「血之祭壇獻祭」被套上每日紅點政策，因無紅點被判定已完成而跳過        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        【架構根因 2：連帶性強行綑綁】                    │
│    血之祭壇 (Blood) 與珠寶加工廠 (Jewelry) 寫死連動，無獨立觸發與守護     │
│    珠寶店在 Handler 內部私自開啟背包整理，畫面邊緣穿透 door.png 觸發攔截    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ (背包開著未關閉，直接退出 Handler)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        【架構根因 3：覆蓋層與場景穿透】                  │
│    背包是 Modal Overlay，但系統缺乏 Overlay 閉環驗證：                 │
│    ├─ 分支 A (NAVIGATING): 看到 door.png 盲點，被背包遮擋逾時卡死      │
│    └─ 分支 B (BULLETIN_BOARD): 看到 quit.png 誤認進屋，任務 OCR 全空吞噬 │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 根因一：維護流水線 (Maintenance) 與每日流水線 (Daily) 的職責混淆
- **每日流水線 (Daily Master Pipeline)** 的目的是在每日 08:05 重置後，**速領每日免費福利**（寶箱 `chest`、酒館抽卡 `hero_draw`、祭壇領血 `blood_altar`、懸賞告示牌 `bulletin_board`）。這些建築物外部具備**驚嘆號紅點 (Red Dot)** 作為「今日待領」之正向證據。
- **背包維護流水線 (Bag-Full Maintenance Pipeline)** 是在戰鬥中因掉落裝備滿溢、觸發背包銷毀後的**資源消化維護行為**（消耗血水獻祭、出售雜物）。此時建築物**絕無紅點**，且與每日重置狀態無關。
- 系統在 `bag_cleaning.py` 完成後直接調用 `trigger_town_subflow_chain()`，將其塞入 `TOWN_SUBFLOW_SPECS`。因 `blood_altar` 規格寫死 `requires_red_dot=True`，城鎮前置控制器因未檢出紅點，判定「今日已領取完畢」，直接調用 `complete_current_town_subflow()` 將獻祭跳過，並錯誤記錄 daily 完成。

### 2.2 根因二：珠寶店與血之祭壇的無序連帶性與 Handler 職責越界
- 珠寶店與血之祭壇在業務上完全正交：玩家滿包時可能只有血水、可能只有裝備、或者兩者皆無。強行將兩者捆綁在同一佇列中，且共用同一組缺乏排他性保護的流程。
- `JewelryWorkshopHandler` 內部存在嚴重的架構越界：在進店前自行嘗試開啟背包執行「城鎮背包預先整理」。背包打開後，畫面雖然變暗，但左下角城鎮大門 `common/door.png` 依舊清晰可見。Handler 內部的 Scene Guard 將其誤判為「已在城鎮大門外（意外脫離建築）」，緊急呼叫 `pop_and_next_town_subflow()` 退出，**卻未呼叫關閉背包**，導致背包視窗裸露於畫面上。

### 2.3 根因三：模態覆蓋層 (Modal Overlay) 缺乏生命週期閉環與穿透誤判
- 依據 [Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md) 第 4.1 節，**Overlay 必須與 Scene 明確分離**。背包本質上是覆蓋在場景上的模態浮層 (`Modal Overlay`)。
- **穿透誤判大門**：導航層看到 `door.png` 就斷言 `SceneId.TOWN` 成立，卻忽略了前景存在全螢幕遮罩的背包視窗，點擊事件被背包吸收，導致逾時重試卡死。
- **穿透誤判告示牌進場**：告示牌處理器將 `common/quit.png` 視為進場充分條件。背包、彈窗與各類選單皆有 `quit.png`，以非排他性特徵代表特定場景，直接違反了 [Lobby Scene Contract](../navigation/lobby_scene_contract.md) 的排他性錨點原則。

---

## 3. 架構對齊與核心約束 (Architectural Invariants)

為徹底根除上述問題，本規格嚴格落實四大架構契約之不變量：

### Invariant 1：流水線與意圖徹底解耦不變量 (Pipeline & Intent Decoupling Invariant)
- **原則**：每日福利領取與背包資源處置屬於不同領域層級，擁有不同的生命週期與完成條件。
- **保證**：
  1. **拔除血之祭壇與珠寶店連帶性**：兩者不再硬編碼綁定於同一寫死鏈條。
  2. **每日領血與戰後獻祭分離**：
     - `blood_altar` (Daily Claim)：僅限每日福利，依賴紅點（`requires_red_dot=True`），領取後記錄 `daily_status.json`。
     - `blood_sacrifice` (Maintenance Sacrifice)：戰後背包滿溢後的血水獻祭，**禁止檢查紅點**，**禁止標記每日 blood_altar 完成**，純以背包內有無血水決定執行或結束。
  3. **商店出售獨立性**：`shop_sell` 專注於商店內出售，不承攬城鎮開包整理之重複職責。

### Invariant 2：覆蓋層排他性門禁保證 (Overlay Exclusion Gate Invariant)
- **原則**：模態覆蓋層（如背包、通用彈窗）未確認徹底關閉前，底層場景絕不可判定為可操作的穩態。
- **保證**：
  1. 在 `SceneSnapshot` 中，只要偵測到 `ElementId.BACKPACK_OPENED` 或 `ElementId.CLOSE_OVERLAY`，底層場景不得視為就緒。
  2. 任何跨場景導航（如點擊 `door.png` 返回大廳）或進入城鎮建築（如點擊 `bulletin_board.png`），其 Dispatch Precondition **必須包含 `OVERLAY_CLOSED`**。
  3. 退出背包必須透過 `click_and_wait_until_gone` 閉環，經下一幀 Snapshot 確認背包特徵徹底消失，方可推進狀態。

### Invariant 3：建築進場排他性錨點保證 (Building Entry Unique Anchor Invariant)
- **原則**：嚴禁以多場景共用的通用按鈕（如 `common/quit.png`）作為特定建築之進入憑證。
- **保證**：
  1. `BulletinBoardHandler` 宣告「已成功進入告示牌」之充要條件，必須是**告示牌介面獨有的正交特徵錨點**：
     - 包含：`reset_btn` (`town_building/bulletin_board/reset.png`) **或** 任務列表特徵 (`task.png` / `task_after.png`) **或** 告示牌標題文字區域。
  2. 當畫面僅有 `quit.png` 但缺乏告示牌專屬特徵時，判定為**非告示牌覆蓋層**，交由 Overlay 守護關閉，絕不進入任務掃描與完成判定。

---

## 4. 具體重構規格 (Detailed Technical Design)

### 4.1 模組一：流水線架構分離與命名正名

#### 4.1.1 領域模型與 Flow Key 拆分
在 `states/town_subflow_registry.py` 中，將原本混淆的流程拆解為語意獨立的規格：

```python
# states/town_subflow_registry.py

TOWN_SUBFLOW_SPECS = {
    # ─── 每日例行福利流水線 (Tier 1: Daily Master Pipeline) ───
    "chest": TownSubflowSpec(
        "chest",
        building_template="town_building/mysterious_treasure/mysterious_treasure.png",
        requires_red_dot=True,
    ),
    "hero_draw": TownSubflowSpec(
        "hero_draw",
        building_template="town_building/Tavern/Tavern.png",
        requires_red_dot=True,
    ),
    "blood_altar": TownSubflowSpec(
        "blood_altar",
        building_template="town_building/Blood_Altar/Blood_Altar.png",
        requires_red_dot=True,   # 每日領取：必須有紅點
    ),
    "bulletin_board": TownSubflowSpec(
        "bulletin_board",
        building_template="town_building/bulletin_board/bulletin_board.png",
        requires_red_dot=True,   # 每日懸賞：必須有紅點
    ),

    # ─── 背包維護流水線 (Maintenance: Bag-Full Post Cleaning) ───
    "blood_sacrifice": TownSubflowSpec(
        "blood_sacrifice",
        building_template="town_building/Blood_Altar/Blood_Altar.png",
        requires_red_dot=False,  # 維護獻祭：不檢查紅點！
        dispatch_on_town=False,
    ),
    "jewelry_workshop": TownSubflowSpec(
        "jewelry_workshop",
        dispatch_on_town=True,   # 商店出售：進城後由 Handler 自行定位商人
    ),
}
```

#### 4.1.2 狀態機與日常管理器解耦
- `DailyManager.record_subflow_completed("blood_altar")` 僅由每日領血觸發；`blood_sacrifice` 完成時**絕不寫入** `DailyManager` 的 daily completed 紀錄。
- 背包清理 (`BagCleaningHandler`) 結束後，不再呼叫泛用的 `trigger_town_subflow_chain()`，改為呼叫專屬的 `trigger_bag_maintenance_chain()`：
  ```python
  def trigger_bag_maintenance_chain(self):
      """
      背包清理完成後，依設定僅執行資源維護（可單獨啟用獻祭或出售，兩者解耦）。
      """
      cfg = self.config or {}
      order = cfg.get("bag_maintenance_order", ["blood_sacrifice", "jewelry_workshop"])
      logging.info("🎒 [背包後續維護] 啟動背包滿後維護佇列: %s", order)
      self.start_subflow_queue(order)
      self.transition_to(self.STATE_NAVIGATING)
  ```

---

### 4.2 模組二：背包模態覆蓋層 (Modal Overlay) 閉環守護

#### 4.2.1 背包退出閉環 (`BagCleaningHandler.quit_backpack`)
在 `states/handlers/bag_cleaning.py` 中，點擊 `common/quit.png` 後必須進行嚴格的消失等待驗證：

```python
def quit_backpack(self, screen_img, rect) -> bool:
    pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.7)
    if pos_quit:
        logging.info("🎒 背包清理：點擊退出按鈕關閉背包，並啟動配對消失閉環...")
        success = self.click_and_wait_until_gone(
            "common/quit.png",
            rect["left"] + pos_quit[0],
            rect["top"] + pos_quit[1],
            rect,
            threshold=0.7,
            timeout=3.0,
        )
        if not success:
            logging.warning("⚠️ [背包清理] 退出背包超時，背包視窗可能殘留！")
        self._reset_and_exit_bag_cleaning()
        return True
    return False
```

#### 4.2.2 導航層 Overlay 前置攔截 (`NavigationHandler`)
在導航層進入大門（`action == "enter_lobby"`）前，加入覆蓋層門禁：
若畫面同時匹配到背包特徵（如 `common/tidy.png`、`common/Disassembly.png` 或 `common/quit.png` 在背包右上角區域），**嚴禁點擊城門 `common/door.png`**，必須優先點擊關閉覆蓋層：

```python
# Navigation 前置守護：檢查是否有未關閉的模態覆蓋層
if self._is_modal_overlay_present(screen_img):
    logging.warning("🛡️ [導航守護] 偵測到畫面存在未關閉之模態視窗/背包，優先點擊關閉，禁止點擊城門！")
    self._dismiss_modal_overlay(screen_img, rect)
    return
```

---

### 4.3 模組三：珠寶店內部職責收斂與 Scene Guard 修復

#### 4.3.1 廢除 Handler 內部城鎮開包行為
- `JewelryWorkshopHandler` 中的 `pre_tidy_done` 與「城鎮背包預先整理」邏輯屬於重複職責且為事故誘因，**予以徹底移除**。
- 背包整理已由 `BagCleaningHandler` 全權保證。`JewelryWorkshopHandler` 啟動時即處於城鎮，直接進行商人金幣排序與進入商店。

#### 4.3.2 修復 Scene Guard 誤判
Scene Guard 僅於「已確認進入建築內部」且「建築特徵完全丟失」時生效。在尚未確認進店前，畫面看見 `door.png` 屬城鎮常態，**絕不能視為防護攔截逃逸的依據**：

```python
# 僅在確信已在商店內部（如已辨識出商人看板、sell_out 或 exit 按鈕）時，若突然看見 door.png 才觸發防護
if self.step_phase in ["SELL_MENU_OPEN", "INSIDE_SHOP"]:
    # 必須同時證明建築內部特徵已全數丟失
    if not self._has_shop_internal_features(screen_img):
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.80)
        if pos_door:
            logging.warning("💎 [珠寶加工廠] 確信已跌出商店回至城鎮大門，安全結束出售流程。")
            self._safe_exit_and_cleanup()
            return
```

---

### 4.4 模組四：懸賞告示牌進場排他性錨點防護

在 `states/handlers/bulletin_board.py` 中，重構進場判定邏輯，**廢除僅以 `pos_quit` 判定在告示牌內之漏洞**：

```python
def _is_inside_bulletin_board(self, screen_img) -> bool:
    """
    排他性驗證是否身處告示牌介面：
    必須滿足：看得到 quit_btn，且必須同時偵測到告示牌專屬特徵之一：
    1. 重置按鈕 (reset.png)
    2. 未接任務圖示 (task.png)
    3. 已接任務圖示 (task_after.png)
    4. 告示牌專屬頂部橫幅
    """
    pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
    if not pos_quit:
        return False

    # 排他性正交特徵錨點檢查
    pos_reset, _ = self.matcher.match(screen_img, "town_building/bulletin_board/reset.png", threshold=0.70)
    if pos_reset:
        return True

    pos_task, _ = self.matcher.match(screen_img, "town_building/bulletin_board/task.png", threshold=0.70)
    if pos_task:
        return True

    pos_after, _ = self.matcher.match(screen_img, "town_building/bulletin_board/task_after.png", threshold=0.70)
    if pos_after:
        return True

    return False
```

在 `BulletinBoardHandler.handle()` 中：
- 若僅有 `quit.png` 但 `_is_inside_bulletin_board(screen_img)` 為 False：
  判定當前畫面為**外部干擾視窗（如殘留背包）**！
  Handler 記錄警告日誌，**僅點擊關閉視窗，絕不切換至 `PROCESS_ACCEPT_QUESTS`，絕不標記 completed**！
- 唯有 `_is_inside_bulletin_board(screen_img)` 為 True 時，方允許轉入 `CHECK_RESET` 或 `PROCESS_ACCEPT_QUESTS`。

---

## 5. 狀態與行為矩陣對照表 (Contract Comparison Matrix)

| 場景與情境 | 重構前 (現況行為) | 重構後 (新契約保證) |
| :--- | :--- | :--- |
| **背包清理結束時** | 呼叫 `trigger_town_subflow_chain`，將 blood 與 jewelry 綁入 Daily 佇列 | 呼叫 `trigger_bag_maintenance_chain`，僅調度獨立的維護任務，與 Daily 脫鉤 |
| **背包滿後獻祭血水** | 視為 `blood_altar`，因無紅點被前置控制器誤當完成跳過，且污染 Daily 紀錄 | 視為 `blood_sacrifice`，不查紅點，正常進入祭壇獻祭；不影響每日領血狀態 |
| **珠寶店進店前** | 在城鎮中再次打開背包整理，觸發 Scene Guard 穿透誤判逃逸，留下開啟的背包 | 移除開包邏輯，直接選店進店；進店前嚴格核驗無覆蓋層 |
| **背包殘留時導航大門** | 盲目點擊 `door.png`，被背包遮擋無效，連續 15 次重試卡死 | 門禁攔截：偵測到 Overlay 先點擊 `quit.png` 關閉，確認無浮層後才點城門 |
| **背包殘留時進告示牌** | 見 `quit.png` 即誤認進屋，OCR 找無任務判定全滿，吞噬當日懸賞 | 專屬錨點門禁：見 `quit.png` 無告示牌特徵時判定為干擾浮層，關閉浮層重試，不吞任務 |

---

## 6. 驗收標準與測試計畫 (Verification & Acceptance Plan)

依據專案規範，本變更需配合聚焦單元測試驗證，主要測試切片如下：

### 6.1 自動化單元測試矩陣
1. **`test_behavior_bag_maintenance_decoupling.py`** (全新測試檔)：
   - 驗證 `BagCleaningHandler` 結束後觸發獨立的 `bag_maintenance` 佇列。
   - 驗證 `blood_sacrifice` 在無紅點狀態下能正常派發 Handler，且不污染 `DailyManager.is_subflow_completed("blood_altar")`。
   - 驗證珠寶店出售與血水獻祭可各自獨立配置啟用。
2. **`test_behavior_jewelry_scene_guard_fix.py`** (修復驗證)：
   - 模擬城鎮背景帶有 `door.png`，驗證珠寶店不會在進店前因門牌誤判而中途逃逸。
   - 驗證珠寶店不再執行額外的城鎮背包開啟。
3. **`test_behavior_bulletin_board_entry_guard.py`** (修復驗證)：
   - 模擬畫面僅有背包視窗與 `quit.png`，輸入 `BulletinBoardHandler`：斷言其不得進入 `PROCESS_ACCEPT_QUESTS`，不得標記 completed，且能正確觸發關閉覆蓋層。
   - 模擬畫面具備 `reset.png` 或 `task.png` + `quit.png`：斷言其成功識別並推進接取任務。
4. **`test_behavior_navigation_overlay_gate.py`** (修復驗證)：
   - 模擬城鎮畫面存在 `door.png` 但同時存在背包浮層：斷言 `NavigationHandler` 優先消除浮層，絕不發出無效的大門點擊。

### 6.2 測試執行命令
```powershell
.venv\Scripts\python -m unittest tests.test_behavior_bag_cleaning
.venv\Scripts\python -m unittest tests.test_behavior_town_subflows
```
*(收尾時提示使用者手動執行全套測試套件)*

---

## 7. 結論與下一步行動

本規格書精確指出了兩個問題同源的深層架構機制，並給出了與現有四大契約 100% 契合的修復架構。

**待確認後之執行順序**：
1. 更新 `docs/todos/future_work.md`，將此規格書作為兩個 Bug 的解耦與修復藍圖。
2. 分支或實作階段依序落實：
   - Step 1: 告示牌專屬排他錨點門禁 (`_is_inside_bulletin_board`)
   - Step 2: 珠寶店移除城鎮開包與 Scene Guard 邊緣防護修復
   - Step 3: 背包維護流水線 (`blood_sacrifice` / `jewelry_workshop`) 與每日福利流水線徹底分離
   - Step 4: 導航層與各 Handler Overlay 關閉驗證閉環
