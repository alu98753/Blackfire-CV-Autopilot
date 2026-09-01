# Greenfield-lite Navigation Intent Routing Spec（v1）

> 狀態：v1 行為與遷移規格，尚未實作  
> 上位標準：[Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md)  
> 範圍：Diamond、Bread、Primary Navigation、Start commitment、未知 Quest fallback，以及 `NAVIGATING`／`LOBBY` 的相容遷移。  
> 固定限制：任務順序由使用者寫死；不做戰鬥策略；timeout／retry／backoff 只由 TOML defaults 設定，不提供 CLI 覆寫。

## 1. 文件責任

上位文件定義整體架構、低負載感知、Navigation Table、Ports 與 Recovery。本文件只定義下列可直接驗收的行為：

1. legacy flags 如何成為 `IntentSnapshot`，再選出唯一 `ActiveIntent`。
2. Bread、Diamond、Start 同時可用時，只能產生一個決策。
3. 已提交的 Start 不得被新到期的 collection 中途搶占。
4. 未知 Quest 與 Tier 4 fallback 不得修改 collection pending facts。
5. Collection action 如何驗證、timeout、defer、backoff 與升級 recovery。
6. 現有 Handler 如何逐步遷移且不形成兩個決策 owner。

本文件不重新定義 `SceneSnapshot`、Detector profile、Ports 或整體 recovery 階層；若有衝突，以上位文件為準。

## 2. 事故與必須消失的路徑

### 2.1 原始活鎖

```text
未知 Quest 無法建立 TaskNode
  → Primary payload 降級為 Tier 4
  → need_bread_collection 仍為 True
  → NAVIGATING 因 Start 可見轉入 LOBBY
  → LOBBY 因 Bread pending 轉回 NAVIGATING
  → 重複，但 Bread 沒有進展
```

直接原因不是未知 Quest，而是 [NavigationHandler](../../states/handlers/navigation.py) 與 [LobbyHandler](../../states/handlers/lobby.py) 各自擁有不同的優先序。State 持續改變也讓只看 `last_state_change` 的 Watchdog 誤以為系統仍在前進。

### 2.2 v1 必須保證

```text
同一 SceneSnapshot
  + 同一 ActiveIntent
  + 同一 InFlightAction
  → 唯一 ActionDecision
```

`NAVIGATING`、`LOBBY` 在相容期間仍可存在，但只能執行共享 Policy 的結果，不能自行重新判斷 collection 與 Start 的優先序。

## 3. Legacy facts 與唯一 ActiveIntent

### 3.1 IntentSnapshot adapter

既有欄位在遷移期仍是 pending fact 的來源：

`IntentSnapshot` 是不可變值，欄位只有 `diamond_pending`、`bread_pending`、`primary_payload` 與 `stamina_retreat_active`。

正規化規則：

```text
diamond_pending = need_diamond_collection
bread_pending = enable_bread AND need_bread_collection
primary_payload = 使用者寫死的目前 stage / dungeon / Tier 4 工作
stamina_retreat_active = stamina_retreat_start_time is not None
```

- Adapter 只讀取與正規化，不清除 flags、不點擊、不 transition。
- Legacy flags 表示「仍待處理」，不是目前決策 owner。
- `ActiveIntentContext` 是唯一目前目標；不得另建一套可由 Handler 寫入的 intent queue。
- Collection flag 只可由對應 outcome handler 在成功或確認 cooldown 後清除。

### 3.2 選擇與安全點

只有在沒有 `InFlightAction`，且目前 intent 已完成、defer、取消或尚未選擇時，才可選擇 intent：

```text
COLLECT_DIAMOND
  > COLLECT_BREAD
  > PRIMARY_NAVIGATION
```

這是使用者核准的固定相容順序，不做 deadline ranking、utility score 或動態排序。重大 overlay／背包滿等 safety guard 屬於控制層中斷，不是第四種業務 intent。

### 3.3 Legacy commitment mapping

`LobbyHandler.start_first_click_time is not None` 在遷移期必須映射為 `InFlightAction(action=START_PRIMARY, expected=SCENE_LOADING_OR_BATTLE)`；`source_frame_id` 使用發出 Start 的 frame，`issued_at` 使用既有時間戳。

`bread_window_opened`、`diamond_window_opened` 只可作為 legacy phase hint；它們不是完成證據，也不能取代新 `SceneSnapshot` 的 window evidence。

## 4. 單一決策契約

`ActionDecision` 是不可變值：`kind` 只能是 `CLICK`、`DELEGATE`、`WAIT`、`RECOVER`；其餘欄位為穩定 `reason`，以及可省略的 semantic `action` 與 `expected` postcondition。

規則：

- 相同 `SceneSnapshot + ActiveIntent + InFlightAction` 必須得到相同 decision。
- 每個 tick 最多執行一個 click、delegate、wait 或 recover。
- Policy 不讀 matcher、mouse、clock、mutable machine 或 `time.sleep()`。
- Decision 引用 semantic `ActionId`／`ElementId`，不包含絕對螢幕座標。
- `reason` 使用穩定 snake_case，供 log、metrics 與公開行為測試使用。

最低 reason codes：`verify_in_flight_action`、`diamond_window_ready`、`diamond_return_to_town`、`diamond_entry_ready`、`bread_window_ready`、`bread_enter_lobby`、`bread_entry_ready`、`primary_start_ready`、`scene_evidence_insufficient`、`collection_deferred`、`collection_recovery_required`。

## 5. Routing precedence 與矩陣

### 5.1 每輪固定 precedence

1. 驗證／timeout 目前 `InFlightAction`。
2. 處理 critical overlay 或 recovery guard。
3. Delegate 已確認開啟且符合 active intent 的 collection window。
4. 沿目前 `ActiveIntent` 的 Navigation Table edge 前進。
5. 證據不足時 `WAIT`；達 no-progress 上限後才 recovery。

Start 只是 `PRIMARY_NAVIGATION` 的一條 edge。畫面上存在 Start，不能改變 `ActiveIntent`。

### 5.2 Collection 與 Primary 決策矩陣

| ActiveIntent | Scene evidence | 唯一 decision | Postcondition | 禁止行為 |
| --- | --- | --- | --- | --- |
| Diamond | `DIAMOND_WINDOW` | delegate Diamond handler | handler phase 前進 | Start／轉 Lobby |
| Diamond | `TOWN + DIAMOND_ENTRY` | click Diamond entry | `DIAMOND_WINDOW` | 清除 pending |
| Diamond | `LOBBY + GOBACK_TOWN` | click Go Back | `TOWN` | 因 Start 可見改做 Primary |
| Bread | `BREAD_WINDOW` | delegate Bread handler | handler phase 前進 | Start／轉 Lobby |
| Bread | `LOBBY + BREAD_ENTRY` | click Bread entry | `BREAD_WINDOW` | 清除 pending |
| Bread | `TOWN + DOOR` | click Door | `LOBBY` | 猜 Bread 座標 |
| Primary | `LOBBY + START` | click Start | `LOADING` 或 `BATTLE` | 同 tick 做第二動作 |
| Primary | Stage／Dungeon scene | 使用 Navigation Table 下一 edge | edge 定義結果 | 重新排序任務 |
| 任一 | `UNKNOWN`／證據不足 | wait／reobserve | 新 snapshot | 猜座標、清 pending |

`GOBACK_TOWN`、`START`、`BREAD_ENTRY` 同時存在是合法 observation。Detector 必須全部回報，由 Policy 依 active intent 選一條路。

### 5.3 Start commitment

若 Start 已發出，之後才 latch Diamond 或 Bread：

1. 保留新 collection pending fact。
2. 不切換 `ActiveIntent`，先等待 Start postcondition 或 timeout。
3. 成功進入 Loading／Battle 後，在下一個安全點重新選 intent。
4. Start timeout 依 action retry 規則處理；不得以返回 `NAVIGATING` 當成成功。

## 6. Collection outcome、Defer 與 Progress

### 6.1 完成語意

[BreadCollectionHandler](../../states/handlers/bread_collection.py) 與 [DiamondCollectionHandler](../../states/handlers/diamond_collection.py) 只有在下列 evidence 成立時才能回報完成：

- 領取成功的畫面／後續 phase 已確認；或
- 明確確認仍在 cooldown，當輪不需領取。

暫時辨識不到按鈕、window flag 被重置、返回其他 state 或 elapsed time 經過，都不算完成。

完成時必須原子化地：

1. 清除對應 pending flag。
2. 重置該 collection handler 的 window／click phase。
3. 清除 `ActiveIntentContext` 的完成項目。
4. 依 `stamina_retreat_active` 顯式返回 `COLLECT_ONLY`，否則回導航骨幹。

### 6.2 有效 Progress

以下才可更新 `last_progress_at`：

- Navigation edge 的 postcondition 成立。
- Collection window 已由 snapshot 確認開啟。
- Collect／confirm／quit phase 確實前進。
- Intent 完成或確認 cooldown。

`NAVIGATING ↔ LOBBY` state 名稱往返、重複產生同一 WAIT，或重複點擊但 postcondition 未成立，都不算 progress。

### 6.3 Timeout 與固定 Backoff

Collection route 達 timeout／retry 上限時：

1. 記錄 `collection_routing_no_progress`。
2. 清理暫態 window／click context，但保留 pending flag。
3. 將 active collection intent 設為 deferred，寫入 `retry_at`。
4. 返回 `PRIMARY_NAVIGATION`；若在體力退避模式則進 `COLLECT_ONLY` 等待。
5. 同一 intent 連續達 recovery 上限後，交由上位 Recovery 執行重新定位或 relaunch。

必要 TOML default keys：

```text
collection_action_timeout_seconds
collection_action_max_attempts
collection_backoff_seconds
collection_recovery_failure_limit
```

這些設定不可成為 CLI options，也不可在 Handler 內使用 magic number fallback。

## 7. Unknown Quest 與 Tier 4 邊界

[QuestMapper](../../utils/quest_mapper.py) 回傳 `None` 並記入 `unknown_quests` 是資料映射結果，不是導航錯誤：

```text
未知 Quest
  → 記錄並略過該 Quest
  → 其他已知 Quest 照常
  → 無可執行 Quest 時，PrimaryPayload 使用 Tier 4 fallback
```

Quest pipeline 只可更新 `primary_payload`，不可：

- 清除、完成或 defer Diamond／Bread pending。
- 因 Start 可見直接繞過 active collection intent。
- 把 unknown Quest 標為完成或建立猜測型 TaskNode。
- 因 unknown Quest 永久停在 `COLLECT_ONLY`。

Unknown Quest 日後被規則庫辨識時，可重新進入 primary fixed workflow；這仍不得改寫 collection outcome。

## 8. Legacy Handler 遷移契約

### 8.1 NavigationHandler 與 LobbyHandler

兩者在遷移期必須共用同一 Policy：

```text
1. 接收本 tick 唯一 SceneSnapshot
2. 取得 IntentSnapshot／ActiveIntent／InFlightAction
3. resolve 一次 ActionDecision
4. 執行一次並 return
```

- 不得在 Policy 前保留 Start 的無條件 early return。
- 不得各自複製 Diamond／Bread precedence。
- 不得在 Handler 現場重新呼叫 matcher。
- `transition_to()` 只執行呼叫者指定的 state 與 lifecycle hook，不暗中改道。

### 8.2 Collection handlers

Collection Handler 只擁有視窗內 phase 與 outcome，不擁有跨場景任務優先序。其輸入必須來自本 tick snapshot；已遷移分支不得直接 matcher。退出時依 [領取流程邊界](../knowledge.md) 與 stamina retreat 規範顯式選擇下一個 state。

### 8.3 相容切換

- Legacy fields 在全部呼叫者遷移前保留，由 adapter 集中讀取。
- 同一路徑切換給新 Policy 後，舊分支必須同次刪除，禁止 feature flag 雙軌決策。
- 不一次重寫城鎮建築、背包、地下城探索或戰鬥 Handler。
- 無呼叫者 helper、舊 decision enum 與重複 matcher 分支必須隨 slice 清除。

## 9. 可觀測性

只在 reason 改變、action 發出、postcondition 成立、defer 或 recovery 時記錄；WAIT 不得每幀刷 INFO。

```text
[IntentRouting] intent=collect_bread scene=lobby action=open_bread reason=bread_entry_ready
[IntentProgress] intent=collect_bread outcome=deferred reason=collection_routing_no_progress retry_at=...
```

最低 metrics：`scene`、`intent`、`decision_reason`、`action_attempt`、`elapsed_without_progress`、`defer_count`。是否寫入 incident journal 由既有事故紀錄規格決定，本文件不新增 incident schema。

## 10. 必要行為測試

1. Bread pending，且 snapshot 同時有 Start、Go Back、Bread：只發 Bread action。
2. Diamond pending，且 snapshot 有 Start、Go Back：只發回城／Diamond route。
3. Diamond 與 Bread 同時 pending：只選 Diamond；Diamond 完成後才選 Bread。
4. 無 collection pending 且 Start 可見：Primary 可發 Start。
5. Start 已 in-flight 後才 latch collection：先完成／timeout Start，pending 保留。
6. Collection scene 證據不足：WAIT，不點 Start、不清 pending。
7. Collection postcondition 未成立：不得視為成功；達上限後 defer。
8. Defer 後 pending 保留，`retry_at` 前不重新選取；達時可重試。
9. 連續 collection failure 達上限：交給 Recovery，不在 Policy 直接操作 process。
10. Unknown Quest + Bread pending：記錄 unknown、保留 Tier 4 payload，但先執行 Bread。
11. Collection 完成：pending、phase、active intent 一次性更新並回正確模式。
12. 固定 snapshot／intent 的 Policy 測試不需要 matcher、圖片、mouse 或真實時間。

回歸範圍至少涵蓋 navigation、collection、daily pipeline、collect-only 與 stamina retreat。日常開發只精準執行相關測試；分支收尾前才依專案規範跑全套測試。

## 11. 實作切片

1. **Adapter 與純 Policy**：建立 IntentSnapshot、ActiveIntent selection、ActionDecision；不改 scheduler ownership。
2. **Navigation／Lobby 共用路由**：移除各自 precedence，接入單一 Policy 與 Start commitment adapter。
3. **Collection outcome 與 InFlightAction**：所有 click 加入 postcondition、timeout、retry 與原子完成語意。
4. **Unknown Quest boundary**：限制 Quest fallback 只能改 primary payload，補齊衝突測試。
5. **Progress／Defer／Recovery**：加入 TOML defaults、retry_at、no-progress 與 recovery escalation。

每個 slice 必須保持未遷移 Handler 可運作，且已遷移路徑只有一個 owner。

## 12. 完成條件

1. `NAVIGATING`、`LOBBY` 不再各自擁有 collection／Start precedence。
2. Bread／Diamond／Primary 同時只存在一個 `ActiveIntent`。
3. Start 與 collection action 都由 `InFlightAction` 驗證，未驗證前不能發第二個業務 action。
4. Unknown Quest／Tier 4 fallback 無法修改 collection pending 或 outcome。
5. Collection timeout 會 defer 並保留 pending；連續失敗才升級 Recovery。
6. 事故序列重播不再形成 `NAVIGATING ↔ LOBBY` 無進展循環。
7. 已遷移 Handler 不直接 matcher，Detector 不執行 action，Policy 不做 IO。
8. 所有 timeout／retry／backoff 使用 TOML defaults，沒有新增 CLI options。
9. 本文件少於 300 行，相關公開行為測試全部通過。
10. 未引入動態任務排序、戰鬥策略、Event Bus、全域 Reducer 或第二套 workflow engine。
