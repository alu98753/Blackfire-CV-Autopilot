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

本節的長期約束是感知與決策的責任分離、以觀測進展判斷停滯、失敗後的有界復原，以及跨場景生命週期隔離。ROI、影像特徵、秒數、次數、私有欄位與重啟實作是可替換的策略；修改後仍須維持同一可觀測行為並通過 `tests/test_behavior_battle_session_lifecycle.py`。術語判讀見 [Canonical Invariant Registry](canonical_invariant_registry.md)。

### Invariant 1: 感知與決策嚴格分離 (Perception / Decision Separation)
- **Scope**：戰鬥進展感知與停滯復原的責任分工。
- **Rule**：感知元件 MUST 只產生觀測結果；停滯判定、復原決策與 UI 操作 MUST 由明確的決策／生命週期擁有人負責。單場戰鬥的進展與復原狀態 MUST 有唯一擁有人。
- **Observable consequence**：更換感知演算法不會自行觸發復原；重複的狀態持有者不會對同一戰鬥做出相互衝突的決策。
- **Allowed variation**：感知訊號、ROI、資料結構、類別與函式名稱可變更。
- **Verification**：`tests/test_behavior_battle_session_lifecycle.py`。

### Invariant 2: 可觀測進展的停滯判定 (Observable Progress Stall Determination)
- **Scope**：可觀測戰鬥進展不足時的停滯判定。
- **Rule**：系統 MUST 只在進展訊號有效時評估停滯；可觀測進展 MUST 重置停滯判定；持續無進展才可宣告停滯。
- **Observable consequence**：轉場或沒有有效進展訊號的畫面不會被誤判為停滯；戰鬥恢復進展後不會沿用先前的停滯時間。
- **Allowed variation**：進展訊號、差異門檻、取樣時間與停滯期限可變更。
- **Verification**：`tests/test_behavior_battle_session_lifecycle.py`。

### Invariant 3: 有界原地重試自癒閉環 (Bounded In-Place Retry)
- **Scope**：已確認停滯且尚可嘗試低成本復原的戰鬥。
- **Rule**：系統 MUST 先執行有界的低成本復原；每次嘗試後 MUST 建立新的戰鬥觀測基準，避免以先前戰鬥狀態判定新嘗試。
- **Observable consequence**：單一停滯不會立即升級為程序重啟；復原後的判定從新的觀測週期開始。
- **Allowed variation**：復原 UI 序列、復原預算、計數器與重置實作可變更。
- **Verification**：`tests/test_behavior_battle_session_lifecycle.py`。

### Invariant 4: 階梯升級殺進程重開 (Escalation to Process Relaunch)
- **Scope**：低成本復原已耗盡且停滯仍持續的戰鬥。
- **Rule**：系統 MUST NOT 無限重試低成本復原；其預算耗盡後 MUST 升級至受 Supervisor 管理的復原層級。
- **Observable consequence**：持續停滯會停止原地循環，並產生可處理的升級復原請求。
- **Allowed variation**：預算、升級機制、退出原因與 Supervisor API 可變更。
- **Verification**：`tests/test_behavior_battle_session_lifecycle.py`。

### Invariant 5: 跨場景重置與生命週期隔離 (Session Clear on Exit)
- **Scope**：離開戰鬥的所有正常、失敗與中止路徑。
- **Rule**：離開戰鬥時，系統 MUST 清除該場戰鬥的停滯與復原生命週期狀態。
- **Observable consequence**：前一場的進展基準與復原預算不會影響下一場戰鬥。
- **Allowed variation**：離場狀態、清除函式與內部欄位可變更。
- **Verification**：`tests/test_behavior_battle_session_lifecycle.py`。

---

## 4. 相關模組與測試依歸

### Current policy / implementation reference

目前的血條訊號、門檻、逾時、復原 UI 步驟與重試預算由 production code 與 `defaults.toml` 維護。這些是 AS-IS 策略，不是本章的 normative rule。

- 感知輔助：`utils/battle_stall_detector.py`
- 狀態儲存：[`states/battle_session.py`](../../states/battle_session.py)
- 決策處理器：[`states/handlers/battle.py`](../../states/handlers/battle.py)
- 參數設定：[`defaults.toml`](../../defaults.toml) (`battle_stall_timeout_sec = 30.0`, `battle_stall_max_retries = 2`)
- 測試覆蓋：`tests/test_long_run_resilience.py`
