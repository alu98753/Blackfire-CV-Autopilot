# Precondition Contracts：Intent、執行就緒與條件語意

> 狀態：正式開發準則（normative）
>
> 上位架構：[Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md)
>
> 已落地案例：[REACH_TOWN Contract](../features/navigation/reach_town_contract.md)
>
> 現況與未完成事項：[Precondition Contracts TODO](../todos/precondition_contracts_todo.md)

## 1. 文件責任與非目標

本文件統一定義「系統已持有 intent，但目前世界狀態尚未允許具體操作」時的語意與
ownership。專案可描述為：

> **BDI-inspired intent semantics + executive-style prerequisite satisfaction + FSM-based handlers.**

這只是責任分層，不表示專案已實作完整 BDI、planner 或通用 executive framework。

本文件不列出每個流程的所有判斷式，也不要求立刻統一現有程式。現況 inventory 與遷移
缺口放在 TODO 文件；具體 Town 回城路徑放在 `REACH_TOWN` 案例。這一輪明確不建立：

- `PreconditionRegistry`／`PreconditionResolver`／條件依賴圖；
- GOAP、PDDL、HTN、workflow DSL 或新的通用 planner；
- 第二套 intent queue、FSM framework 或大型抽象；
- 將所有 Handler phase guard 搬到同一個中央 registry。

## 2. 統一術語

不能把所有布林判斷都稱為 precondition。新增或修改流程時，先將條件歸入下列一類：

| 類型 | 回答的問題 | 典型 owner | Blackfire 例子 |
| --- | --- | --- | --- |
| Selection／context condition | 這項工作現在是否應被選為候選？ | Scheduler、`DailyManager`、固定 policy | 今日未完成、未 defer、Boss 次數未滿且 cooldown 已到 |
| Intent commitment | 系統目前承諾完成什麼？ | 唯一 intent owner／active slot | `ActiveIntent`、`current_town_subflow` |
| Execution／dispatch precondition | 現在是否可以開始一個具體 operation／Handler？ | Dispatcher／operation 邊界 | `TOWN` 已確認且入口 evidence 成立 |
| Prerequisite | 哪項前置工作能使 dispatch precondition 成立？ | Navigation／prerequisite satisfaction layer | `REACH_TOWN` |
| Maintenance／in-condition | 執行期間哪些條件必須維持，或誰仍擁有目前 frame？ | `InFlightAction`、workflow／Handler FSM | Start 已送出時不切 intent；Dungeon 探索未完成時仍由探索流程擁有 |
| Postcondition | 一個 action 發出後，下一張新 observation 要證明什麼？ | action progress owner | `RETURN_TOWN -> SceneId.TOWN`、overlay 已消失 |
| Completion condition | 什麼 evidence 足以結束整個 intent／工作？ | Domain outcome owner、Handler、`DailyManager` | free button 消失、cooldown 成立、退出後紅點消失 |
| Recovery condition | 何時從正常執行升級為 retry、defer、relocalize 或 relaunch？ | Progress／Recovery owner | action timeout、連續無進展、capture failure |

補充原則：

- 「待辦存在」不是 dispatch readiness。
- 「位於正確 scene」通常只是 dispatch precondition 的一部分。
- 「點擊已送出」不是 postcondition，也不是 completion。
- `DEFER` 不是完成；它只代表現在暫不選取，原始 pending fact 仍存在。
- Recovery target、startup readiness、idle destination 都可能是 `TOWN`，但不因此自動成為 execution precondition。

## 3. 核心契約：Intent 不因可滿足的前置條件缺失而消失

規範句：

> **Intent 描述系統持續承諾達成的目標；execution precondition 描述某個具體 operation
> 何時可以執行。未滿足但可達成的 precondition 不得銷毀 intent；它會產生 prerequisite
> 工作，而 prerequisite 經新 observation 驗證的 postcondition，才讓原 operation 變為
> dispatchable。**

以 Chest 為例：

```text
Intent: CLAIM_CHEST（保留）
  -> AtTown? no
  -> prerequisite: REACH_TOWN
  -> click return-to-town
  -> next SceneSnapshot verifies TOWN
  -> verify chest entry + red-dot policy
  -> dispatch ChestHandler
  -> Handler verifies claim/exit completion evidence
  -> complete or defer intent
```

`REACH_TOWN` 的 postcondition `AtTown` 可以滿足 Chest dispatch precondition 的其中一項；
它不等於 Chest 已完成，也不保證入口與紅點已成立。

## 4. 未滿足條件時的合法結果

| 情況 | 結果 | Intent／pending fact |
| --- | --- | --- |
| 本 profile 尚未檢查，或 evidence 不足 | `WAIT` 並用新 snapshot 重觀察；等待必須有上限或由既有 no-progress recovery 管理 | 保留 |
| 條件可由已登錄安全動作達成 | 執行一個 prerequisite action，建立 `InFlightAction`，等待 postcondition | 保留 |
| 暫時不可用但之後可重試 | `DEFER`／fixed backoff | 保留，不得標成 completed |
| 目前 route／plan context 已失效，但有既定替代路徑 | 回到既有 policy 重新選合法 edge／safe point；這是小型 replan，不新增通用 planner | 保留，除非 owner 明確取消 |
| 明確 completion evidence 成立 | 由 completion owner 完成工作並清除對應 commitment | 可結束 |
| 明確取消、永久不可達或有界失敗政策要求終止 | 只有唯一 owner 能取消、defer 或升級 recovery | 依明確 outcome 處理 |

不得以「找不到模板」、「FSM state 改變」、「config 被替換」、「經過一段時間」或「已經
點擊」單獨推導 intent 完成。

## 5. Ownership 邊界

| 層級 | 擁有的責任 | 不得承擔的責任 |
| --- | --- | --- |
| `DailyManager`／Scheduler／`QuestScheduler` | eligibility、cooldown、pending、固定順序與候選工作；落實 Tier 1 (城鎮) > Tier 1.5 (魔王) > Tier 2 (首領) > Tier 3 (懸賞) > Tier 4 (退守) 排程階梯 | 用 FSM state／config 假裝 dispatch 已就緒；直接操作跨場景 UI |
| Intent owner | latch 唯一目前 commitment；在 completion、cancel 或 defer 邊界更新 | 因 scene 暫時不合就清除 intent |
| Perception／`SceneSnapshot` | 回報本 frame、目前 profile 實際檢查到的 evidence | 點擊、transition、修改 pending fact |
| Navigation／prerequisite layer | 依目的地選一個安全 edge；驗證 prerequisite action postcondition | 選擇業務任務；宣告 domain completion；在受管流程非 Tier 4 退守時擅自切換頁籤 |
| Dispatcher | 在 dispatch precondition 完整成立後切入對應 Handler | 在 evidence 不足時猜測入口或提前換 config |
| Handler／FSM | 已派發 operation 的 phase、maintenance guard、內部 postcondition 與 domain outcome | 重做全域任務優先序或世界級回城導航 |
| Progress／Recovery | action timeout、bounded retry、defer、relocalize、relaunch escalation | 將 recovery 成功當成原業務 intent 完成 |

相容期允許 legacy field 仍是 pending fact 的來源，也允許 town subflow 以
`current_town_subflow` latch commitment；但同一條實際路徑只能有一個決策 owner。不得為了
「統一名稱」建立第二個可寫入 queue 或讓新舊 policy 同時發 action。

## 6. Evidence 與 dispatch readiness

1. Decision 只可使用同一張不可變 `SceneSnapshot` 中、目前 detection profile 保證已檢查的 evidence。
2. 「未檢查」不等於「不存在」。負向 evidence 只有在對應 detector 已執行且契約允許時才有效。
3. Scene、overlay、entry、availability 應分別表達；不能以 FSM state 或 config type 代替世界 observation。
4. 每個 tick 最多一個 transition、click、delegate 或 wait；舊座標不跨 frame 使用。
5. Action 發出後先維持 `InFlightAction` commitment；下一張較新的 snapshot 驗證 postcondition 前，不發第二個業務 action或切換 intent。
6. Completion evidence 應由 domain owner 定義，不能由 generic navigation layer 推測。
7. 需要用「元素不存在」表示完成時，應先證明其 parent scene／panel 已正確定位，並依風險使用 debounce 或多幀確認。

Town subflow 的特殊例子是：只有在 `TOWN` 與 building entry 均成立後，連續觀察不到
required red dot 才可套用「今日已完成」政策；單純找不到 building 只能 bounded wait 後
defer，不能完成。

## 7. Intent commitment 與 maintenance condition

Intent commitment 不代表立即搶占所有流程。下列 maintenance ownership 高於新 prerequisite：

1. 已提交且尚未驗證的 `InFlightAction`；
2. critical safety／recovery；
3. 已提交的不可安全中斷 workflow，例如 Battle、Loading、Result 或未完成的 Dungeon Explore；
4. 到達 safe point 後，才重新處理等待中的 prerequisite／intent。

因此「Chest intent 在 Battle 中仍存在」與「Battle 中立刻回城」是兩件不同的事。正確行為
是保留 intent，讓既有 workflow 到達安全點，再沿已登錄路徑滿足前置條件。

## 8. 開發時必須回答的問題

新增 operation、導航 edge 或 Handler phase 時，規格至少要回答：

1. 這是 selection、dispatch、maintenance、postcondition、completion 還是 recovery condition？
2. 條件的 evidence 是什麼？哪個 detection profile 保證檢查？
3. 哪個元件是唯一判斷 owner？
4. 不成立但可達成時，哪個既有 prerequisite action／route 能滿足？
5. prerequisite 的 postcondition 是什麼？由哪張新 snapshot 驗證？
6. 等待何時 timeout；何時 retry、defer、回既有 route 或 recovery？
7. intent／pending fact 在上述過程如何保留？
8. completion 的正向或負向 evidence 是什麼？誰有權清除 commitment？
9. 執行期間有哪些 maintenance conditions，在哪個 safe point 才能交還控制權？
10. 是否能用既有 table、registry、policy 或 Handler phase 表達，而不新增 framework？

## 9. 通用驗收條件

- 從任何已支援且可辨識的驗收場景開始，pending intent 不因 scene／state 不符而遺失。
- Dispatch precondition 未成立時，不得進入需要該條件的 Handler，也不得提前替換其 config context。
- 可滿足的前置條件沿既有 prerequisite route 前進；每次 action 都由新 snapshot 驗證 postcondition。
- `UNKNOWN`／未檢查 evidence 只會 wait、relocalize 或 bounded recovery，不猜座標或宣告完成。
- 已提交 action／workflow 的 maintenance ownership 不被新 intent 中途破壞。
- Completion、defer、cancel 與 recovery 是不同 outcome；log、狀態與 pending fact 不得混用。
- 相同 `SceneSnapshot + ActiveIntent + InFlightAction` 產生相同 decision。
- 同一路徑只有一個 decision owner，且不引入動態排序、通用 planner 或第二套 workflow engine。

## 10. 明確不採用的捷徑

- 不在任務 Handler 的 `INIT` 內堆疊全世界的 close／quit／goback 模板。
- 不按 flow key 或 Handler state 複製目的地相同的導航 edges。
- 不用 FSM state、config type、elapsed time 或 click issued 代替 scene／postcondition evidence。
- 不把找不到入口、找不到按鈕或 detector 未執行當成 completion。
- 不讓 Watchdog 取代正常 prerequisite routing；Watchdog 只處理有界失敗與異常復原。
- 不因文件統一術語就宣稱程式已有全域 precondition registry。
- 不一次建立 workflow engine、Navigation DSL、Event Bus、Statechart 或通用條件圖。

## 11. 文件邊界

- 本文件：長期、跨功能的語意與開發準則。
- [Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md)：整體 runtime 不變量、資料流與精簡架構限制。
- [Navigation Intent Routing Spec](navigation_intent_routing_spec.md)：Diamond／Bread／Primary 的固定 precedence、Start commitment 與相容 routing。
- [REACH_TOWN Contract](../features/navigation/reach_town_contract.md)：Town subflow prerequisite 的已落地 reference。
- [Precondition Contracts TODO](../todos/precondition_contracts_todo.md)：目前散落位置、分類、缺口與後續盤點。

