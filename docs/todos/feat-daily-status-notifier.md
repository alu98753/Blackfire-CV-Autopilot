我重新看了你目前的 `main`。我認為你的想法方向對，但**真正需求不是「每日任務完成時通知我」**，而是：

> **早上我不打開遠端、不看遊戲，也能相信腳本自己處理；只有真的需要我介入時才打擾我。**

這個差異很重要。因為如果只有「完成通知」，到了 10:30 還沒收到，你還是會想：「是不是當機了？」最後照樣打開遠端。

### 你現在 repo 已經很接近能做到

你已經有兩個很好的資訊來源：

* `DailyManager` 有每日週期與各 subflow 的 `completed_today` 持久化狀態，而且現在是 **08:05 reset cycle**。
* `runtime/supervisor.py` 已經是 **process-external watchdog**，會看 heartbeat、偵測 child crash/stall、重啟 bot。

所以**不要另外打造一套監控系統**。

我建議 MVP 只有兩種手機訊息：

```text
✅ SAFE_TO_IGNORE
今天早上的自動流程正常，目前不需要你處理。

⚠️ NEEDS_ATTENTION
自動恢復持續失敗，需要人工查看。
```

平常 `RUNNING` 完全不通知。

---

### 不要直接用「進 Tier 4 = Daily 全完成」

你現在架構裡 Tier 4 的語意是：

> 目前週期活動「暫無可執行項目」就可以去長駐 stage/domain，而且 Lord Boss cooldown 到期後仍可能再次搶佔。

所以：

```text
進 Tier4
≠
今天所有事情永久完成
```

這是你在寫 spec 前最需要先定義清楚的地方。

我會把你的需求定義成：

> **「目前 autonomous system 已經穩定運作，而且沒有任何需要人工介入的事情。」**

而不是硬說：

> 「每日任務全部完成。」

這更符合你真正想解決的「不要去看遊戲」。

---

### 最小實作

架構可以非常小：

```text
Daily scheduler ──→ SAFE_TO_IGNORE event ─┐
                                         ├→ NotificationPort
Supervisor ───────→ NEEDS_ATTENTION event ┘
                                               ↓
                                      Discord Webhook
                                               ↓
                                             iPhone
```

**不要**在 `state_machine.py` 裡直接 `requests.post(discord...)`。

Domain 只產生事件：

```text
SAFE_TO_IGNORE
NEEDS_ATTENTION
```

Discord 只是 adapter。以後要換 LINE 不動 scheduler。

---

### 通知工具我會先選 Discord Webhook

因為 Discord 原生 webhook 就是為「外部程式把自動訊息丟進 Discord channel」設計的，MVP 不需要真的寫 Discord Bot。([Discord 支援][1])

LINE 以前最方便的 LINE Notify 已在 **2025/3/31 結束服務**；現在若走 LINE 要用 Messaging API，設定比 Discord webhook 多。([LINE Notify][2])

所以第一版：

```text
Discord Webhook
outbound only
不做遠端指令
不做 dashboard
不做進度 spam
```

Webhook URL 放環境變數，不 commit。

---

### 我會把這個 feature 定義成

```text
feat/daily-status-notifier
```

成功條件只有：

1. 正常執行中 → **不通知**
2. 到達「今天早上不需要你管」的可信狀態 → **每天只通知一次**
3. crash / stall 但 Supervisor 自己救得回來 → **不通知**
4. 超過你定義的 recovery threshold、真的值得人工介入 → **通知一次**
5. restart 後不能重複洗通知
6. Discord 掛掉不能影響遊戲 automation

其中 **第 2 點的精確判定條件**，才是這個 feature 現在最值得先釐清的 spec；Discord 發訊息本身反而是最簡單的部分。

如果目的是讓你早上真的不再打開遊戲，我甚至會把產品原則寫成一句 contract：

> **Silence means automation is still responsible; a notification means responsibility has transferred to the user.**

這會比單純「打完 daily 傳 LINE」真正解決你的問題。

[1]: https://support.discord.com/hc/zh-tw/articles/228383668-Webhook-%E5%85%A5%E9%96%80?utm_source=chatgpt.com "Webhook 入門 – Discord"
[2]: https://notify-bot.line.me/?utm_source=chatgpt.com "LINE Notify"
