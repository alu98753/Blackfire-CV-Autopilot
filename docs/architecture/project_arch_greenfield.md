# Greenfield Architecture：導航與行動重新設計

> 狀態：理想重建方案，尚未實作
> 前提：允許不受既有 `GameStateMachine`／Handler 結構限制，重新設計核心。
> 不變限制一：任務順序由使用者寫死，不做動態排序、效用評分或自動規劃。
> 不變限制二：不做戰鬥策略；戰鬥只處理進入、進行、結束與異常。

## 1. 結論

若可以重新打掉，我會採用：

> **Functional Core / Imperative Shell + 單執行緒事件迴圈 + 不可變 AgentState + Reducer + 宣告式 UI Navigation Graph + 可驗證 Command Transaction + 分層 Ports/Adapters**

這個方案的核心不是換一套更大的 FSM，而是拆開五種現在容易混在一起的概念：

| 概念 | 回答的問題 | 範例 |
| --- | --- | --- |
| Observation | 畫面現在客觀上有什麼？ | Lobby、Start、Bread、Popup |
| Intent | 現在必須完成什麼？ | `COLLECT_BREAD` |
| Route | 從目前畫面如何走到 intent 的目的地？ | Lobby → Bread Window |
| Command | 本輪唯一要執行什麼？ | Click `common/bread.png` |
| Control State | Agent 現在正在觀察、驗證還是復原？ | `VERIFYING_COMMAND` |

最大的架構選擇是：

- `LOBBY`、`TOWN`、`BATTLE` 是 **Observation／UI graph node**，不是 Agent 控制狀態。
- `COLLECT_BREAD` 是 **Intent**，不是 UI state。
- `CLICK_BREAD` 是 **Command**，不是 Intent。
- `VERIFYING_COMMAND` 才是控制 state。

如此便不會再出現「狀態機在 LOBBY，但意圖是領體力，另一段程式卻因看到 Start 又把 state 改走」的概念衝突。

## 2. 為何不沿用大型畫面 FSM

以每個遊戲畫面建立一個 state，初期直觀，但功能增加後會產生：

- 相同畫面因不同 intent 需要不同動作；
- 一個 intent 必須跨越多個畫面 state；
- popup、loading、collection deadline 與 recovery 形成交叉轉移；
- 每個 Handler 都重新判斷全域旗標；
- state transition 發生了，卻不代表業務有進展；
- 新需求常變成更多特殊 `if` 與雙向 fallback。

Greenfield 方案不讓 FSM 承擔世界模型。FSM 只管理 Agent 本身的執行生命週期；遊戲 UI 關係交由 navigation graph 表達。

## 3. 整體資料流

```text
CapturePort.capture()
        │
        ▼
Perception Pipeline
        │
        ▼
FrameObserved(SceneSnapshot)
        │
        ▼
Reducer ───────────────────────────────┐
        │                              │
        ▼                              │
Immutable AgentState                  │
        │                              │
        ▼                              │
Decision Engine                       │
  ├─ Safety Policy                    │
  ├─ Fixed Intent Policy              │
  └─ Navigation Graph Router          │
        │                              │
        ▼                              │
ActionCommand                         │
        │                              │
        ▼                              │
InputPort.execute()                    │
        │                              │
        ▼                              │
CommandIssued / Verified / TimedOut ──┘
```

整個核心是單執行緒、逐事件處理。Capture、OCR preload 等 IO 可以在 adapter 層背景執行，但所有 domain state mutation 必須序列化回唯一 event loop。

## 4. 分層架構

### 4.1 Ports / Adapters：隔離 Windows 與工具細節

Ports 定義核心需要的能力：

```python
class CapturePort(Protocol):
    def capture(self) -> Frame: ...


class InputPort(Protocol):
    def execute(self, command: ActionCommand) -> ExecutionReceipt: ...


class ClockPort(Protocol):
    def monotonic(self) -> float: ...
```

Adapters 實作：

- Windows client-area screenshot
- Template matcher／OCR
- PyAutoGUI／Win32 mouse and keyboard
- monotonic clock
- TOML config loader
- structured logging

理由：Domain、Reducer、Router 與測試不應依賴 Windows handle、OpenCV、PyAutoGUI 或真實時間。

### 4.2 Perception：從影像產生不可變 Observation

Perception Pipeline 只負責將一張 frame 轉為 `SceneSnapshot`：

```python
@dataclass(frozen=True)
class SceneSnapshot:
    frame_id: int
    captured_at: float
    scene: SceneId
    confidence: float
    elements: Mapping[ElementId, ElementMatch]
    overlays: frozenset[OverlayId]
    active_tabs: frozenset[TabId]
    window_available: bool
```

規則：

1. 一張 frame 只產生一份 snapshot。
2. Snapshot 建立後不可修改。
3. Perception 不讀 ActiveIntent 決定要回報哪些事實。
4. Perception 不點擊、不發 command、不修改 AgentState。
5. 無法可靠判斷時輸出 `SceneId.UNKNOWN` 與 evidence，不猜測 action。
6. 多個元素同時存在是合法 observation，由 Decision Engine 選擇。

### 4.3 Domain State：單一真相來源

所有會影響決策的核心狀態集中為不可變 `AgentState`：

```python
@dataclass(frozen=True)
class AgentState:
    control: ControlState
    observation: SceneSnapshot | None
    active_intent: Intent | None
    in_flight: CommandAttempt | None
    recovery: RecoveryContext | None
    fixed_workflow: FixedWorkflowCursor
    last_progress_at: float
```

不再讓任意 Handler 持有自己的全域 boolean 副本。State 只能由 reducer 接收 event 後產生新版本：

```python
next_state = reduce(current_state, event)
```

理由：

- 只有一個 writer，不會有兩個 Handler 同時清除或覆蓋 intent。
- 每次改變都有明確 event 原因。
- 可以重播 event 測試狀態演進。
- Pause、timeout 與 recovery 的時間補償能集中處理。

這是 event-driven reducer，不要求把所有 event 永久保存成 Event Sourcing 資料庫。

### 4.4 Fixed Workflow：只提供寫死順序

任務順序由一個明確的 `FixedWorkflow` 提供：

```python
FIXED_WORKFLOW = (
    IntentId.COLLECT_DIAMOND,
    IntentId.COLLECT_BREAD,
    IntentId.PRIMARY_NAVIGATION,
)
```

正式順序由使用者決定；上例只表示資料形狀，不替使用者決定實際內容。

Fixed Workflow 只負責：

- 目前是哪個 intent；
- intent 完成後移到寫死的下一個；
- cooldown 尚未到時略過明確不可執行的項目；
- restart 後恢復 cursor。

明確不做：

- 不計算 utility score；
- 不比較哪個任務比較划算；
- 不使用 deadline 動態排序；
- 不由 AI 產生新任務序列；
- 不同時維持多個互相競爭的 active intents。

系統同一時間只有一個 `active_intent`。系統安全／popup recovery 可以中斷執行，但它們不是業務任務排序。

### 4.5 Navigation Graph：描述 UI 可以怎麼走

導航使用宣告式有向圖，而不是把路徑散落在 Handler `if` 中：

```python
@dataclass(frozen=True)
class NavigationEdge:
    source: SceneId
    target: SceneId
    required_element: ElementId
    command_factory: CommandFactory
    expected_outcome: Postcondition
    timeout_seconds: float
```

概念範例：

```text
TOWN --click door--> LOBBY
LOBBY --click bread--> BREAD_WINDOW
LOBBY --click select_stage--> STAGE_SELECT
STAGE_LOBBY --click start--> LOADING
RESULT --click retry--> LOADING
```

Intent 只指定目的地或完成條件：

```text
COLLECT_BREAD → goal: BREAD_COLLECTED_OR_COOLDOWN_CONFIRMED
PRIMARY_NAVIGATION → goal: BATTLE_ENTERED
```

Router 只為目前唯一 active intent 尋找下一個 UI edge。這是「如何到達已確定目的地」的導航，不是任務排序或 GOAP。

選擇 graph 的理由：

- 路徑是資料，可以驗證不可達節點、重複 edge 與缺少 postcondition。
- 同一個 `TOWN → LOBBY` edge 可被多個 intent 重用。
- 新增 UI 路徑不需要增加跨所有 state 的 transition。
- Router 可在畫面跳到意外但已知的 node 時重新定位，不必先猜原 state。

v1 可使用 deterministic BFS／固定 edge order；若存在多條等價路徑，以宣告順序決定，不做效用最佳化。

### 4.6 Decision Engine：固定 precedence，單一輸出

Decision Engine 只在沒有未完成 command 時運作：

```text
1. STOP／PAUSE 等控制事件
2. 既有 in-flight command 的驗證或 timeout
3. Critical overlay／window recovery
4. ActiveIntent 的 navigation edge
5. WAIT_FOR_OBSERVATION
```

這是系統安全 precedence，不是業務任務排序。

輸出只有一個 `Decision`：

```python
@dataclass(frozen=True)
class Decision:
    reason: DecisionReason
    command: ActionCommand | None
```

同樣的 `AgentState` 必須產生同樣的 Decision。Decision Engine 不做 IO，也不修改 AgentState。

### 4.7 Command Transaction：行動必須可驗證

Action 不再是「點完 sleep 後假設成功」，而是帶 precondition、postcondition 與 deadline 的 transaction：

```python
@dataclass(frozen=True)
class ClickElement:
    command_id: UUID
    frame_id: int
    element: ElementId
    precondition: Precondition
    postcondition: Postcondition
    deadline: float
    max_attempts: int
```

生命週期：

```text
PLANNED
  → ISSUED
  → VERIFYING
  ├─ SUCCEEDED
  ├─ RETRYABLE_FAILURE
  └─ TERMINAL_FAILURE
```

執行規則：

1. 同一時間只能有一個 in-flight command。
2. Command 使用產生它的 `frame_id`；若 observation 已過期，重新決策，不使用舊座標。
3. Input adapter 只執行，不判斷業務成功。
4. 成功必須由後續 `SceneSnapshot` 滿足 postcondition 證明。
5. Retry 使用同一 command transaction 的 attempt context，不重新選另一個業務 intent。
6. 超過 retry/deadline 才送出 `CommandTimedOut` 給 reducer。

這能直接防止重複點擊、點擊後被另一條流程搶占，以及 state 已切換但 UI 根本沒改變。

### 4.8 Control Statechart：只管理 Agent 生命週期

控制 statechart 保持很小：

```text
STOPPED
RUNNING
  ├─ OBSERVING
  ├─ READY_TO_DECIDE
  └─ VERIFYING_COMMAND
PAUSED
RECOVERING
```

它不包含 `LOBBY`、`TOWN`、`BATTLE` 等畫面名稱。

狀態責任：

- `OBSERVING`：等待新的 frame。
- `READY_TO_DECIDE`：有 snapshot 且沒有 in-flight command。
- `VERIFYING_COMMAND`：等待 postcondition 或 timeout。
- `PAUSED`：凍結 command deadline，resume 時集中補償。
- `RECOVERING`：執行 bounded recovery transaction。

不使用一個巨型 Handler registry；特殊 UI 流程以 graph edges、postcondition 與小型 domain service 組合。

### 4.9 Recovery：依進度與 command failure 復原

Recovery 不以「state 是否改名」當進度，而使用：

- observation 是否改變；
- command postcondition 是否成立；
- intent completion condition 是否成立；
- 相同 command／route 是否反覆失敗。

建議層級：

```text
重新觀察
  → 重試目前 command
  → 重新定位 UI graph node
  → 關閉已知 overlay
  → intent defer/backoff
  → relaunch game
  → terminate child for supervisor recovery
```

所有 retry、timeout 與 backoff 由 TOML defaults 定義，不提供 CLI 臨時調整，也不散落 magic number。

## 5. 戰鬥在 Greenfield 架構中的邊界

戰鬥視為外部黑盒 scene：

```text
LOADING → BATTLE → RESULT
```

允許的行為：

- 確認已進入戰鬥；
- 必要時啟用既有自動戰鬥按鈕；
- 監控結果畫面；
- 戰鬥硬上限與遊戲重啟；
- 結算後通知目前 intent 已完成一輪。

不允許在此階段加入：

- 技能選擇；
- 隊伍與裝備最佳化；
- 元素、Buff、敵人行為推理；
- Utility、MCTS、Minimax、RL 或 simulator；
- 自動決定該打哪一場戰鬥。

未來戰鬥策略必須是獨立 bounded context，只能透過 `BattleCommandPort` 與事件契約接入，不得污染 Navigation Core。

## 6. 建議目錄

```text
agent/
  application/
    agent_loop.py
    fixed_workflow.py
  domain/
    agent_state.py
    events.py
    reducer.py
    intents.py
    decisions.py
  perception/
    scene_detector.py
    scene_snapshot.py
  navigation/
    graph.py
    graph_catalog.py
    router.py
    policy.py
  execution/
    commands.py
    command_verifier.py
  recovery/
    recovery_policy.py
  ports/
    capture.py
    input.py
    clock.py
  adapters/
    windows_capture.py
    pyautogui_input.py
    opencv_matcher.py
```

限制：

- 每檔單一責任，最多 300 行。
- 方法最多 60 行，巢狀最多 3 層。
- Domain 不 import adapters。
- Reducer、Router、Policy 不 import OpenCV、PyAutoGUI 或 Windows API。
- Adapter 不 import Reducer 或 FixedWorkflow。
- 組裝與 dependency injection 只發生在 application composition root。

## 7. 關鍵事件契約

最小事件集合：

```text
FrameObserved
SceneUncertain
IntentActivated
IntentCompleted
IntentDeferred
CommandPlanned
CommandIssued
CommandVerified
CommandRetryRequested
CommandTimedOut
PauseRequested
ResumeRequested
RecoveryStarted
RecoverySucceeded
RecoveryFailed
```

事件只描述已發生的事，不攜帶可執行 callback，也不直接修改其他元件。

## 8. Bread 活鎖案例在新架構中的流程

Given：

```text
active_intent = COLLECT_BREAD
scene = LOBBY
elements = {START, GOBACK_TOWN, BREAD}
in_flight = None
```

流程：

```text
Router 查詢 COLLECT_BREAD 的 goal
  → 選擇 LOBBY --click bread--> BREAD_WINDOW edge
  → 產生 ClickElement(BREAD, postcondition=BREAD_WINDOW)
  → InputPort 執行一次
  → control = VERIFYING_COMMAND
  → 下一幀若看到 BREAD_WINDOW，CommandVerified
  → intent 繼續執行 collect/confirm transaction
```

`START` 雖然存在，卻不屬於目前 active intent 的合法下一條 edge，因此不可能搶走控制權。系統也沒有 `NAVIGATING → LOBBY` 這種以畫面名稱互推的業務 state transition，原本的活鎖路徑在模型中不存在。

## 9. 測試架構

### 9.1 Pure Core Tests

- Reducer：event 是否產生正確 immutable AgentState。
- Router：每個 scene/intent 是否有唯一合法下一條 edge。
- Graph validation：不可達 goal、重複 edge、缺少 postcondition 必須在啟動時失敗。
- Policy：相同 state 必須產生相同 decision。
- Command verifier：success、retry、timeout 與 stale frame。

### 9.2 Contract Tests

- Capture adapter 產生合法 frame/client rect。
- Input adapter 只執行 command，不修改 domain state。
- Detector 輸出符合 `SceneSnapshot` schema。
- TOML timeout/retry 設定正規化。

### 9.3 Behavioral Tests

- Bread、Diamond 與 Start 同時可見時，只執行 active intent 對應 edge。
- Command 尚未驗證前，不會發出第二個 command。
- 點擊後畫面未改變，會 retry/timeout，不會假設成功。
- 未知 quest fallback 只能改變 FixedWorkflow cursor，不會覆蓋 active collection intent。
- Pause/resume 正確補償 command deadline。
- Battle 超時走 recovery，不產生戰鬥策略 decision。

測試核心不需要 screenshot、sleep 或真實 mouse；只有 perception/adapter contract tests 使用圖片 fixture。

## 10. 這個方案刻意不做的事

- 不採用 Behavior Tree 或 StateTree 作為第二套流程 owner。
- 不採用完整 BDI；只保留單一 explicit active intent。
- 不採用 Utility AI、GOAP、HTN 或 PDDL 排任務。
- 不建立 mutable Blackboard 讓所有模組任意寫入。
- 不讓 LLM／VLM 控制正常 runtime action。
- 不做戰鬥策略與學習模型。
- 不為了抽象而建立 generic plugin framework 或規則 DSL。

## 11. 與現行增量方案的差異

| 面向 | 現行增量方案 | Greenfield 方案 |
| --- | --- | --- |
| UI 畫面 | 多數仍映射為 FSM state | `SceneSnapshot`／navigation graph node |
| 全域狀態 | GameStateMachine mutable fields | Immutable `AgentState` + reducer single writer |
| 導航 | Handler + Policy 漸進抽離 | Declarative graph router |
| 動作 | Handler 點擊後自行追蹤 | 可驗證 command transaction |
| 進度 | state/time 與 handler context | command postcondition + intent completion |
| 復原 | Watchdog 依 state duration | command/intent no-progress escalation |
| 遷移成本 | 低，可逐步導入 | 高，需重寫核心 loop 與現有 handlers |

若目標是近期修正現有 livelock，應採現行增量方案；若確定願意承擔核心重寫、雙軌驗證與較長遷移期，Greenfield 方案會得到更乾淨且更不易再次產生狀態／意圖混淆的長期架構。

## 12. Greenfield 完成定義

1. 所有 domain state 只能由 reducer 更新。
2. 一張 frame 只產生一份不可變 `SceneSnapshot`。
3. 同一時間只有一個 active intent 與一個 in-flight command。
4. UI graph 中每條 edge 都有 precondition、command、postcondition 與 timeout。
5. Router 只導航目前 intent，不排序或發明任務。
6. Agent control statechart 不包含 Town、Lobby、Battle 等 UI 畫面名稱。
7. Input adapter 不理解 intent，Perception 不發 action。
8. Bread/Start 事故無法在模型中形成雙狀態活鎖。
9. 戰鬥維持黑盒邊界，沒有策略決策。
10. Pure core tests 不需要 Windows、OpenCV、真實時間或 mouse。
