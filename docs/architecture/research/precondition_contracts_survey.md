> 狀態：整理工作的研究／決策依據，已於 2026-09-10 收斂至正式文件；本檔不再是開發規範或 active TODO。
>
> 正式規範：[Precondition Contracts](../precondition_contracts.md)
>
> 現況與未完成事項：[Precondition Contracts TODO](../../todos/precondition_contracts_todo.md)
>
> 已落地案例：[`REACH_TOWN` Contract](../../features/navigation/reach_town_contract.md)

我先給結論：**你現在不用急著做「全域 Precondition Framework」**。先把文件語意整理成一套 **Precondition Contracts 開發準則 + 現況 inventory/TODO**，反而最符合你現在的 Greenfield-lite 原則。

而且 survey 完後，我會稍微修正「BDI + State Machine」這個說法：你的系統目前比較準確是：

> **BDI-inspired Intent Layer + Executive/Prerequisite Satisfaction Layer + FSM-based Skills/Handlers**

不是純 canonical BDI，但結構已經很接近業界 autonomous-agent 的三層架構。

---

## 1. 業界遇到「有 Intent，但 precondition 不成立」怎麼做？

最重要的共識其實非常一致。

假設現在：

```text
Intent:
  CLAIM_CHEST

Execution precondition:
  At(Town)
  AND ChestEntryVisible
  AND ChestAvailable
```

但目前人在 Dungeon。

**頂尖做法不是：**

```text
CLAIM_CHEST
→ ChestHandler
→ INIT 發現不在 Town
→ failure / retry / skip
```

而是：

```text
CLAIM_CHEST                         ← intent 繼續存在
    │
    ├─ At(Town)? NO
    │
    ▼
satisfy prerequisite
    REACH_TOWN
        ↓
    postcondition: At(Town)
        ↓
re-observe world
        ↓
ChestEntryVisible?
        ↓
ChestAvailable?
        ↓
READY
        ↓
dispatch ChestHandler
```

也就是：

> **不滿足的 precondition，如果它是可達成的，就轉成 prerequisite/subgoal，而不是把原 Intent 判失敗。**

這正好就是你現在 `REACH_TOWN` 做出來的事情。

---

# 2. BDI：你的做法其實非常合理

BDI 裡最重要的不只是 Belief / Desire / Intention 三個名字，而是 **commitment**。

現在研究文獻對 BDI 的典型描述是：

* Belief：目前相信世界是什麼狀態
* Goal/Desire：希望達成什麼
* Intention：已經 commit、正在追求的目標
* Plan：在某些 context conditions 下實現 intention 的方法

Plan 通常有 trigger + context condition；而 intention 一旦建立，不應因為中間世界狀態稍微不適合就立刻消失。([Springer][1])

這跟你 `project_arch_greenfield_lite_v1.md` 裡已經寫的：

> Intent 不因 scene 或 FSM state 改變而消失。

其實完全一致。

### BDI 還有一個對你非常重要的概念：reconsideration

BDI 不代表「Intent 永遠死抱著」。

在動態環境中，agent 會在適當時機重新判斷：

```text
還想做嗎？
還做得到嗎？
現在這個 plan 還有效嗎？
需要換 plan 嗎？
```

BDI intention reconsideration 的研究甚至特別指出：

* 靜態環境可以更「bold」，少 reconsider
* 動態環境應更「cautious」，比較常根據新 belief reconsider

([Amsterdam UMC][2])

你的遊戲 CV automation 屬於：

```text
partially observable
+ UI transition
+ popup
+ 非同步動畫
+ gameplay state changes
```

所以應該偏後者。

這也是為什麼：

```text
click town
≠
我已經在 town
```

而要：

```text
click
→ next snapshot
→ verify At(Town)
```

這件事非常正確。

---

# 3. BDI 裡還要區分 3 種「條件」

這是我認為你整理文件時**最值得引進的觀念**。

不能全部叫 `precondition`。

| 種類                                    | 意義                      | Blackfire 例子                                    |
| ------------------------------------- | ----------------------- | ----------------------------------------------- |
| **Applicability / Context condition** | 這個 plan 現在適不適合選         | chest 今日尚待執行                                    |
| **Execution / Dispatch precondition** | 可以開始這個 skill/handler 了嗎 | `At(Town) && chest_entry_visible`               |
| **Maintenance / In-condition**        | 執行期間必須繼續成立              | committed battle 不可被 town intent 中途搶走           |
| **Postcondition**                     | action 成功後應看到什麼         | `RETURN_TOWN → SceneId.TOWN`                    |
| **Completion condition**              | 整個 intent 是否完成          | chest cooldown / red dot gone / reward verified |

BDI 對 suspend/resume 的研究也明確區別：

* selection 時需要的 precondition
* 執行期間需要持續成立的 in-condition

當 in-condition 在 resume 時已經失效，可能應 abort current plan、改試其他 plan，而不是硬接著跑。([ResearchGate][3])

這個區分對你非常有價值。

---

# 4. Planning / GOAP / PDDL 的答案更直接

如果用 planning 的語言，你現在這個問題甚至非常標準。

例如：

```text
Action: CLAIM_CHEST

preconditions:
  at_town
  chest_available

effects:
  chest_claimed
```

另外：

```text
Action: RETURN_TOWN

preconditions:
  at_lobby

effects:
  at_town
```

Planner 發現：

```text
goal = chest_claimed
```

但：

```text
at_town = false
```

它就會向後找：

```text
哪個 action 的 effect 可以產生 at_town？
→ RETURN_TOWN
```

然後形成：

```text
RETURN_TOWN
→ CLAIM_CHEST
```

這就是 GOAP / classical planning 的基本 precondition-effect chain。([goap.crashkonijn.com][4])

ROS 2 的 PlanSys2 更接近實際機器人架構：

```text
Domain Expert
    ↓
Problem / World State
    ↓
Planner
    ↓
Plan
    ↓
Executor
    ↓
Action performers
```

而且 Executor **執行時還會再次檢查 requirement 是否成立**，不是 planner 算完就相信世界永遠不變。([plansys2.github.io][5])

### 這對 Blackfire 的啟示

你不需要 PDDL。

但可以借它最漂亮的一個語意：

> **一個 prerequisite acquisition action 的 Postcondition，可以成為下一個 operation 的 Precondition。**

例如：

```text
RETURN_TOWN
postcondition = AtTown

             ↓ satisfies

CHEST
precondition = AtTown
```

你現在：

```python
PostconditionId.TOWN
```

以及 `NavigationProgress` 在下一幀驗證 Town，其實已經有這個雛形。

---

# 5. Robotics 業界：通常多一層 Executive

這反而是我認為**最像 Blackfire** 的模型。

Stanford robot autonomy 教材把常見 autonomous architecture 分：

```text
Planning / Mission
        ↓
Executive
        ↓
Behavior / Reactive Control
```

Planner 決定「我要什麼」。

Executive 負責：

* task decomposition
* sequencing
* prerequisite
* monitoring
* recovery

底層 behavior 才真的控制 actuator。([Stanford University][6])

Dependable robotics 的研究也把 executive 定位成：

> 判斷 commanded task 在目前 system state 是否能執行，並管理 termination/failure。

([科學直通車][7])

### 放到你的系統

其實就是：

```text
DailyManager / Scheduler
      │
      │ desire / requested work
      ▼
ActiveIntent
      │
      │ committed objective
      ▼
Executive-ish layer
  ├─ prerequisite check
  ├─ REACH_TOWN
  ├─ popup ownership
  ├─ InFlight verification
  └─ defer / recovery
      │
      ▼
FSM Handler
  ChestHandler
  BloodAltarHandler
  Dungeon...
```

所以我不太建議未來讓 FSM 本身承擔 Intent。

FSM 比較適合：

```text
Chest:
INIT
→ ENTERING
→ CLAIMING
→ VERIFYING
→ EXITING
```

而不是：

```text
我要做 Chest
→ 我在哪？
→ 我要不要先退出 Dungeon？
→ 是否應該優先領 diamond？
→ ...
```

後者是 Executive / Intent 層的事。

---

# 6. Behavior Tree 業界也採同樣概念

ROS Nav2 是 production-grade navigation framework，使用 Behavior Tree orchestration，導航 goal、planner、controller、recovery 都是分離的。([Nav2 Docs][8])

BehaviorTree.CPP 更直接支援：

```text
PreCondition
PostCondition
While-condition
```

而且特別提醒不要把大量複雜邏輯都塞進 condition script。([behaviortree.dev][9])

也就是即使使用 BT：

```text
Fallback
├─ IsAtTown
└─ NavigateToTown
```

本質還是：

> **ensure prerequisite → execute desired behavior**

並不是 BT 特有。

---

# 7. Autoware 也是「Goal 不因目前位置不同而消失」

Autoware Mission Planner 接受 goal pose 之後，會從：

```text
current ego pose
→ route
→ goal pose
```

route 會持續存在，直到新的 route/goal 被指定；不是「車現在不在 goal 附近，所以 goal 無效」。([Autoware Foundation][10])

這跟：

```text
current_town_subflow = chest
```

被 latch 起來，

然後慢慢：

```text
Dungeon
→ Result
→ Lobby
→ Town
```

其實是一模一樣的 architectural idea。

---

# 8. 所以我會怎麼定義你的架構

我目前**不會在正式文件直接寫「我們是 BDI architecture」**。

因為 canonical BDI 還包含比較正式的：

```text
Belief revision
Desire generation
Plan library
Context matching
Intention reconsideration
```

而你目前沒有刻意做完整模型。

我會寫成：

> **BDI-inspired goal/intention semantics with an executive-style prerequisite layer and FSM-based workflow execution.**

映射大約是：

| 你的系統                                  | BDI / Robotics                    |
| ------------------------------------- | --------------------------------- |
| `SceneSnapshot`、daily state           | Beliefs / World Model             |
| Daily pending task                    | Desire / Goal                     |
| `ActiveIntent`、`current_town_subflow` | Intention                         |
| Navigation Table / fixed workflow     | Plan / procedural knowledge       |
| Precondition Controller               | Executive                         |
| Handler FSM                           | Skill / reactive execution        |
| `InFlightAction`                      | committed atomic action           |
| `PostconditionId`                     | observable effect / postcondition |

而你現在 `ActiveIntent` 已經明確包含 Diamond、Bread、Town Subflow、Primary Navigation。

---

# 9. 回頭看你現在 repo：「Precondition 到底註冊在哪？」

這裡目前其實**沒有一個全域 Precondition Registry**。

而且我認為現在不要硬做。

目前是：

| Contract                     | 現在在哪                                                                |
| ---------------------------- | ------------------------------------------------------------------- |
| Town 任務需要去哪                  | `town_subflow_registry.py → navigation_goal`                        |
| Town 任務入口                    | `town_subflow_registry.py → building_template`                      |
| 是否需要 red dot                 | `town_subflow_registry.py → requires_red_dot`                       |
| Town 即可 dispatch             | `dispatch_on_town`                                                  |
| 怎麼 Reach Town                | `navigation_table.py → REACH_TOWN_EDGES`                            |
| 怎麼證明現在在哪                     | `town_subflow_perception.py`                                        |
| 不滿足 precondition 怎麼處理        | `town_subflow_navigation.py`                                        |
| action 成功證據                  | `navigation_intent.py → PostconditionId` + `navigation_progress.py` |
| Handler 內部 phase guards      | **散落在各 Handler**                                                    |
| Daily eligibility / cooldown | DailyManager / scheduler 等                                          |
| completion evidence          | 各 Handler + DailyManager                                            |
| defer / bounded retry        | navigation progress / controllers / handlers                        |

真正 declarative 的 **dispatch-precondition registry**，目前主要就是：

```text
states/town_subflow_registry.py
```

因此不要因為檔名叫 `precondition.md`，就誤以為「所有東西應該最後全部進一個 Python precondition registry」。

---

# 10. `precondition_reach_town.md` 現在其實混了不同概念

這份文件目前收集了：

```text
Diamond collection
Stamina retreat
Bag cleanup
Daily reset
Pipeline drain
Domain exit
Town subflows
Watchdog recovery
Game relaunch
...
```

但這些**不全都是 Precondition**。

例如：

```text
Chest needs Town
```

這是真的：

> execution precondition。

但是：

```text
Watchdog 回 Town
```

比較像：

> recovery target。

而：

```text
Daily pipeline drain → Town
```

比較像：

> terminal/idle policy。

而：

```text
Game relaunch → wait until Town
```

比較像：

> startup postcondition。

所以你現在想整理文件是完全正確的。

---

# 11. 我建議的文件架構

我目前最推薦先只有 **2 個主文件 + 1 個 REACH_TOWN reference**，不要開十幾個檔案。

```text
docs/
├─ architecture/
│  ├─ project_arch_greenfield_lite_v1.md
│  │
│  └─ precondition_contracts.md          ← 新的長期開發準則
│
├─ todos/
│  └─ precondition_contracts_todo.md     ← 現況 inventory + migration TODO
│
└─ features/navigation/
   └─ reach_town_contract.md             ← 已落地案例 / reference implementation
```

### `precondition_contracts.md`

這會跟 `project_arch_greenfield_lite_v1.md` 同一等級。

不是列「Chest 要 Town」而已。

它回答：

```text
什麼叫 precondition？
誰負責判斷？
什麼 evidence 才算成立？
不成立時誰負責 satisfy？
Intent 是否保留？
何時 WAIT？
何時 DEFER？
何時 REPLAN？
何時取消 Intent？
Precondition / invariant / postcondition / completion 如何區分？
```

而你說**一定要留下的東西**：

```text
驗收條件
明確不採用的捷徑
```

我完全同意，這兩節應該成為 normative architecture contract。

---

### `precondition_contracts_todo.md`

才是真正「所有目前還沒有整理好的 precondition」。

我會做成 inventory：

| Flow / Operation  | Preconditions                | Evidence owner  | Satisfier                     | Current implementation | Gap       |
| ----------------- | ---------------------------- | --------------- | ----------------------------- | ---------------------- | --------- |
| Chest             | Town + entry + available     | Town perception | REACH_TOWN                    | partial                | —         |
| Hero draw         | Town + tavern + red dot      | ...             | REACH_TOWN                    | ...                    | ...       |
| Start battle      | correct lobby + stamina      | scattered       | navigation / stamina recovery | scattered              | normalize |
| Dungeon selection | correct tab + target visible | handler         | card navigator                | scattered              | document  |
| ...               |                              |                 |                               |                        |           |

**先 inventory，不重構 code。**

---

### `reach_town_contract.md`

現在的：

```text
precondition.md
precondition_reach_town.md
```

有大量非常好的設計決策，不應刪掉。

但整理完後它應該變成：

> `Precondition Contracts` 的第一個已完成案例。

尤其目前那份 `precondition.md` 的：

* Chest-first rationale
* REACH_TOWN ownership
* precedence
* acceptance criteria
* 明確不採用捷徑

都值得留下。

---

# 12. 現在「統一 Precondition code」真的不用急

這點我的答案是 **對，不急**。

因為你現在才剛有第一個真正抽象成功的：

```text
REACH_TOWN prerequisite family
```

目前就馬上做：

```python
PreconditionRegistry
PreconditionResolver
PreconditionGraph
GenericContract
GenericSatisfier
GenericDependencyPlanner
```

很容易直接走向你 `Greenfield-lite` 自己明確說不要做的：

> workflow engine / graph framework / DSL / unnecessary abstraction。

更好的順序是：

1. **先定義語言與 ownership。**
2. **把目前 scattered conditions inventory 出來。**
3. 新功能繼續按照 contract 原則寫。
4. 等你看到第二、第三種真正重複的 prerequisite satisfaction pattern，再抽 code。

我甚至會訂一條開發準則：

> **Documentation may unify semantics before code unifies mechanism.**

這非常適合你現在的階段。

---

## 最後，我認為最重要的一條 architecture rule

可以先把這句當成之後 `precondition_contracts.md` 的核心：

> **Intent describes what the agent remains committed to achieve; preconditions describe when a concrete operation may execute. An unmet but satisfiable precondition must not destroy the intent—it creates prerequisite work whose verified postcondition makes the intended operation dispatchable.**

Blackfire 對應就是：

```text
Intent: chest
      ↓
not AtTown

不是 FAIL CHEST

而是

REACH_TOWN
      ↓
verify TOWN
      ↓
Chest dispatch precondition
      ↓
Chest FSM
```

我認為這就是你接下來整理整份文件時應該圍繞的核心。

[1]: https://link.springer.com/article/10.1007/s10458-020-09453-y "https://link.springer.com/article/10.1007/s10458-020-09453-y"
[2]: https://pure.amsterdamumc.nl/en/publications/the-theory-and-practice-of-intention-reconsideration/ "https://pure.amsterdamumc.nl/en/publications/the-theory-and-practice-of-intention-reconsideration/"
[3]: https://www.researchgate.net/publication/286639381_Aborting_suspending_and_resuming_goals_and_plans_in_BDI_agents "https://www.researchgate.net/publication/286639381_Aborting_suspending_and_resuming_goals_and_plans_in_BDI_agents"
[4]: https://goap.crashkonijn.com/goap-v2/general/conditionsandeffects "https://goap.crashkonijn.com/goap-v2/general/conditionsandeffects"
[5]: https://plansys2.github.io/design/index.html "https://plansys2.github.io/design/index.html"
[6]: https://web.stanford.edu/class/cs237b/pdfs/lecture/lecture_14.pdf "https://web.stanford.edu/class/cs237b/pdfs/lecture/lecture_14.pdf"
[7]: https://www.sciencedirect.com/science/article/pii/S092188902200207X "https://www.sciencedirect.com/science/article/pii/S092188902200207X"
[8]: https://docs.nav2.org/ "https://docs.nav2.org/"
[9]: https://behaviortree.dev/docs/guides/pre_post_conditions/ "https://behaviortree.dev/docs/guides/pre_post_conditions/"
[10]: https://autowarefoundation.github.io/autoware_core/pr-669/planning/autoware_mission_planner/ "https://autowarefoundation.github.io/autoware_core/pr-669/planning/autoware_mission_planner/"
