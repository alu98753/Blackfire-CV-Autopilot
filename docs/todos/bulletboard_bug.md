分析今日 8:15-20的log 了解告示牌 目前程式的問題

我已經對到實際程式了。這不是單純把 timeout 調大的問題，而是目前「感知契約 + 狀態轉移契約」一起形成 livelock。



實際執行鏈是：



INIT → 點 bulletin_board → WAIT_BOARD_OPEN → quit 出現 → board detector=False → 2.5 秒 → 當成干擾層關閉 → INIT → 紅點仍在 → 再點一次



這與你提供的 runtime log 完全一致。



更關鍵的是，is_inside_bulletin_board() 現在只接受 quit + (reset | task | task_after) 三種正向證據；真實畫面明明已開出一個有 quit 的視窗，但三個正向 template 全部沒命中，因此永遠回 False。 隨後 _step_wait_board_open() 又把「2.5 秒仍無正向證據」直接等同於「這是干擾層」，關閉後 _back_to_init()。



而且現有測試還明確把這個錯誤假設寫成契約：quit 有、board feature 無、超過 2.5 秒 => 必須關閉並回 INIT。所以這是典型的測試通過，但測試保護了錯誤行為契約。



我會把 spec 定義成「先修正真實世界契約，不針對這次案例塞 patch」。

我會把這個問題定義成 P0 perception/state-contract bug + anti-livelock 缺口，而不是「template matching threshold 小 bug」。尤其不建議 coder 第一手就把 2.5 → 5 秒：那只會把現在約十秒一次的無限循環變慢，根因完全還在。



另外值得注意的是，這套 detector 正好是 2026-09-12 那次 fix(bulletin_board): adapt dynamic candidate scales and isolate detector 重構加入/抽離的範圍，因此下一步 code review 我會優先做 該 commit 前後的 contract diff，確認是不是這次重構導入 regression。

# Bulletin Board 開窗辨識與 Livelock 修正 Spec

## 1. 問題

目前 `bulletin_board` 在真實執行環境產生無限閉環：

```text
INIT
→ 偵測 bulletin_board + red_dot
→ click building
→ WAIT_BOARD_OPEN
→ quit detected
→ is_inside_bulletin_board == False
→ 等待 2.5s
→ 判定為 interference overlay
→ close quit
→ INIT
→ 再次偵測同一 red_dot
→ repeat forever
```

實際 log 已證明此流程可持續數分鐘，且每輪均成功：

* 找到城鎮大門
* 找到 bulletin board
* 找到 red dot
* 點擊建築
* 找到 quit
* 關閉 quit
* 回城

因此問題**不在城鎮建築或紅點偵測的第一層入口**。

---

## 2. 已定位程式

### `states/handlers/bulletin_board.py`

問題轉移位於：

```python
_step_wait_board_open(...)
```

現行語意：

```text
is_board=True
    → CHECK_RESET

quit=True && is_board=False
    → 最多等待 BOARD_OPEN_SETTLE_TIMEOUT = 2.5s
    → 關閉目前 overlay
    → _back_to_init()
```

`_back_to_init()` 不保留任何：

* retry count
* failure reason
* target suppression
* cooldown

因此返回 INIT 後，同一個仍帶紅點的告示牌立即再次被點擊。

### `utils/bulletin_board_detector.py`

`is_inside_bulletin_board()` 現在要求：

```text
quit
AND NOT bag_features
AND
(
    reset
    OR task
    OR task_after
)
```

因此 `quit=True` 只能證明「某個 overlay 已經開啟」，無法證明告示牌。

問題是目前程式又反過來假設：

```text
quit=True
AND bulletin_positive_features=False
AND elapsed >= 2.5s

=> 一定是 interference overlay
```

這個推論不成立。

「無法證明是 Bulletin Board」
不等於
「已證明不是 Bulletin Board」。

---

## 3. Root Cause

### RC1 — Bulletin Board positive evidence 與真實 UI 不一致

真實 runtime 開窗後：

```text
quit = detected
reset = not detected
task = not detected
task_after = not detected
```

所以 detector 持續輸出 False。

目前僅憑現有 log **還不能進一步斷言是哪一張 template 有問題**。

可能原因必須透過真實 `debug_bulletin_board_verify.png` 驗證，包括：

* template 已與目前 UI 外觀不同
* ROI 不正確
* scale 不正確
* threshold 不正確
* 開窗後存在另一種合法 UI state，根本不包含這三個 feature

實作時禁止未取得證據便直接調低 threshold。

### RC2 — UNKNOWN 被錯誤分類成 INTERFERENCE

現有狀態只有隱含二分：

```text
BOARD
NOT BOARD → interference
```

但實際應至少存在：

```text
BOARD_CONFIRMED
KNOWN_INTERFERENCE
UNKNOWN_OVERLAY
NO_OVERLAY
```

沒有 positive board feature 只能得到 `UNKNOWN_OVERLAY`。

### RC3 — retry 沒有上界，形成 livelock

`WAIT_BOARD_OPEN → close → INIT` 可以無限循環。

同一個 `(building + red_dot)` 沒有：

* attempt budget
* backoff
* cooldown
* defer

因此只要 perception 永遠 False，主流程就永遠無法前進。

---

# 4. 目標行為

## Detector

Detector 必須輸出「觀察結果」，而不是只有 `bool`。

建議概念契約：

```python
BulletinBoardObservation(
    quit_visible: bool,
    bag_features: bool,
    reset_visible: bool,
    task_visible: bool,
    task_after_visible: bool,
    ...
)
```

Handler 再負責將 observation 分類。

至少必須能區分：

```text
BOARD_CONFIRMED
KNOWN_INTERFERENCE
UNKNOWN_OVERLAY
NO_OVERLAY
```

不要求一定使用 enum/dataclass；重點是保留這四種語意。

---

# 5. WAIT_BOARD_OPEN 狀態契約

### BOARD_CONFIRMED

有足夠 Bulletin Board positive evidence：

```text
→ CHECK_RESET
```

### KNOWN_INTERFERENCE

必須具有**明確負向證據**。

例如目前已有：

```text
quit + bag_features
```

才允許：

```text
close overlay
→ bounded retry
```

### UNKNOWN_OVERLAY

條件：

```text
quit visible
but
沒有 board positive evidence
and
沒有 known interference evidence
```

不得直接記錄：

```text
「判定為干擾層」
```

必須記錄：

```text
UNKNOWN_OVERLAY
```

並走有界 recovery。

### NO_OVERLAY

點擊建築後，在 hard timeout 內連 `quit` 都沒有：

```text
→ 視為 click/open failure
→ bounded retry
```

---

# 6. Retry / Anti-Livelock 契約

任何同一 bulletin-board execution attempt 都必須有 retry budget。

例如：

```text
MAX_OPEN_ATTEMPTS = 2~3
```

流程：

```text
attempt 1 failed
→ recover
→ attempt 2

attempt N failed
→ 不得再次回 INIT 無限重試
→ defer bulletin_board
→ pop_and_next_town_subflow()
```

可沿用專案目前已存在的：

```python
daily_manager.defer_subflow(...)
```

模式。

具體 cooldown 秒數屬 policy/config，不應硬耦合在 detector。

### Invariant

在沒有任何 UI progress 的情況下：

```text
同一 bulletin_board subflow
不得無限執行
```

---

# 7. 真實感知修復要求

本次修復不能只增加 timeout。

必須保存一次失敗時的真實畫面，確認：

```text
quit confidence
reset confidence
task confidence
task_after confidence
bag feature confidence
candidate scales
ROI
```

目前 `debug_bulletin_board_verify.png` 只輸出失敗畫面，但不足以回答「差多少沒過」。

應增加 detector diagnostic log，例如：

```text
[BulletinBoardDetector]
quit=0.94
reset=0.31
task=0.58
task_after=0.42
bag_tidy=0.12
bag_disassembly=0.08
classification=UNKNOWN_OVERLAY
```

之後才能依真實數據決定：

* 更新 template
* 改 ROI
* 改 scale
* 改 threshold
* 新增合法 board anchor

禁止為了讓測試通過加入：

* 黑圖特判
* 測試專用 bypass
* `if np.max(...) == 0`
* 單純把 threshold 大幅降低
* 單純把 2.5 秒改成更大的數字

---

# 8. 測試修正

現有測試：

```text
quit only + >2.5 sec
→ interference
→ close
→ INIT
```

這個契約必須修改。

新增至少以下行為測試：

1. `quit + board anchor`
   → `CHECK_RESET`

2. `quit + explicit bag feature`
   → 判定 known interference
   → close

3. `quit only`
   → 不得宣稱為 known interference

4. `UNKNOWN_OVERLAY`
   → recovery 次數必須有上限

5. persistent `red_dot`

   * board detector 永遠失敗
     → subflow 最終必須 defer / yield
     → 不得無限 `INIT → WAIT_BOARD_OPEN → INIT`

6. click 後完全沒有 quit
   → hard timeout
   → bounded retry

7. detector diagnostic
   → 失敗時能取得所有 positive/negative evidence confidence

---

# 9. 驗收條件

完成後必須同時滿足：

* 真實遊戲中 Bulletin Board 可以正常辨識並進入下一 phase。
* `quit-only` 不再被武斷記錄為「干擾層」。
* 明確背包 overlay 仍能正常排除。
* perception 永久失敗時，bulletin subflow 仍會在有限次嘗試後退出，不會阻塞整個 Daily pipeline。
* 不降低既有 `red_dot` / town building 門禁。
* 所有新增/修改測試驗證的是 production behavior，而非 mock 專用邏輯。
* 一次失敗 runtime log 足以回答「哪個 board feature 為何沒有達門檻」。

---

# 10. 非目標

本次不處理：

* OCR 任務標題品質
* 接任務流程
* reset 流程
* red-dot detector 重構
* 整個 DailyManager 重構
* 其他 town building handler

除非實際調查證明它們直接構成本問題 root cause。
