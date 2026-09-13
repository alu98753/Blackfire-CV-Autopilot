# 測試執行效率優化與 Blocking Control Flow 收斂

## 1. 目標

本工作的第一優先目標是：

> **在不降低 regression protection、不刪除有效 behavior coverage 的前提下，顯著降低完整測試套件的 wall-clock execution time。**

第二優先目標是：

> 對經 profiling 證實造成測試延遲、且違反 Greenfield-lite 單次 tick 契約的 legacy blocking flow，逐步遷移為 tick-driven / state-driven execution。

Greenfield-lite 的 canonical runtime contract 已明確定義：

```text
Capture once per tick
→ SceneSnapshot
→ ActiveIntent
→ ActionDecision
→ InFlightAction
→ return

next snapshot
→ verify postcondition
→ timeout / retry / defer / recovery
```

因此 Handler 不應為等待未來 UI evidence 而自行 capture 多幀並佔住 control flow。

---

## 2. 成功標準

Baseline：

```text
Full suite: 380s+
```

第一階段 Required Target：

```text
After <= Baseline × 0.50
```

若 baseline 為 380s：

```text
<= 190s
```

Stretch Goal：

```text
<= 120s
```

若未達目標：

* 不得為達數字而刪測試。
* 必須重新輸出 remaining hotspot ranking。
* 下一輪仍由 profiling evidence 決定工作優先序。

---

# Phase 0 — Baseline 與 Hotspot Inventory

任何 production refactor 前先取得證據。

記錄：

```text
Full-suite total time
Slowest test files
Slowest test methods
OCR initialization overhead
Real sleep
Real-clock timeout
Busy-spin
Thread/process integration
CV/OCR computation
Filesystem/setup overhead
```

每個 hotspot 分類：

```text
A. OCR/model initialization
B. real sleep
C. real-clock busy-loop
D. blocking production polling
E. real thread/process integration
F. CV/image computation
G. fixture/setup overhead
```

不得根據：

* test file 大小
* test 數量
* 檔名相似

直接推論效能根因或 redundancy。

---

# Phase 1 — Quick-Win Test Runtime Decoupling

## 1.1 OCR Preload 必須 Explicit Opt-In

目前：

```python
GameStateMachine(..., preload_ocr=True)
```

constructor 會啟動 EasyOCR background preload。

修改為：

```python
GameStateMachine(..., preload_ocr=False)
```

production composition root：

```python
GameStateMachine(
    ...,
    preload_ocr=True,
)
```

### 必要前置條件

修改 default 前必須 audit 所有 production `GameStateMachine(...)` construction sites。

確認：

* 真正 runtime entry 顯式 `preload_ocr=True`
* tool / script 若需要 preload 也顯式指定
* unit/behavior tests 預設不 preload
* OCR preload 專用測試仍明確測試 preload behavior

### 風險描述

這不是：

```text
Zero Behavioral Risk
```

而是：

```text
Constructor contract change
+
Production composition explicit wiring
→ application observable behavior preserved
```

不得把 constructor default change 描述為零風險。

---

## 1.2 Time Semantics 分類

不得機械地把全專案：

```python
time.time()
```

全部替換成：

```python
machine.clock.monotonic()
```

時間必須區分兩種語意。

### Elapsed / Duration Time

例如：

* timeout
* retry interval
* watchdog duration
* debounce
* animation settling
* battle duration

應使用：

```text
ClockPort.monotonic()
```

### Calendar / Persistent Wall Time

例如：

* 每日重置日期
* 08:00 scheduled restart
* persistence 跨 process restart 的 absolute timestamp

仍使用 wall-clock / datetime。

---

## 1.3 Busy-Loop 根除

禁止：

```python
start = time.time()

while time.time() - start < timeout:
    time.sleep(...)
```

搭配：

```python
patch("time.sleep", return_value=None)
```

形成：

```text
sleep = instant
clock = real
→ CPU busy-spin 到真實 timeout
```

已知：

`test_click_and_wait_until_gone_triggers_reclick_if_not_disappeared`

不得再真的等待約 2.5 秒。

---

## 1.4 FakeClock 使用規則

既有：

```python
ClockPort.monotonic()
SystemClock
```

應直接沿用，不建立另一個 TimeManager。

但是：

> **只把 blocking loop 的 `time.time()` 換成 FakeClock 並不足以完成此工作。**

若 blocking legacy helper 暫時保留，必須採以下其中一種策略：

### Preferred

直接在 Phase 2 將該 hotspot 轉成 tick-driven state。

### Transitional only

若短期必須保留 blocking helper，其 waiting mechanism 必須同樣可控制，例如：

```text
Clock.monotonic()
+
可 deterministic advance 的 wait/sleep seam
```

不得出現：

```text
FakeClock 永遠停在 now=0
+
while elapsed < timeout
```

造成測試無限迴圈。

不得為了這個 transitional case 建立大型新 time framework。

---

# Phase 2 — Performance-Driven Blocking Migration

本 Phase 不採：

> 「搜尋所有 while 然後全部消滅」

而採：

> **只有 profiling hotspot + architecture violation 同時成立者優先遷移。**

---

## 2.1 `click_and_wait_until_gone`

目前有兩份 legacy implementation：

```text
BaseStateHandler.click_and_wait_until_gone
GameStateMachine.click_and_wait_until_gone
```

兩者皆執行：

```text
click
→ while
→ sleep
→ capture
→ match
→ optional reclick
→ timeout
```

### 不做

不要先：

```text
兩份 blocking implementation
→ DRY 成一份漂亮 blocking implementation
→ 再淘汰
```

這會產生無效 churn。

### 要做

先建立 consumer inventory：

```text
caller
behavior contract
timeout
retry semantics
postcondition
current tests
runtime contribution
```

然後依 hotspot 逐個遷移。

Desired behavior：

```text
Tick N
target visible
→ CLICK
→ create pending phase / InFlightAction
→ return

Tick N+1
target still visible
→ WAIT
→ return

retry deadline reached
→ bounded RETRY
→ return

next snapshot target gone
→ COMPLETE
→ phase advance

attempt/timeout exhausted
→ DEFER / RECOVERY
```

所有 postcondition 必須由新 snapshot 驗證。

---

## 2.2 第一批 Migration Candidates

已確認高優先候選：

### A. `click_and_wait_until_gone`

原因：

* production blocking
* test busy-loop
* duplicate implementation
* implementation-coupled tests 已存在

### B. `LordBossHandler`

目前至少存在兩段重複：

```text
click Start
→ while 2.5s
→ capture
→ battle feature detection
```

應收斂為 phase，例如：

```text
READY_TO_START
→ START_CLICKED
→ VERIFY_BATTLE_ENTRY
→ BATTLE / FAILED_ENTRY
```

每 tick 一次 evidence evaluation。

### C. `ResultHandler`

目前：

```text
giveup click
→ while 5s
→ capture confirm
→ click confirm
```

應改成 existing Result phase progression。

---

## 2.3 ExploreHandler

Explore 不直接整檔納入本 branch。

先量測：

```text
_run_treasure_subflow
_wait_for_treasure_terminal
_handle_bless_subflow
_handle_relic_subflow
```

對完整 suite 的實際 contribution。

只有：

```text
measured hotspot
AND
blocking architecture violation
AND
migration boundary 可控
```

才進本次 scope。

否則建立 follow-up migration item。

---

# Phase 3 — Test Contract Convergence

Phase 3 與 test speed 有關，但**不得靠刪 tests 當第一優化手段**。

---

## 3.1 Implementation-Coupled Tests

例如：

```python
handler.click_and_wait_until_gone.assert_called_once()
```

測到的是：

```text
implementation mechanism
```

而不是：

```text
observable behavior
```

若 helper 被淘汰，測試應改為：

```text
Given target visible
When tick
Then exactly one click emitted

Given target still visible before retry deadline
Then no premature completion

Given retry deadline reached
Then bounded retry occurs

Given next snapshot target disappeared
Then workflow progresses

Given max attempts / timeout exceeded
Then recovery/defer occurs
```

---

## 3.2 Redundant Test 判定

不得因：

```text
Bag 有六個 test files
Dungeon 有七個 test files
```

就直接刪除。

先建立：

```text
Behavior / Invariant × Test Matrix
```

每個 test 必須回答：

> 如果刪掉我，會失去哪一種獨特 failure detection？

只有當兩個 tests：

```text
same invariant
same abstraction level
same input partition
same observable assertions
same failure detection
```

才列為真正 consolidation candidate。

---

## 3.3 Mutation Testing

Mutation testing 是：

```text
輔助 redundancy / effectiveness 判定工具
```

不是本 branch Required Dependency。

不得為了這次 test-speed branch 大規模導入 mutation framework。

優先順序：

```text
Behavior Matrix
→ targeted behavior mutation / manual mutation
→ coverage
→ 必要時再導入 mutation tooling
```

正式 mutation infrastructure 可另開 branch。

---

# Test Classification Invariant

## Deterministic tests

包括：

* policy
* FSM
* timeout
* retry
* cooldown
* debounce
* N-frame confirmation
* scenario transition

原則：

```text
Real sleep = forbidden
Real timeout = forbidden
```

使用：

```text
FakeClock
explicit timestamps
observation sequence
SceneSnapshot sequence
```

---

## Integration / concurrency tests

只有測試目標本身是：

* real thread scheduling
* process lifecycle
* OS integration
* game/window integration

才允許 bounded real wait。

例如 PauseController live-thread heartbeat test 可保留少量 real sleep。

---

# Logging Invariant

不得在 high-frequency WAIT/polling path 每 iteration 輸出 INFO log。

應只記錄有意義的事件：

```text
action committed
retry issued
state/phase changed
completed
timed out
recovery triggered
```

因此 busy-loop 修復後，也應消除目前單一 timeout case 產生數千行重複 log 的可能性。

---

# Behavioral Safety Invariants

任何 test-speed optimization 不得：

* 修改 production timeout 只是為了讓 tests 快。
* 降低 retry / postcondition verification。
* 加入 `if TESTING`。
* 判斷 `MagicMock` 後走特殊 production path。
* 省略原本有效的 failure path。
* 把 integration behavior 改成完全 mock 後仍宣稱等價。
* 用 parallel execution 掩蓋 deterministic tests 的 real-time coupling。

---

# Validation

Implementation 中：

```text
AI 只跑直接相關 test method/class/file。
```

完成 focused verification 後，由使用者執行完整 suite。

記錄：

```text
BEFORE
Tests:
Pass:
Fail:
Wall time:
Top hotspots:

AFTER
Tests:
Pass:
Fail:
Wall time:
Top hotspots:

Speedup:
Baseline / After
```

除了 PASS/FAIL 外，wall-clock speedup 是本 branch 的主要 acceptance evidence。

---

# Deliverables

最終必須有：

1. Before slow-test inventory。
2. OCR construction audit。
3. Deterministic-time strategy。
4. Busy-loop elimination。
5. 第一批 measured blocking hotspots migration。
6. Behavior-equivalent regression tests。
7. Before/After wall-time report。
8. Remaining hotspot ranking。
9. Suspected redundant test matrix；只有證據充分者才刪除。

---

# Long-Term Invariants

> **業務 timeout 可以是 30 秒，但 deterministic test 不應因此跑 30 秒。**

> **測時間語意，不等待時間。**

> **測 observation → decision → transition，不等待 Handler 自己跑完整個世界。**

> **Handler 發出 action 後應歸還控制權，由下一個 snapshot 驗證 postcondition。**

> **Test speedup 來自 deterministic architecture，而不是降低 regression protection。**
