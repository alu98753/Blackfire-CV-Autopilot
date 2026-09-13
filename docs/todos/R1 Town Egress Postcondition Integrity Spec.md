# R1 — Town Egress Postcondition Integrity v2

## 1. Status

**Type:** Correctness Hotfix / Behavior Correction
**Scope:** Chest + BulletinBoard Town egress false-success paths
**Architecture change:** No
**Shared abstraction:** No

本規格依 current branch `docs/intent-routing-observability-todo` 的實際 implementation 更新。

---

# 2. Goal

修正兩條已確認存在的 false-success path：

### BulletinBoard

```text
exit click
→ Town evidence UNKNOWN
→ _record_completion()
→ pop
```

### Chest

```text
VERIFY_EXIT
→ found_building == False × threshold
→ 假稱「已確認回到城鎮」
→ pop
```

共同問題為：

```text
absence of evidence
        ≠
positive Town evidence
```

以及：

```text
click issued
        ≠
postcondition satisfied
```

---

# 3. Architectural Model

本 R1 必須明確區分三種不同語意：

```text
Business completion
Physical egress postcondition
Recovery
```

它們不得互相替代。

---

## 3.1 Business completion

回答：

> 業務工作本身成功了嗎？

例如 Chest：

```text
free.png disappeared
OR
cooldown OCR established
```

目前 Chest 在此時呼叫：

```python
_complete_subflow()
```

並記錄：

```text
completed_today = True
```

這是既有 business-completion semantics。

**R1 不移動、不重新設計此 completion timing。**

---

## 3.2 Physical egress postcondition

回答：

> Handler 是否已經有 positive evidence 證明畫面回到 Town，可安全交棒？

例如：

```text
building anchor positively detected
+ corresponding Town-side evidence
```

只有這層成立，才允許：

```text
pop_and_next_town_subflow()
```

---

## 3.3 Recovery

當：

```text
egress postcondition UNKNOWN
```

且 bounded retry exhausted：

這代表：

```text
physical localization / egress recovery needed
```

不是：

```text
business failed
```

因此預設 recovery 為：

```python
relinquish_subflow_to_navigation(...)
```

交還 shared `REACH_TOWN` normalization。

---

# 4. Hard Invariants

## Invariant A — UNKNOWN Is Never Success

```text
UNKNOWN != SUCCESS
```

下列 evidence 不足：

```text
building not found
template miss
transition frame
black frame
overlay interference
exit click timeout
```

不得單獨推導：

```text
Town confirmed
```

---

## Invariant B — Click Is Not Egress Completion

發射：

```text
quit
exit
close
```

只代表：

```text
exit request submitted
```

不得直接表示：

```text
physical egress completed
```

必須由後續 observation 驗證。

---

## Invariant C — No Pop Before Positive Egress Evidence

在 physical Town postcondition 尚未成立前，不得呼叫：

```python
pop_and_next_town_subflow()
```

亦不得間接造成：

```text
_finish_town_subflow_queue()
→ STATE_NAVIGATING / COLLECT_ONLY
```

---

## Invariant D — Preserve Business Intent During Physical Recovery

如果 failure 原因是：

```text
cannot prove Town / cannot localize after exit
```

則不得：

```text
pop current_town_subflow
complete unfinished business
cancel intent
business-defer merely because location is unknown
```

應：

```text
preserve current_town_subflow
→ relinquish physical ownership
→ REACH_TOWN
→ resume same business intent
```

---

## Invariant E — Physical Recovery != Business DEFER

`DEFER` 只適用於：

```text
business temporarily unavailable
```

例如明確觀測到某個 business outcome 要求稍後重試。

它不是處理：

```text
「我不知道現在到底在哪」
```

的預設工具。

因此：

```text
egress UNKNOWN threshold
```

不得僅因 timeout 而：

```python
_defer_subflow()
```

除非已有明確 business evidence 支持 defer。

預設：

```python
relinquish_subflow_to_navigation()
```

---

## Invariant F — Existing Valid Business Completion Must Not Be Rolled Back

Chest 目前：

```text
VERIFY_CLAIM_SUCCESS
→ free disappeared / cooldown established
→ _complete_subflow()
→ WAITING_QUIT
```

此 business completion 與後面的 physical egress 為兩個獨立 postconditions。

R1 不得因後續 egress UNKNOWN：

```text
重新把已驗證的 successful claim 視為 business failure
```

也不得為了「統一」而移動 Chest completion timing。

---

# 5. R1-A — BulletinBoard

## Current Bug

目前：

```text
EXIT_BOARD
→ raw mouse.click(quit)
→ immediately ALL_DONE_EXITING
```

接著：

```python
if found_building and has_red_dot:
    defer
else:
    _record_completion()
```

因此：

```text
found_building == False
```

會掉進：

```text
_record_completion()
```

形成：

```text
UNKNOWN → completion → pop
```

---

# 6. BulletinBoard Required Behavior

## Phase 1 — Submit Exit

`EXIT_BOARD`：

如果看到 quit：

```text
submit exit
```

但不得把 click 本身當成成功。

應使用既有 bounded click/postcondition mechanism，例如：

```python
click_and_wait_until_gone(...)
```

或等價、行為一致的 bounded verification。

禁止裸：

```text
click
→ assume exited
```

---

## Phase 2 — Verify Physical Exit

進入 exit verification 後：

### Case A — Positive Town evidence + red dot exists

維持既有 business semantics：

```text
business incomplete
→ existing defer/yield behavior
```

R1 不重新定義其 business policy。

### Case B — Positive Town evidence + red dot absent

```text
_record_completion()
→ pop_and_next_town_subflow()
```

合法。

### Case C — Town evidence UNKNOWN

```text
WAIT / bounded retry
```

不得：

```text
_record_completion()
pop
```

---

## Phase 3 — UNKNOWN Exhausted

當 bounded retry exhausted：

```text
do NOT complete
do NOT pop
do NOT business-defer solely due to UNKNOWN
```

應：

```python
relinquish_subflow_to_navigation(
    reason="bulletin_board_exit_unverified"
)
```

並讓：

```text
current_town_subflow == bulletin_board
```

保持不變。

---

# 7. R1-B — Chest

## Existing Business Semantics

Chest 現行合法流程：

```text
VERIFY_CLAIM_SUCCESS

free disappeared
OR cooldown detected

→ _complete_subflow()
→ completed_today=True
→ WAITING_QUIT
```

R1 **保留此行為**。

---

# 8. Chest Current Egress Bug

目前：

```python
if check.found_building or self.not_found_count >= 3:
    logging.info("已確認回到城鎮")
    pop_and_next_town_subflow()
```

其中：

```text
not_found_count >= 3
```

只代表：

```text
bounded no-evidence threshold reached
```

不代表：

```text
Town confirmed
```

---

# 9. Chest Required Behavior

## Case A — Positive Town evidence

維持現有 positive path。

只有：

```text
check.found_building == True
```

時，才允許 physical handoff：

```python
pop_and_next_town_subflow()
```

---

## Case B — Positive Town evidence + red dot

目前存在：

```python
_defer_subflow(...)
```

R1 不主動重新設計此 business semantic。

如果 implementation 發現它與：

```text
claim_verified == True
```

存在邏輯衝突：

**不要在 R1 順手重構。**

應：

1. 保持最小既有行為；
2. 將矛盾記錄成 follow-up；
3. 不讓它阻塞 false-success hotfix。

---

## Case C — Town evidence UNKNOWN

```text
not_found_count < threshold
→ bounded retry
```

不得 pop。

---

## Case D — Town evidence UNKNOWN threshold exhausted

禁止：

```text
log "Town confirmed"
pop_and_next_town_subflow()
_defer_subflow() merely because location is unknown
```

應：

```python
relinquish_subflow_to_navigation(
    reason="chest_exit_unverified"
)
```

保留：

```text
current_town_subflow == chest
```

讓 shared `REACH_TOWN` 完成 physical recovery。

---

# 10. Queue Tail Safety

必須覆蓋特殊情況：

```text
Chest / BulletinBoard
is last queue item
```

在 egress UNKNOWN 時：

不得產生：

```text
pop
→ queue empty
→ _finish_town_subflow_queue()
→ STATE_NAVIGATING
```

因為這會形成：

```text
physical world: unknown / still inside
logical world: primary navigation resumed
```

R1 必須封死這條路徑。

---

# 11. Required Tests

## BulletinBoard

至少新增：

### Test 1

```text
EXIT_BOARD sees quit
→ click issued
→ exit postcondition not yet verified
```

不得：

```text
_record_completion
pop
```

### Test 2

```text
ALL_DONE_EXITING
found_building=False
```

不得：

```text
_record_completion
pop
```

### Test 3

```text
UNKNOWN below threshold
```

應繼續 bounded wait。

### Test 4

```text
UNKNOWN threshold exhausted
```

應：

```text
relinquish_subflow_to_navigation
```

並驗證：

```text
current_town_subflow preserved
no completion
no pop
```

### Test 5

```text
found_building=True
has_red_dot=False
```

既有 successful completion + pop 保持不變。

---

# 12. Chest Tests

至少新增：

### Test 1

```text
VERIFY_EXIT
found_building=False
count < threshold
```

不得 pop。

### Test 2

```text
VERIFY_EXIT
found_building=False
threshold exhausted
```

不得：

```text
pop
Town-confirmed log
business defer solely from UNKNOWN
```

應：

```text
relinquish_subflow_to_navigation
```

### Test 3

確認 relinquish：

```text
preserves current_town_subflow
does not pop queue
does not call _finish_town_subflow_queue
```

### Test 4

Chest 為 queue 最後 item：

```text
UNKNOWN exhausted
```

不得：

```text
STATE_NAVIGATING due to queue completion
```

### Test 5

```text
found_building=True
```

既有 positive egress path仍允許 pop。

### Test 6

既有 claim success：

```text
free disappeared / cooldown established
→ completed_today
```

不得因本 R1 被改變。

---

# 13. Characterization Before Modification

修改 production code 前，先新增 failing regression tests 證明：

```text
Bulletin UNKNOWN → false completion
Chest UNKNOWN threshold → false pop
```

推薦流程：

```text
RED
→ minimal production fix
→ GREEN
```

如果現有測試本身把錯誤行為寫成 expectation：

```text
先辨識那是 bug-locking test
→ 按本 spec 修改該 test
```

不要為了讓舊 test 綠而保留已確認錯誤。

---

# 14. Allowed Production Change Surface

預期主要只修改：

```text
states/handlers/bulletin_board.py
states/handlers/chest.py
```

以及直接相關 tests。

只有在既有 helper 無法支持必要 verification 時，才允許做最小 supporting change。

---

# 15. Explicit Non-Goals

R1 不做：

* IntentRouting observability 修改
* HeroDraw lifecycle 修正
* universal/shared Town egress framework
* 全部 Town Handler migration
* `NavigationProgress` redesign
* scheduler redesign
* `REACH_TOWN` redesign
* Town clear-anchor redesign
* lifecycle flags consolidation
* Chest completion timing redesign
* Chest red-dot-after-claim semantic redesign
* `state_machine.py` structural refactor

---

# 16. Existing Mechanisms To Reuse

優先重用：

```text
click_and_wait_until_gone()
relinquish_subflow_to_navigation()
REACH_TOWN normalization
existing handler bounded counters
```

不得平行建立第二套 recovery owner。

---

# 17. Acceptance Criteria

R1 完成需同時滿足：

1. BulletinBoard `found_building=False` 不會 `_record_completion()`。
2. BulletinBoard UNKNOWN 不會 pop。
3. BulletinBoard exit click 有 bounded postcondition verification。
4. BulletinBoard UNKNOWN exhausted 交由既有 REACH_TOWN recovery。
5. Chest `not_found_count >= threshold` 不再等於 Town success。
6. Chest UNKNOWN exhausted 不會 pop。
7. Chest UNKNOWN exhausted 不會單純因 physical uncertainty 而 business defer。
8. Chest UNKNOWN exhausted 保留 `current_town_subflow`，交由 REACH_TOWN。
9. Queue-tail UNKNOWN 不會 `_finish_town_subflow_queue()`。
10. 正常 positive Town path behavior-preserving。
11. Chest 原本 claim-success completion timing behavior-preserving。
12. 相關 targeted tests 全綠。
13. full suite 全綠。
14. 無 scheduler / navigation-routing semantic change。
15. 無 shared egress framework。
16. diff 可獨立 rollback。

---

# 18. Follow-up Debt Discovered But Explicitly Deferred

R1 已確認一項值得後續調查的 semantic tension：

```text
Chest:
claim postcondition verified
→ completed_today=True

later:
Town positive evidence still has red dot
→ _defer_subflow()
```

這可能代表：

```text
business completion evidence
vs
post-exit red-dot evidence
```

存在 ownership / truth-source 不一致。

**R1 不處理。**

建立獨立 follow-up analysis，再決定是否屬於 R2/R3 前的 semantic cleanup。

---

# 19. Next Order

R1 完成並實體驗證後：

```text
R1 Town Egress Correctness
↓
IntentRouting Observability
↓
R2 HeroDraw Entry Lifecycle
↓
Evidence Review
↓
R3 Shared Post-Execution Town Handoff
```

R3 不是 R1 的必要條件，也不得在 R1 中提前實作。
