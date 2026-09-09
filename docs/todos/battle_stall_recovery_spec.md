# 戰鬥血條靜止卡死自癒重啟架構規格 (Battle Stall Recovery Spec) ⚔️

> 依據架構規範：[Greenfield-lite Architecture v1](../../docs/architecture/project_arch_greenfield_lite_v1.md)  
> 建立日期：2026-09-09  
> 狀態：已定稿 (Finalized)

---

## 1. 問題定義與背景 (Problem Statement)

* **現狀盲點**：
  目前戰鬥唯一逾時機制是 `battle_max_duration_seconds`（預設 900 秒 / 15 分鐘）。
  當遊戲因底層動畫死鎖或技能互卡時，**人物模型可能有原地動作，但敵我雙方血條完全沒有任何變化**，導致腳本空等 15 分鐘才由外部看門狗強制殺遊戲重開，嚴重浪費掛機效率。
* **目標**：
  在戰鬥進行中，由純感知層低負載觀察血條區域變化，由 `BattleSession` 追蹤卡死進展。
  若連續達 TOML 設定門檻（預設 30 秒）血條完全靜止（無傷害、無治療、無戰鬥進展），判定為戰鬥邏輯卡死，由 `BattleHandler` 觸發「設定 ➔ 重新開始戰鬥」子流程，在 2~3 秒內原地重置該場戰鬥，無需重開遊戲。

---

## 2. 架構分層職責劃分 (Architecture Boundaries)

根據 `docs/architecture/project_arch_greenfield_lite_v1.md` 第 3 節、第 4.8 節與第 6 節之 Runtime 不變量：
> **「依賴只能向下：Detector 只觀察不點擊、Policy 只決策不做 IO、BattleSession 是時間與復原邊界的唯一持有者」**

```text
[Perception 純感知 Helper] (utils/battle_stall_detector.py)
  │ 輸入當前 frame，提取血條區域 HSV 紅色長度/特徵簽章 (無狀態、無副作用)
  ▼
[BattleSession] (states/battle_session.py)
  │ 唯一持有者：記錄 last_hp_signature 與 stall_started_at
  │ 提供 check_stall_progress(signature, now, timeout_sec)
  ▼
[BattleHandler] (states/handlers/battle.py)
  │ 若 check_stall_progress() 判定卡死且未超重試上限 (<= 2次)
  │ 觸發 _run_restart_battle_subflow()：
  │ 點擊 setting.png -> restart_battle.png
  ▼
[ProcessPort Recovery]
  若單場戰鬥重試超過 2 次仍卡死，升級為 request_relaunch 殺進程重開
```

### 模組具體劃分：
1. **純感知輔助（`utils/battle_stall_detector.py`）**：
   - 函式 `extract_health_bar_signature(screen_img) -> tuple`
   - 純無狀態函式，輸入單張截圖，截取敵我血條 ROI，計算紅色血量像素數量與分佈雜湊。
2. **狀態與進展追蹤（`BattleSession` 位於 `states/battle_session.py`）**：
   - 新增 `hp_stall_started_at: float | None`
   - 新增 `last_hp_signature: Any`
   - 新增 `restart_battle_attempts: int = 0`
   - 提供方法 `is_hp_stalled(signature, now, stall_limit_sec) -> bool`：若簽章改變（差距 > 門檻）則刷新計時，若持續未變超過 `stall_limit_sec` 則判定為卡死。
   - `clear()` 時自動連同血條靜止狀態與重試次數一併重置。
3. **決策與動作復原（`BattleHandler` 位於 `states/handlers/battle.py`）**：
   - 每一輪戰鬥調用 `extract_health_bar_signature` 並傳入 `session.is_hp_stalled()`。
   - 卡死時執行 `_run_restart_battle_subflow()`：
     - 點擊 `templates/battle/setting.png`
     - 點擊 `templates/battle/restart_battle.png`
     - 增加 `session.restart_battle_attempts += 1`
     - 若 `restart_battle_attempts > max_restart_attempts`（預設 2 次），升級為 `machine.request_relaunch("battle_stall_max_retries_exceeded")`。

---

## 3. TOML 設定配置 (config/defaults.toml)

於 `[global]` 區塊新增：
```toml
battle_stall_timeout_sec = 30.0     # 戰鬥血條完全無變化卡死上限 (秒)
battle_stall_max_retries = 2        # 單場戰鬥卡死最多重新開始次數，超過則重開遊戲
```

---

## 4. 自癒動作子流程 (Restart Battle Subflow)

```text
1. 點擊右上角設定按鈕: templates/battle/setting.png (閥值 0.75)
   └── 等待 0.3s 選單彈出
2. 點擊重新開始按鈕: templates/battle/restart_battle.png (閥值 0.80)
   └── 等待 0.3s 遊戲重置回到戰鬥載入/開場
3. 狀態機清理與復歸:
   ├── 重置 BattleSession 戰鬥開始時間為當前 now (歸零單場戰鬥計時)
   ├── 清空血條比對基準
   └── BattleHandler 自動在下一 tick 重新點擊 common/auto.png 啟用自動戰鬥！
```
