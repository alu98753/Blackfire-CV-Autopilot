# 任務 Precondition 導航：Chest-first 設計筆記

> 分支：`fix/chest-precondition-navigation`
>
> 上位原則：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)
>
> 第一個行為切片只驗證 Daily 的 `chest`；`REACH_TOWN` 導航能力從一開始就由
> `chest`、`hero_draw`、`blood_altar`、`bulletin_board`、`jewelry_workshop` 共用。

## 實作狀態（2026-09-10）

本文件描述的 Chest-first 切片已完成：queue head 會先移入
`current_town_subflow`，但不會先換 config 或切入任務 Handler；共用 controller 取得
`REACH_TOWN` 證據後才 dispatch。五個任務的入口差異集中在
`states/town_subflow_registry.py`，共用路徑只在 `states/navigation_table.py` 登錄一次。

目前已覆蓋 Town、Town Building、Lobby／選擇頁、Domain、Battle、Result、Dungeon
Exploring 與 `common/quit.png` 前景視窗；無法達成 navigation postcondition 時採有界重試，
耗盡後 defer 180 秒，不會無限重點或把任務標成完成。

### 評閱後補正（2026-09-10）

- `TOWN` 已成立但入口建築未辨識，不再無限制 `WAIT`；連續
  `navigation.town_entry_wait_max_observations`（預設 5）次觀察仍無入口 evidence 會
  defer 180 秒，避免主迴圈靜默空轉。
- `task_complete` 與 `backpack_full` 是全域高優先 popup，先於 Town intent 處理，避免
  底層 Lobby／Town anchor 搶走點擊。
- `bulletin_board` 的無紅點意義由其 Handler 判定；Router 只要求看見告示牌建築，不會
  因無紅點先行 defer。
- 當一項 Town subflow 結束而下一項僅被選中時，FSM 先恢復 `NAVIGATING` 與
  `primary_config`，避免保留上一個 Handler 的 state／config 身分。
- 目前已登錄的通用前景關閉證據為 `common/confirm.png`、`common/ok.png`、
  `common/cancel.png`、`common/quit.png`。倉庫目前沒有 `bag/close.png` 或
  `common/close.png` 資產；新增該類 template 時必須加入同一個 registry，不能在
  Handler 內私自處理。

## 1. 問題不是 Chest INIT 本身，而是過早派發

目前啟動 Daily 的實際路徑：

```text
runtime/bootstrap.py
  -> evaluate_and_schedule_daily_pipeline()
  -> start_subflow_queue(["chest", ...])
  -> pop_and_next_town_subflow()
  -> config 立即換成 chest
  -> current_state 立即換成 CHEST
  -> ChestHandler.INIT 假設畫面已是城鎮
```

這條路徑在第一張畫面擷取前就會執行。此時 state 仍是 `UNKNOWN`，程式並不知道
玩家實際位於 Town、Building、Battle、Result、Domain、Lord、Dungeon，或某個已開啟
的 Bread／Bag 視窗。

`ChestHandler.INIT` 的真實前置條件是：

```text
scene == TOWN
AND chest building 可見
AND chest building 的紅點可見
```

目前若不在 Town，Handler 連續 5 輪找不到 chest building 後會呼叫
`pop_and_next_town_subflow()`。這條路徑：

- 不會呼叫 `defer_subflow("chest")`；
- 不會標記 `completed_today`；
- 會把 chest 從本輪記憶體 queue 移除；
- 只能期待未來某個 scheduler 邊界從 DailyManager 再次派發。

因此目前不是明確的「等待 precondition」，而是「本輪靜默跳過，未來碰運氣重派」。
180 秒 defer 只發生在「已找到 chest building，但沒有紅點」或領取驗證失敗時。

另外，派發時過早把 config 換成 `chest`，會讓 SceneDetector／既有 Handler 失去原本
Battle、Dungeon、Domain 等活動 context，增加錯誤定位與錯誤 recovery 的風險。

## 2. Chest-first 的正確語意

「想執行 chest」應先建立一個能跨 scene／state 存活的待辦意圖，而不是直接進入
`STATE_CHEST`：

```text
request CHEST
  -> 保留原活動 config
  -> 重新觀察目前 scene
  -> 沿已登錄的安全路徑前往 TOWN
  -> 在 TOWN 驗證 chest building + red dot
  -> precondition 成立後才套用 chest config 並 delegate ChestHandler
  -> 成功／冷卻證據／明確 defer 後才結束本次 intent
```

Chest Handler 只負責「已到入口後」的建築內 phase：進入、領取、確認、退出。它不應
負責猜測自己現在在哪裡，也不應自己導航整個世界回城。

## 3. 與 Greenfield-lite 對齊的 owner 邊界

### 3.1 Scheduler 只提出工作，不直接切 Handler

`DailyManager` 與 scheduler 只負責回答「chest 尚待執行」。它們不得用 config 或 FSM
state 假裝 precondition 已成立。

`town_subflow_queue` 的首項在 precondition 成立前不得遺失。實作上會把首項移入顯式的
`current_town_subflow` active slot，剩餘項目才留在 queue：

```python
current_town_subflow = "chest"
town_subflow_queue = ["hero_draw", "blood_altar", ...]
```

第一階段只有：

```text
flow_key = chest
navigation_goal = REACH_TOWN
```

不要新增 `ChestNavigationHandler`、第二套 queue engine 或通用 DSL。

### 3.2 ActiveIntent 是唯一業務決策 owner

城鎮子流程待辦應成為既有 intent adapter 的一種 primary payload／明確的 town-subflow
intent，而不是由 `ChestHandler`、scheduler、ResultHandler 各自判斷一次優先級。

固定 precedence 延續現行契約：

```text
已提交的 InFlightAction
  > critical safety / recovery
  > COLLECT_DIAMOND
  > COLLECT_BREAD
  > pending town subflow (chest-first)
  > 一般 PRIMARY_NAVIGATION
```

若 Start 已送出或戰鬥已開始，chest intent 必須保留，但只能在下一個安全點要求離場；
不得中途亂點，也不得把戰鬥當成 chest precondition failure。

### 3.3 Navigation Policy 決定下一步，Handler 執行一次

Policy 只消費同一張不可變 `SceneSnapshot`，回傳一個 semantic decision。輸入層仍只
負責執行 click；Detector 不得 transition 或修改 queue。

```text
SceneSnapshot + ActiveIntent + InFlightAction
  -> one ActionDecision
  -> one click / delegate / wait / recover
```

到達 `TOWN` 只是 navigation postcondition；`chest building + red dot` 才是進入
ChestHandler 的 dispatch precondition。兩者不可混為同一個「找不到就完成」。

### 3.4 依「目的地」共用導航，不依「任務名稱」複製 edge

五個 town subflow 的共同需求都是 `REACH_TOWN`。Router 不需要知道要求回城的是
chest 還是 jewelry workshop：

```text
TownSubflowRequest(flow_key="chest", goal=REACH_TOWN) ─┐
TownSubflowRequest(flow_key="hero_draw", goal=REACH_TOWN) ─┤
TownSubflowRequest(flow_key="blood_altar", goal=REACH_TOWN) ├─> 共用 REACH_TOWN route
TownSubflowRequest(flow_key="bulletin_board", goal=REACH_TOWN) ─┤
TownSubflowRequest(flow_key="jewelry_workshop", goal=REACH_TOWN) ┘
```

因此不應在 `states/navigation_table.py` 為五個 `flow_key` 各登錄一套相同 edge。建議讓
`NavigationEdge`／Router 以 `NavigationGoal.REACH_TOWN` 查找共用路徑：

```python
class NavigationGoal(str, Enum):
    REACH_TOWN = "reach_town"


def next_edge(scene: SceneSnapshot, goal: NavigationGoal) -> NavigationEdge | None:
    ...
```

只有當 `REACH_TOWN` postcondition 成立後，才由 `TownSubflowDispatcher` 根據
`flow_key` 查詢入口規格並 delegate 對應 Handler。也就是：

```text
Navigation Table：目前 scene 要怎麼到 Town？
Town Subflow Registry：到 Town 後，這個任務的入口證據與 Handler 是什麼？
```

這不是建立通用 graph／DSL，而是把「去哪裡」與「到達後做什麼」分離。現有
既有 `TOWN_SUBFLOW_CONFIG_MAP` 繼續負責 state transition 時套用 config；新 registry
只保存 Town 入口證據與紅點政策，避免 navigation table 同時承擔任務派發責任。

## 4. 共用 `REACH_TOWN` 導航矩陣

| 已確認場景 | 決策 | 下一個 postcondition |
| --- | --- | --- |
| 任一場景 + 已登錄的 Bread／Bag／Diamond／其他前景分頁 | 優先點擊已登錄的 confirm／ok／cancel／quit | overlay 消失；重新觀察底層 scene |
| 任一 Town Building + 無前景分頁 | 點擊 `town_building/exitfromhouse_and_to_town.png` | `TOWN` |
| `TOWN` 且 chest building + red dot | delegate `ChestHandler` | handler phase 前進 |
| `TOWN` 且 building 可見、紅點不存在 | defer chest，保留未完成事實 | `retry_at` 已建立 |
| `TOWN` 但 building 尚未被可靠檢查 | 最多 WAIT 設定次數（預設 5），仍無 evidence 則 defer | `retry_at` 已建立 |
| Lobby／Stage Select／Dungeon Select／Lord Select／Demon Lord Select | 點擊 `goback_town` | `TOWN` |
| `DOMAIN_EXPLORE` | 點擊 `exit_to_lobby` | Lobby |
| `BATTLE`／`LOADING` | 保留 intent，讓已提交活動繼續 | `RESULT` 或可退出場景 |
| 一般關卡的 `RESULT` | town intent 已等待時選擇 exit，不得 retry | Lobby／Town |
| 尚在 Dungeon workflow 內的戰鬥 `RESULT` | 仍交回 `DUNGEON_EXPLORING`，不得因 town intent 提早 exit | 下一層／探索主畫面 |
| `DUNGEON_EXPLORING` | 保留 intent，繼續既有探索直到完整結束；不得為回城中途 leave | 探索完成後的 Result／Dungeon Select／Lobby |
| `UNKNOWN` | WAIT、重新定位；達有界上限才 recovery | 已知 scene 或 relaunch |

矩陣的固定 precedence 是：已提交 `InFlightAction` 驗證 → 前景 overlay close／quit →
已提交活動生命週期（尤其 Dungeon Explore／Battle）→ `REACH_TOWN` edge → Town 任務入口
precondition。即使玩家在 Building 內打開 Bread／Bag／Diamond 分頁，也必須先關閉前景
分頁；下一張 snapshot 確認分頁消失後，才允許點擊 building exit。

每個 click 都必須建立 `InFlightAction` 並由下一張 snapshot 驗證；不能因呼叫 click 就
認定已回城。

## 5. 感知範圍與限制

「玩家可能在任何地方」只能承諾為「任何已登錄且可辨識的場景」。目前資料契約已有
多個 `SceneId`，但實際 detector／全域定位仍未完整產生所有場景證據：

- `SceneId` 已宣告 Loading、Battle、Result、Domain、Dungeon 等；
- `SceneDetector` 目前主要完整覆蓋 Town、Lobby tabs、collection windows 與部分
  Dungeon／Domain；
- `detect_current_state()` 仍以另一套 legacy 全域掃描辨識 Battle、Defeat、Domain；
- victory Result 已加入啟動重定位 anchor；Town Building／Bag 等使用
  `common/quit.png` 作為前景 overlay evidence。
- `town_building/exitfromhouse_and_to_town.png` 已映射成
  `ElementId.EXIT_BUILDING_TO_TOWN`，供所有 town-return intent 共用。

因此不能只在 Chest INIT 前加一個 `if not town: transition_to(NAVIGATING)`。那會把
辨識缺口藏起來，並讓 NAVIGATING 在未知畫面使用 primary config 猜路。

第一階段必須至少補齊 chest 驗收場景所需的 anchor；未登錄場景保持 `UNKNOWN`，遵守
「Unknown never guesses」。

## 6. 已完成的實作切片

### Slice 1：鎖住事故，不改 UI 行為

- 新增公開行為測試，重播 Daily 啟動時分別位於 Town、Lobby、Battle、Result。
- 證明 scheduler 不會在沒有 Town evidence 時直接進 `STATE_CHEST`。
- 證明 chest 尚未成功／冷卻／defer 前，pending fact 與目前 queue head 都不會消失。

### Slice 2：共用 REACH_TOWN goal + Chest dispatch precondition

- 將 queue 的「選中」與「pop」拆開；新增明確 active town-subflow request。
- 啟動時先定位；Town 才驗證 building + red dot。
- Lobby／選關頁使用一套以 `REACH_TOWN` 為 key 的 Navigation Table 回 Town。
- 五個 town subflow 共用這套 route；`navigation_table.py` 不登錄 flow key。
- 到達 Town 後才透過既有 `transition_to()` hook 套用 chest config。
- ChestHandler 移除「非 Town 找不到 5 次就推進下一任務」的語意。

### Slice 3：Battle／Loading／Result 安全點

- 戰鬥中保留 chest intent，不搶已提交 action。
- 一般關卡 Result 的 `should_exit_battle` 納入 pending town-subflow intent，確保點 exit
  而非 retry。
- Dungeon 內部戰鬥 Result 仍由 Dungeon workflow 擁有；尚未完成整趟探索時不得套用
  上述一般關卡離場規則。
- 離場 postcondition 成立後回到 Navigation Policy，不能由 ResultHandler 直接進 Chest。
- `DUNGEON_EXPLORING` 保留 intent 並繼續探索至完整結束，不因 town goal 中途離場。

### Slice 4：Domain／Building／已開啟分頁

- 將前景分頁 close／quit 登錄為 overlay action，優先於底層 scene routing。
- Building 在前景分頁關閉後，統一使用
  `town_building/exitfromhouse_and_to_town.png` 回 Town。
- Domain 沿 `exit_to_lobby -> goback_town` 返回 Town。
- 一 tick 一動作，一律驗證 postcondition。
- 補齊有界 retry、defer 與 recovery；禁止座標猜測。

### Slice 5：推廣其他城鎮子流程

共用 route 不需等待 chest 完成才存在；在 chest 行為驗證穩定後，其他任務只新增／確認
聲明式入口規格：

```text
chest             -> handler state + building evidence + red-dot policy
hero_draw         -> handler state + tavern evidence + red-dot policy
blood_altar       -> handler state + altar evidence + red-dot policy
bulletin_board    -> handler state + board evidence；無紅點 outcome 由 Handler 判定
jewelry_workshop  -> handler state + workshop evidence + 專屬入口政策
```

所有規格的 navigation goal 都是 `REACH_TOWN`。不同子流程只聲明入口 evidence、
Handler state 與「無紅點」的 outcome；共用 Router 不知道具體 flow key。

## 7. Chest 驗收條件

1. Daily 從 Town、Lobby、Battle、Battle Result、Domain、Demon Lord、Lord、Dungeon、
   Bread 視窗、Bag 視窗啟動時，chest pending 都不會遺失。
2. 沒有 `TOWN` evidence 時絕不執行 chest building／red-dot 判定。
3. 到達 Town 但沒有紅點時才允許建立 180 秒 defer；這不是完成。
4. 只有領取後 free button 消失、出現 cooldown evidence，或完成離場驗證時紅點已消失，
   才標記完成。
5. Battle 中不強制退出；一般關卡 Result 安全點必須 exit，不得 retry。
6. Dungeon Exploring 必須自然探索至完整結束，pending town subflow 不得觸發中途 leave。
7. Dungeon 內部戰鬥的 Result 必須返回探索流程；不得誤套一般關卡 Result 的強制離場。
8. 若 Building 內有前景分頁，先驗證 close／quit 成功，再點擊
   `town_building/exitfromhouse_and_to_town.png` 回 Town。
9. 每 tick 共用一張畫面，最多一個 action，所有 navigation click 都驗證 postcondition。
10. config 在 dispatch precondition 成立前保持原活動 config；不得因 pending chest 破壞
   Dungeon／Domain／Battle 的 scene detection context。
11. `UNKNOWN` 不猜座標；有界重試耗盡後才交給 recovery／relaunch。
12. 五個 town subflow 共用唯一 `REACH_TOWN` route；新增任務不需在
    `navigation_table.py` 複製回城 edges。
13. `TOWN` 已成立但入口建築連續設定次數（預設 5）未辨識時，必須 defer；不得以每幀
    WAIT 阻塞主迴圈。
14. `task_complete` 與 `backpack_full` popup 必須先於 pending Town intent 處理。

## 8. 明確不採用的捷徑

- 不在 `ChestHandler.INIT` 內硬塞一串 close／goback／exit 模板。
- 不以 flow key／Handler state 在 `navigation_table.py` 複製五份相同的回城路徑。
- 不用 FSM state 或 config type 假裝它就是目前 scene。
- 不把「找不到 chest building」當成完成、defer 或 queue pop 的充分證據。
- 不讓 Watchdog 取代正常 precondition routing；Watchdog 只處理有界失敗。
- 不一次建立通用 workflow engine、Navigation DSL、Event Bus 或完整 Statechart。
