我重新依照目前 branch `53a98cb` 的實際 production code 審了一遍。結論要改：

## Verdict：**CHANGES REQUIRED**

更精確地說：

> **Slice 4 的 Login / WORLD_READY boundary 本身大致成立；但整個 Town Building Egress Normalization 工作還不能宣告 COMPLETE。真正沒收乾淨的是 Slice 3。**

而且我會**修正我前面對 Slice 3 的 approve**：現在看到完整 handler lifecycle 後，Slice 3 的實作其實只覆蓋了一個簡化版 Chest case，沒有完整覆蓋 Spec 所描述的 Failure A。

### 核心問題：agent 審錯層了

他的判斷主要是：

> `_ensure_in_town` 在 queue-driven mode 都被 guard 掉，所以 handler 不會搶 shared REACH_TOWN。

這句本身大致沒錯，但它不是 Failure A 的核心。

真正的 Failure A 發生在：

```text
shared REACH_TOWN 已經成功
→ handler 被 dispatch / committed
→ current_state == handler state
→ shared precondition 主動退讓
→ handler 自己持有 physical ownership
→ 此時才誤入別的建築
```

而 `_committed_workflow_owns_frame()` 正是故意讓 committed handler 擁有畫面，因此 shared controller 此時不會幫忙。

所以真正要問的是：

> **每一個 committed Town handler，在發現「我已經不在自己的合法畫面」時，有沒有 relinquish？**

答案目前是：**沒有。**

---

## 我找到的實際反例

| Handler             | 誤入其他建築後目前會怎樣                                                                                | 判定                           |
| ------------------- | ------------------------------------------------------------------------------------------- | ---------------------------- |
| **Chest**           | relinquish 只在 `INIT`；如果是「自己點入口時點偏」造成誤入，此時 phase 已經變成 `CLICK_FREE_CHEST`，guard 根本不跑          | 🔴 Blocker                   |
| **HeroDraw**        | 只看到通用 `exitfromhouse` 就認定「已在酒館內」                                                            | 🔴 Blocker                   |
| **BloodAltar**      | 只看到通用 `exitfromhouse` 就認定「已在血祭壇內」                                                           | 🔴 Blocker                   |
| **BagTidy**         | 錯誤房間中找不到 Town/Bag，20 秒後直接 `pop_and_next_town_subflow()`                                     | 🔴 Blocker                   |
| **BulletinBoard**   | foreign building 沒自己的 board evidence，也沒有 relinquish path，可能一直持有 owner 到 watchdog 介入         | 🟠 Blocking architecture gap |
| **JewelryWorkshop** | foreign building 無 sell evidence / Town door 時沒有 relinquish，仍由 Jewelry handler 持有 ownership | 🟠 Blocking architecture gap |

### 其中 Chest 是最關鍵的新發現

目前測試是這樣開始：

```text
STATE_CHEST
step_phase = INIT
畫面一開始就已經是別棟建築
```

然後 `exitfromhouse` 連續兩幀 → relinquish。

但 Spec 原本描述的 Failure A 是：

```text
Chest 在 Town
→ 找到 Chest 建築
→ 點擊入口
→ 點偏，實際進了 Blood Altar
```

真實 production 中 Chest 點擊入口後立刻：

```text
step_phase = CLICK_FREE_CHEST
```

所以「下一幀已經在錯誤建築」時，Slice 3 加在 `_handle_init()` 的 relinquish guard **根本不會執行**。

接著它會：

```text
CLICK_FREE_CHEST
→ 找不到 chest dialog ×5
→ WAITING_QUIT
→ 看見通用 exitfromhouse
→ 離開那棟錯誤建築
→ VERIFY_EXIT
→ Chest 紅點還在
→ defer Chest / pop
```

也就是：

> **我們原本想修掉的 Failure A，在最真實的「入口點偏」路徑上其實仍然存在。**

這個是 blocker。

---

### HeroDraw 更明顯

它現在 INIT 裡：

```python
if pos_free_check or pos_rec_check or pos_exit_check:
    self.step_phase = "ENTERED_TAVERN"
```

其中：

```text
pos_exit_check = exitfromhouse_and_to_town.png
```

問題是 `exitfromhouse` 不是「酒館特徵」。

它只能證明：

> 「你在某棟實體建築裡。」

不能證明：

> 「你在 Tavern。」

所以：

```text
HeroDraw
→ 誤入 Blood Altar
→ 看見通用 exit
→ 認定自己已進 Tavern
→ 找不到 recruitment
→ 最後退出
→ Tavern 紅點仍在
→ defer HeroDraw + pop
```

而 VERIFY_EXIT 確實有「紅點仍在就 defer」的行為。

這正是：

```text
physical mislocation
→ business punishment
```

直接違反 Invariant 2。

---

### BloodAltar 有同樣問題，而且可能更危險

它也把：

```python
pos_exit_check
```

當作「已在 Blood Altar 內」的正向證據。

如果實際是其他 building：

```text
通用 exit 可見
→ ENTERED_BUILDING
→ 找不到 receive_entry
→ SACRIFICE_MENU_OPEN
→ 找不到 blood ×3
→ 判定「全數獻祭完成」
→ ALL_DONE_EXITING
```

之後回 Town 再依 Blood Altar 紅點決定 defer / complete。

所以它不只是卡住：

> **它可能因為 physical mislocation 而推進 business phase。**

這是明確 correctness bug。

---

### BagTidy 也不是安全的

BagTidy 在錯誤建築裡：

```text
沒有 Town door
沒有 Backpack UI
→ INIT 無法前進
```

20 秒後 timeout branch：

```python
self.reset_state()
self.machine.pop_and_next_town_subflow()
```

所以它會直接把 BagTidy intent 消耗掉。

也是：

```text
physical location error
→ business intent consumed
```

---

### BulletinBoard / Jewelry 雖然沒直接 defer，也不能算安全

BulletinBoard queue mode 的 `_ensure_in_town()` 確實會被跳過，這部分 agent 說對了。

但它在 foreign physical building 裡：

```text
不是 BOARD_CONFIRMED
不是 Town door
不是自己的 building
→ 沒有 relinquish
```

`_step_init()` 沒有處理 `exitfromhouse` foreign-room evidence。

Jewelry 也是：

```text
queue mode → skip _ensure_in_town
foreign building
→ 沒 sell_out
→ 沒 Town door
→ 沒 own shop evidence
→ 沒 relinquish
```

它們可能最後被 Watchdog 救，但：

> **Watchdog 是最後安全網，不應取代 committed-handler relinquishment protocol。**

---

## 所以 agent 的 5 個回答，我會這樣改判

`1. Login → Chest 先經 shared REACH_TOWN`：**✅ 基本正確。**

`2. Dungeon login 不強制 Town`：**✅ 基本正確。**

`3. 所有 Registry consumer 都經 shared precondition`：**✅ 只在「dispatch 前」正確。**

這句不能推出：

> dispatch 後 mislocation 也安全。

另外它說「動態未知 flow 也靠 `spec_for` fallback REACH_TOWN」其實不準。`spec_for()` 的確有 REACH_TOWN default， 但 `_select_next_town_subflow()` 對 **不在 `TOWN_SUBFLOW_SPECS` 的 key 會直接 `dispatch_current_town_subflow()`**，根本不走 shared precondition。

目前若沒有實際 unknown Town flow，這點可以 non-blocking，但 audit 的說法不正確。

`4. 沒有 handler-local navigation 能繞過 relinquishment`：**❌ 錯，而且是本輪最重要的錯誤。**

問題不是 `_ensure_in_town` 偷點回城，而是：

```text
committed handler
→ 不認得自己已經在錯誤場景
→ 繼續 business FSM / defer / pop
```

`5. 不需要 production change`：**❌ 我不同意。**

---

# 架構上真正該怎麼修

我不建議把 Chest 現在那 30 行 `mislocation_count` 原封不動複製到 5 個 handler。

真正應該固定的是這個語意：

```text
Generic topology evidence:
EXIT_BUILDING_TO_TOWN
= 「我在某棟 building」

≠
「我在自己的 building」
```

Handler 要有自己的 **positive ownership evidence**：

```text
Chest          → chest dialog / chest-specific UI
HeroDraw       → recruitment / recruited UI
BloodAltar     → receive / sacrifice UI
Jewelry        → sell_out / sell UI
BulletinBoard  → BOARD_CONFIRMED
BagTidy        → Town / backpack UI
```

然後：

```text
own evidence visible
→ retain ownership

own evidence absent
+ clear foreign physical evidence
+ bounded consecutive confirmation
→ relinquish_subflow_to_navigation()
→ preserve current_town_subflow
→ shared REACH_TOWN
```

這個才符合 Greenfield-lite 的：

> 點擊不等於成功；必須用後續畫面驗證 postcondition。

尤其像 Chest，我甚至會優先考慮：

```text
INIT
→ click chest building
→ VERIFY_ENTRY
→ 看見 chest-specific evidence
→ 才進 CLICK_FREE_CHEST
```

而不是：

```text
click building
→ 直接假設已成功進 Chest
→ CLICK_FREE_CHEST
```

這會比在後面每個 business phase 補洞乾淨很多。

---

## Scope 判定

這些不是新 Slice 4 設計。

**它們是 Slice 3 沒完整落地，現在被 Slice 4 completion audit 揪出來。**

現有 Spec 已經明寫：

> `ChestHandler 等實體 Handler` 要導入 Relinquish guard。

所以：

> **不用開新 Spec。不要改架構。直接 reopen Slice 3 做 completion patch。**

兩個新 test commits：

```text
a01d9b0
53a98cb
```

我仍然認為 **可以保留**。它們測的 Login / recovery lifecycle 沒問題。

但是 feature 的狀態應改成：

```text
Slice 1 ✅
Slice 2 ✅
Slice 3 ❌ REOPEN — committed-handler coverage incomplete
Slice 4 ✅ Login boundary tests / integration largely done
Overall feature ❌ NOT COMPLETE
```

下一個 coding-agent 任務應該不是「繼續 Slice 4」，而是：

> **補完 Slice 3 的真實 committed-handler mislocation contract，尤其先補一條「Chest 從 Town 點入口 → phase 已前進 → 實際落入 foreign building」的 regression。**

這條如果現在跑，我高度預期會直接把現有缺口測紅。
