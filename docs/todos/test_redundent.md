RFC: 測試跑太慢且while部分不符合BDI架構

A:

可以，而且我認為**你的測試也應該跟著架構一起演進**。但更精確地說，不是「因為改成 BDI，所以測試不要時間」，而是你的 runtime 正從：

```text
一次 handler call
→ while
→ sleep
→ capture
→ retry
→ 直到完成
```

轉成：

```text
Observation(t)
→ Intent / State
→ Decision
→ Action
→ return

下一 tick：
Observation(t+1)
→ verify postcondition
→ Decision...
```

那測試自然也應該從「**真的等流程跑完**」變成「**逐 tick 餵 observation + 控制 logical time**」。

## 我 survey 你目前 repo 後，最明顯的分界

### 第一類：這些「等待時間」應該消失

最典型就是現在：

`BaseStateHandler.click_and_wait_until_gone()`。

它自己做 `while + time.sleep + capture + matcher + retry`，甚至最後還有 `post_delay`。

而 `test_click_and_wait_until_gone_closed_loop.py` 又反過來保護這個 blocking implementation。這類測試未來應該隨 blocking helper 一起退休，而不是努力把它測得更快。

尤其其中有一個危險模式：

```python
patch(time.sleep)  # 不真的睡

while time.time() - start < 2.5:
    ...
```

`sleep` 被 mock 掉、但真實 clock 還在跑，結果可能變成 **CPU busy-loop 真的轉 2.5 秒**。

這就是你現在「明明 mock sleep 但測試還很慢」的一個很合理來源。

Martin Fowler 也明確建議 asynchronous test 不要用 bare sleep；時間應包在可替換的 clock 後面。([martinfowler.com][1])

---

## 第二類：時間語意一定要測，但絕對不用真的等

你已經有非常好的範例：

`test_behavior_navigation_progress.py`

例如 timeout 是 5 秒，但測試直接：

```text
now = 10
→ action start

now = 16
→ timeout
```

根本不用睡 6 秒。

Battle 更漂亮：

```python
clock.advance(31)
```

直接測「30 秒沒有 HP progress 就 restart」，31 秒可以在幾毫秒內測完。

這些時間語意**不能刪**：

* timeout
* retry deadline
* cooldown
* backoff / defer
* watchdog threshold
* battle duration
* debounce
* N-frame confirmation
* daily reset boundary

但測的是：

> `elapsed_time` 對決策的影響

不是：

> 「電腦真的過了 30 秒沒有？」

---

## 第三類：甚至不是「時間」，而是 observation sequence

你的 Town Precondition 測試已經開始長成我要的樣子。

例如無紅點：

```text
Frame 1:
Town + Building + no red dot
→ 不完成

Frame 2:
Town + Building + no red dot
→ complete
```

以及：

```text
Missing building × 4
→ WAIT

Missing building × 5
→ DEFER
```

它完全不用：

```python
sleep(0.5)
sleep(0.5)
...
```

因為真正的 contract 是 **連續 N 次 observation**，不是經過 N 秒。

這很符合你現在的架構。

---

# 哪些真的可以保留 real-time wait？

非常少。

我目前找到一個合理案例：

`test_long_run_resilience.py` 裡真的開 `PauseController` background thread，然後用：

```python
time.sleep(0.08)
time.sleep(0.1)
time.sleep(0.08)
```

確認實際 thread 在 pause 時會送 heartbeat。

這是在測：

> **真的 thread scheduling / concurrency wiring**

所以 real wait 有價值。

但它不該跟普通 policy/unit test 混為同一級。

Google 的 Test Sizes 也有類似區分：Small tests 不應有 sleep、多執行緒；這些應進到較大的 integration tests。([Google Testing Blog][2])

我會把你的測試概念分成：

| 類型                                       |         Real sleep |
| ---------------------------------------- | -----------------: |
| Policy / Intent decision                 |                  ❌ |
| FSM transition                           |                  ❌ |
| Timeout / cooldown / backoff             |        ❌ FakeClock |
| debounce / N frames                      |     ❌ 餵多個 snapshot |
| Navigation table                         |                  ❌ |
| CV fixture → Scene detection             |                  ❌ |
| actual thread scheduling                 |            ⚠️ 少量允許 |
| real process / Windows / game smoke test | ⚠️ integration 才允許 |

所以理想上 **95%+ 的 automated behavior tests 不需要 wall-clock waiting**。

---

# 你其實已經有「未來測試形狀」

例如 `NavigationIntentPolicy`：

```text
SceneSnapshot
+
ActiveIntent
       ↓
    Policy
       ↓
ActionDecision
```

你的測試已經可以：

```python
scene = SceneSnapshot(...)
intent = ...

decision = policy.resolve(scene, intent)

assert decision.action == ...
```

沒有 capture、沒有 mouse、沒有 sleep。

這應該成為未來最多的測試。

再上一層才測：

```text
tick 1 snapshot
→ CLICK
→ InFlightAction

tick 2 snapshot
→ WAIT

clock.advance(...)

tick 3 snapshot
→ RETRY / DEFER / COMPLETE
```

這種我會稱它是 **scenario / state-transition test**，非常適合你的架構。

---

# 你另一個大問題：測試已經明顯有「歷史堆積」

光從目前 tests inventory，就看到幾個高度可疑 cluster。

例如 Bag 同時有：

```text
test_bag_cleaning_dual_mode_behavior
test_bag_cleaning_modular_functions
test_behavior_bag_cleaning
test_behavior_bag_scenarios
test_behavior_bag_state_machine
test_backpack_full_dynamic_destroyable
```

Dungeon 更誇張：

```text
test_behavior_dungeon_cards
test_behavior_dungeon_scenarios
test_behavior_dungeon_state_machine
test_dungeon_runtime_context
test_dungeon_swipe_unit
test_dungeon_relaunch_recovery
test_behavior_dungeon7_integration
...
```

Navigation 也有：

```text
test_behavior_navigation
test_behavior_navigation_scenarios
test_behavior_navigation_intent
test_behavior_navigation_progress
test_behavior_navigation_table
test_town_subflow_precondition_navigation
...
```

**我不能只看名字就說它們 redundant**，但這個結構很像多年增量修 bug 後，每次新增測試檔卻沒有 retire 舊 tests。

---

# 那到底怎麼知道 test 是不是 redundant？

不要用：

> 「兩個 test 都 cover 同一行 code，所以刪一個。」

這是不可靠的。

Google 特別提醒：兩個 test 即使 code coverage 完全相同，也可能測不同 edge case，其中一個仍能抓到另一個抓不到的 bug。([Google Testing Blog][3])

你應該建立：

### `Behavior / Invariant × Test` matrix

例如：

| Contract                          | Policy test | FSM test | Integration |
| --------------------------------- | ----------- | -------- | ----------- |
| Diamond > Bread precedence        | ✅           |          |             |
| Pending intent 不因 scene 消失        | ✅           | ✅ wiring |             |
| click 後需新 frame 驗證                | ✅           |          |             |
| 5 次 entry missing → defer         | ✅           |          |             |
| Battle safe-point ownership       | ✅           | ✅        |             |
| real pause thread emits heartbeat |             |          | ✅           |

然後問每一個 test：

> **如果刪掉它，我失去哪一個獨特的 failure detection？**

如果答案是：

> 沒有，它跟另一個 test 在相同 abstraction level、相同 input partition、相同 assertions、保護同一 invariant。

才是真的 redundancy。

---

# 我建議你用三種證據判斷 redundant

第一個是 **Behavior Matrix**，這是最重要的。每個 canonical contract 至少要知道誰在 guard 它。

第二個是 **coverage**，但只當輔助工具。它可以找「沒測到」，不能可靠證明「測試重複」。Google 也建議不要為了 coverage 數字 copy/paste tests。([Google Testing Blog][4])

第三個是最強的：**Mutation Testing**。

它會故意把：

```python
if confidence > threshold:
```

變成：

```python
if confidence <= threshold:
```

看看哪個 test 會紅。

如果：

```text
Test A kills mutant #1 #2 #3
Test B kills mutant #1 #2 #3
```

而 B 沒有任何自己的 contract / edge case，

B 就非常像 redundant。

如果：

```text
A kills #1 #2
B kills #3
```

那即使 coverage 一模一樣，B 也有價值。

Google 本身大量使用 mutation testing 來評估 test effectiveness。([Google Testing Blog][5])

---

# 甚至可以「測試你的測試」

這個概念你應該會喜歡。

Google 很早就給過一個實用方法：

> 要 refactor tests 時，**故意先把 production behavior 改錯**，確認相關 tests 真的紅；然後再整理 tests。([Google Testing Blog][6])

例如 Contract：

```text
UNKNOWN 絕不能猜 route
```

故意暫時把：

```python
UNKNOWN → RETURN_TOWN
```

打開。

你期待：

```text
哪幾個 test 應該紅？
```

如果 12 個都紅：

→ 很可能太重複。

如果一個都沒紅：

→ test gap。

如果 1–3 個精準紅：

→ 通常很健康。

做完一定 revert production mutation。

---

# 我目前最先整理的順序

我不建議「一次清全部 tests」。

應該跟 production migration 綁在一起：

1. **先量測 test runtime baseline**，找到真正最慢的 test files / methods。
2. 搜尋測試與 production 的 `sleep / wait / while / time.time / monotonic / Thread`，分成 `logical time`、`real concurrency`、`legacy blocking`。
3. 第一批優先處理 `click_and_wait_until_gone` 這種 production blocking primitive；它的 implementation-coupled tests 隨之退休，改成 `InFlightAction + next snapshot` 的 behavior tests。你目前 `AGENTS.md` 本來也要求「測 public behavior，不綁 private implementation」。
4. 每整理一個 domain，例如 `navigation`，做一張 **Contract → Tests mapping**，合併真正重複的 scenario/unit tests。
5. 保留少量 broad integration tests，其他盡量下沉成 pure policy / state-transition tests。
6. 最後針對這個 domain 跑 coverage + targeted mutation testing，再決定哪些 legacy tests 可以安全刪掉。

這裡還有一個具體的小 smell：`test_behavior_navigation_table.py` 目前有：

```python
self.assertEqual(len(V1_NAVIGATION_EDGES), 13)
```

如果「**恰好 13 條**」不是你的業務 contract，這就是 implementation-coupled assertion。未來合法增加 edge 反而會讓測試紅。應該保護的是「必要 routes 存在、非法 routes 不存在、precedence 正確」，而不是現在剛好有幾筆。

---

## 最後濃縮成你的新測試原則

我會建議你之後把測試架構收斂成一句：

> **測時間語意，不等待時間；測 observation → decision → transition，不等待 Handler 自己跑完整個世界。**

也就是：

```text
Real time       → FakeClock
UI waiting      → next SceneSnapshot
debounce        → repeated observations
timeout         → clock.advance()
async ownership → InFlightAction / state
whole flow      → sequence of ticks
actual OS/thread timing
                → 少量 integration test
```

這會同時讓你的 production 架構更 BDI/event-loop 化、測試更快，而且更不容易因 refactor 就整批爆掉。

我目前已經能指出第一批高風險區，但**還沒逐一讀完你 80+ 個 test files，所以現在不會直接叫你刪哪些檔案**。下一步最合理的是做一輪完整的 **Test Suite Audit**：輸出每個 test file 的「runtime risk / real sleep / fake clock / implementation coupling / overlap domain / 保留或合併候選」，再依證據開始刪。

[1]: https://martinfowler.com/articles/nonDeterminism.html "https://martinfowler.com/articles/nonDeterminism.html"
[2]: https://testing.googleblog.com/2010/12/test-sizes.html "https://testing.googleblog.com/2010/12/test-sizes.html"
[3]: https://testing.googleblog.com/2008/03/tott-understanding-your-coverage-data.html "https://testing.googleblog.com/2008/03/tott-understanding-your-coverage-data.html"
[4]: https://testing.googleblog.com/2020/08/code-coverage-best-practices.html "https://testing.googleblog.com/2020/08/code-coverage-best-practices.html"
[5]: https://testing.googleblog.com/2021/04/mutation-testing.html?hl=lv "https://testing.googleblog.com/2021/04/mutation-testing.html?hl=lv"
[6]: https://testing.googleblog.com/2007/04/tott-refactoring-tests-in-red.html "https://testing.googleblog.com/2007/04/tott-refactoring-tests-in-red.html"
