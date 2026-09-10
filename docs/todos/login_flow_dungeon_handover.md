# 登入後地下城通關場景感知解耦與前置離場路徑規範 (login_flow_dungeon_handover.md) 🧭

> **建立日期**：2026-09-10  
> **上位架構**：[`docs/architecture/project_arch_greenfield_lite_v1.md`](../architecture/project_arch_greenfield_lite_v1.md)  
> **核心契約**：[`docs/architecture/precondition_contracts.md`](../architecture/precondition_contracts.md) (Section 4.4.1, 7, 7.1)  
> **關聯契約**：[`docs/features/navigation/reach_town_contract.md`](../features/navigation/reach_town_contract.md)、[`docs/features/navigation/lobby_scene_contract.md`](../features/navigation/lobby_scene_contract.md)  
> **關聯模組**：[`states/login_flow.py`](../../states/login_flow.py)、[`states/state_machine.py`](../../states/state_machine.py)、[`states/handlers/explore.py`](../../states/handlers/explore.py)、[`states/exceptions/subflows/game_relaunch.py`](../../states/exceptions/subflows/game_relaunch.py)

---

## 1. 架構審查與問題本質 🔍

### 1.1 現場問題重現 (Failure Trajectory)
當使用者啟動腳本（例如以普通關卡 `stage` 模式掛機），而遊戲重連/登入後角色**實際滯留在已通關的地下城畫面 (`dungeons_complete.png`)** 時，系統無法順暢點擊通關並回到大廳，而是陷入以下惡性循環：
```text
2026-09-10 22:51:51,216 [INFO] 👉 [登入流程] 偵測到可能遮擋的彈窗按鈕 [common/ok.png] (相似度: 0.9609)，進行關閉...
2026-09-10 22:52:21,683 [ERROR] ❌ [登入流程] 等待城鎮大門超時 (35 秒) 仍未進入城鎮，認定登入失敗！發起 GameRelaunchSubflow 強制重開自癒...
2026-09-10 22:52:21,686 [INFO] [GameProcess] Terminating target process PID 15764 (taskkill /f /pid 15764)...
2026-09-10 22:52:33,998 [INFO] 🔄 [GameRelaunchSubflow] 重啟完成！轉移狀態至 STATE_UNKNOWN 交由全域掃描與 LoginFlow 接管...
2026-09-10 22:52:39,889 [WARNING] ⚠️ [Watchdog] (第 1 次逾時) 狀態 [UNKNOWN] 已卡住逾時 62.5s (門檻 30.0s)，啟動特徵掃描與輕量復原！
```

### 1.2 架構審查：駁回舊有 Patch 思維
經對照 Greenfield-lite 核心契約審查，原先提出之「在 `login_flow.py` 的白名單內追加 `dungeons_complete.png`」以及「在 `ExploreHandler` 內部補上一組預設 priorities」純屬**局部症狀補釘 (Local Patch)**，嚴重違背架構精神，全數予以駁回：

| 舊提案 (已駁回) | 違反的架構原則 | 架構真相剖析 |
| :--- | :--- | :--- |
| **駁回 Task 1**：在 `login_flow.py` 的 `ready_feature` 補上通關圖標 | **Single Source of Truth 違規**<br>**感知與決策分離違規** | 「遊戲是否載入完成」是**全域感知層 (Perception Layer)** 的責任，絕不允許 `login_flow.py` 封閉維護一套殘缺的私有模板列表！只要畫面上是全域註冊的合法世界場景 (`SceneId != UNKNOWN`)，即代表載入完成。 |
| **駁回 Task 2**：在 `ExploreHandler` 補 `DEFAULT_EXPLORE_PRIORITIES` | **Precondition Contracts 違規**<br>**Maintenance Ownership 違規** | 這不是缺字典 key 的小問題，而是**目標意圖 (Intent) 與世界狀態不符時，缺少前置條件路徑 (Prerequisite Route)** 的架構問題！角色肉身在地下城，外部意圖是關卡，此時關卡意圖的 `AtLobby` 前置條件未成立，系統必須保留原意圖，走完地下城離場前置路徑回到大廳，才能派發目標意圖。 |

---

## 2. Greenfield-lite 契約化架構剖析 🏛️

本問題涉及 Greenfield-lite 四大核心支柱的協同運作：

```text
[點擊登入開始冒險]
       ↓
[全域感知層 SceneDetector / detect_current_state]
   - 移除 login_flow 私有白名單
   - 判定世界場景 SceneId != UNKNOWN ➔ 宣告登入載入閉環
       ↓
[判定 ActiveIntent 與客觀場景差異]
   - 目標意圖 (ActiveIntent): PRIMARY_NAVIGATION (Stage) 或 REACH_TOWN (Town)
   - 客觀場景 (SceneSnapshot): IN_DUNGEON (dungeons_complete.png)
   - 診斷：目標的 Dispatch Precondition (AtLobby / AtTown) 未成立！
       ↓
[Prerequisite Route: 地下城離場路徑 (DungeonExit)]
   - Latch Committed Intent (鎖定並保留使用者的原意圖，不被沖掉)
   - 移交 Maintenance Ownership 給 ExploreHandler
   - 執行點擊通關 dungeons_complete.png
       ↓
[Postcondition Verification (Section 7.1 閉環)]
   - 負向證據：dungeons_complete.png 徹底消失
   - 正向證據：觀測到大廳錨點 (goback_town) 或城鎮錨點 (door)
       ↓
[Safe Point: 前置條件達成 ➔ Dispatch Handler]
   - 角色已回到大廳或城鎮，AtLobby / AtTown 成立！
   - 正式派發控制權給原先等待中的 ActiveIntent Handler
```

### 2.1 登入載入判定：全域感知單一真相契約
- **現狀違規**：[`states/login_flow.py`](../../states/login_flow.py) 的 `_wait_for_town` 採用 35 秒同步阻塞式迴圈，並以私有硬編碼白名單 `ready_feature` 孤立比對，破壞了以幀為單位的 Agent Loop。
- **架構規範**：
  1. 點擊「開始冒險」僅是一次 In-Flight 動作，其 Postcondition 為：
     - **負向證據**：`login/login.png` 消失；
     - **正向證據**：全域感知層判定當前畫面已抵達任何合法且非載入中的世界場景 (`SceneCatalog.is_known_world_scene(scene)`)，包含 `TOWN`、`LOBBY`、`STAGE_SELECT`、`DUNGEON_SELECT`、`IN_DUNGEON`、`BATTLE`、`RESULT` 等。
  2. 登入後的遮擋彈窗（如 `common/ok.png`）屬於通用 Overlay，由全域 Overlay 機制消除，絕不允許由登入流程私自定義世界白名單。
  3. 徹底廢除 `_wait_for_town` 的私有場景白名單，統一回歸全域狀態定位 (`state_machine.detect_current_state`) 或 `SceneDetector`。

### 2.2 前置條件路徑：地下城離場路徑 (DungeonExit Prerequisite Route)
依據 [`docs/architecture/precondition_contracts.md`](../architecture/precondition_contracts.md) 第 4.4.1 節與第 7 節：
- **Intent Commitment 不變量**：
  使用者啟動時承諾的目標（如普通關卡 `PRIMARY_NAVIGATION` 或城鎮子流程 `REACH_TOWN`）代表**系統的長期承諾**，不得因角色身處地下城而直接遺失、取消或退回 `UNKNOWN`。
- **Dispatch Precondition 檢查**：
  - `PRIMARY_NAVIGATION (Stage)` 需要前置條件：`AtLobby` (`SceneId.STAGE_SELECT` 或 `SceneId.LOBBY`)；
  - `REACH_TOWN` 需要前置條件：`AtTown` (`SceneId.TOWN`)。
  - 當前世界為 `IN_DUNGEON` 時，上述前置條件皆**未滿足 (Unsatisfied)**，因此**絕不允許將目標意圖的 Handler 派發上場**，亦不允許將目標意圖的 config（如缺乏 `explore_priorities` 的 stage config）強加在當前世界。
- **維護權優先級 (Maintenance Ownership)**：
  地下城探索是「不可安全任意中斷的 workflow」，擁有高於新意圖的維護權。
  此時系統必須啟動地下城離場路徑：
  1. 保持當前 Intent 處於等待 (Latched / Pending)；
  2. 暫時由地下城領域擁有人（`ExploreHandler`）接管維護權；
  3. 專注執行通關離場動作（`dungeons_complete.png`）；
  4. 唯有在抵達安全點（大廳或城鎮，滿足目標意圖的 Precondition）後，才切換 Config 並派發目標 Handler。

### 2.3 通關確鑿離場後置條件 (Section 7.1 Invariant)
依據契約第 7.1 節，`ExploreHandler` 在執行通關離場時：
1. **點擊 ≠ 完成**：點擊 `dungeons_complete.png` 後保持維護權，不早產切換狀態。
2. **確鑿雙重證據**：
   - 負向：`dungeons_complete.png` 消失；
   - 正向：觀測到大廳錨點（`goback_town.png`）或城鎮錨點（`common/door.png`）。
3. 抵達安全點後，觸發完成結算，通知狀態機「地下城離場前置路徑已完成」，由狀態機接續推進等待中的目標 Intent。

---

## 3. 架構修正實施計畫 (Architectural Action Plan) 🛠️

### Phase 1: 登入載入感知解耦與全域委託 ([states/login_flow.py](../../states/login_flow.py))
- [x] **移除私有白名單**：徹底刪除 `_wait_for_town` 內部硬編碼的 `ready_feature` 列表，改為由全域感知判定。
- [x] **委託全域感知**：在無遮擋彈窗時，直接調用全域感知定位（`state_machine.detect_current_state` 或 `SceneDetector`）。只要識別出任何已註冊之合法世界場景（包括 `IN_DUNGEON`、`TOWN`、`LOBBY` 等），即判定載入完成，立即交棒跳出迴圈。
- [x] **消除誤殺進程**：廢除「35 秒超時就直接 taskkill 遊戲進程」的暴力防禦，超時應降級交由全域 Watchdog / Supervisor 有界復原階梯處理。

### Phase 2: 地下城前置離場機制與意圖保留 ([states/state_machine.py](../../states/state_machine.py))
- [x] **意圖鎖定 (Intent Latching)**：當進入狀態機且客觀世界為 `IN_DUNGEON`，但當前配置為非地下城（如 `stage` 或每日任務）時，**鎖定當前主配置為 pending intent**，不覆蓋。
- [x] **離場維護權委派**：在 `IN_DUNGEON` 狀態下，確保 `ExploreHandler` 獲取足夠的離場探索權能（若當前配置無 `explore_priorities`，提供專用於離場退守的最小探索集，包含 `dungeons_complete.png` 與 `leave.png`），專注於走出副本，嚴禁因缺少 priorities 直接拋錯退回 `UNKNOWN`。
- [x] **Safe Point 派發**：當 `ExploreHandler` 驗證 Section 7.1 離場後置條件成功回到大廳或城鎮時，原 pending intent 之 Precondition 達成，由狀態機平滑銜接目標流程。

### Phase 3: 重啟時間戳與 Watchdog 校準 ([states/exceptions/subflows/game_relaunch.py](../../states/exceptions/subflows/game_relaunch.py))
- [x] **顯式時間戳刷新**：`GameRelaunchSubflow` 結束轉移至 `STATE_UNKNOWN` 時，顯式強制刷新 `machine.last_state_change = time.time()` 與 `consecutive_stuck_count = 0`，防止因原狀態同為 `UNKNOWN` 導致 Watchdog 依據重啟前的舊時間誤判 60s+ 逾時。

### Phase 4: 契約測試與行為驗證
- [x] **登入載入全場景相容性測試**：在 `tests/test_behavior_login_flow.py` 驗證登入後直達 `IN_DUNGEON`、`LOBBY`、`TOWN` 等各類場景時，皆能透過全域感知正確交棒，不再超時殺進程。
- [x] **跨模式地下城離場前置路徑測試**：在 `tests/test_dungeon_relaunch_recovery.py` 模擬於 `stage` 模式下掉入 `dungeons_complete.png`，驗證系統能保留 Stage intent，先由 ExploreHandler 執行通關離場，確鑿抵達大廳後順利派發回 Stage 流程。
