# Spec / Bug Analysis: 首領領主 (lord_boss) 討伐中斷、次數誤殺與地下城插隊真相分析及 Precondition Contracts 契約化修復規格

- **狀態**：分析完畢 / 待實作修復 (Ready for Implementation)
- **類別**：Bug Fix / Architecture Invariant & Precondition Contract Alignment
- **影響範圍**：首領討伐狀態處理器 (`LordBossHandler`)、日常持久化管理器 (`DailyManager`)、全域活動調度階梯 (`evaluate_next_activity`)、戰鬥結算插隊機制 (`ResultHandler`)
- **相關核心檔案**：
  - [states/handlers/lord_boss.py](../../states/handlers/lord_boss.py) (開始戰鬥驗證、彈窗遮擋防護、自癒回退邏輯)
  - [utils/daily_manager.py](../../utils/daily_manager.py) (`is_boss_available`, `record_boss_fight`, `mark_boss_completed`)
  - [states/state_machine.py](../../states/state_machine.py) (`get_available_selected_lord_bosses`, `evaluate_next_activity`)
  - [states/handlers/result.py](../../states/handlers/result.py) (戰鬥結算後之 Tier 4 週期性任務插隊)
  - [user_data/native/daily_status.json](../../user_data/native/daily_status.json) (角色狀態持久化紀錄)
  - [docs/architecture/precondition_contracts.md](../architecture/precondition_contracts.md) (Precondition / Postcondition / Completion 契約標準)
  - [docs/architecture/project_arch_greenfield_lite_v1.md](../architecture/project_arch_greenfield_lite_v1.md) (Tier 1~Tier 4 全域活動排程階梯)

---

## 1. 原始問題描述 (User Problem Statement)

> **使用者提問**：
> 「分析 native 帳號中 他打 boss 只打一個 沒有去打雪山獅王 就被地下城搶佔的原因」

---

## 2. 核心結論與真相還原 (Executive Summary & Timeline)

### 2.1 疑點解答：為什麼只打了一個 Boss（古代惡靈）而沒打雪山獅王（雪山食屍王）？

**真相結論：雪山獅王並不是在晚上 19:10 被跳過，而是在今天下午 14:16:38 就已經被系統誤判標記為「今日已打滿 5/5」！**

1. **下午 14:16 的誤殺現場（誤將彈窗遮擋當成打滿）**：
   - 下午 14:16:21，雪山獅王（當時進度僅為 2/5）冷卻結束，系統喚醒進入首領討伐。
   - 14:16:28，機器人找到雪山獅王卡片、確認無冷卻木牌，點擊進入關卡資訊頁。
   - 14:16:30，機器人點擊「開始戰鬥」按鈕 (`stages/start.png`)。
   - **關鍵異常**：點擊後遊戲彈出了未知彈窗（例如體力不足、每日提醒或提示對話框）。此時遊戲以半透明黑底遮罩蓋住背景，使得背景按鈕的**相對亮度比驟降至 0.49**，且頂層浮現了 `common/ok.png`。
   - **程式致命缺陷**：[LordBossHandler](../../states/handlers/lord_boss.py) 在 2.5 秒戰鬥進場驗證超時後，發現畫面未轉移至戰鬥特徵，且背景仍依稀匹配到 `stages/start.png`，竟武斷推導：「判定 Boss [雪山食屍王瓦爾瑪] 次數已滿或無法挑戰」，並立即呼叫 `dm.mark_boss_completed("ghoul_snow")`！
   - [DailyManager.mark_boss_completed](../../utils/daily_manager.py) 將 `today_count` 直接改寫為 `5`、`completed_today = true`，**活生生沒收了雪山獅王剩餘的 3 次討伐機會**。

2. **晚上 19:10 的真實執行佇列**：
   - 19:10 啟動時，讀取 `user_data/native/daily_status.json` 的盤點結果為：
     - 育母蜘蛛 (`lord_spider`)：12:47 已自然打滿 5/5。
     - 雪山獅王 (`ghoul_snow`)：14:16 被強制記為 5/5。
     - 古代惡靈 (`lord_spectre`)：進度 4/5（距 14:47 上次挑戰已滿 2 小時冷卻）。
   - 因此，**當次系統的可挑戰 Boss 佇列中本來就只有古代惡靈（1 隻）**。
   - 19:11:47 進入古代惡靈戰鬥，19:12:08 結算完成，古代惡靈進度達 5/5。
   - 此時系統宣告：「今日所有 Boss 均已打滿 5 次！標記 lord_boss 今日完全完成」，合法且完整地結束了首領討伐子流程。

---

### 2.2 疑點解答：為什麼打完古代惡靈後「被地下城搶佔」？

**真相結論：首領討伐並非被地下城中途搶跑，而是首領流程已宣告 100% 完成；系統降級至 Tier 4 退守模式後，剛好觸發了合法的週期性地下城就緒插隊。**

1. **19:12:08 首領完結 ➔ 降級 Tier 4 退守**：
   - 領主 Boss 全數打滿，且懸賞任務為空（0 項），系統依 Profile 設定切換為 **Tier 4 長駐退守模式**。
   - Native Profile TOML 配置：`tier4_mode = "stage"`（普通關卡），目標為 Level 7 遺忘荒地 middle。
2. **19:13:30 ~ 19:13:45 進行關卡戰鬥**：
   - 機器人依退守配置進入遺忘荒地，打完一場並進入 `RESULT` 結算畫面。
3. **19:13:48 觸發週期性地下城插隊**：
   - 使用者在啟動參數與 TOML 中啟用了 `greedy_dungeon = true`（自動貪婪挑選地下城，允許 `[冰雪洞窟, 獸人地堡]`）。
   - 在戰鬥結算點 (`ResultHandler`)，系統檢查到冰雪洞窟與獸人地堡冷卻已過、處於可挑戰狀態：
     `[Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。`
   - 19:14:02 離開結算畫面後，系統切換至地下城頁籤，於 19:15:56 進入地下城。

**這給使用者的直觀感受像是「被地下城搶跑導致沒打雪山獅王」，但真正的斷鏈在下午 14:16 就已經發生。**

---

### 2.3 事故核心時間線對照表 (Incident Timeline)

| 時間戳記 | 模組 / 狀態 | 事件與日誌內容 | 關鍵事實還原 |
| :--- | :--- | :--- | :--- |
| **11:07:34** | `RESULT` | `⚔️ [DailyManager] 記錄 Boss [雪山食屍王瓦爾瑪] 戰鬥完成 (今日進度: 2/5)` | 雪山獅王今日第 2 次正常打完，進入 3 小時冷卻。 |
| **12:47:57** | `RESULT` | `⚔️ [DailyManager] 記錄 Boss [育母蜘蛛麗拉西亞] 戰鬥完成 (今日進度: 5/5)` | 育母蜘蛛打滿 5/5，今日正式完成。 |
| **14:16:21** | `COLLECT_ONLY` | `👑 [定時待機喚醒] 偵測到首領 Boss 冷卻結束 (可用: ['ghoul_snow'])` | 距 11:07 已滿 3 小時，系統精準喚醒準備打第 3 場。 |
| **14:16:30** | `LORD_BOSS` | `🚀 [首領討伐] 點擊開始戰鬥按鈕 [0.9786]，啟動 2.5 秒戰鬥進場驗證` | 點擊開始戰鬥，畫面出現未知彈窗/黑罩遮擋。 |
| **14:16:33** | `LORD_BOSS` | `⚠️ 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕依然存在！` | **【誤殺關鍵點】** 2.5 秒超時，背景亮度比 0.49，遮擋彈窗擋住進場。 |
| **14:16:38** | `LORD_BOSS` | `🛡️ [DailyManager] 已手動將 Boss [雪山食屍王瓦爾瑪] 強制標記為今日已打滿` | **【誤殺致命點】** 呼叫 `mark_boss_completed`，進度直接暴衝至 5/5！ |
| **14:16:42** | `BREAD` | `🍞 領體力：偵測到體力 OK 按鈕 [0.9537]，點擊 OK。` | 此時才由領體力流程誤打誤撞點掉了遮擋的 `common/ok.png`。 |
| **14:47:59** | `RESULT` | `⚔️ [DailyManager] 記錄 Boss [古代惡靈伊瑟倫] 戰鬥完成 (今日進度: 4/5)` | 古代惡靈打完第 4 場。 |
| **19:10:38** | `Supervisor` | `⚔️ [Activity Scheduler] 觸發 Tier 2 領主 Boss 討伐 (可用 Boss: ['lord_spectre'])` | 重開腳本，因存檔中蜘蛛 5/5、獅王 5/5，**可用 Boss 僅剩古代惡靈**！ |
| **19:12:08** | `RESULT` | `⚔️ [DailyManager] 記錄 Boss [古代惡靈伊瑟倫] 戰鬥完成 (今日進度: 5/5)` | 古代惡靈滿 5/5，今日所有領主 Boss 全滿完結。 |
| **19:12:08** | `StateMachine` | `🔄 已切換至使用者設定的 Tier 4 退守配置: 每日懸賞任務 (關卡: 遺忘荒地)` | 正常降級至 Tier 4 普通關卡退守。 |
| **19:13:30** | `NAVIGATING` | `進入遺忘荒地戰鬥` | 執行關卡戰鬥。 |
| **19:13:48** | `RESULT` | `🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。` | 遺忘荒地結算時，貪婪地下城就緒，合法執行 Tier 4 週期插隊。 |

---

## 3. 架構契約違背盤點與根因分析 (Architectural Violations)

對照 [Precondition Contracts](../architecture/precondition_contracts.md) 與 [Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)，此 Bug 暴露了四項核心契約違背：

### 3.1 違背契約一：把 Action Postcondition Failure 誤當 Domain Completion

- **契約規範（Section 2 & 6）**：
  > 「『點擊已送出』不是 postcondition，也不是 completion。」
  > 「不得以『經過一段時間』或『已經點擊』單獨推導 intent 完成。」
- **違背實況**：
  在 [LordBossHandler](../../states/handlers/lord_boss.py) 中，發送 `click(start_btn)` 後，postcondition 應該是「進入戰鬥特徵 (`battle_entered`)」或者「出現對話框/Overlay (`dialog/modal overlay`)」。
  當 2.5 秒驗證超時且 `start_btn` 依然存在時，這只是一個 **Action Postcondition Timeout / Failure**，程式卻直接呼叫 `dm.mark_boss_completed()` 宣告 **Domain Completion**！

### 3.2 違背契約二：DEFER / RETRY 與 COMPLETION 語意嚴重混淆

- **契約規範（Section 2 & 4）**：
  > 「DEFER 不是完成；它只代表現在暫不選取，原始 pending fact 仍存在。」
  > 「不把找不到入口、找不到按鈕或 detector 未執行當成 completion。」
- **違背實況**：
  即便點擊無反應或次數真的異常，其合法處置只能是：
  1. `RETRY`：有界重試 1 次；
  2. `DEFER`：若仍失敗，退回大廳並在記憶體中標記暫緩 5~10 分鐘再試；
  絕不能直接將永久存檔改寫為 `today_count = 5`！`mark_boss_completed` 的存在本身就是一種侵蝕狀態真實性的危險後門。

### 3.3 違背契約三：Overlay 遮罩盲區與未確認父場景即判定負向條件

- **契約規範（Section 6）**：
  > 「需要用『元素不存在』表示完成時，應先證明其 parent scene／panel 已正確定位。」
- **違背實況**：
  遊戲在彈出對話框時會套前半透明黑底（亮度比降至 0.49）。`LordBossHandler` 在判定 `still_start` 時，完全沒有先檢查是否有前景彈窗（Overlay），直接用被遮蔽的畫面比對 `stages/start.png`，誤將「被彈窗蓋住的按鈕」當成「有效可點擊的按鈕」，導致誤判。

### 3.4 架構合規澄清：Tier 4 週期性退守插隊的合規性

- **架構規範（Greenfield-lite v1 Section 4.3.1）**：
  ```text
  Tier 1: 城鎮速領 -> Tier 1.5: 深淵魔王 -> Tier 2: 首領 Boss -> Tier 3: 懸賞任務 -> Tier 4: 長駐退守
  ```
- **合規判定**：
  19:12:08 時，Tier 2 首領 Boss 已經全部 5/5 完成，Tier 3 懸賞任務為空，因此流向 Tier 4 是 100% 合規的。在 Tier 4 內部，地下城探索（貪婪模式）與普通關卡屬於同階退守，結算時地下城冷卻結束進行插隊完全符合活動調度規範。系統並沒有發生「跨 Tier 搶跑」，純粹是因為前述的 Tier 2 被提前誤殺。

---

## 4. 首領討伐生命週期與驗證條件契約 (Verification Contracts)

為徹底根除此類誤殺，必須根據 Precondition Contracts 定義完整的條件分類：

```text
[Selection Condition]
  dm.is_boss_available(boss_key) == True (today_count < 5 且 cooldown_seconds 到期)
        │
        ▼ (Scheduler 排入 Tier 2 佇列)
[Dispatch Precondition]
  AtTown / AtLobby 且 Lord_entry 開啟 且 第一張卡片已對齊 (CardListNavigator.aligned)
        │
        ▼ (派發 LordBossHandler)
[Action: Click Boss Card & Start]
  發送點擊 start_btn
        │
        ▼
[Action Postcondition 驗證 (2.5s)]
  ├── 情況 A: 偵測到 battle_features (進入戰鬥) ➔ 轉移至 STATE_BATTLE
  ├── 情況 B: 偵測到 modal overlay (如 common/ok.png, confirm.png) ➔ 執行 DISMISS_OVERLAY
  └── 情況 C: 逾時且無彈窗 ➔ 執行 Bounded Retry (最多 1 次)
        │
        ▼ (戰鬥打完)
[Positive Completion Evidence]
  唯一合法來源: 戰鬥結束 -> RESULT 狀態結算確認 -> record_boss_fight() (today_count + 1)
```

### 4.1 條件分類與責任 Owner

| 條件類型 | 條件定義 | 唯一責任 Owner | 處置方式 |
| :--- | :--- | :--- | :--- |
| **Selection Condition** | `today_count < 5` 且 `now - last_fight >= cd` | `DailyManager` | 不符則不選入佇列；冷卻中由定時器喚醒。 |
| **Dispatch Precondition** | 大廳已到達、領主頁籤已開啟、第一張卡片已復位 | `NavigationController` | 未滿足則沿路徑滿足，不進入選關派發。 |
| **Maintenance Condition** | 點擊卡片後 1.5s 內維持等待；點擊開始戰鬥後 2.5s 內維持驗證 | `LordBossHandler` | 期間禁止切換 Intent 或被其他 Scheduler 打斷。 |
| **Postcondition** | 點擊開始戰鬥後，必須於 2.5s 內證明「已進入戰鬥」或「出現對話框」 | `LordBossHandler` | 若未證明，進入異常復原階梯。 |
| **Positive Completion** | 戰鬥勝利/結束，於 `RESULT` 結算畫面確認完成 | `ResultHandler` | 呼叫 `record_boss_fight()`，計數嚴格 `+1`。 |
| **Negative / Defer Policy** | 點擊開始戰鬥後出現彈窗、或連續 2 次點擊無效 | `LordBossHandler` | 關閉彈窗並退出，標記記憶體 DEFER 5 分鐘，**嚴禁改寫 completed**。 |

---

## 5. 修復規格方案 (Repair Implementation Spec)

### 5.1 修復項目 1：`LordBossHandler` 重構進場驗證與彈窗自癒閉環

- **目標檔案**：[states/handlers/lord_boss.py](../../states/handlers/lord_boss.py)
- **修改要點**：
  1. **移除危險的 `dm.mark_boss_completed()` 呼叫**：
     點擊開始戰鬥 2.5 秒未進戰鬥，絕對不可認定「今日已打滿」。
  2. **加入前景彈窗遮罩檢測與關閉**：
     驗證戰鬥特徵時，同步檢測畫面上是否存在 `common/ok.png`、`common/confirm.png`、`common/cancel.png`。
     - 若偵測到彈窗：記錄 `WARNING`（如體力不足或異常提示），點擊關閉按鈕解除遮罩。
     - 點擊卡片關閉按鈕 (`common/quit.png`) 退回大廳。
     - 退出首領子流程，並對該 Boss 設定短期內存退避 (`defer_until = now + 300`)，不污染持久化檔案。
  3. **加入單次補點重試機制 (Bounded Retry = 1)**：
     若未見彈窗且 `start_btn` 依然存在，執行第 2 次點擊；若依然未進戰鬥，才安全退場並 `DEFER`。

### 5.2 修復項目 2：`DailyManager` 廢除隨意覆寫 `today_count = 5`

- **目標檔案**：[utils/daily_manager.py](../../utils/daily_manager.py)
- **修改要點**：
  1. 審視並限縮 `mark_boss_completed()`：
     - 若無明確的 OCR 證據證明伺服器顯示「0/5 次」，嚴禁外部呼叫者因「點擊超時」就直接將 `today_count` 強改為 `5`。
     - 改名或重構為 `set_boss_temporary_defer(boss_key, duration=300)`，僅在記憶體中設定暫時冷卻，保護當日真實挑戰次數。

### 5.3 修復項目 3：Native Profile 存檔即時校正

- **目標檔案**：[user_data/native/daily_status.json](../../user_data/native/daily_status.json)
- **修復內容**：
  將被誤殺的 `ghoul_snow` 恢復為實際打過的 2 次：
  ```json
  "ghoul_snow": {
    "name": "雪山食屍王瓦爾瑪",
    "today_count": 2,
    "max_daily_count": 5,
    "cooldown_seconds": 10800,
    "last_fight_timestamp": 1789020998.7872906,
    "completed_today": false
  }
  ```

---

## 6. 測試與驗收清單 (Verification Checklist)

根據專案測試規範，編寫專屬單元測試：`tests/test_behavior_lord_boss_preconditions.py`。

- [ ] **測試案例 1：進場驗證出現彈窗遮蔽**
  - **Given**：點擊開始戰鬥後，畫面出現 `common/ok.png`（模擬體力不足彈窗），背景亮度變暗。
  - **When**：`LordBossHandler` 執行進場驗證。
  - **Then**：系統應點擊 `ok.png` 關閉彈窗，並點擊 `quit.png` 退回大廳；**斷言 `DailyManager.mark_boss_completed` 未被呼叫，`today_count` 維持原值**。
- [ ] **測試案例 2：點擊開始戰鬥超時無反應（單次重試與 Defer）**
  - **Given**：點擊開始戰鬥後，未進戰鬥且無彈窗。
  - **When**：等待 2.5 秒逾時。
  - **Then**：系統進行第 2 次重試點擊；若仍逾時，退出子流程並進行 Defer；**斷言存檔狀態未被標記為 completed**。
- [ ] **測試案例 3：正常進場與結算計數累加契約**
  - **Given**：點擊開始戰鬥後 2.5 秒內偵測到 `auto.png` 進入戰鬥。
  - **When**：戰鬥結束由 `ResultHandler` 結算。
  - **Then**：斷言僅在此時呼叫 `record_boss_fight()`，`today_count` 由 2 變 3。

---

## 7. 附錄：原始事故核心日誌節錄 (Incident Logs)

<details>
<summary>點擊展開 14:16:21 ~ 14:16:45 雪山獅王誤殺原始日誌</summary>

```text
2026-09-10 14:16:21,043 [INFO] 👑 [定時待機喚醒] 偵測到首領 Boss 冷卻結束 (可用: ['ghoul_snow']) ➔ 喚醒轉入 LORD_BOSS！
2026-09-10 14:16:28,130 [INFO] 成功匹配模板 'load/lord_spider.png'！相似度: 0.9853，相對亮度比: 1.00，座標: (278, 321)
2026-09-10 14:16:28,131 [INFO] 🎯 [首領討伐] 偵測到第一個 Boss (起點) [lord_spider] (信心度: 0.9853)，已確立回歸最左側起點！
2026-09-10 14:16:28,437 [INFO] 成功匹配模板 'load/ghoul_snow.png'！相似度: 0.9920，相對亮度比: 1.00，座標: (1107, 328)
2026-09-10 14:16:28,440 [INFO] 🔍 [首領討伐] 於畫面發現 Boss 卡片 [雪山食屍王瓦爾瑪] [0.9920]，檢查是否有冷卻木牌...
2026-09-10 14:16:28,504 [INFO] ℹ️ [CooldownDetector] 木牌模板最高匹配分數: 0.4919 (門檻: 0.58) ➔ 判定無冷卻木牌
2026-09-10 14:16:28,506 [INFO] 🎯 [首領討伐] 確認 Boss [雪山食屍王瓦爾瑪] 無冷卻木牌！進行點擊選擇討伐！
2026-09-10 14:16:30,159 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9786，相對亮度比: 0.99，座標: (790, 606)
2026-09-10 14:16:30,161 [INFO] 🚀 [首領討伐] 點擊開始戰鬥按鈕 [0.9786]，啟動 2.5 秒戰鬥進場驗證 [雪山食屍王瓦爾瑪]...
2026-09-10 14:16:33,223 [WARNING] ⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [stages/start.png] 依然存在！判定 Boss [雪山食屍王瓦爾瑪] 次數已滿或無法挑戰。
2026-09-10 14:16:33,431 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9585，相對亮度比: 0.49，座標: (1022, 151)
2026-09-10 14:16:33,433 [INFO] 🚪 [首領討伐] 點擊卡片關閉按鈕 [common/quit.png] 退回大廳...
2026-09-10 14:16:37,786 [WARNING] ⚠️ [配對確認逾時] 模板 [common/quit.png] 在 4.0 秒內未能確認消失。
2026-09-10 14:16:38,789 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-10 14:16:38,790 [INFO] 🛡️ [DailyManager] 已手動將 Boss [雪山食屍王瓦爾瑪] 強制標記為今日已打滿 (completed_today: True)。
2026-09-10 14:16:38,790 [INFO] 🔄 狀態轉移: LORD_BOSS -> NAVIGATING
2026-09-10 14:16:38,793 [INFO] 🔄 狀態轉移: NAVIGATING -> COLLECT_ONLY
2026-09-10 14:16:42,943 [INFO] 成功匹配模板 'common/ok.png'！相似度: 0.9537，相對亮度比: 1.00，座標: (845, 452)
2026-09-10 14:16:42,945 [INFO] 🍞 領體力：偵測到體力 OK 按鈕 [0.9537]，點擊 OK。
```
</details>