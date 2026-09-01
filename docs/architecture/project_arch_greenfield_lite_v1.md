# Greenfield-lite Architecture v1：低負載 24/7 導航 Agent

> 狀態：v1 核心骨架 M1–M6 已實作；全場景感知遷移與 metrics 仍依第 9 節追蹤
> 完整理想版本：[Greenfield Architecture](project_arch_greenfield.md)
> 關係：本文件是完整版本的可交付子集，不取代、不刪除完整版本；未納入 v1 的設計只是延後。
> 範圍：導航、行動確認、最低必要復原，以及支撐低 CPU 長時間運作的感知排程。
> 固定限制：任務順序由使用者寫死；不做戰鬥策略。

## 1. v1 結論

第一版採用：

> **單執行緒 Agent Loop + 單幀 SceneSnapshot + 範圍化 Detector Registry + 單一 ActiveIntent + 簡單 Navigation Table + 單一 InFlightAction + 有界 Progress Recovery**

v1 先解決三件事：

1. 降低每輪不必要的全畫面 CV／OCR 成本。
2. 讓目前意圖擁有唯一決策權，避免 Bread、Diamond、Start 與未知任務互搶控制權。
3. 點擊後必須確認結果；長時間無進展時能退避或重開遊戲。

不一次實作完整 Functional Core、全域 Reducer、事件體系與 Statechart framework。

## 2. 成功定義

- 從任一「已支援且可辨識」場景重新定位，沿既定路徑前往目前 intent 的目的地。
- 每個 tick 最多擷取一張畫面，所有判斷共用該幀結果。
- 不再於每一幀掃描全部 templates，只執行目前 detection profile 允許的 CV／OCR。
- 同一時間只有一個 `ActiveIntent` 與一個 `InFlightAction`。
- 點擊不等於成功；後續畫面符合 postcondition 才算完成。
- 未知任務 fallback 不得清除、覆蓋或提前完成 Bread／Diamond intent。
- 無進展、截圖失敗與戰鬥超時都有上限，最後可重新啟動遊戲。

「任何場景」在 v1 指已登錄於 `SceneCatalog` 且具有辨識 anchor 或合法 fallback 的場景。未登錄畫面一律是 `UNKNOWN`，不得猜測點擊。

## 3. 資料流與依賴

```text
Capture once per tick
  → Perception Scheduler
      ├─ cheap global guards（低頻）
      ├─ scene anchors
      └─ detectors_for(scene family, control phase)
  → Frozen SceneSnapshot
  → ActiveIntent + FixedWorkflow
  → Deterministic Policy / Navigation Table
  → One ActionDecision
  → InputPort.execute()
  → InFlightAction
  → next snapshot verifies postcondition
      └─ timeout → retry / defer / recovery / relaunch
```

依賴只能向下：

```text
main / composition root
  → agent loop
    → perception / intent / navigation / recovery
      → ports
        → capture / matcher / input / process adapters
```

Detector 不點擊；Policy 不做 IO；Input adapter 不理解 intent；底層不得持有上層 runtime instance。

## 4. v1 要做的東西

### 4.1 單幀不可變 SceneSnapshot

最小契約：

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
    detection_profile: DetectionProfileId
```

- 一個 tick 只建立一份 snapshot，建立後不可修改。
- `scene`、`overlay` 與 `element` 分開表達，避免彈窗擴張成大型 FSM state。
- 「本 profile 未檢查」不得當成「元素不存在」；Decision 只能使用 profile 保證的 evidence。
- Handler 不得為同一決策重新逐張呼叫 matcher。

### 4.2 範圍化感知與低負載排程

`DetectorRegistry` 依場景家族與 control phase 回傳有限 detector 集合：

| Profile | 允許的主要檢查 |
| --- | --- |
| `UNKNOWN` | login、town、lobby、loading、battle、result anchors |
| `TOWN` | town anchors、building entrances、diamond |
| `LOBBY` | lobby tabs、bread、goback、目前 primary entry |
| `STAGE_SELECT` | stage list、locked、selected tab |
| `DUNGEON_SELECT` | dungeon list、cooldown、selected tab |
| `LOADING` | battle、lobby、login anchors |
| `BATTLE` | auto、result、defeat；不掃 town、quest、building |
| `RESULT` | retry、continue、exit |

- Detector 優先使用固定 Client ROI；卡片與彈窗內禁止全螢幕掃描。
- 同一 frame、template 與 options 的 matcher 結果必須快取。
- OCR 只在對應 scene／phase 需要讀文字時執行，正常導航預設不跑 OCR。
- 全域 safety guard 保留低頻檢測；登入與重大彈窗不依賴每幀全模板盲掃。
- 互斥頁籤沿用 `match_mutually_exclusive_tabs`，不可退回單張 threshold 判斷。
- 記錄各 profile 的 matcher 次數、OCR 次數與耗時，先建立 baseline，再由 TOML defaults 調整頻率。

降低 CPU 的主要手段是 scheduling、ROI、frame cache 與 OCR gating，不是 Reducer 或 interface 數量。

### 4.3 單一 ActiveIntent 與寫死順序

v1 intent 家族：

```text
COLLECT_DIAMOND
COLLECT_BREAD
PRIMARY_NAVIGATION
```

`PRIMARY_NAVIGATION` 只繼續使用者寫死的 stage／dungeon／既定任務流程，不計算最佳任務。

- 同時只有一個 `ActiveIntent`；固定 precedence 只有一個 owner。
- Start 是 `PRIMARY_NAVIGATION` 的候選 action，不是全域最高優先行為。
- Intent 不因 scene 或 FSM state 改變而消失。
- Intent 只在 completion condition 成立、明確取消或有界失敗後 defer 時改變。
- 未知 quest 降級 Tier 4 只影響 primary workflow，不得修改 collection pending 狀態。
- v1 可從既有 machine flags 建立不可變 `IntentSnapshot`，不建立第二份多 writer queue。

### 4.4 簡單 Navigation Table

使用資料化 adjacency table，不建立通用 graph framework 或 DSL：

```python
@dataclass(frozen=True)
class NavigationEdge:
    source: SceneId
    target: SceneId
    required_element: ElementId
    action: ActionId
    postcondition: PostconditionId
    timeout_key: str
```

第一批導航骨幹：

```text
TOWN ↔ LOBBY
LOBBY ↔ BREAD_WINDOW
TOWN ↔ DIAMOND_WINDOW
LOBBY → STAGE_SELECT → STAGE_LOBBY → LOADING
LOBBY → DUNGEON_SELECT → DUNGEON_LOBBY → LOADING
LOADING → BATTLE → RESULT
RESULT → LOADING / LOBBY
```

Router 只回答「已知目的地的下一步」，不選任務。多條合法 edge 以宣告順序決定；可用小型 deterministic BFS，不做成本評分或路徑學習。既有城鎮建築與特殊子流程先留在原 Handler，經明確入口／出口 scene 與新骨幹共存，不一次重寫。

### 4.5 單一 InFlightAction 與畫面驗證

v1 不建立完整 transaction framework，只建立最小待確認動作：

```python
@dataclass
class InFlightAction:
    action_id: ActionId
    source_frame_id: int
    expected: PostconditionId
    issued_at: float
    attempt: int
    deadline: float
```

- 每輪最多輸出一個 transition、action 或 wait。
- 同時只能有一個 in-flight action；驗證前不得發出第二個業務 action 或切換 intent。
- Action 使用來源 frame 的 Client coordinate；snapshot 過期時重新觀察，不用舊座標。
- 點擊後由新 snapshot 驗證 scene／element／overlay postcondition。
- retry 與 timeout 由 TOML default config 提供，不新增 CLI 參數。

### 4.6 最小 Ports / Adapters

只抽離四個確實需要測試或替換的邊界：

- `CapturePort`：擷取 Client 區域 frame。
- `InputPort`：執行 click／drag／key。
- `ClockPort`：提供 monotonic time。
- `ProcessPort`：啟動、關閉與重新啟動遊戲。

OpenCV matcher 留在 perception adapter；不為每個 helper 建 interface。TOML loader、logger 與 config normalization 沿用既有設施。

### 4.7 有界 Recovery、Defer 與重啟

有效進展只包括：scene／關鍵 overlay 改變、postcondition 成立、intent 完成，或 primary workflow cursor 前進。State 名稱改變本身不算進展。

```text
重新觀察
  → 重試目前 action
  → 重新定位已知 SceneId
  → 關閉已知 overlay
  → collection intent 固定 defer / backoff
  → relaunch game
  → 交由外部 supervisor
```

- Defer 只暫緩失敗 intent，不視為完成，也不清除原始 pending fact。
- v1 只做固定、有界 backoff，不做自適應 scheduler。
- 戰鬥是黑盒；超過 `battle_max_duration_seconds` 直接進入 relaunch recovery。
- 戰鬥上限、capture failure limit、action timeout、retry 與 backoff 全放 TOML defaults。
- Recovery 參數不提供 CLI 覆寫，避免 24/7 行為因臨時參數漂移。

## 5. v1 明確不做的東西

| 不做項目 | 原因 |
| --- | --- |
| 完整 immutable `AgentState` | 先凍結跨層契約；runtime context 由唯一 Agent Loop 擁有。 |
| 全域 Reducer | v1 沒有多 writer；先以單一 owner 與 pure policy 防競爭。 |
| 完整 Event Contract／Event Bus | 使用必要 return value 與少量結果 enum，不建通用訊息設施。 |
| Event Sourcing／永久 replay store | 不屬於低 CPU 導航閉環；事故紀錄沿用獨立規格。 |
| Statechart framework | 控制階段只需小型 enum／phase，不引進第二套流程 owner。 |
| Command Bus／Transaction framework | `InFlightAction` 已涵蓋一次 action 與驗證。 |
| Navigation DSL／plugin framework | 場景與 edge 先用 Python declarative table。 |
| 動態任務排序 | 順序寫死；不做 ranking、Utility、GOAP、HTN 或 PDDL。 |
| 戰鬥策略 | 不做技能、隊伍、裝備、Buff、Boss phase、MCTS、RL 或 simulator。 |
| LLM／VLM runtime controller | 正常導航必須低延遲、可重現、可離線測試。 |
| 一次重寫所有 Handler | 先遷移共用骨幹與 collection 衝突路徑。 |
| 從 `.tres` 熱路徑查完整資料庫 | Metadata 於啟動／離線解析；runtime 只載所需索引。 |

## 6. Runtime 不變量

1. **One tick, one frame**：一輪最多擷取一次畫面。
2. **One frame, one snapshot**：所有決策共用同一不可變 observation。
3. **Scoped perception**：Detector 必須屬於明確 profile，禁止每幀全模板盲掃。
4. **One active intent**：固定工作順序只有一個 owner。
5. **One turn, one decision**：一輪最多一個 transition、action 或 wait。
6. **One in-flight action**：postcondition 未成立前不發第二個業務 action。
7. **Observation is not intention**：看到 Start 不等於應該點 Start。
8. **Intent outlives scene/state**：scene／state 轉移不會自動清除 intent。
9. **Detector has no side effect**：感知層不得點擊、transition 或改 pending flag。
10. **Action is business-blind**：輸入層不知道 Bread、Diamond 或 Quest。
11. **Recovery is bounded**：每一層 retry 都有 TOML default 上限與下一級處置。
12. **Unknown never guesses**：證據不足時等待、重新定位或復原，不猜座標。

## 7. 第一版實作切片

1. **契約與量測**：建立 snapshot IDs、單次 capture、frame cache 與 profile metrics，不改公開行為。
2. **Scoped Perception**：建立 Detector Registry，先遷移 Town、Lobby、Loading、Battle、Result anchors。
3. **Intent 與 Navigation Spine**：建立唯一 precedence 與 table，覆蓋 Diamond、Bread、Start、Stage／Dungeon 衝突。
4. **Action Verification**：建立 InFlightAction，驗證 stale frame、retry、timeout 與 committed action。
5. **Progress Recovery**：接入 no-progress、capture failure、battle hard timeout、fixed backoff 與 relaunch。

每個切片都必須讓未遷移 Handler 繼續運作；同一路徑不得有兩個決策 owner。

### 7.1 M1–M6 落地狀態（2026-09-02）

| Milestone | 狀態 | 落地範圍 |
| --- | --- | --- |
| M1 契約 | 完成 | `SceneSnapshot`、Intent、Decision 與語意 ID |
| M2 共用路由 | 完成 | `NAVIGATING`／`LOBBY` 共用 intent precedence 與 Start commitment |
| M3 Progress | 完成 | `InFlightAction`、collection outcome、TOML timeout／backoff、unknown Quest 邊界 |
| M4 Scoped Perception | 部分完成 | `DetectorRegistry`、單幀 match cache、Lobby profile；其他 profile 保留相容偵測 |
| M5 Navigation Table | 完成 | Diamond、Bread、Start 固定 edge；未引入 graph framework 或 DSL |
| M6 Ports／Recovery | 完成 | Capture／Input／Clock／Process ports、collection escalation、既有 relaunch adapter |

本批次「M1–M6 完成」表示核心骨架與相容接線已可運作，不等同第 9 節所有遷移條件皆完成。後續仍需逐一遷移 Stage、Dungeon、Loading、Battle、Result profiles，加入 detector metrics，並讓已遷移 Handler 完全只消費 snapshot。

## 8. 測試與驗收

### 8.1 行為與感知契約

- 同一 snapshot 與 intent 必須得到相同 decision。
- Bread、Start、goback 同時存在時，Bread intent 只產生 Bread action。
- Diamond intent 未完成時，unknown quest fallback 不得清除它。
- In-flight action 未驗證前不得執行下一個業務 action。
- Action 達 timeout 上限後必須升級 recovery。
- Battle hard timeout 呼叫 `ProcessPort` relaunch，不產生戰鬥策略 decision。
- 一個 tick 只 capture 一次；Battle profile 不執行 Town／Building templates。
- 非文字流程不呼叫 OCR；未檢查元素不標記為確定不存在。

### 8.2 架構檢查

- Detector 不 import mouse／actions。
- Policy／router 不 import OpenCV、Windows API、sleep 或 mutable machine。
- Input／Process adapter 不 import intent 或 navigation policy。
- 檔案最多 300 行、方法最多 60 行、巢狀最多 3 層。
- 日常精準執行業務領域測試；分支收尾前才跑全套測試。

## 9. v1 完成條件

1. Town、Lobby、Stage、Dungeon、Loading、Battle、Result 與 collection window 已登錄 SceneCatalog。
2. 已遷移路徑符合 one tick／one frame／one snapshot。
3. Metrics 證明 detection profile 有縮小工作集，不再每幀掃描全部模板。
4. ActiveIntent、NavigationDecision 與 InFlightAction 各有唯一 owner。
5. Bread、Diamond、Start 與 unknown quest 衝突具有鎖定測試。
6. 已遷移 click 都有 postcondition、timeout 與有界 retry。
7. Collection defer 不遺失 pending fact；成功或 cooldown evidence 才完成 intent。
8. Battle timeout、capture failure 與 no-progress 最終可觸發遊戲重啟。
9. 沒有引入任務排序或戰鬥策略。
10. 完整理想版本保持不變，供後續評估 Reducer、完整事件契約與 Statechart。

## 10. 升級完整版本的觸發條件

只有出現實際需求才升級：第二個合法 state writer；多來源事件無法維持序列化；需要完整狀態重播；command 補償超出 `InFlightAction`；控制生命週期出現多層並行／巢狀狀態；或 navigation edge 必須版本化、外掛化、交由非程式人員維護。

在觸發前，優先維持 v1 的小型、確定性與可量測特性。
