## 目標

依最新 full-suite profiling evidence 繼續降低 deterministic tests 的 wall-clock dependency。

不得依「搜尋所有 sleep/while」機械重構；只處理已有 profiling evidence 的 hotspots。

### Phase A — Navigation Quick Wins

盤點 `NavigationHandler` 中造成 hotspot 的裸 `time.sleep()`。

僅對 **elapsed-duration / animation-settling / debounce** semantics：

```python
time.sleep(x)
```

改為既有：

```python
self._sleep(x)
```

並讓相關 deterministic tests 明確注入 `FakeClock`。

要求：

* Production 使用 `SystemClock` 時 timing behavior 不變。
* 不修改 timeout/cooldown 數值。
* 不改 calendar/persistent wall-time semantics。
* 不新增 test-aware production branch。

完成後執行相關 Navigation tests，記錄該 test cluster before/after time。

---

### Phase B — ResultHandler Tick-Driven Migration

優先處理 profiling 已確認的 Result wall-clock hotspots。

目前至少包含：

```text
INIT_DELAY real sleep
retry post-click real sleep
_run_defeat_giveup_subflow blocking confirm while
```

目標改為顯式 Result phase：

```text
INIT_DELAY
CONTINUE_LOOP
FINAL_MATCH

GIVEUP_READY
WAIT_GIVEUP_CONFIRM
WAIT_GIVEUP_EXIT
```

必要時增加少量具名 phase，但不得建立 generic workflow engine。

核心 invariant：

```text
one tick
→ consume current screen_img
→ at most one logical/action progression
→ return
```

Handler 不得為等待 future evidence：

```text
sleep
capture
while
```

### Giveup Contract

```text
Tick N:
defeat limit reached
→ click giveup
→ WAIT_GIVEUP_CONFIRM
→ return

Tick N+1:
confirm absent + deadline not reached
→ WAIT
→ return

Tick N+x:
confirm visible
→ click confirm
→ WAIT_GIVEUP_EXIT
→ return

later snapshot:
exit evidence verified
→ reset defeat state
→ apply cooldown if required
→ transition
```

Timeout 必須 bounded，且測試用 `FakeClock.advance()` 驗證，不得等待真實 5 秒。

---

### Phase C — Re-profile

Phase A+B 完成 focused tests 後，由使用者執行完整 suite。

比較：

```text
Current baseline:
298.145s

New:
Xs

Delta:
298.145 - X
```

重新產生：

```text
Top real-time gaps
Top slow modules
Remaining real sleep
Remaining blocking capture loops
```

**只有新的 profiling 結果仍顯示 Explore/Treasure 為高 hotspot，才開始 Explore migration。**

不得因為目前已知 Explore 有 legacy while 就直接把整個 ExploreHandler 一次重寫。

---

### Deferred

以下本輪不處理：

* Boss Completion Evidence semantic bug。
* LordBoss failure egress legacy `click_and_wait_until_gone`。
* Redundant test deletion。
* Parallel test runner。
* Process/window real-time waits，除非 profiling 與 test classification 證明它們屬 deterministic unit tests。
