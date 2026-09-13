# REACH_TOWN Postcondition Normalization Contract

## 1. Executive Summary & Scope Definition

本規範定義全專案統一的 **`NavigationGoal.REACH_TOWN` Postcondition Normalization Contract**。

在先前的架構演化中，城鎮建築離場（Egress）被局部視為各 Handler 內部或 `TownSubflowPreconditionController` 私有的例外補釘，導致：
1. 各 Handler（`BloodAltar`、`JewelryWorkshop`、`HeroDraw`、`Chest`、`BulletinBoard`、`CollectOnly`、`Navigation`）各自重複實作私有的大廳退回城鎮（`goback_town.png`）與離場邏輯；
2. 業務流程在邏輯完成後未驗證物理畫面即切換 Intent（如 `JewelryWorkshop` 的同幀立即 pop 缺陷），造成物理場景與邏輯狀態漂移；
3. 當 Committed Handler 因點擊偏差誤入其他非目標建築時，共享控制器因 `_committed_workflow_owns_frame()` 阻擋而無法介入，Handler 自身又不認識其他建築，最終誤將業務 Intent 標記為 defer 或跳過，**用懲罰業務邏輯來掩蓋物理定位錯誤**；
4. 現行實作在 `TownSubflowPreconditionController` 中，一旦底層動作逾時即映射為 `ProgressStatus.DEFERRED` 並直接調用 `defer_current_town_subflow()`，導致環境歸一化失敗直接污染並延遲了業務任務。

本規範將問題自「TownSubflow 專屬修補」提升為「以目的地為中心的全域契約 (Destination-scoped Contract)」：
> **任何 workflow 如果要求實體後置條件為 `TOWN`，絕不假設上一個 action/workflow 已把角色帶回城鎮；必須由實際 `SceneSnapshot` 實證。若尚未到 Town，統一經由共用 `NavigationGoal.REACH_TOWN` 歸一化鏈多步復原，且物理歸一化過程嚴禁竄改或延遲原始業務意圖。**

---

## 2. Current Repository Mapping & Empirical Findings

經盤點代碼庫目前實作，獲得以下客觀依據：

### 2.1 Producers & Consumers of `PostconditionId.TOWN`
- **Definition**: [`states/navigation_intent.py`](../../states/navigation_intent.py) 定義 `PostconditionId.TOWN`。
- **Producers**:
  - [`states/navigation_table.py`](../../states/navigation_table.py) 中：
    - `V1_NAVIGATION_EDGES`: `IntentId.COLLECT_DIAMOND` 自 `LOBBY` / `STAGE_SELECT` / `DUNGEON_SELECT` 點擊 `GOBACK_TOWN` 宣告 `PostconditionId.TOWN`。
    - `REACH_TOWN_EDGES`: `NavigationGoal.REACH_TOWN` 自 `TOWN_BUILDING` 點擊 `EXIT_BUILDING_TO_TOWN` 宣告 `PostconditionId.TOWN`；自 `LOBBY` 等點擊 `GOBACK_TOWN` 宣告 `PostconditionId.TOWN`。
- **Consumer**:
  - [`states/navigation_progress.py:187-188`](../../states/navigation_progress.py#L187-L188) 純粹核驗：
    ```python
    if expected == PostconditionId.TOWN:
        return scene.scene == SceneId.TOWN
    ```
    此處職責完全純粹，未混入點擊或決策。

### 2.2 Dual-Layer Contract: `WORLD_READY` vs `REACH_TOWN`
必須明確區分兩層契約，嚴禁混淆：
```text
WORLD_READY (Producer-scoped / System-level)
    ≠
REACH_TOWN (Consumer-scoped / Destination-level)
```
- **Login / GameRelaunch 的真正契約是 `WORLD_READY`，絕非 `TOWN`**：
  檢視 [`states/login_flow.py:46-62`](../../states/login_flow.py#L46-L62)：
  ```python
  if SceneCatalog.is_known_world_scene(scene_info.scene_type):
      if getattr(scene_info, "is_in_dungeon", False) or scene_info.scene_type == SceneType.IN_DUNGEON:
          state_machine.is_in_dungeon = True
      ready_found = True
  ```
  登入或進程重啟的唯一義務是**確認畫面已載入合法遊戲世界 (`WORLD_READY`)**。
  若重啟時角色身在地下城 (`IN_DUNGEON`) 或戰鬥中 (`BATTLE`)，系統必須保持世界狀態以供既有恢復流程接手，**絕對不得強制導向城鎮 (`REACH_TOWN`)**！
- **`REACH_TOWN` 僅適用於真正需要城鎮的消費者 (Town-Requiring Consumers)**：
  只有當下一個即將執行的業務流程明確要求城鎮作為前置條件時（如 `chest`、`hero_draw`、`blood_altar`、`bulletin_board`、`jewelry_workshop`、`bag_tidy`、`collect_diamond`），才發起 `REACH_TOWN` 歸一化。

### 2.3 Current `NavigationGoal.REACH_TOWN` Topology & Source Scenes
[`states/navigation_table.py:192-229`](../../states/navigation_table.py#L192-L229) 中 `REACH_TOWN_EDGES` 現已具備之拓撲邊：
- `SceneId.TOWN_BUILDING` + `ElementId.EXIT_BUILDING_TO_TOWN` -> `SceneId.TOWN` (`ActionId.EXIT_BUILDING_TO_TOWN`)
- `SceneId.LOBBY` + `ElementId.GOBACK_TOWN` -> `SceneId.TOWN` (`ActionId.RETURN_TOWN`)
- `SceneId.STAGE_SELECT` + `ElementId.GOBACK_TOWN` -> `SceneId.TOWN` (`ActionId.RETURN_TOWN`)
- `SceneId.DUNGEON_SELECT` + `ElementId.GOBACK_TOWN` -> `SceneId.TOWN` (`ActionId.RETURN_TOWN`)
- `SceneId.LORD_SELECT` + `ElementId.GOBACK_TOWN` -> `SceneId.TOWN` (`ActionId.RETURN_TOWN`)
- `SceneId.DEMON_LORD_SELECT` + `ElementId.GOBACK_TOWN` -> `SceneId.TOWN` (`ActionId.RETURN_TOWN`)
- `SceneId.DOMAIN_EXPLORE` + `ElementId.EXIT_TO_LOBBY` -> `SceneId.LOBBY` (`ActionId.EXIT_DOMAIN_TO_LOBBY`)

### 2.4 TownSubflow Dispatch & Handoff Gap (JewelryWorkshop Code Evidence)
檢視 [`states/handlers/jewelry_workshop.py:441-464`](../../states/handlers/jewelry_workshop.py#L441-L464)：
```python
pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
if pos_exit:
    self.mouse.click(left + pos_exit[0], top + pos_exit[1])
    self._record_completion()
    self.reset_state()
    self.machine.need_jewelry_workshop = False
    self.last_action_time = now
    self.machine.notify_ui_progress()
    self.machine.pop_and_next_town_subflow()
    return
```
**漏洞依據**：`JewelryWorkshopHandler` 在點擊 `exit_building_btn` 的同幀內，未經任何畫面檢驗即直接執行 `_record_completion()` 與 `pop_and_next_town_subflow()`。下一個 Intent（如 `chest`）被 latch 為 `current_town_subflow`，而下一幀遊戲物理畫面仍在珠寶店內或淡出中。

### 2.5 Duplicated Handler-Local Town Recovery Survey
代碼搜尋顯示，以下 Handler 均在自身內部重複編寫了 `goback_town.png` 點擊邏輯：
- `BloodAltarHandler._ensure_in_town()` ([`blood_altar.py:34-44`](../../states/handlers/blood_altar.py#L34-L44))
- `JewelryWorkshopHandler._ensure_in_town()` ([`jewelry_workshop.py:120-128`](../../states/handlers/jewelry_workshop.py#L120-L128))
- `BulletinBoardHandler._ensure_in_town()` ([`bulletin_board.py:77-84`](../../states/handlers/bulletin_board.py#L77-L84))
- `HeroDrawHandler.handle()` ([`hero_draw.py:47-53`](../../states/handlers/hero_draw.py#L47-L53))
- `ChestHandler.handle()` ([`chest.py:73-78`](../../states/handlers/chest.py#L73-L78))
- `CollectOnlyHandler.handle()` ([`collect_only.py:141-158`](../../states/handlers/collect_only.py#L141-L158))
- `NavigationHandler.handle()` ([`navigation.py:464, 537, 735, 899, 1115, 1204`](../../states/handlers/navigation.py))
**架構評價**：各 Handler 自行檢查大廳並點擊回城，是典型的反向依賴與重複實作（DRY 違規）。

### 2.6 Conflict: Committed Handler Ownership vs Shared REACH_TOWN
檢視 [`states/town_subflow_navigation.py:89-91, 171-182`](../../states/town_subflow_navigation.py#L89-L91)：
```python
def _should_skip_handle(self, flow_key, progress) -> bool:
    if not flow_key or self._committed_workflow_owns_frame(flow_key):
        return True
    ...
def _committed_workflow_owns_frame(self, flow_key):
    target_state = self.machine.state_for_town_subflow(flow_key)
    if target_state is not None and self.machine.current_state == target_state:
        return True
    ...
```
**衝突機制**：
1. 當任務已被 dispatch（如 `current_state == STATE_CHEST`），`_committed_workflow_owns_frame()` 恆為 `True`。
2. 若點擊偏差誤入 `Blood_Altar`，畫面物理上呈現 `Blood_Altar` 房間與 `exitfromhouse_and_to_town.png`。
3. `TownSubflowPreconditionController` 因 committed ownership 跳過處理；`ChestHandler` 則因非寶箱畫面而累計 `not_found_count`，5 幀後觸發 `_defer_subflow("未找到神秘寶箱建築")` 並 `pop_and_next_town_subflow()`。
4. **結果**：原應執行的寶箱任務被錯誤 defer 180 秒，且角色依然留在 `Blood_Altar` 內，將問題推延至下一任務。

### 2.7 Blocker: Normalization Failure Leaking into Business Intent Deferral
檢視 [`states/town_subflow_navigation.py:113-117`](../../states/town_subflow_navigation.py#L113-L117)：
```python
if status == ProgressStatus.DEFERRED:
    self.machine.defer_current_town_subflow(
        TOWN_SUBFLOW_DEFER_SECONDS
    )
    return True
```
**嚴重架構缺陷**：
現行代碼中，`REACH_TOWN` 動作的多次超時直接導致 `ProgressStatus.DEFERRED`，而控制器不分青紅皂白直接呼叫 `defer_current_town_subflow()`！這代表實體層的離場點擊失敗，直接被轉譯為對當前業務 Intent（如 `chest`）的懲罰延遲。

---

## 3. Core Architectural Invariants

### Invariant 1: Destination-Scoped Normalization for Town Consumers
> **REACH_TOWN applies to consumers that require TOWN, not to every producer that happens to finish in the game world.**
>
> 任何需要城鎮作為物理起點的流程，在執行前均進入 shared `REACH_TOWN` 歸一化鏈；非城鎮需求流程（如地下城重啟）絕不被強制回城。

### Invariant 2: Intent Preservation Across Physical Normalization & Independent Failure Domains
> [!CRITICAL]
> **REACH_TOWN normalization owns physical recovery failures independently from the suspended business intent. Exhausting normalization retries MUST NOT, by itself, defer, complete, consume, or replace that business intent.**
>
> 物理位置偏差與動作失敗屬於環境暫態（Transient Environmental Misalignment），與業務領域結果正交。
> Shared `ReachTownNormalizationController` 必須擁有獨立的物理重試與復原階梯，**嚴禁將其重試耗盡映射至 `defer_current_town_subflow()` 或任何業務級的 defer / complete 操作**。
> 例如：目前 Intent 為 `chest`，誤入 `Blood_Altar` 觸發歸一化，在回到城鎮後，系統**必須繼續執行 `chest`**，嚴禁呼叫 `defer_subflow("chest")`，嚴禁 `pop_and_next_town_subflow()`。

### Invariant 3: Progress Tracker vs Pure Policy vs Executor Lifecycle
- **`NavigationProgress`（動作級進展驗證與有界重試記帳 - PROGRESS BOOKKEEPING）**：
  - **MAY**: 追蹤 `deadline`、`attempt` / `failure` 計數、判定狀態（`WAITING` / `TIMED_OUT` / `PROGRESSED` / `DEFERRED`）。
  - **MUST NOT**: 執行點擊 (click)、選擇導航路由 (routing)、跳轉狀態機狀態 (transition)、或僅因實體歸一化失敗而完成/延遲/替換業務 Intent。
- **`ReachTownNormalizationPolicy`（純粹決策 - PURE POLICY）**：
  - 純映射：`SceneSnapshot -> ActionDecision`。
  - 專注回答「若尚未到達 Town，下一動作是什麼」，**無副作用、不點擊、不持有狀態、不發起進展追蹤**。
- **`ReachTownNormalizationController`（多幀執行與生命週期 - EXECUTOR）**：
  - 持有 Policy，驅動 `observe -> policy.resolve() -> click -> progress.begin() -> next snapshot verify -> bounded normalization recovery` 之完整狀態機生命週期。

### Invariant 4: Semantic Separation of Overlay Dismissal vs Building Egress
```text
CLOSE_OVERLAY ≠ EXIT_BUILDING_TO_TOWN ≠ TOWN verified
```
- 現行相容性感知識別（Existing compatibility perception mappings）可能將 `common/quit.png` / `confirm` / `cancel` 暴露為 `ElementId.CLOSE_OVERLAY`；但 `REACH_TOWN` 絕不得單憑這些控制項推論已離開建築或已抵達城鎮。
- `town_building/exitfromhouse_and_to_town.png` 映射為 `ElementId.EXIT_BUILDING_TO_TOWN`，專指自房間型建築點擊門型圖示退場。
- 唯有觀察到 `common/door.png` 等城鎮專屬特徵時，方可認可 `SceneId.TOWN`。

### Invariant 5: Action Postcondition Verification Ownership
> **A transition must not be considered complete until its declared postcondition is observed. The component owning the InFlightAction is responsible for verification.**
>
> 發起轉場動作的組件，必須確保該 action 被明確持有並追蹤至 postcondition 成立：
> - 既有 Handler-local 模式下：Handler 發出 `exit` 點擊後，必須在自身的 `VERIFY_EXIT` 階段追蹤到城門出現後才允許交棒；
> - 共享 Controller 模式下：Controller 發出 `EXIT_BUILDING_TO_TOWN` 後，必須由 Controller 追蹤驗證 `SceneId.TOWN` 成立後才放行目標 Handler。
> 嚴禁任何元件「click 完即放手不管」。

---

## 4. Strategy Comparison: Strategy A vs Strategy B

| 評估維度 | Strategy A: 擴充既有 `TownSubflowPreconditionController` | Strategy B: 抽出純粹 `Policy` 與獨立 `Controller` (採納) |
| :--- | :--- | :--- |
| **職責劃分** | 試圖將非 TownSubflow 需求塞入已有的 TownSubflow 控制器。 | 拆分為純決策 `ReachTownNormalizationPolicy` 與多幀執行 `ReachTownNormalizationController`。 |
| **職責純度 (SRP)** | ❌ **職責混淆 (Smell)**：TownSubflow 模組承擔全域性回城職責，產生命名債與邊界模糊。 | ✅ **邊界清晰**：`Policy` 純決策、`Controller` 管生命週期，`TownSubflowPreconditionController` 僅專注子流程前置條件，委託該共用模組。 |
| **生命週期界線** | REACH_TOWN 的物理歸一化生命週期與子流程紅點判定混在同一方法中。 | `ReachTownNormalizationController` 負責「到 Town 為止」；`TownSubflowPreconditionController` 負責「到 Town 之後是否滿足 dispatch 條件」。 |
| **可測試性** | 測試必須包裝在 TownSubflow 複雜狀態中。 | `ReachTownNormalizationPolicy` 可進行純資料結構單元測試；`Controller` 可進行清晰的 Mock 驗證。 |

### 架構裁決：採用 Strategy B
1. 定義純決策類別 `ReachTownNormalizationPolicy`：負責 `(scene: SceneSnapshot) -> ActionDecision`。
2. 定義執行控制器 `ReachTownNormalizationController`：負責「到 Town 為止」的物理歸一化多幀生命週期，並將 normalization 動作與業務 Intent 隔離。
3. `TownSubflowPreconditionController` 將 REACH_TOWN 階段委託給此控制器，自身僅保留「到達城鎮後」的業務入口與紅點檢查。

---

## 5. Relinquishment Protocol for Committed Handlers

為解決 Failure A（Committed Handler 誤入其他建築），建立最小侵入式的 **Relinquishment Protocol**：

```text
Handler in execution (e.g. ChestHandler)
   │
   ├─ 觀察到自身合法特徵 (e.g. chest building / dialog)
   │    → 正常推進業務 (Retain ownership)
   │
   └─ 連續有界確認 (Bounded Consecutive Confirmation) 未見自身特徵
        │
        ├─ 畫面明確辨識到 EXIT_BUILDING_TO_TOWN 或 GOBACK_TOWN
        │    │ (明確處於非自身之其他房間或大廳)
        │    ▼
        │    Handler 主動 Yield / Relinquish Physical Ownership:
        │    1. 不修改當前 Intent (保留 current_town_subflow = chest)
        │    2. 不呼叫 defer_subflow，不簽核完成
        │    3. 將實體控制權轉移交回 shared REACH_TOWN normalization 路徑
        │       (具體機制可經由 STATE_NAVIGATING 或最小專屬 ownership-release 原語，
        │        前提是不得觸發任何無關的排程搶佔或 intent 變更副作用)
        │    4. Log: "⚠️ [Mislocation Detected] 處於非目標場景，釋放實體所有權交由 REACH_TOWN 歸一化..."
        │
        └─ 畫面為自身特徵遺失且無明確其他場景特徵
             → 維持原 Handler 既有的 bounded retry / defer 機制
```

> **架構原則與門禁細節**：
> 1. **Relinquishment 核心契約**：Handler relinquishment MUST transfer physical ownership to the shared REACH_TOWN normalization path without mutating the suspended business intent. 具體實作僅在經代碼審查確認 `transition_to(STATE_NAVIGATING)` 不會觸發無關排程副作用時方可沿用，否則應引入最小專屬釋放原語。
> 2. **門禁確認幀數**：觸發退讓需滿足「連續有界確認 (Bounded Consecutive Confirmation)」（實作預設 2 幀，平衡畫面閃爍防護與反應速度），此參數屬執行期組態，非硬性架構不變量。

---

## 6. Implementation Slices

為確保改動具備增量性、保行為、可單獨測試與回滾友好，切分為以下 4 個切片：

```text
[Slice 1] JewelryWorkshop Handoff Race Fix (Local VERIFY_EXIT)
    ↓
[Slice 2] Destination-Scoped REACH_TOWN Core (Policy + Minimal Controller)
    ↓
[Slice 3] Committed Handler Mislocation Relinquishment Protocol
    ↓
[Slice 4] Town-Requiring Consumer Integration & Login Boundary Regression
```

### Slice 1: Fix JewelryWorkshop Handoff Race (Local Fix)
- **目標**：徹底修復珠寶店同幀 pop 的具體缺陷。
- **異動**：
  - 修改 [`states/handlers/jewelry_workshop.py`](../../states/handlers/jewelry_workshop.py)：點擊 `exit_building_btn` 後切換至 `step_phase = "VERIFY_EXIT"`。
  - 在 `VERIFY_EXIT` 觀察到 `common/door.png` 後，方可調用 `_record_completion()` 與 `pop_and_next_town_subflow()`。
- **驗證**：單元測試驗證點擊退出後下一幀若未到城鎮，絕不提前交棒。

### Slice 2: Destination-Scoped REACH_TOWN Core (Policy + Minimal Controller)
- **目標**：建立純粹決策與執行解耦的 REACH_TOWN 核心，徹底隔離 normalization failure 與 business intent。
- **異動**：
  - 建立 `ReachTownNormalizationPolicy`（純映射 `SceneSnapshot -> ActionDecision`）。
  - 建立最小 `ReachTownNormalizationController`（管理「到 Town 為止」的 InFlightAction、核驗與有界歸一化重試，重試耗盡絕不調用 `defer_current_town_subflow`）。
  - `TownSubflowPreconditionController` 委託此共用控制器負責 REACH_TOWN 階段；自身專注「到達城鎮後」的 dispatch 與紅點檢查。
  - 補齊多步場景歸一化（Modal over Building -> Dismiss Overlay -> Exit Building -> Town）單元測試。

### Slice 3: Committed Handler Mislocation Relinquishment Protocol
- **目標**：解決 Failure A，守護 Intent Preservation Invariant。
- **異動**：
  - 在 `ChestHandler` 等實體 Handler 的 `INIT` 階段導入 Relinquish 守護：連續有界確認未見自身建築但辨識到 `EXIT_BUILDING_TO_TOWN` 時，釋放 physical ownership（透過經核驗無副作用的狀態轉移或最小專屬原語），交由 shared REACH_TOWN controller 歸一化回城，保留業務 Intent 不 defer。
  - 補足回歸測試：模擬 ChestHandler committed 後畫面為 Blood Altar，斷言其自動釋放 ownership、由 REACH_TOWN 退出、並在城鎮重新派發 ChestHandler。

### Slice 4: Town-Requiring Consumer Integration & Login Boundary Regression
- **目標**：全域邊界對齊與非城鎮登入/重連行為保護。
- **異動**：
  - 嚴格守護 `login_flow.py` 的 `WORLD_READY` 語意：不將 Login 硬改造成城鎮導航器，若在地下城登入則保持地下城狀態。
  - 確保只有在下一個任務要求 Town 時才由狀態機啟動 `REACH_TOWN`。
  - （後續漸進）評估淘汰 Handler-local 的私有 `_ensure_in_town`。

---

## 7. Required Regression Scenarios (Acceptance Tests)

在測試套件中必須包含以下 6 個確定性場景驗證：

### Scenario 1: Login Mislocation with Town Consumer
```text
Given: Login flow completes and observes a valid known-world scene, but physical scene is TOWN_BUILDING.
And: The next intended workflow requires TOWN (e.g. Chest).
Then: Login satisfies WORLD_READY only.
And: Before the Town-dependent workflow executes, shared REACH_TOWN normalization exits the building,
     verifies SceneId.TOWN, and then executes the original intended workflow.
```

### Scenario 2: Login / Relaunch in Dungeon (Negative Boundary Protection)
```text
Given: Login or relaunch completes
When: Physical scene is observed to be IN_DUNGEON
Then: WORLD_READY is satisfied
And: System MUST NOT force REACH_TOWN
And: Existing dungeon recovery / continuation behavior is strictly preserved.
```

### Scenario 3: TownSubflow Handoff Lag
```text
Given: Subflow A (JewelryWorkshop) clicks exit
When: Screen remains in jewelry shop interior on the next frame
Then: Subflow A does NOT pop or hand off
And: Waits until SceneId.TOWN is observed before popping next flow.
```

### Scenario 4: Accidental Building Entry & Intent Preservation
```text
Given: Subflow A (Chest) is committed (current_state == STATE_CHEST)
When: Physical screen is observed to be an unrelated TOWN_BUILDING (exitfromhouse visible)
Then: ChestHandler yields ownership without calling defer_subflow or mutating intent
And: System transitions to STATE_NAVIGATING
And: REACH_TOWN exits building to TOWN
And: ChestHandler is resumed/redispatched from TOWN.
```

### Scenario 5: Already in Town (Zero Redundancy)
```text
Given: A workflow requiring TOWN starts
When: Physical screen is already SceneId.TOWN (common/door.png visible)
Then: REACH_TOWN policy issues no extra clicks
And: Immediately dispatches / continues workflow.
```

### Scenario 6: UNKNOWN Scene Bounded Protection
```text
Given: Physical screen is SceneId.UNKNOWN
When: Observed repeatedly
Then: System bounds observations (bounded retry)
And: Does NOT falsely progress, does NOT blind click, and does NOT consume/defer business intent.
```

---

## 8. Non-Goals

- 本次階段不寫 production code，僅完成架構審查與規範確立。
- 不建 generic graph planner 或 DSL。
- 不引入新的 SceneId 狀態爆炸。
- 不重構所有 Handler 的業務規則。
- 不變更現有日常排程（DailyManager）之業務優先級。
