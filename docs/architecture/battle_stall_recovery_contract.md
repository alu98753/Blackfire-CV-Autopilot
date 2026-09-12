# 戰鬥血條靜止卡死自癒重啟契約 (Battle Stall Recovery Contract) ⚔️

> 狀態：Canonical Architecture Contract（正式架構規範）  
> 適用範圍：[`states/battle_session.py`](../../states/battle_session.py)、[`states/handlers/battle.py`](../../states/handlers/battle.py)、`utils/battle_stall_detector.py` 與戰鬥狀態生命週期管理。

---

## 1. 問題背景與設計意圖 (Problem Statement & Purpose)

在無人值守 24/7 掛機期間，戰鬥狀態受 `battle_max_duration_seconds`（預設 900 秒 / 15 分鐘）全域保護。然而，當遊戲因動畫死鎖、技能碰撞互卡或角色模型阻擋時，畫面可能仍有原地踏步或待機動作，但敵我雙方血條完全無任何變化。若僅依賴外部大上限逾時，系統將在死鎖畫面空等 15 分鐘才強制重啟遊戲，嚴重損耗自動化掛機效益。

本契約旨在規範**「純感知無狀態特徵提取 ➔ Session 時間與重試邊界維護 ➔ Handler 有界原地自癒 ➔ 超限殺進程重開」**的自癒升級機制。在血條完全靜止達到設定門檻（預設 30.0 秒）時，於 2~3 秒內透過遊戲內設定選單原地重置該場戰鬥，無需殺除遊戲進程即可快速恢復。

---

## 2. 架構分層職責邊界 (Architecture Boundaries)

依據專案全域規範與 [Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md)，戰鬥卡死自癒遵循嚴格的分層單向依賴：

```text
[純感知層: utils/battle_stall_detector.py]
  │ 輸入當前 frame，提取血條 ROI 紅色像素統計值 (純函式，無狀態、無副作用)
  ▼
[領域狀態層: states/battle_session.py (BattleSession)]
  │ 唯一持有者：記錄 started_at, last_hp_signature, last_diff, hp_stall_started_at, restart_battle_attempts
  │ 提供 is_hp_stalled(signature, now, timeout_seconds) 判定
  ▼
[決策與執行層: states/handlers/battle.py (BattleHandler)]
  │ 每一輪主迴圈取得簽章傳入 session.is_hp_stalled()
  │ 若判定卡死且 restart_battle_attempts < 2:
  │   觸發 _run_restart_battle_subflow(): 點擊 setting.png ➔ restart_battle.png ➔ reset_after_restart(now)
  │ 若重試超限 (>= 2):
  │   升級調用 machine.request_relaunch("battle_stall_max_retries_exceeded") 殺進程重開
```

---

## 3. 核心不可變鐵律 (Core Invariants)

### Invariant 1: 感知與決策嚴格分離 (Perception / Decision Separation)
- `utils.battle_stall_detector.extract_health_bar_signature` 必須是純無狀態函式（Pure Function）。
- 其職責僅限於從單幀畫面中截取血條 ROI 並計算紅色像素統計值 (`int`)。
- 純感知層**嚴禁自行持有時間戳、嚴禁快取前次數值、嚴禁判定卡死，更絕對禁止觸發滑鼠點擊**。
- `BattleHandler` 嚴禁在 Handler 物件內部維護計時器；[`BattleSession`](../../states/battle_session.py) 是單場戰鬥起始時間、停頓計時與重試次數的**唯一持有者（Single Source of Truth）**。

### Invariant 2: 血條靜止客觀判定門檻 (HP Stall Determination Thresholds)
- **視覺有效性門檻**：僅當當前幀簽章 `current_signature > 0`（ROI 內確實見到血條紅色像素）時方參與卡死判定；黑屏、轉場或結算彈窗遮擋時直接略過，絕不將轉場空幀誤判為卡死。
- **實質進展重置**：當前後幀簽章差距 $\text{diff} = |\text{current} - \text{last}| \ge \text{BLOOD\_DIFF}$（實作門檻為 300 像素，代表敵我雙方產生實質傷害或治療）時，必須立即刷新 `hp_stall_started_at = now` 與 `last_hp_signature = current`，確認戰鬥正常推進。
- **卡死宣告**：當 $\text{diff} < \text{BLOOD\_DIFF}$ 持續時間 $\ge \text{timeout\_seconds}$（預設 30.0 秒）時，`is_hp_stalled()` 回傳 `True`，宣告戰鬥邏輯卡死。

### Invariant 3: 有界原地重試自癒閉環 (Bounded In-Place Retry)
- 當判定卡死且未達上限時，`BattleHandler` 優先啟動低成本原地自癒：
  1. 點擊 `templates/battle/setting.png`（閥值 0.75）。
  2. 點擊 `templates/battle/restart_battle.png`（閥值 0.80）。
- 自癒動作完成後，必須調用 `BattleSession.reset_after_restart(now)`：
  - 重置單場戰鬥開始時間（`started_at = now`），歸零單場 900 秒大上限計時。
  - 清空血條簽章基準（`last_hp_signature = None`, `hp_stall_started_at = None`），避免剛進場吃到舊的卡死時間。
  - 累加重試計數 `restart_battle_attempts += 1`。
  - 重置自動戰鬥點擊計時器，促使次幀自動點擊 `common/auto.png` 重新啟用自動施法。

### Invariant 4: 階梯升級殺進程重開 (Escalation to Process Relaunch)
- 單場戰鬥的原地重新開始次數受嚴格硬上限保護：`max_retries = 2`。
- 當 `restart_battle_attempts >= max_retries` 且再次判定卡死時，**嚴禁無限在戰鬥內原地重試**！
- 必須果斷升級自癒階梯：調用 `machine.request_relaunch("battle_stall_max_retries_exceeded")`，交由看門狗與外部 Supervisor 殺進程並強制重開遊戲，杜絕死循環。

### Invariant 5: 跨場景重置與生命週期隔離 (Session Clear on Exit)
- 戰鬥結束離場（勝利結算、失敗結算、體力耗盡退避、手動中止）時，必須於狀態機退出戰鬥狀態時呼叫 `BattleSession.clear()`。
- 所有時間戳、血條基準與重試計數必須無條件歸零，**絕對禁止將上一場戰鬥的重試次數洩漏至下一場戰鬥**。

---

## 4. 相關模組與測試依歸

- 感知輔助：`utils/battle_stall_detector.py`
- 狀態儲存：[`states/battle_session.py`](../../states/battle_session.py)
- 決策處理器：[`states/handlers/battle.py`](../../states/handlers/battle.py)
- 參數設定：[`defaults.toml`](../../defaults.toml) (`battle_stall_timeout_sec = 30.0`, `battle_stall_max_retries = 2`)
- 測試覆蓋：`tests/test_long_run_resilience.py`
