# 每日懸賞任務與常規地下城優先順序修復規格 (Daily Quest vs Dungeon Priority Spec)

> **建議分支名稱**: `fix/daily-quest-dungeon-priority`  
> **上位架構規範**: [Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)  
> **條件語意契約**: [Precondition Contracts](../architecture/precondition_contracts.md)  
> **關聯契約**: [REACH_TOWN Contract](../features/navigation/reach_town_contract.md), [Lobby Scene Contract](../features/navigation/lobby_scene_contract.md), [AGENTS.md](../../.agents/AGENTS.md)

---

## 1. 問題本質與現象還原

### 1.1 使用者提問的深層核心
使用者在終端機日誌中觀察到：已接取 8 項懸賞任務（包含地下城 #2、#1 與關卡 6, 5, 3, 1 任務），但機器人卻未先執行任何一項懸賞任務，反而直接在活動大廳點擊進入地下城頁籤，開始左右滑動尋找 Tier 4 常規貪婪地下城（冰雪洞窟 #6、獸人地堡 #7）。

使用者提出兩個核心疑問：
1. **任務與地下城的優先順序目前怎麼決定的？有沒有統一標準？**
2. **使用者期望先去做完任務，為什麼腳本會先跑去打地下城？**

### 1.2 概念釐清：做任務 vs 刷常規副本
此處必須區分兩個極易混淆的概念：
- **概念 A：懸賞任務內的地下城任務 (Tier 3 Bounty Dungeon Task)**
  - 例如：`清除蜘蛛 (地下城 #2 幽影地穴)`、`史萊姆王的毀滅 (地下城 #1)`。
  - 這是每日懸賞告示牌排程器的一部分，**屬於「做任務」**。
- **概念 B：常規長駐貪婪地下城 (Tier 4 Greedy Dungeon Fallback)**
  - 例如：CLI 輸入允許名單 `[6, 7]` 冰雪洞窟、獸人地堡。
  - 這是玩家在全任務完成或全冷卻時的**背景長駐刷本，屬於「常規活動」**。

👉 **日誌中的真實狀況**：機器人並非在執行「懸賞任務中的地下城任務」，而是**徹底脫軌跳過了全部 8 項懸賞任務，直接掉入 Tier 4 去刷常規地下城**！

---

## 2. 深度對照架構規範：先前方案為何「不符合標準」？

對照 [Precondition Contracts](../architecture/precondition_contracts.md) 與 [Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)，先前的分析雖然定位到現象，但提出的修復草案存在嚴重的**架構違規與反模式**：

### 2.1 違規點一：在 NavigationHandler 底層增加排程判斷（嚴重視反依賴與分層）
- **錯誤草案**：在 `NavigationHandler.handle()` 內部加入：
  ```python
  has_pending_quests = bool(self.machine.quest_scheduler and self.machine.quest_scheduler.get_pending_tasks())
  if not has_pending_quests: ...
  ```
- **違反規範**：
  1. **[Precondition Contracts 第 5 節](../architecture/precondition_contracts.md#L91-L106)**：
     - `Navigation / prerequisite layer` 的責任是「依目的地選一個安全 edge；驗證 prerequisite action postcondition」，**絕對禁止「選擇業務任務」**！
     - `Handler / FSM` 的責任是「已派發 operation 的 phase 與內部 outcome」，**絕對禁止「重做全域任務優先序」**！
  2. **[Greenfield-lite 第 3 節](../architecture/project_arch_greenfield_lite_v1.md#L54-L65)**：
     - 依賴方向必須嚴格只能由上往下：`main -> agent loop -> perception / intent / navigation -> ports`。底層模組（`handlers/navigation.py`）**嚴禁反向依賴上層排程器物件並私自做 Selection 決策**！
  3. **[AGENTS.md 核心原則 3](../../.agents/AGENTS.md)**：
     - 「狀態驅動，拒絕補釘」：嚴禁無視模組邊界隨手插入跨層 `if is_special_case` 補釘。

### 2.2 違規點二：條件語意混淆：把 DEFER 誤當成 Blocking Precondition
- **問題本質**：
  - `BreadCollectionHandler` 在打不開視窗時觸發了 `defer_collection`。
  - 依據 [Precondition Contracts 第 2 & 4 節](../architecture/precondition_contracts.md#L43-L50)：
    > `DEFER` 不是完成；它代表該工作暫時不可用，進入冷卻/退避，稍後再選取。原始 pending fact 仍存在，但**暫時不選取，絕對不應阻斷其他活躍工作**。
  - 然而在現有程式碼中：
    - `BreadCollectionHandler` 逾時退避後未清 `need_bread_collection = False`。
    - `TownSubflowPreconditionController._collection_pending()` 只是盲目檢查 `need_bread_collection`，根本沒有檢查 `navigation_progress.is_deferred(IntentId.COLLECT_BREAD)`。
    - 這導致「處於退避狀態的 Bread」被錯誤當成了「必須立即維持的 blocking precondition」，將城鎮前置條件活鎖（Livelock），高層狀態機因此永遠無法推進至 Tier 3 懸賞任務。

### 2.3 違規點三：以 Config Type 代替真實 Intent 承諾
- **問題本質**：
  - [Precondition Contracts 第 6 節第 3 條](../architecture/precondition_contracts.md#L107-L116) 明確規定：
    > **「不能以 FSM state 或 config type 代替世界 observation 或真實 Intent」**。
  - 系統在啟動 `--mode daily` 時，底層 config 預設繼承了 `type: "mix"`。當城鎮任務在跑前置條件時，保留原 config 的做法讓 `config["type"]` 依舊是 `"mix"`。
  - 結果底層 `NavigationHandler` 就以 `config["type"] == "mix"` 作為事實，擅自跑去大廳點地下城頁籤！

---

## 3. 系統統一標準確立 (Canonical Priority Standard)

### 3.1 跨活動 Tier 階梯不變量
系統排程只有唯一決策者（State Machine 的 `evaluate_next_activity`），嚴格遵守以下階梯：

```text
Tier 1: 城鎮每日速領 (chest -> hero_draw -> blood_altar -> bulletin_board -> jewelry_workshop)
  ↓ (城鎮速領全完成)
Tier 1.5: 深淵魔王討伐 (demon_lords)
  ↓ (深淵魔王全完成/無門票)
Tier 2: 首領 Boss 討伐 (lord_boss)
  ↓ (首領次數耗盡/無門票)
Tier 3: 每日懸賞任務 (QuestScheduler: TaskNode 佇列)
  ↓ (8 項懸賞全完成，或全處於冷卻中)
Tier 4: 常規長駐退守 (自選貪婪地下城 / 黃金古國 / 遺忘荒地關卡)
  ↓ (全冷卻且無長駐打怪)
Tier 0: 基底定時待機 (collect_only)
```

👉 **第一統一標準**：**Tier 3 (懸賞任務) 絕對優先於 Tier 4 (常規地下城)！**
只要懸賞排程器中還有任何一個任務可打，系統的唯一承諾就是做懸賞任務，絕不允許私自退守 Tier 4 刷常規地下城。

### 3.2 懸賞任務內部排序標準
依據 [QuestMapper.get_quest_sort_key](../../utils/quest_mapper.py)：
1. **模式優先**：`地下城懸賞 (0) > 普通關卡懸賞 (1)`
   - **設計意圖**：地下城通關後有 5~35 分鐘冷卻。**先打地下城懸賞，讓冷卻時間在背景倒數，同時去推無冷卻的關卡懸賞任務，達成流水線（Pipelining）最大效益**。
2. **確定性優先**：`確定怪物擊殺計數 (0) > 僅憑通關彈窗核銷 (1)`
3. **層數優先**：`地下城編號大者優先` / `關卡層數大者優先`

---

## 4. 多階段架構重構與修復規格 (Multi-Phase Architecture Blueprint)

為了徹底根治問題且不引入新補釘，依據 Greenfield-lite 與 Precondition Contracts 分為三個明確階段實施：

### Phase 1: 條件語意與退避生命週期收斂 (Collection Deferral & Precondition Unblocking)
- **職責領域**: Intent Lifecycle & Precondition Guard
- **對照契約**: [Precondition Contracts 第 2 & 4 節](../architecture/precondition_contracts.md)
- **具體實作**:
  1. **修正 Defer 狀態清理**:
     - 在 [states/handlers/bread_collection.py](../../states/handlers/bread_collection.py) 的 `missing_count >= 3` 逾時退避分支中，確保呼叫 `defer_collection` 同時同步清除活躍標記：`self.machine.need_bread_collection = False`。
  2. **完善 Precondition 的 Defer 感知**:
     - 在 [states/town_subflow_navigation.py](../../states/town_subflow_navigation.py) 的 `_collection_pending()` 中，增加防禦：
       若 `navigation_progress` 顯示 `COLLECT_BREAD` 或 `COLLECT_DIAMOND` 處於 `is_deferred(...)`，則該 collection 視為已暫緩，**不得阻塞 `TOWN_SUBFLOW` 的前置條件推進**。

### Phase 2: 責任邊界劃分：剝離 NavigationHandler 越權 Selection (Strip Task Selection from Navigation Layer)
- **職責領域**: Navigation Layering & Single Responsibility
- **對照契約**: [Greenfield-lite 第 3 節](../architecture/project_arch_greenfield_lite_v1.md) & [Precondition Contracts 第 5 節](../architecture/precondition_contracts.md)
- **具體實作**:
  1. **拒絕在 NavigationHandler 注入上層依賴**: 嚴禁在 `NavigationHandler` 內部引用 `quest_scheduler` 或 `daily_manager` 進行業務判斷。
  2. **收斂混合模式大廳觸發條件**:
     - 檢查 `NavigationHandler` L1012 的混合模式分支：該分支原本是為了純粹的 `PRIMARY_MODES["mix"]` 獨立掛機設計。
     - 在 `--mode daily` 運作期間，所有主路由均為受管活動（Managed Activities）。高層狀態機在推進任務時，下發的配置必須具有明確的目標導航路徑（如地下城 #2 的專屬 entry 或關卡 6-1 的專屬 entry）。
     - 確保受管活動（`is_daily_pipeline_active()`）期間，底層導航僅嚴格執行當前 `config["navigation_path"]` 或 `ActiveIntent` 指定目標，**徹底移除「看到 mix 就擅自點大廳地下城頁籤切換」的旁路搶跑**。

### Phase 3: 每日懸賞與常規退守調度契約收斂 (Bounty Quest vs Tier 4 Scheduling Invariant)
- **職責領域**: State Machine & Quest Dispatcher
- **對照契約**: [Greenfield-lite 第 4.3 節](../architecture/project_arch_greenfield_lite_v1.md) & [AGENTS.md](../../.agents/AGENTS.md)
- **具體實作**:
  1. **高層調度嚴格把關**:
     - 在 [states/state_machine.py](../../states/state_machine.py) 的 `evaluate_next_activity()` 中，落實不變量：只要 `quest_scheduler.get_pending_tasks()` 存在且未全冷卻，**唯一合法動作就是調用 `check_and_advance_quest_target()` 派發下一項懸賞任務**，絕不允許流向 Tier 4 常規地下城。
  2. **退守與插隊語意化**:
     - 只有在全任務冷卻時，才顯式標記 `is_tier4_fallback = True` 切換至 Tier 4，並武裝 `arm_daily_quest_preemption()`，保證懸賞任務 CD 一到立即在結算安全點（Result Safe Point）插隊切回。
  3. **語意化日誌對齊**:
     - 在日誌中明確顯示 `[Tier 3 每日懸賞: 地下城 #2 (做任務)]` 與 `[Tier 4 常規長駐: 冰雪洞窟 (刷副本)]`，消除使用者對任務與地下城的語意混淆。

---

## 5. 驗證計畫 (Verification Plan)

依據專案測試規範，AI 僅執行聚焦單元測試，嚴禁自行執行全套測試：

1. **聚焦測試 1：Bread Deferral 下 Town Precondition 暢通性測試**
   ```bash
   .venv\Scripts\python -m unittest tests.test_town_subflow_precondition_navigation
   ```
   - 驗證領體力退避後，`chest` 前置條件導航仍能正常運行，不被阻斷。

2. **聚焦測試 2：城鎮子流程行為測試**
   ```bash
   .venv\Scripts\python -m unittest tests.test_behavior_town_subflows
   ```
   - 驗證城鎮子流程佇列推進與完成流程 100% 綠燈。

3. **聚焦測試 3：導航層不越權與懸賞插隊行為測試**
   ```bash
   .venv\Scripts\python -m unittest tests.test_behavior_navigation tests.test_behavior_daily_preemption
   ```
   - 驗證在有未完成懸賞任務或城鎮任務時，導航層不會擅自切換大廳頁籤搶跑 Tier 4 常規地下城。
