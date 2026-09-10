# Precondition Contracts：現況 Inventory 與 TODO

> 狀態：現況盤點／未完成事項，基準日 2026-09-10
>
> 正式語意：[Precondition Contracts](../architecture/precondition_contracts.md)
>
> 已落地案例：[REACH_TOWN Contract](../features/navigation/reach_town_contract.md)

## 1. 盤點結論

目前專案沒有全域 `PreconditionRegistry`，也不應把現有程式描述成已有通用 prerequisite
framework。條件依責任散落於 scheduler、registry、navigation table、progress、Handler FSM、
`DailyManager` 與 recovery；其中 Town subflow 的 dispatch/prerequisite 已有相對清楚的
declarative slice，其餘仍多為 domain-local 判斷。

本文件只建立 inventory 與後續收斂順序，不要求本次修改任何 `.py`。

### 1.1 狀態判讀

| 狀態 | 內容 |
| --- | --- |
| 正式規範 | Intent 不因 scene／FSM state 改變而消失；click 必須驗證 postcondition；selection、dispatch、maintenance、completion 與 recovery 不得混稱；可滿足的 dispatch precondition 產生 prerequisite work。 |
| 已落地 | Diamond／Bread／Primary 固定 intent routing 與 `InFlightAction` 核心；五個 Town subflow 的 committed slot、共用 `REACH_TOWN_EDGES`、Town dispatch gate、bounded wait／defer。 |
| 相容現況 | Town subflow 仍由 `current_town_subflow` 與專屬 controller 接入；許多 Handler 仍自行持有 phase condition、blocking click verification 或 completion evidence。這是已知邊界，不等於違規 TODO 全部已解。 |
| 尚未完成 | 全場景 snapshot／postcondition 遷移、Result 離場條件拆分、Bag 與 Daily ownership、defer 持久化決策、各 domain evidence 表。 |
| 未核准／明確不做 | 全域 Precondition Registry、generic resolver graph、planner、workflow DSL 與一次性 Handler 重構。 |

## 2. 現有條件分類

### 2.1 Selection／context conditions

| Flow／condition | Evidence／狀態來源 | 現在的 owner／位置 | 現況與缺口 |
| --- | --- | --- | --- |
| Town subflow 今日是否待執行 | enabled、`completed_today`、in-memory defer deadline | `utils/daily_manager.py -> get_pending_town_subflows()` | 已能篩選候選；不是 dispatch precondition。defer 不持久化，relaunch 後會消失，是否需要持久化仍待決定。 |
| Lord Boss 是否可選 | today count、max count、cooldown timestamp | `DailyManager.is_boss_available()`／`get_available_lord_bosses()`，`GameStateMachine` scheduler | 已實作 domain eligibility；不要稱為「人在 Town 的 precondition」。 |
| Demon Lord 是否可選 | completed/count/max | `DailyManager.get_available_demon_lords()`、`GameStateMachine.evaluate_next_activity()` | 已實作 selection；入場資源／ticket readiness 仍由 Handler 處理，尚未形成集中 contract。 |
| Daily Quest／Dungeon 下一工作 | TaskNode 狀態、cooldown、固定 priority | `utils/quest_scheduler.py`、`GameStateMachine.evaluate_next_activity()` | selection 與 Result safe-point preemption 分散；需持續記錄 owner，暫不重構。 |
| Diamond／Bread／Primary precedence | legacy pending flags + primary payload | `states/navigation_intent.py`、`states/navigation_routing.py` | 已有固定 policy。Town subflow 目前由獨立 active slot/controller 接入，尚非同一個 selection function。 |

### 2.2 Execution／dispatch preconditions 與 prerequisite

| Operation | Dispatch precondition | Evidence owner | Prerequisite／satisfier | 現在的位置 | 現況與缺口 |
| --- | --- | --- | --- | --- | --- |
| Chest／Hero Draw／Blood Altar／Bulletin Board | `TOWN` + 對應 building entry；需要紅點時 red dot 存在 | `TownSubflowPerception` | `NavigationGoal.REACH_TOWN` | `town_subflow_registry.py`、`town_subflow_perception.py`、`town_subflow_navigation.py` | 已落地；entry missing 採 bounded wait 後 defer；無紅點 completion 需連續觀察。 |
| Jewelry Workshop | `TOWN` | `TownSubflowPerception` | `REACH_TOWN` | `TownSubflowSpec(dispatch_on_town=True)` | 目前沒有 building／red-dot dispatch gate；進入後需求與商店流程由 Handler 判斷。 |
| Diamond collection | Town／Diamond window 與對應 entry evidence | navigation snapshot／policy | intent-specific navigation edges | `navigation_table.py`、`navigation_intent.py` | 語意上含 Town prerequisite，但不是 `REACH_TOWN_EDGES` 的 consumer；勿誤寫成同一套 goal route。 |
| Bread collection | Lobby／Bread window 與 entry evidence | navigation snapshot／policy | Town -> Lobby 或 select page -> Bread window | 同上 | 已有固定 edges；Handler 內部 completion 仍是 domain-local。 |
| Primary Start | 正確 Lobby／Select scene + Start element + Primary intent | scoped scene info／`NavigationIntentPolicy`、`LobbyHandler` | 既有 primary navigation | `navigation_table.py`、`handlers/lobby.py` | Start commitment 已接 `InFlightAction`；部分 retry/phase 相容邏輯仍在 Handler。 |
| Dungeon／Stage card selection | 正確 tab、目標 card／位置可用等 | Navigation Handler 與 card helpers | 翻頁／滑動／選卡 | `handlers/navigation.py` 與相關 helpers | 條件與動作仍集中在大型 Handler；應先補文件 inventory，不建立通用 registry。 |
| Town building 內部 operation | 已進入正確 panel／phase、按鈕或 cooldown evidence | 各 Town Handler | Handler-local phase action | `handlers/chest.py`、`hero_draw.py`、`blood_altar.py`、`bulletin_board.py`、`jewelry_workshop.py` | 合理保留在 FSM skill 內；只需避免再次承擔世界級導航。 |

### 2.3 Maintenance／in-conditions

| Condition | Owner／位置 | 現況與缺口 |
| --- | --- | --- |
| 已提交 action 在 postcondition 前保持唯一 | `NavigationProgress.in_flight`、`navigation_routing.py`、Town controller | 已落地於共用導航 slice；legacy Handler 的 blocking/click-until 邏輯尚未全面遷移。 |
| Town intent 不搶 Battle／Loading／Result／Dungeon Explore／Popup Recovery | `TownSubflowPreconditionController._committed_workflow_owns_frame()` | 已明確 skip；安全點由原 workflow/Result 邏輯決定。 |
| Dungeon 內部 Result 回到探索而非被一般 exit policy 搶走 | `handlers/result.py` + `is_in_dungeon`／workflow context | 已有特殊 ownership；條件仍與多個離場原因混在 `should_exit_battle`。 |
| Battle timeout session 必須跨 frame 維持，離開 battle 才清除 | `states/battle_session.py`、`GameStateMachine`、Battle Handler | 已有唯一 session owner；屬 maintenance/recovery，不是 dispatch precondition。 |
| Stamina retreat phase 必須按 dismiss -> quit -> return/collect-only 前進 | `states/stamina_retreat.py` | 獨立 bounded recovery FSM；不屬共用 `REACH_TOWN` prerequisite route。 |
| 各 Handler phase guard | 各 `states/handlers/*.py` 的 `step_phase`／sub-phase | 有意保留在 skill 內；後續只盤點跨層 guard，不要求中央化所有 phase。 |

### 2.4 Postconditions

| Action family | Postcondition／驗證 | Owner／位置 | 現況與缺口 |
| --- | --- | --- | --- |
| 共用 navigation click | `TOWN`、`LOBBY`、`DIAMOND_WINDOW`、`BREAD_WINDOW`、`LOADING_OR_BATTLE`、`OVERLAY_CLOSED` | `PostconditionId` + `NavigationProgress._postcondition_met()` | 核心集合已落地；`PRIMARY_ROUTE_PROGRESS` 與 Handler delegate 不全由 generic progress 驗證。 |
| Town `REACH_TOWN` edges | exit building／goback -> `TOWN`；domain exit -> `LOBBY` | `REACH_TOWN_EDGES` + `NavigationProgress` | 已落地且 task-agnostic。 |
| Start | Start 消失並觀察 Loading／Battle | `NavigationProgress` + `LobbyHandler` 相容 phase | 兩種驗證路徑並存；未來遷移時要維持單一 owner。 |
| Handler 內部 click | popup 消失、panel 出現、free button/cooldown 改變、exit 結果 | 各 Handler | 仍有 `click_and_wait_until_gone`、sleep 與下一 tick phase 混用；不可宣稱全數已符合 one-frame contract。 |
| Game relaunch／login | 登入後任一支援 ready anchor，再轉 `UNKNOWN` 做全域定位 | `states/login_flow.py`、relaunch subflow | 舊文件所稱「唯一成功條件是 Town door」已過時；目前也接受 battle、stage select、dungeon anchors。 |

### 2.5 Completion conditions

| Flow | Completion evidence | Owner／位置 | 現況與缺口 |
| --- | --- | --- | --- |
| Town subflow 在入口處無紅點 | `TOWN` + building 已找到 + required red dot 連續不存在 | Town controller -> `complete_current_town_subflow()` -> `DailyManager` | 已落地；這是 domain policy，不是 `REACH_TOWN` postcondition。 Jewelry Workshop 不適用。 |
| Chest | free button 消失、cooldown evidence，或退出後紅點消失 | `handlers/chest.py` + `DailyManager` | 已有明確驗證；辨識／領取失敗走 defer。 |
| Hero Draw／Blood Altar／Bulletin Board | 各 Handler 完成 phase；退出後紅點政策或已接任務 evidence | 對應 Handler + `DailyManager.record_subflow_completed()` | domain-local；細節不可用通用「找不到按鈕」取代。 |
| Jewelry Workshop | enabled shop/sell 流程完成與 settlement | `handlers/jewelry_workshop.py` + `DailyManager` shop records | 與 Daily/BAG 後續觸發來源仍需釐清，但不是 Town dispatch 問題。 |
| Lord／Demon Lord | fight count、max count、明確 exhausted evidence | Result/Boss Handler + `DailyManager` | cooldown 與 completed 不同；已有部分強制 completion 自癒路徑，需個別審查 evidence。 |
| Daily Quest | Task banner／kill progress／TaskNode 完成 | `QuestScheduler`、Result／OCR path、`DailyManager` | 多來源；保持 domain-local，後續補齊 evidence 對照表。 |

### 2.6 Recovery conditions

| Trigger | Recovery owner／結果 | 現在的位置 | 分類說明 |
| --- | --- | --- | --- |
| navigation action timeout／attempts exhausted | retry；collection/town subflow defer；達上限升級 relaunch | `states/navigation_progress.py`、controllers | 正常 progress recovery；不是 completion。 |
| Town 已成立但入口連續未找到 | 觀察達設定次數後 defer 180 秒 | `TownSubflowPreconditionController` | bounded dispatch-readiness failure。 |
| Town Handler 領取／退出驗證失敗 | `DailyManager.defer_subflow(..., 180)` | 各 Town Handler | operation-level defer；目前 magic number/呼叫位置分散。 |
| `no_bread` 已確認 | bounded dismiss／quit／return，最後進 `COLLECT_ONLY` 或 relaunch | `states/stamina_retreat.py` | recovery target／mode transition，不是 Town subflow precondition。 |
| 全域 stuck／popup／長期無進展 | popup recovery 或 `GameRelaunchSubflow` | `states/exceptions/watchdog.py`、`states/exceptions/*` | 異常 recovery，不應取代正常 routing。 |
| relaunch 後等待 UI ready | 支援 anchor 出現後交回全域定位；timeout 再 relaunch | `states/login_flow.py` | startup readiness/postcondition，不等於必須先 `REACH_TOWN`。 |

## 3. `REACH_TOWN` 使用情境重新分類

舊 `precondition_reach_town.md` 將「目的地碰巧是 Town」與「共用 `REACH_TOWN` prerequisite」
混在一起。依現況應改讀如下：

| 情境 | 正確分類 | 是否使用共用 `REACH_TOWN_EDGES` | 備註 |
| --- | --- | --- | --- |
| 五個 Town subflow | execution prerequisite | 是 | 已落地 reference；到 Town 後仍要各自驗證 dispatch readiness。 |
| Diamond collection | execution prerequisite／intent-specific navigation | 否 | 自己的 Diamond edges 會先回 Town。 |
| 背包清理後啟動 Town subflow | workflow handoff + 後續 prerequisite | 後續是 | Bag 本身不是 `REACH_TOWN` precondition；active town request 建立後才進共用 route。 |
| Stamina retreat | recovery target + idle-mode transition | 否 | 由專屬 recovery FSM 管理。 |
| Daily reset 要求離開目前工作 | scheduling boundary／safe-point exit policy | 否 | `pending_daily_reset_exit` 影響 Result 離場；不可籠統宣稱立即強制回 Town。 |
| Pipeline drain -> `COLLECT_ONLY` | terminal／idle fallback policy | 否 | Town 是偏好的待機位置，不是下一個 Handler 的 dispatch precondition。 |
| Dungeon／Domain 結束 | workflow termination／navigation transition | 視等待中的 town intent 而定 | Domain 在 town intent 下可使用 `DOMAIN_EXPLORE -> LOBBY` edge；一般退出仍由原 workflow 擁有。 |
| Watchdog／未知 popup | recovery | 否 | recovery 可 relocalize 或 relaunch；不是無腦共用回城路由。 |
| Game relaunch／login | startup readiness/postcondition | 否 | 現況接受多種已知 ready anchors，不只 Town door。 |
| Lord／Demon Lord 發起 | selection + domain navigation | 否 | 目前沒有正式契約要求先以共用 goal 回 Town。 |

## 4. 目前 defer 的實際依據

為避免把 defer 與 completion 混用，現況列為：

1. Town subflow navigation action 的 postcondition 在 retry 上限內未成立。
2. 已確認在 Town，但入口 building 連續觀察達上限仍無 evidence。
3. Handler 已派發後，領取／確認／退出的 domain evidence 失敗，例如 Chest free button
   持續存在或退出後紅點仍在。
4. Diamond／Bread navigation action 連續失敗，由 `NavigationProgress` 套用 collection backoff；
   連續 defer 達 recovery 上限再 request relaunch。

上述機制目前分屬 `NavigationProgress`、Town controller、各 Handler 與 `DailyManager`；秒數、
持久化方式與 failure count 尚未完全一致。這是 inventory gap，不是建立通用 framework 的理由。

## 5. 後續 TODO（依優先順序）

- [x] 建立統一術語，區分 selection、dispatch、maintenance、postcondition、completion 與 recovery。
- [x] 將 Chest-first 決策與驗收條件移至明確的 `REACH_TOWN` reference，而非泛稱全系統 precondition。
- [x] 更正「所有回城都共用 `REACH_TOWN`」與「login 只接受 Town」等過時敘述。
- [ ] 每次修改一個 domain 時，補齊該 operation 的 evidence owner、satisfier、timeout、completion 與 defer 表；不做一次性全域重構。
- [ ] 盤點 `handlers/result.py -> should_exit_battle` 的每個條件，分成 safe-point preemption、workflow completion、recovery 與 idle policy，避免繼續以單一布林聚合不同語意。
- [ ] 盤點 Town Handler 內的 phase postcondition，標記哪些使用新 snapshot、哪些仍使用 blocking `click_and_wait_until_gone`／sleep；逐 slice 遷移。
- [ ] 釐清 Town subflow、Diamond／Bread 與 Primary 在同時 pending 時的單一 precedence 文件與 runtime 接線；不得建立第二套 queue。
- [ ] 釐清 Bag cleanup 後續子流程與 Daily town pipeline 的觸發來源／completion ownership；兩者可共用 route，但不得互相冒充 scheduler owner。
- [ ] 決定 Town subflow defer 是否需要跨 process 持久化；決定前維持文件標註為 in-memory backoff。
- [ ] 為 Lord／Demon Lord 的 ticket、資源、cooldown 與「次數已滿」分別命名，不再都寫成 precondition。
- [ ] 僅當至少第二、第三種 prerequisite satisfaction pattern 真正重複且現有 table/controller 無法合理承載時，再提出小型抽象 RFC(request for comments)。

## 6. 明確不在 TODO 中的項目

- 不建立全域 `PreconditionRegistry`、resolver graph 或 generic contract engine。
- 不把所有 Handler phase guard 搬到 navigation layer。
- 不把 recovery、startup readiness、idle destination 統一改名為 precondition。
- 不在本文件任務中重構 `.py`、改變 runtime 行為或宣告未驗證的 migration 已完成。
