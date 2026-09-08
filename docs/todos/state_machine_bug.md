# 這個檔案不要commit 是拿來追蹤實作的

# Question:
這是我的問題點與我的survvey
### 問題摘要：Daily 模式（領地退守）在進入 `collect_only` 待機後無法定時回歸地下城

在 `[primary_modes.daily]` 同時啟用 `auto_resume_dungeon_on_cd = true`、`enable_stage_farming = false` 且長駐路由設為領地探索（`tier4_mode = "domain"`，如黃金古國）時，系統一旦進入 `COLLECT_ONLY`（定時領取待機）狀態，便無法在地下城冷卻結束後自動切回地下城，主要問題點如下：

---

#### 1. 路由類型衝突導致地下城可用性判定永久失效
* **現象**：當 Daily 模式退守至黃金古國時，運行中的配置類型會被動態設為 `type = "domain"`。
* **問題點**：地下城可用性檢查函式（`has_available_dungeon`）內部設有型態白名單，僅允許 `["dungeon", "mix", "daily"]`。當傳入或讀取當前運行的領地配置（`domain`）時，系統直接將其視為非地下城模式並固定回傳 `False`，導致即便冷卻時間已過，系統仍判定「無可用地下城」。

#### 2. 因關卡停用（`enable_stage_farming = false`）進入待機時遺漏復歸配置
* **現象**：當指定的地下城全部處於冷卻中，且因設定關閉了普通關卡打怪，導航處理器會自動返回城鎮並切換至 `COLLECT_ONLY`。
* **問題點**：該轉移流程僅發起狀態切換，未保存原本的地下城設定（`dungeon_cooldown_return_config` 為空），亦非體力耗盡退避流程（未設定 `original_config`）。待機處理器因而失去了「冷卻結束後該回到哪一個模式」的上下文依據。

#### 3. 待機喚醒機制依賴當前臨時配置而非 Daily 基準策略
* **現象**：處於 `COLLECT_ONLY` 待機迴圈時，系統會定期掃描是否有週期性任務已就緒。
- **問題點**：待機處理器僅檢驗當前暫存的路由設定（此時為無地下城設定的 `collect_only` 或 `domain`），並未參照 Daily 主策略（`primary_config`）來評估地下城冷卻；同時，Daily 流水線在進入 `COLLECT_ONLY` 期間會被標記為停用，全域活動調度器因而停止運作，使地下城冷卻就緒訊號無法傳遞給待機迴圈。


因為我的地下城跟stage lord, demon_lord , domains 應該都是可插拔的 而其中 lord,dungeon 有冷卻時間  根據 [project_arch_greenfield_lite_v1.md](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/docs/architecture/project_arch_greenfield_lite_v1.md)  你認為應該怎麼修正架構可以徹底解決該問題

===

# Answer

結論：不要再補更多 `original_config`／`dungeon_cooldown_return_config`。根治方式是把「長期策略、客觀冷卻、當前執行路由、FSM 狀態」拆成四個獨立概念，並讓唯一的 Activity Scheduler 在 `COLLECT_ONLY` 期間仍然存活。

你列出的三個根因判斷是正確的，而且本質上是同一個架構問題：目前 `config` 同時扮演了過多角色。

## 現況問題

| 現在的概念 | 實際混入的責任 | 後果 |
|---|---|---|
| `primary_config` | Daily 長期策略 | 方向正確，但待機時取不到 |
| `config` | 當前路由、功能開關、模式身分 | 切成 `domain`／`collect_only` 後遺失 Daily 語意 |
| `type` | UI 路由類型兼功能能力白名單 | `domain` 被錯判成不具地下城能力 |
| `original_config` | 體力退避復歸 | 只能處理特定入口 |
| `dungeon_cooldown_return_config` | 地下城冷卻復歸 | 每增加一種活動就要再增加一份 return config |
| `COLLECT_ONLY` | FSM 狀態、待機策略、臨時模式 | 一進入就關閉 Daily scheduler |

目前有三個非常直接的斷點：

- [`has_available_dungeon()`](E:/Side_Project/BlackfireCrusade_tool/states/state_machine.py:1046) 用 `type` 白名單判斷能力，`domain` 必然失敗。
- [`NavigationHandler`](E:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py:346) 在 `enable_stage_farming=False` 分支只切 `COLLECT_ONLY`，沒有保留任何復歸語意。
- [`is_daily_pipeline_active()`](E:/Side_Project/BlackfireCrusade_tool/states/state_machine.py:1851) 明確規定 `COLLECT_ONLY => False`，導致原本已有的 `primary_config`／`has_available_daily_dungeon()` 在待機時失效。
- [`CollectOnlyHandler`](E:/Side_Project/BlackfireCrusade_tool/states/handlers/collect_only.py:186) 又回頭依賴臨時 `config.enable_dungeon`，形成循環依賴。

另外，[`build_tier4_fallback_config()`](E:/Side_Project/BlackfireCrusade_tool/utils/tier4_config.py:25) 是複製整份 Daily policy 再覆寫成 `type="domain"`。這正是「策略」與「路由」混合的源頭。

## 建議的目標架構

```text
WorkflowPolicy（使用者長期策略，永不因狀態切換消失）
        │
        ├── ActivityRegistry
        │     ├── dungeon
        │     ├── lord_boss
        │     ├── demon_lords
        │     ├── stage
        │     └── domain
        │
Cooldown/Runtime Facts（客觀事實）
        │
        ▼
ActivityScheduler（唯一活動選擇 owner）
        │
        ▼
ActiveIntent（目前要完成的活動）
        │
        ▼
RouteFactory → ActiveRouteConfig（一次性的執行路由）
        │
        ▼
NAVIGATING / BATTLE / RESULT / WAITING
```

這符合 greenfield-lite 的三條核心規則：

- Intent 不因 scene／FSM state 改變而消失。
- Defer 不等於完成，也不能清除 pending fact。
- 同一路徑不能有兩個 decision owner。

參見[架構文件](E:/Side_Project/BlackfireCrusade_tool/docs/architecture/project_arch_greenfield_lite_v1.md:127)。

### 1. `COLLECT_ONLY` 只能是等待控制狀態

保留 `STATE_COLLECT_ONLY` 以避免一次重寫所有 Handler，但重新定義它：

> `COLLECT_ONLY` 是 Agent 暫時沒有可執行 primary activity 時的 `WAITING` control phase，不是一個新的業務模式。

進入待機時：

- 不再執行 `config = GAME_CONFIGS["collect_only"]`。
- 不清除 `ActiveIntent`／Workflow。
- 不停用 Daily scheduler。
- 只建立 `IdleContext(reason, next_wake_at)`。
- Diamond／Bread 仍可用較高順位 intent 插隊。

因此 `is_daily_pipeline_active()` 應只取決於：

```python
workflow_policy.workflow_id == "daily"
```

絕不能再參考：

- `current_state == COLLECT_ONLY`
- `config["type"]`
- `quest_scheduler is not None`
- 是否正在 domain／stage／dungeon

### 2. 將 Policy 與 Route Config 完全分離

建議最小契約：

```python
@dataclass(frozen=True)
class WorkflowPolicy:
    workflow_id: str
    activities: Mapping[ActivityId, ActivityPolicy]
    fallback_activity: ActivityId | None


@dataclass(frozen=True)
class ActivityPolicy:
    enabled: bool
    priority: int
    preempt_when_ready: bool
    settings: Mapping[str, object]


@dataclass(frozen=True)
class ActiveRoute:
    activity_id: ActivityId
    target_id: str | None
    route_config: Mapping[str, object]
```

對應語意：

- `WorkflowPolicy`：使用者選擇，長期存在。
- `ActiveRoute`：目前為了執行某個 Activity 暫時產生。
- `config["type"]`：只描述這條 route 要交給哪種 Handler，不再代表整個工作流程身分。

Daily 的配置應解讀成：

```text
activities.dungeon.enabled = true
activities.stage.enabled = false
fallback_activity = domain
domain.target = golden_empire
```

如此 `enable_stage_farming=false` 只會停用 Stage，不會被錯誤解讀為「沒有退守活動」。`tier4_mode=domain` 已經明確指定 Domain 才是 fallback。

### 3. 使用輕量 Activity Registry，不做動態 plugin framework

greenfield-lite 明確延後通用 plugin framework；所以這裡適合的是 Python 宣告式 registry：

```python
ACTIVITY_REGISTRY = {
    ActivityId.DUNGEON: DungeonActivitySpec(),
    ActivityId.LORD_BOSS: LordBossActivitySpec(),
    ActivityId.DEMON_LORDS: DemonLordsActivitySpec(),
    ActivityId.STAGE: StageActivitySpec(),
    ActivityId.DOMAIN: DomainActivitySpec(),
}
```

每個 Activity module 只提供：

```python
class ActivitySpec(Protocol):
    def evaluate(
        self,
        policy: ActivityPolicy,
        facts: ActivityFacts,
        now: float,
    ) -> ActivityAvailability:
        ...

    def build_intent(
        self,
        policy: ActivityPolicy,
        availability: ActivityAvailability,
    ) -> PrimaryIntent:
        ...

    def build_route(
        self,
        intent: PrimaryIntent,
    ) -> ActiveRoute:
        ...
```

其中：

- `evaluate()` 必須是純查詢，不點擊、不切狀態、不跑 OCR。
- OCR／Result Handler 只更新 cooldown facts。
- Scheduler 是唯一可以選擇下一個 Activity 的元件。
- Navigation 只負責執行選好的 route。

這已足以達到你要的「可插拔」：新增活動時增加一個 module、一筆 registry、一組測試，不需要更動 `CollectOnlyHandler` 的大量 `if activity == ...`。

### 4. 用統一的 Availability 取代所有 `has_available_xxx`

建議共同回傳：

```python
class AvailabilityState(Enum):
    READY = auto()
    COOLDOWN = auto()
    DISABLED = auto()
    COMPLETED = auto()
    BLOCKED = auto()


@dataclass(frozen=True)
class ActivityAvailability:
    state: AvailabilityState
    ready_at: float | None = None
    target_id: str | None = None
    reason: str = ""
```

不同 Activity 的判定：

- Dungeon：允許的 dungeon target 中是否至少一個 `ready_at <= now`。
- Lord Boss：目標已選取、今日未完成且 CD 到期。
- Demon Lord：今日次數／重置狀態允許。
- Stage：啟用時通常為 `READY`。
- Domain：啟用且資源條件滿足時通常為 `READY`。

`DungeonActivitySpec` 不需要知道目前是不是 `domain`。它只檢查：

```text
Dungeon policy 是否啟用
＋允許哪些 dungeon
＋對應 cooldown fact 是否到期
```

所以 [`has_available_dungeon()`](E:/Side_Project/BlackfireCrusade_tool/states/state_machine.py:1062) 的 `type` 白名單應最終刪除，而不是把 `"domain"` 加入白名單。加入 `"domain"` 只是另一個特例。

### 5. 統一 Cooldown Store

目前 Dungeon CD 在 `GameStateMachine.dungeon_cooldowns`，Lord Boss CD 在 `DailyManager`，這也讓活動模組難以真正對稱。

建議集中成：

```python
CooldownKey(
    activity_id=ActivityId.DUNGEON,
    target_id="ice_cave",
)

CooldownFact(
    ready_at=...,
    observed_at=...,
    source="ocr",
)
```

Lord Boss 也使用相同結構：

```python
CooldownKey(ActivityId.LORD_BOSS, "lord_spider")
```

注意兩種時間不能混用：

- Action timeout／watchdog：monotonic time。
- 遊戲活動 CD：可持久化的 epoch wall time，重開程式後仍有效。

Dungeon 與 Lord 的 OCR Handler 只負責寫入 `CooldownStore`，不負責決定下一個活動。

### 6. Scheduler 在所有狀態下持續工作

Scheduler 每次只輸出一個決策：

```python
RUN_ACTIVITY
KEEP_CURRENT
DEFER_CURRENT
WAIT_UNTIL
PREEMPT_AT_SAFE_POINT
```

大致流程：

```python
decision = scheduler.decide(
    policy=workflow_policy,
    facts=activity_facts.snapshot(),
    active_intent=active_intent,
    now=clock.wall_time(),
)

if decision.is_ready:
    active_intent = decision.intent
    active_route = registry[decision.activity_id].build_route(decision.intent)
elif decision.wait_until:
    idle_context = IdleContext(decision.reason, decision.wait_until)
```

即使 FSM 正處於 `COLLECT_ONLY`，仍然執行同一個 `scheduler.decide()`。

`CollectOnlyHandler` 不再自行逐一詢問 Dungeon、Lord、Demon Lord；它只：

- 處理目前 collection intent。
- 消費 scheduler 已產生的 wake/preemption decision。
- 沒有決策時等待或做心跳。

### 7. 用 `ActivityOutcome` 取代復歸配置

Handler 結束時回報：

```python
ActivityOutcome.completed(...)
ActivityOutcome.deferred(reason="cooldown", retry_at=...)
ActivityOutcome.blocked(reason="no_stamina", retry_at=...)
ActivityOutcome.failed(...)
```

然後 Scheduler 重新選擇活動。

這會讓以下欄位逐步消失：

- `dungeon_cooldown_return_config`
- `original_config` 作為通用路由復歸手段
- 各 Handler 內自己恢復 `primary_config`
- `ensure_explore_config()` 裡依序猜哪份 config 可以用

體力退避也應該是：

```text
Dungeon intent
  → BLOCKED(no_stamina, retry_at=...)
  → Scheduler 選擇 Domain／Stage／WAITING
  → retry_at 到期後重新評估 Dungeon
```

而不是備份整份 config、換成 collect-only、幾小時後再複製回去。

## 這個案例修正後的行為

你的設定：

```text
Daily workflow
Dungeon enabled
Stage disabled
Fallback = Golden Empire domain
```

執行結果會是：

1. Dungeon 可用：Scheduler 選擇 Dungeon intent。
2. Dungeon 全冷卻：Dungeon 回傳 `COOLDOWN(next_ready_at)`。
3. Scheduler 選擇 fallback Domain。
4. 若因體力或其他原因 Domain 也不可執行，進入 `WAITING/COLLECT_ONLY`，但 Daily workflow 仍存在。
5. Dungeon CD 到期後，不論目前在 Domain、Town 或 `COLLECT_ONLY`，Dungeon evaluator 都會回傳 `READY`。
6. Scheduler 產生 `PREEMPT_AT_SAFE_POINT(DUNGEON)`。
7. 目前活動安全退出後，RouteFactory 從 Dungeon policy 重新產生路由並進入導航。

整段流程完全不需要知道「原本 config 是哪一份」。

## 建議的漸進遷移順序

1. 先修正生命週期：

   - `is_daily_pipeline_active()` 改由 workflow identity 判斷。
   - `COLLECT_ONLY` 不再覆蓋 Daily policy。
   - 所有 Daily availability 一律讀 `primary_config`。
   - `type` 不再作為 Dungeon capability gate。

2. 建立 `ActivityAvailability` 與中央 Scheduler：

   - 先遷移 Dungeon、Lord Boss。
   - 再遷移 Demon Lord。
   - Stage／Domain 成為 fallback providers。

3. 建立統一 `CooldownStore`：

   - 先包裝現有 dungeon dict 與 DailyManager，不需要一次改存檔格式。
   - 穩定後再統一持久化。

4. 最後刪除 legacy context：

   - `dungeon_cooldown_return_config`
   - 通用用途的 `original_config`
   - `CollectOnlyHandler` 裡各 Activity 的硬編碼掃描
   - Handler 內直接呼叫全域 scheduler 的分支

## 必要鎖定測試

至少應補這些架構行為測試：

- Daily + Domain fallback + Dungeon CD 到期，即使位於 `COLLECT_ONLY` 仍選中 Dungeon。
- 不存在任何 return config 時仍可復歸。
- `active_route.type == "domain"` 不影響 Dungeon availability。
- `enable_stage_farming=false` 且 fallback 為 Domain 時，Dungeon 冷卻期間選擇 Domain，不是待機。
- Bread／Diamond pending 時先完成 collection，之後 Dungeon intent 仍存在。
- `auto_resume_dungeon_on_cd=false` 時 Dungeon READY 不插隊持續活動。
- Lord Boss 與 Dungeon 同時 READY 時，依固定 precedence 只選一個。
- 狀態切到 `COLLECT_ONLY`、`UNKNOWN`、`NAVIGATING` 都不改變 workflow identity。
- Profile hot reload 發生在待機狀態時，新 policy 仍能生效。

你目前工作樹中針對 `tier4_dungeon_index` 的修正是必要的，能避免讀錯 Dungeon CD；但它只修正 target selection，沒有處理 `COLLECT_ONLY` 的 workflow lifecycle。真正的架構邊界應是：

> `WorkflowPolicy` 決定有哪些活動；`CooldownFacts` 決定何時可執行；`Scheduler` 決定現在做哪一個；`RouteConfig` 只決定如何走；FSM state 只表示目前控制階段。