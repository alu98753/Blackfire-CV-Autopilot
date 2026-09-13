# [TODO] IntentRouting 觀測性日誌語意解耦與結構化收斂

> 狀態：規劃中（Ready for Implementation）  
> 領域：[Navigation Routing](../../states/navigation_routing.py) / [Logging Specification](../architecture/logging_and_diagnostics_spec.md)  
> 上位架構契約：[Precondition Contracts](../architecture/precondition_contracts.md) (Section 11)  

---

## 1. 問題脈絡與背景 (Context & Symptom)

在 2026-09-11 的運行日誌中，曾出現以下一行排程紀錄：

```text
2026-09-11 12:53:18,694 [INFO] [IntentRouting] intent=collect_bread scene=stage_select action=open_bread reason=bread_entry_ready progress=deferred in_flight=return_town expected=town age=5.7s deadline=52018.812 attempt=3
```

該行日誌將多個維度的資訊壓縮在同一行輸出，導致閱讀者（包括工程師與 AI 協同代理人）產生嚴重的語意誤解：
1. 直觀上看，日誌將 `intent=collect_bread` 與 `progress=deferred` 放在一起，容易被解讀為「`collect_bread` 處於 deferred 狀態」。
2. 同時，日誌中又出現 `action=open_bread` 與 `in_flight=return_town`，使人誤以為「系統正在為 `collect_bread` 執行回城，且又在進行打開體力視窗」。
3. 這種語意混淆進一步衍生出虛假的架構假設，懷疑「定時領體力在特定畫面觸發 DEFER 時被誤當成 Blocking 導致主排程活鎖」，並一度計畫發起不必要的排程器架構修改。

---

## 2. 根本原因分析 (Root Cause in Code)

審查 [states/navigation_routing.py](../../states/navigation_routing.py) 中 [NavigationDecisionExecutor.execute](../../states/navigation_routing.py#L226) 與 [NavigationRoutingContext](../../states/navigation_routing.py#L198) 的建構時序：

```python
# states/navigation_routing.py:
observed_action = progress.in_flight if progress is not None else None
progress_status = progress.observe(scene, now) if progress is not None else ProgressStatus.IDLE
...
active_intent = _select_available_intent(policy, intent_snapshot, progress, now)
decision = policy.resolve(scene, active_intent)
```

當前日誌記錄邏輯為：

```python
logging.info(
    "[IntentRouting] intent=%s scene=%s action=%s reason=%s "
    "progress=%s in_flight=%s expected=%s age=%.1fs "
    "deadline=%.3f attempt=%d",
    context.active_intent.intent_id.value,      # 當前 tick 剛選出的全新 Intent (例如 collect_bread)
    context.scene.scene.value,                  # 當前觀測到的場景 (例如 stage_select)
    decision.action.value if decision.action else "none",  # 當前 tick 針對全新 Intent 做出的動作 (例如 open_bread)
    decision.reason.value,                      # 當前決策原因
    context.progress_status.value,              # 前一個 InFlightAction 經 observe 後的狀態 (例如 deferred)
    action.action_id.value,                     # 前一個 InFlightAction 的動作名稱 (例如 return_town)
    action.expected.value,                      # 前一個 InFlightAction 的預期後置條件 (例如 town)
    ...
)
```

**矛盾根源**：
- `intent` 與 `action` 描述的是「**當前 tick 決策層**（Decision / Candidate Selection）剛選出的新意圖與即將執行的動作」。
- `progress` 與 `in_flight` 描述的是「**前一個 tick 執行層**（Observation / InFlightAction）所遺留之動作的驗證結果」。
- 將「前置動作的驗證進展」與「當前新選取的業務意圖」未加區分地混合同行印出，造成主謂語意錯位。

實際上，排程器行為完全正確：前一個動作（`return_town`）逾時被標記為 `deferred` 後，選擇器順利選出了下一個合法的候選任務 `collect_bread`，並做出 `open_bread` 決策；隨後更成功降級推進主導航進入戰鬥。系統並無活鎖 bug，問題完全出在日誌的可觀測性（Observability）。

---

## 3. 改造規劃 (Proposed Observability Cleanup)

本工作僅修改日誌輸出格式，嚴格不變更任何排程調度或狀態機行為：

### 欄位解耦對齊

將目前混合語意的欄位：
- `intent=`
- `action=`
- `progress=`
- `in_flight=`

明確拆分為五個具備清晰主詞的結構化欄位：

| 原欄位 | 建議新欄位 | 語意與資料來源 | 範例數值 |
| --- | --- | --- | --- |
| `intent=` | `selected_intent=` | 當前 tick 經選擇器決策之活躍 Intent (`context.active_intent.intent_id.value`) | `collect_bread` / `primary_navigation` |
| `action=` | `decision_action=` | 當前 tick 針對 `selected_intent` 決定發射之新動作 (`decision.action.value`) | `open_bread` / `continue_primary` |
| *(新增)* | `observed_intent=` | 前置 In-Flight 動作所屬之 Intent（無 in-flight 時為 `none`） | `collect_diamond` / `none` |
| `in_flight=` | `observed_action=` | 前置 In-Flight 動作之 Action 名稱（無 in-flight 時為 `none`） | `return_town` / `none` |
| `progress=` | `observed_progress=` | 前置 In-Flight 動作當前幀之觀測驗證狀態 | `waiting` / `satisfied` / `timed_out` / `deferred` / `idle` |

### 日誌輸出前後對比

- **改造前（易誤導）**：
  ```text
  [IntentRouting] intent=collect_bread scene=stage_select action=open_bread reason=bread_entry_ready progress=deferred in_flight=return_town expected=town age=5.7s deadline=52018.812 attempt=3
  ```
- **改造後（清晰明確）**：
  ```text
  [IntentRouting] selected_intent=collect_bread decision_action=open_bread reason=bread_entry_ready scene=stage_select observed_intent=collect_diamond observed_action=return_town observed_progress=deferred expected=town age=5.7s deadline=52018.812 attempt=3
  ```
  在無 in-flight action 時：
  ```text
  [IntentRouting] selected_intent=primary_navigation decision_action=continue_primary reason=primary_route_delegated scene=stage_select observed_progress=idle
  ```

---

## 4. 三大守護不變量 (Three Guiding Invariants)

本項清理及後續任何涉及 `navigation_routing.py` 或 `state_machine.py` 的重構，必須嚴格遵守以下三條長效不變量（已收斂於 [Precondition Contracts](../architecture/precondition_contracts.md#11-狀態機重構三大硬性不變量-refactoring-invariants)）：

1. **Gate Invariant**：不得破壞 `is_deferred()` 對 intent eligibility 的門禁。
   - Deferred 期間的 Intent 必須維持不可被選取；主排程必須保有自由降級並推進其他非依賴任務的自由度。
2. **In-Flight Action Exclusivity Invariant**：既有動作未 resolution 前禁止發射第二動作。
   - 在既有 `InFlightAction` 未達成 postcondition 或超時確認前，禁止任何模組發送第二個業務點擊或強行切換 Intent。
3. **Lifecycle Migration Slice Isolation Invariant**：禁止在重構中順手統一雙重生命週期。
   - 既有相容層的 legacy flags（如 `need_bread_collection`、`need_diamond_collection`）與 `NavigationProgress` 內部生命週期屬於獨立的 migration slice，嚴禁在本次日誌修復或一般重構中順手整併。

---

## 5. 驗收標準 (Acceptance Criteria)

- [ ] [states/navigation_routing.py](../../states/navigation_routing.py) 的 `NavigationDecisionExecutor.execute` 日誌輸出格式更新為新結構化欄位名稱。
- [ ] 無 InFlightAction 與存在 InFlightAction 兩種情境的日誌均可正確區分 `selected_intent`、`decision_action` 與 `observed_*`。
- [ ] 現有單元測試（特別是 `tests/test_behavior_navigation_intent.py` 與 `tests/test_behavior_runtime_ports.py`）維持 100% 通過。
- [ ] 日誌更新不改變任何決策邏輯、狀態跳轉或 InFlightAction 處理生命週期。
