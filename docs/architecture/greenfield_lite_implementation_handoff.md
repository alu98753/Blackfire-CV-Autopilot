# Greenfield-lite v1 實作交接

> 建立日期：2026-09-02  
> 建立時分支：`feat/greenfield-lite-v1`  
> 建立時 HEAD：`82d859c`  
> 用途：讓後續對話從 repository 的已確認事實繼續工作，不依賴舊對話記憶。

## 1. 新對話的閱讀順序

開始任何架構調整前，依序完整閱讀：

1. [專案規則](../../.agents/AGENTS.md)
2. [Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md)
3. [Navigation Intent Routing Spec](navigation_intent_routing_spec.md)
4. 本交接文件
5. [M1–M6 PARS 開發故事](../storys/greenfield_lite_navigation_m1_m6_pars.md)

發生衝突時，採用以下事實來源優先序：

1. 使用者在當前對話的明確決策
2. `.agents/AGENTS.md`
3. 目前程式碼與測試所呈現的實際行為
4. 本交接文件
5. 兩份架構規格
6. 歷史故事、舊文件與舊對話摘要

規格與實作不一致時，不可默默選一邊；先列出差異，再確認要修正規格或實作。

## 2. 專案目標與 v1 邊界

這是一個低電腦負載、可長時間 24/7 執行的遊戲 Agent。它需要在有限的畫面辨識成本下，從不同場景導航到任務目的地，執行可驗證的動作，並在卡住時有限度重試與復原。

Greenfield-lite v1 只處理目前最需要的兩件事：

- 導航：根據當前畫面與唯一意圖，決定下一個固定路徑動作。
- 行動：每次只執行一個動作，並用後續畫面驗證 postcondition。

v1 明確不做：

- 動態任務排序或效用評分；順序固定寫死。
- 戰鬥策略、Boss 戰術、Buff 選擇最佳化。
- Event Bus、Event Sourcing、完整 immutable `AgentState` 或 Reducer。
- Statechart framework、通用 workflow engine、Navigation DSL 或 plugin framework。
- 規劃演算法、PDDL、HTN、MCTS、RL 或 LLM runtime controller。
- 把 `.tres` metadata 全量轉成 runtime graph。

## 3. 不再重複討論的既定決策

除非新的事故證據證明決策本身錯誤，後續實作應維持：

1. 每個控制回合只接受一份畫面觀察，形成一份 frozen `SceneSnapshot`。
2. 畫面辨識只描述 observation；Detector 不負責 transition、click 或修改 pending flag。
3. 同一時間只有一個 `ActiveIntent`，固定優先序為：
   `COLLECT_DIAMOND > COLLECT_BREAD > PRIMARY_NAVIGATION`。
4. 未知懸賞任務降級為 Tier 4 primary payload，不得清除或覆蓋待領鑽石、體力的 pending facts。
5. Scene／FSM state 可以改變，但 intent 必須存活到成功、冷卻證據、defer 或明確失敗結果。
6. 每回合最多產生一個 `ActionDecision`，同一時間最多保留一個 `InFlightAction`。
7. 點擊不是成功；只有後續 snapshot 符合 postcondition 才能提交進度。
8. 已提交的 Start 在驗證或 timeout 前不得被 collection intent 搶走。
9. 所有 retry、timeout、backoff 與 recovery 都必須有上限。
10. 影響 24/7 復原的預設值放在 `config/defaults.toml`，不新增 CLI 選項。
11. Unknown 不猜測；證據不足時 `WAIT`、重新觀察，累積無進展後才進入有限 recovery。
12. Process recovery 統一經過 `GameRelaunchSubflow`／`ProcessPort` 邊界，不在 Handler 各自發明重啟方式。

## 4. M1–M6 已完成內容

| Milestone | Commit | 已完成的核心內容 |
| --- | --- | --- |
| M1 Contracts | `589ac9a` | `SceneSnapshot`、`IntentSnapshot`、`ActiveIntent`、`ActionDecision` 與語意 ID |
| M2 Shared routing | `605e2ef` | `NAVIGATING`／`LOBBY` 共用 intent policy，統一 collection 與 Start precedence |
| M3 Progress | `8f9ebae` | `InFlightAction`、postcondition、collection outcome、defer/backoff 與 pending preservation |
| M4 Scoped perception | `ecbaaf2` | `DetectorRegistry`、profile detector gating 與單幀 match cache 基礎 |
| M5 Navigation table | `400793b` | Town／Lobby 固定 edge 改由 declarative `NavigationTable` 決定 |
| M6 Ports/recovery | `4a48ba2` | Capture／Input／Clock／Process ports，collection recovery 統一進入 relaunch boundary |

M1–M6 的「骨幹與 contract」已完成，不應重新建立另一套平行模型。這不等於所有 legacy Handler 都已遷移完成。

## 5. 目前實際模組對照

| 責任 | 目前實作 |
| --- | --- |
| Scene 與 element contract | `utils/scene_snapshot.py` |
| Scoped detector registry | `utils/detector_registry.py` |
| Legacy `SceneInfo` 偵測與 frame-local cache | `utils/scene_detector.py` |
| Intent、decision、postcondition contract | `states/navigation_intent.py` |
| Legacy machine fields → intent policy bridge | `states/navigation_routing.py` |
| 固定 Town／Lobby navigation edges | `states/navigation_table.py` |
| In-flight、timeout、defer、backoff | `states/navigation_progress.py` |
| Collection outcome boundary | `states/handlers/collection_progress.py` |
| 共用導航 consumers | `states/handlers/navigation.py`、`states/handlers/lobby.py` |
| Runtime ports 與既有 adapter | `runtime/ports.py` |
| Composition 與 recovery owner | `states/state_machine.py` |
| TOML-only runtime defaults | `config/defaults.toml` 的 `[navigation]` 與 `[global]` |

目前 navigation defaults：

```toml
[navigation]
action_timeout_seconds = 5.0
action_max_attempts = 3
collection_backoff_seconds = 60.0
collection_recovery_failure_limit = 3

[global]
battle_max_duration_sec = 900.0
```

## 6. M1–M6 後的重要事故修正

這些修正是目前架構行為的一部分，新工作不可倒退：

| Commit | 行為保證 |
| --- | --- |
| `2f09cd2` | Lord Boss 結算不被地下城 recovery anchor 誤導；完成只在回到 Lord panel 後提交 |
| `2db6f34` | 寶箱子流程只有看到下樓或地下城完成 anchor 才算完成 |
| `e096630` | Town 偵測到 Door 時，primary intent 可再次走 Town → Lobby；in-flight action 需驗證，避免回城後活鎖 |
| `02e2fb7` | 寶箱確認按鈕以閉環方式重點到消失，仍受整體 timeout 保護 |

上述事故共同顯示：不能把「辨識到可點按鈕」、「已經點擊」或「Handler 返回」直接視為 workflow 完成；完成條件必須是下一個可信任場景或 terminal anchor。

## 7. 已完成與尚未完成的界線

### 7.1 已完成

- Diamond、Bread、Primary 的唯一 intent precedence。
- Town／Lobby 的主要固定 edge 與 Start commitment。
- Collection pending preservation、outcome、defer、backoff 與 recovery escalation。
- 導航 action 的 in-flight 驗證與有限重試。
- Lobby 為主的 scoped perception 接入與 detector registry 基礎。
- Battle hard timeout、capture failure 與 collection failure 的 relaunch 邊界。
- Unknown Quest → Tier 4 fallback 不破壞 collection facts。

### 7.2 部分完成

- `SceneSnapshot` 目前主要由 legacy `SceneInfo` adapter 產生，尚未成為所有 Handler 的唯一輸入。
- `DetectorRegistry` 已定義多種 profile，但明確接入與驗證主要集中在 Lobby；不可假設所有場景已全面 scoped。
- `NavigationTable` 目前只涵蓋 Diamond、Bread、Primary 的 Town／Lobby 固定 edge；不是完整遊戲 graph。
- Ports 已包住關鍵 runtime 邊界，但現有 Handler 仍保留 legacy object 與 helper 呼叫。
- Progress log 已有 intent、scene、action 與 reason；完整 detector cost／profile metrics 尚未建立。

### 7.3 尚未完成

- Stage Select、Dungeon Select、Loading、Battle、Result 全部改為只消費 frozen snapshot。
- 所有 Handler 移除同一 tick 內的直接 matcher 重掃。
- 對每個 scene family 建立可量測的 detector budget 與 CPU baseline。
- 清楚定義「完整 v1 migration 完成」是導航骨幹完成，或所有相關 Handler 都完成 snapshot migration。
- 移除已被 adapter 取代的 legacy flags；目前不可提前刪除，仍有相容性用途。

## 8. 下一個建議的小切片

建議先做「M7：Primary navigation scene contract expansion」，仍只處理導航與行動，不碰探索策略或戰鬥策略。

建議範圍：

1. 盤點 Stage Select 與 Dungeon Select 導航所需的最小 `SceneId`、`ElementId`、postcondition。
2. 將兩者的固定入口 edge 加入既有 `NavigationTable`，不建立通用 graph 或 DSL。
3. 讓對應 Handler 的 route decision 消費同一份 snapshot；專屬子流程暫時仍由既有 Handler 負責。
4. 每次只遷移一個 scene family，先 Stage Select，再 Dungeon Select。
5. 為每個 edge 加入 Given／When／Then 精準行為測試，包括返回 Town／Lobby 後可重新進入。
6. 記錄遷移前後每 tick matcher 次數，確認 scoped perception 確實降低重複 CV。

開始 M7 前先和使用者確認：M7 是否是當前最高優先序。若當前有可重現的 runtime 卡死事故，先修復事故並把新的 invariant 回寫本文件，再繼續架構遷移。

## 9. 下次需要和使用者討論的問題

以下尚未形成最終決策，不可自行假定：

1. v1 的完成定義：導航骨幹完成即算 v1，或 Stage／Dungeon／Loading／Battle／Result 全部 snapshot-only 才算。
2. `SceneId` 粒度：Stage／Dungeon 的選擇頁、卡片頁、確認頁是否各自獨立 scene，或以 scene + overlay 表達。
3. 子流程是否使用全域 `InFlightAction`：寶箱、Lord Boss 等局部閉環目前由 Handler 自己持有 phase；是否要納入同一個 progress owner 尚未決定。
4. Detector budget 的驗收方式：以 matcher 次數、平均 tick latency、CPU 使用率，或三者共同設門檻。
5. Navigation Table 的邊界：只放跨 scene 固定 edge，還是也放同 scene 的 tab／popup 動作。
6. Legacy flags 的移除時點與相容期；在 owner 尚未完整遷移前不可直接清除。
7. 是否將常見 terminal anchor verification 抽成共用 action contract；目前已有 `click_and_wait_until_gone`，但場景到達驗證仍分散。

## 10. 工作與測試規則

- 修改程式前先確認工作樹，保留所有使用者既有變更。
- 不使用 `git add .`、`git add -A` 或 `git commit -a`。
- 每個小切片只執行直接相關的 test method、test class 或 test file。
- AI 永遠不執行完整測試套件。
- 所有工作完成後，由使用者執行一次完整測試並回報失敗。
- 純 `docs/**/*.md` 或 `.agents/AGENTS.md` 修改不跑 Python 測試，只做 `git diff --check` 與變更範圍確認。
- Commit 必須精準指定本次檔案；除非使用者要求，不自行 merge。

## 11. 建立本文件時的工作樹注意事項

建立本文件前，工作樹存在一個使用者未追蹤檔案：

```text
新增 文字文件.txt
```

此檔案不是 Greenfield-lite 工作的一部分，不可讀取、修改、刪除、stage 或 commit。

分支上的其他 Greenfield-lite、Lord Boss、Dungeon 與 navigation 修正均已在建立時的 Git 歷史中。後續對話仍必須重新執行 `git status --short`，不可假設工作樹狀態沒有改變。

## 12. 建議的新對話開場

```text
請先完整閱讀：
1. .agents/AGENTS.md
2. docs/architecture/project_arch_greenfield_lite_v1.md
3. docs/architecture/navigation_intent_routing_spec.md
4. docs/architecture/greenfield_lite_implementation_handoff.md

以目前程式碼、測試與 handoff 為事實來源，不要重做 M1–M6。
先檢查 handoff 與目前 Git 狀態是否仍一致，再列出規格與實作差距。
這個專案目前只做導航與可驗證行動，不做動態任務排序或戰鬥策略。
AI 不執行完整測試；實作中只跑最小相關測試，最後提醒我執行完整測試。
在修改前，先和我確認下一個最小切片是否採用 handoff 建議的 M7。
```
