# `REACH_TOWN` Contract：Town Subflow Prerequisite Reference

> 狀態：已落地案例；Chest-first 行為切片於 2026-09-10 完成
>
> 上位語意：[Precondition Contracts](../../architecture/precondition_contracts.md)
>
> 整體架構：[Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md)
>
> 其他回城情境分類：[Precondition Contracts TODO](../../todos/precondition_contracts_todo.md#3-reach_town-使用情境重新分類)

## 1. 文件責任

本文件只描述 Daily Town subflow 如何在保留 committed request 的前提下，滿足
`AtTown` prerequisite，再驗證各自的 dispatch readiness。它是 Precondition Contracts 的
第一個 reference implementation，不代表全系統所有 precondition，也不宣稱所有回城需求
都使用這套 route。

- committed request: 系統已經承諾要做 但是尚未完成的請求/意圖(intent)
- prerequisite: 為了讓後續操作能進行,必須先達成的條件/subgoal
- dispatch readiness: 是否已經滿足「可以把控制權交給該 Handler」的條件。以及為甚麼
  - dispatch：把工作正式交給某個 Handler/執行單元
  - readiness：已經準備好了
- route:從目前狀態到目標狀態所採取的路徑

Intent
→ prerequisite：先到正確地方
→ dispatch readiness：到了之後，確認 Handler 啟動條件
→ dispatch Handler

共用 consumer：

```text
chest
hero_draw
blood_altar
bulletin_board
jewelry_workshop
  -> NavigationGoal.REACH_TOWN
```

## 2. 已解決的原始問題

舊路徑在第一張畫面定位前就 pop queue、換成 Chest config 並切入 `ChestHandler.INIT`。
如果玩家其實在 Lobby、Battle、Result、Domain、Dungeon 或某個前景視窗，Handler 會把
「不在 Town」誤讀成「找不到 Chest」，造成 queue head 靜默遺失或錯誤 context。

現在的正確語意是：

```text
Scheduler 提出尚待執行的 flow
  -> current_town_subflow latch committed request
  -> 保留原活動 config／FSM ownership
  -> 觀察目前 scene
  -> 在 safe point 沿 REACH_TOWN route 前進
  -> 新 snapshot 驗證 SceneId.TOWN
  -> 驗證該 flow 的 entry/red-dot dispatch policy
  -> 才套用對應 config 並 dispatch Handler
  -> completion evidence 或明確 defer 後才釋放 request
```

## 3. Owner 與資料邊界

| 責任 | 唯一 owner／位置 |
| --- | --- |
| 今日是否尚待執行、是否在 defer | `DailyManager.get_pending_town_subflows()` |
| 目前 committed Town request | `GameStateMachine.current_town_subflow` active slot |
| flow 的目的地、入口 template、red-dot policy | `states/town_subflow_registry.py -> TownSubflowSpec` |
| `REACH_TOWN` scene/element evidence | `states/town_subflow_perception.py` |
| 共用目的地 edge | `states/navigation_table.py -> REACH_TOWN_EDGES` |
| prerequisite 決策與 bounded entry wait | `TownSubflowPolicy`／`TownSubflowPreconditionController` |
| click postcondition、retry attempts | `NavigationProgress`／`InFlightAction` |
| Building 內 phase 與 domain completion | 對應 Town Handler + `DailyManager` |

`NavigationTable` 只回答「現在怎麼到 Town」；`TownSubflowSpec` 與 dispatcher 才回答
「到 Town 後如何判斷這個 flow 可以派發」。Router 不讀 `flow_key` 來複製五套 edge。

- bounded entry wait: 在剛進入某個流程或狀態時，設置一個有時間或次數上限（有界限，Bounded）的等待保護期。避免因為剛切換場景、畫面尚未完全載入時就誤判「失敗」或「找不到目標」；同時也不會無休止地無限等待（避免死鎖/掛死）。時間或重試次數一旦達到上限（逾時），就必須主動退出並宣告超時或觸發恢復機制。

## 4. Dispatch readiness

| Flow | 到 Town 後的 dispatch condition | 無紅點／入口缺失政策 |
| --- | --- | --- |
| `chest` | building entry + red dot | building 已確認且 red dot 連續不存在 -> complete；building entry 連續未找到 -> defer |
| `hero_draw` | Tavern entry + red dot | 同上 |
| `blood_altar` | Blood Altar entry + red dot | 同上 |
| `bulletin_board` | Board entry + red dot | 無紅點代表今日任務已接滿／已完成；經連續觀察後 complete |
| `jewelry_workshop` | `TOWN` | `dispatch_on_town=True`；building／需求判斷仍由 Handler 負責 |

到達 `TOWN` 是 prerequisite postcondition，不是 Town subflow completion。對需要 entry 的 flow：

- 沒有 `TOWN` evidence 時，禁止做 building／red-dot 判定。
- building 未找到代表 dispatch evidence 不足；bounded wait 後 defer，不能完成。
- building 已找到且 required red dot 不存在，才可套用該 flow 的負向 completion policy；
  現況要求連續數幀（例如連續 2~3 次）都觀測到相同的場景特徵，才正式確認狀態，防抖動(連續 observation debounce)。

## 5. 共用導航矩陣

| 已確認場景／evidence | 決策 | 下一個 postcondition／owner |
| --- | --- | --- |
| 已登錄前景 close element | 點擊 close／confirm／ok／cancel／quit | `OVERLAY_CLOSED`，下一 snapshot 重觀察底層 scene |
| `TOWN_BUILDING + EXIT_BUILDING_TO_TOWN` | 點擊 building exit | `TOWN` |
| Lobby／Stage Select／Dungeon Select／Lord Select／Demon Lord Select + `GOBACK_TOWN` | 點擊 goback | `TOWN` |
| `DOMAIN_EXPLORE + EXIT_TO_LOBBY` | 點擊 domain exit | `LOBBY`，下一輪再尋找 Town edge |
| `TOWN` | 停止 goal routing，交給 flow dispatch policy | entry/red-dot readiness 或 `dispatch_on_town` |
| `BATTLE`／`LOADING`／`RESULT`／`DUNGEON_EXPLORING` | 不由 Town controller 搶 frame | 原 committed workflow／Result safe point |
| `UNKNOWN`／缺少 required element | WAIT／重新定位；有界失敗才 recovery | 新 observation 或上位 recovery |

`REACH_TOWN_EDGES` 目前實際只包含 Town Building、Lobby／各 Select scene 與 Domain Explore。
Battle、Result、Dungeon Exploring 的處理是 ownership／safe-point policy，不是 edge 表中的
立即回城捷徑。

## 6. 固定 precedence 與 maintenance ownership

1. 驗證已提交的 `InFlightAction`。
2. 處理 critical safety／全域 popup owner。
3. 讓已提交的 Battle、Loading、Result、Dungeon Explore 或 Popup Recovery workflow 持續到 safe point。
4. 關閉已登錄的前景 overlay。
5. 沿 `REACH_TOWN` edge 執行一個 action。
6. `TOWN` 成立後才檢查 flow dispatch readiness。

因此 pending Chest 在 Battle 中必須保留，但不得中途亂點退出；一般 Result 到安全點時可依
pending town request 選 exit，Dungeon 內部 Result 仍先交回 Dungeon Explore owner，直到
完整探索結束。

## 7. Postcondition、Defer 與 Completion

- 每個 route click 都建立 `InFlightAction`；呼叫 click 不等於抵達 Town。
- `RETURN_TOWN`／building exit 由較新的 snapshot 證明 `SceneId.TOWN`。
- Domain exit 先證明 `LOBBY`，再由下一輪決定是否有回城 edge。
- Route action retries 用盡後，Town request defer 180 秒；不標完成。
- 已在 Town 但 entry 連續設定次數（預設 5）未出現時，defer 180 秒，避免無限 WAIT。
- required red dot 的負向 completion 目前需連續設定幀數（預設 2）確認。
- Handler 派發後，claim／cooldown／exit evidence 由 Handler 決定 completion 或 defer；
  navigation layer 不替代 domain outcome。

## 8. 感知範圍與限制

「任何地方都能回 Town」只表示任何已登錄且可辨識、並有合法 edge 或 safe-point handoff 的
場景。`UNKNOWN` 不猜座標。

目前 Town prerequisite perception：

- 以 `common/door.png`／`diamond.png` 識別 Town 核心 anchor；
- 以 building exit、`goback_town`、domain exit 辨識可用 route element；
- 額外辨識 Battle、Result、Dungeon Explore，目的是保留其 workflow ownership；
- 前景關閉 registry 現含 `common/confirm.png`、`common/ok.png`、`common/cancel.png`、
  `common/quit.png`；新增資產時應加入共用 evidence owner，不在個別 Handler 私藏世界級 routing。

Scene catalog 的存在不等於 detector 已完整覆蓋；未能可靠產生 evidence 的場景仍是
`UNKNOWN`，交由等待／relocalize／bounded recovery。

## 9. 驗收條件

### 9.1 通用 Town subflow

1. Daily 從 Town、Lobby、Battle、Battle Result、Domain、Demon Lord、Lord、Dungeon、Bread
   視窗或 Bag 視窗啟動時，active／pending Town request 不會因 scene 不符而遺失。
2. 沒有 `TOWN` evidence 時絕不執行 building／red-dot dispatch 判定。
3. Dispatch readiness 成立前保留原活動 config；不得破壞 Dungeon／Domain／Battle scene context。
4. Battle 中不強制退出；一般 Result safe point 可 exit，不得 retry。
5. Dungeon Exploring 必須自然完成；其內部 Result 返回探索流程，不誤套一般關卡離場規則。
6. Building 內有前景分頁時，先驗證 close／quit 成功，再點 building exit。
7. 每 tick 共用一張畫面、最多一個 action；所有 navigation click 驗證 postcondition。
8. `UNKNOWN` 不猜座標；有界 retry 耗盡後才 defer／recovery／relaunch。
9. 五個 Town subflow 共用唯一按目的地定義的 `REACH_TOWN` route；新增 flow 不複製 edges。
10. Town 已成立但入口連續設定次數未辨識時必須 defer，不得每幀 WAIT 阻塞。
11. `task_complete`、`backpack_full` 等 critical popup owner 先於 pending Town request。
12. Completion、defer 與 queue advancement 必須有明確 outcome；不得靜默 pop request。

### 9.2 Chest-first 保留驗收

1. Chest building 已確認且 required red dot 經 debounce 不存在時，代表今日福利已領取，
   可標記 `completed_today` 並前進；單純找不到 building 不足以完成。
2. Handler 內只有 free button 消失、cooldown evidence 成立，或完成離場驗證時 red dot 已消失，
   才可簽核 claim completion。
3. 領取驗證失敗或退出後 red dot 仍存在時 defer，pending fact 不得被標成完成。

## 10. 明確不採用的捷徑

- 不在 `ChestHandler.INIT` 或其他 Town Handler 內堆世界級 close／goback／exit 分支。
- 不以 flow key／Handler state 在 `navigation_table.py` 複製五份回城路徑。
- 不用 FSM state 或 config type 假裝目前 scene。
- 不把找不到 building 當成 completion、defer 或 queue pop 的充分證據。
- 不讓 Watchdog 取代正常 prerequisite routing；Watchdog 只處理有界失敗。
- 不把 Stamina Retreat、pipeline drain、login readiness 等不同語意強塞進這個 contract。
- 不建立通用 workflow engine、Precondition Registry、Navigation DSL、Event Bus 或完整 Statechart。

