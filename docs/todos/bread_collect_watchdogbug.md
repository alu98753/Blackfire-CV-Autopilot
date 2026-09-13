我審過目前 main 的實際 BreadCollectionHandler 與 GenericAntiStuckSubflow。我的結論是：
```
經真人觀察後 我認為問題出在 不管事要去Lobby中的stage ,domains dungeon等場警還是 單純到lobby領麵包 他都是用統一的方案: 進去就先比對12張圖片 這才是導致30s watchdog的問題 重新審視你認為可以怎麼做

具體而言 我認為這兩者都不需要比對12張圖片

前者只需要比對
gobacktown 與 bread

後者只需要比對
gobacktown,與要去的那個地點 的before即可(雖然她有可能是after但是 依然可以有85%以上的逼配threshold來觸發) 這樣就可以正確定位
```


根因方向大致正確，但最後提出的修復方案我不建議直接採用。
尤其不要直接塞 click_and_wait_until_gone()。

我給這份計畫：7/10

最正確的觀察是：

bread_click_attempted 現在只被當成「曾經點過」，卻沒有改變後續的 action policy。

目前程式確實是：

if pos_coll:
    self.mouse.click(...)
    self.machine.bread_click_attempted = True
    time.sleep(0.03)
    return

下一個 tick 如果 bread_collection.png 還存在，就會再次走完全相同的 branch，再 click 一次。bread_click_attempted=True 並沒有阻止它。



所以真正的 bug 可以更準確描述成：

Bread collect action 缺少 committed/in-flight phase。Action 發出後，Handler 仍把舊畫面上的 actionable evidence 當成新的 action invitation。

這其實正好就是你前面 Greenfield contract 在解的問題：

看到按鈕
→ click
→ action committed
→ 等下一幀 postcondition
→ 成功 / timeout / retry

而現在 Bread 是：

看到按鈕
→ click
→ 下一幀還看到
→ click
→ 還看到
→ click
→ ...

但分析裡有兩個地方講得太滿

第一個是：

「Sandbox 的 Win32 PostMessage 跨沙盒發送延遲」

目前你提供的 log 並不能證明這是根因。



我們只能證明：

click 已發出
bread_collection template 持續存在
confirm 尚未被 Handler 成功辨識

原因可能是：



input delivery latency

game/server response latency

animation

sandbox rendering

click 根本沒有成功送到

confirm 尚未出現



所以我會把 root cause 寫成：

環境存在較長的 action→UI-transition latency，而 Handler 不容忍這個 latency。

不要把 PostMessage 定死，除非之後有 input instrumentation 證明。



第二個更重要。



它說 Watchdog：

先用 exceptions/cancel.png 0.7584 命中 GenericAntiStuck。

但目前 main 的 GenericAntiStuckSubflow.can_handle() threshold 是 0.80。



你貼的 log：

exceptions/cancel.png 相似度 0.7584
→ 命中 generic_anti_stuck_subflow

和目前這份程式碼對不上。



這可能代表：



那次執行不是目前 main

Watchdog discovery 還有另一條 matcher path

當時 threshold 不同

log 的「命中原因」不是 can_handle() 這段



所以「Watchdog 是靠 cancel 0.7584 選中 generic subflow」這個結論目前不能當成確定事實。



反而後面的：

common/confirm.png = 1.0000
→ GenericAntiStuck 點 confirm

這部分證據很強。

我不同意 click_and_wait_until_gone

這是這份計畫最大的問題。



你現在正在把架構往：

one action per tick → future frame validates postcondition

遷移。



而 click_and_wait_until_gone() 本質是：

click
while timeout:
    capture
    match
    sleep
    maybe click again

它會：



blocking Handler

自己 capture 新 frame

自己 retry

bypass Agent tick

bypass snapshot ownership

再造一套 progress/retry lifecycle



這正是你現在想慢慢清掉的 legacy pattern。



你自己的 precondition inventory 已經明確承認：

legacy Handler 的 click_and_wait_until_gone / blocking verification 尚未全面遷移，是已知缺口。

所以不要為了解這次 bug，再新增一個。

我建議的修法

不用搞很大。



Bread handler 加一個極小型 phase：

READY_TO_COLLECT
       │
       │ click once
       ▼
WAIT_COLLECT_RESULT
       │
       ├─ confirm / ok 出現 → click confirm
       │
       ├─ collect 消失 → 視 domain evidence 決定
       │
       ├─ timeout → retry
       │
       └─ retry exhausted → defer/recovery

最關鍵的不變量只有一句：

一旦 bread_collection click 已 committed，在 timeout 前，即使 collect button 仍可見，也禁止再次 click。

例如概念上：

if phase == READY:
    if pos_coll:
        click()
        phase = WAIT_RESULT
        issued_at = now
        return

if phase == WAIT_RESULT:
    if confirm:
        click_confirm()
        ...
        return

    if now - issued_at < timeout:
        return

    # timeout
    retry_count += 1
    phase = READY

注意：



不是固定 sleep 1.5 秒。



因為 1.5 秒只是猜測 latency：

今天 sandbox 1.2s → 過
明天 1.8s → 又壞

應該是：

bounded wait + evidence + bounded retry

還有一個順便值得修的小語意問題

現在：

confirm
→ bread_collected_this_run = True

以及：

ok
→ bread_collected_this_run = True

但原本註解自己寫：

「獲得體力確認 或體力已滿提示確認」

也就是：



看到 confirm/OK 不一定等價於「成功領到體力」。



現在卻一律：

bread_collected_this_run = True

這是 completion evidence 有點過強。



這次不一定非得一起改，但我會要求測試至少把：

success
cooldown/already claimed
full stamina
delayed confirm
click ignored

分開，不要讓「confirm 存在」直接等價於 domain success。

我會怎麼改這份修復計畫

我會批准這個版本：



不要改 Watchdog。 Watchdog 是最後一道 recovery，不應成為正常 Bread 流程的一部分。

Bread collect 第一次 click 後進入 WAIT_RESULT / in-flight。

WAIT 期間禁止因 bread_collection.png 仍存在而重新 click。

每 tick 照正常 Agent loop 重新觀察：

confirm/ok → 處理結果；

collect 消失 / quit 狀態改變 → 判定 progress；

尚無變化 → 繼續等待。

設定 bounded timeout，例如 2–3 秒；timeout 後才允許 一次 retry。

retry 有上限；超限走既有 defer_collection() / recovery，而不是無限點。

加 regression test：
collect 按鈕連續存在 N frames 時，mouse.click 只能發生一次，直到 timeout。



其中第 7 點是這個 bug 最重要的測試。



所以我會對 coder 說：

根因分析接受，但不要採用 click_and_wait_until_gone() 或單純 1.5 秒 cooldown。請改成非 blocking、bounded、postcondition-driven 的 collect in-flight phase；同一 committed collect action 在 timeout 前最多只能 click 一次。

這會比原計畫更符合你現在整個 Blackfire 的架構方向，也真正解掉 24/7 latency sensitivity，而不是把 sandbox 的延遲數字硬編進去。