# 例外處理與卡死自癒子系統架構說明書 (Exception & Anti-Stuck Subsystem Architecture) 🛡️

本文件詳細說明專案中 **意外彈窗處理、雙層自癒救援、Watchdog 狀態監控與進程重開兜底** 之集中化架構設計 (`states/exceptions/`)。

---

## 🎯 一、 設計理念與核心原則

1. **集中化處置 (Single Source of Truth)**：
   所有意外彈窗（如 `Raid_Box.png` 掃蕩、`Wheel_of_Fortune.png` 幸運輪盤）與逾時卡死點擊，**嚴禁在 `state_machine.py` 或業務 Handler 中編寫 ad-hoc 硬編碼補釘**，統一由 `states/exceptions/` 獨立模組處置。
2. **純粹執行介面 (Pure Execution Subflows)**：
   Subflow 僅負責單純的圖像識別與點擊動作。業務狀態的暫存 (`stash_current_state`) 與復原 (`restore_stashed_state`) 由 [UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py) 統一發起與管理。
3. **雙層救援 + 重開遊戲兜底 (Double-Layer Recovery & Relaunch Fallback)**：
   * **優先級 1 (專屬 Subflows)**：根據 `config/exception_features.json` 特徵進行點對點精確處置。
   * **優先級 2 (通用防卡死兜底 Subflow)**：**當且僅當無任何專屬 Subflow 圖片被匹配到時**，執行全域關閉/確認按鈕掃描。
   * **兜底 (Game Relaunch)**：當輕量救援嘗試達 5 次仍無效，或同一狀態連續 2 次逾時卡死時，強行終止進程並透過 Steam 重新啟動遊戲自癒。

---

## 🏗️ 二、 系統架構與運轉流程 (Architecture Workflow)

```mermaid
graph TD
    A["主狀態機 (state_machine.py)"] -->|每一幀呼叫 check()| B["ExceptionWatchdog (watchdog.py)"]
    B -->|1. 狀態維持 30s/90s 未推進| C["第 1 次逾時：stash_current_state() & 轉移至 STATE_POPUP_RECOVERY"]
    C --> D["UnexpectedPopupRecoveryHandler (handler.py)"]
    D -->|優先級 1| E{"匹配專屬 Subflow ?"}
    E -->|YES| F["執行 RaidBoxSubflow / WheelOfFortuneSubflow"]
    E -->|NO| G{"優先級 2 通用防卡死 ?"}
    G -->|YES| H["執行 GenericAntiStuckSubflow"]
    
    F -->|處理成功| J["restore_stashed_state() 恢復原狀態與 Context"]
    H -->|處理成功| J
    
    D -->|3. 重試達 5 次仍無法排除阻礙| K["觸發 GameRelaunchSubflow 強行殺進程重開"]
    B -->|2. 同一狀態連續 2 次逾時 (輕量救援無效)| K
    K -->|重新開遊戲置頂 1080p| L["切換至 STATE_NAVIGATING 由全域登入接管"]
```

---

## 📁 三、 目錄結構與關鍵組件

```text
states/exceptions/
├── __init__.py                 # 匯出對外 Facade 介面
├── watchdog.py                 # ExceptionWatchdog (逾時、動態 CD 與 HWND 遺失監控)
├── handler.py                  # UnexpectedPopupRecoveryHandler (生命週期、雙層調度、暗色遮罩分析)
└── subflows/                   # 純粹執行子流程目錄
    ├── __init__.py
    ├── base.py                 # BaseExceptionSubflow 基礎抽象類別與 safe_match
    ├── raid_box.py             # RaidBoxSubflow (懸賞/掃蕩對話框)
    ├── wheel_of_fortune.py     # WheelOfFortuneSubflow (幸運輪盤檢測)
    ├── generic_anti_stuck.py   # GenericAntiStuckSubflow (全域防卡死兜底)
    └── game_relaunch.py        # GameRelaunchSubflow (進程終止與 Steam 重開)
```

### 1. 超時監控器：[ExceptionWatchdog](../../states/exceptions/watchdog.py)
* **平時效能保護**：狀態變動未達門檻時，僅進行極輕量之時間浮點數相減 (`now - last_state_change`)，完全不執行任何圖像模板匹配，將 CPU 佔用降至最低。
* **分級時間門檻**：
  * **常規短狀態**（大廳、結算等）：`30.0` 秒無進展即判定逾時。
  * **長流程任務**（導航、戰鬥、地下城探索、背包整理、城鎮子流程等）：給予 `90.0` 秒寬鬆門檻。
  * **待機模式 (`COLLECT_ONLY`)**：實作 `max(diamond_cd, bread_cd) + 60s` 智慧動態 CD 逾時與遊戲視窗消失檢查。

### 2. 意外彈窗恢復處理器：[UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py)
* **暗色遮罩分析 (`analyze_dimming_overlay`)**：即時計算畫面邊框與中央明暗度對比，診斷是否存在模態彈窗遮罩。
* **重試上限門檻**：最多嘗試 5 次。若 5 次嘗試後畫面仍無法復原，立即調用 `GameRelaunchSubflow` 進入重開流程。

### 3. 遊戲重開自癒子流程：[GameRelaunchSubflow](../../states/exceptions/subflows/game_relaunch.py)
* 透過 Win32 API 取得遊戲 HWND 與 PID，執行精確 `taskkill /f /pid <pid>` 及 `taskkill /f /im BlackfireCrusade.exe`。
* 呼叫 `SteamGameLauncher` 重新開啟遊戲並自動定位與縮放至標準 1080p 視窗。
* 重置所有連鎖卡死計數器、暫存與視窗旗標，無縫切換回 `STATE_NAVIGATING` 由全域登入導航接管。

---

## 🔍 四、 歷史卡死成因深度分析與已完成優化

在早期版本中，系統有時發生卡死卻未能觸發重開，經深度剖析後已全數完成防禦性修復：

### 1. 狀態假切換與時間戳刷洗 (已修復)
* **成因**：當業務 Handler 重複觸發無效的 `transition_to(current_state)` 時，`last_state_change` 被持續刷新為當前時間，導致時間永遠無法累積到 30s/90s。
* **修復方案**：在 [state_machine.py](../../states/state_machine.py) 的 `transition_to` 入口處加入 `if self.current_state != new_state:` 狀態防抖檢查。

### 2. 連續逾時卡死計數器被重置 (已修復)
* **成因**：原先 Watchdog 嚴格要求「同狀態連續 2 次逾時」才重開；若第 1 次逾時後通用點擊使狀態短暫切換，計數器被重置，導致永遠無法達到重開門檻。
* **修復方案**：在 [handler.py](../../states/exceptions/handler.py) 中新增「5 次點擊未果直接重開自癒」護欄，不再等待第二次逾時。

### 3. 長作業進度回報契約 (`notify_ui_progress`) (已實作)
* **機制**：針對長途背包銷毀與珠寶出售，建立嚴格的進度回報契約：只有在內部 Iterator 推進、點擊有效生效或 Phase 階段推進時，才調用 `self.machine.notify_ui_progress()` 刷新時間戳，兼顧長作業不誤判與卡死必自癒。

---

## 🛠️ 五、 開發者指引：如何新增一個 Exception Subflow

當遊戲新增一種未預期的特定活動彈窗或 UI 阻礙時，請依據以下 4 個步驟進行擴充：

### 1. 建立 Subflow 檔案
在 `states/exceptions/subflows/` 下新增 `my_popup.py`：
```python
from states.exceptions.subflows.base import BaseExceptionSubflow, safe_match

class MyPopupSubflow(BaseExceptionSubflow):
    name = "my_popup_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        pos, conf = safe_match(matcher, screen_img, "exceptions/My_Popup.png", threshold=0.75)
        return pos is not None

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        # 進行精確點擊處置...
        return True
```

### 2. 登錄設定檔 ([config/exception_features.json](../../config/exception_features.json))
在 `subflow_feature_mapping` 新增對應關係：
```json
"my_popup_subflow": {
  "trigger_template": "exceptions/My_Popup.png",
  "description": "我的自訂意外彈窗"
}
```

### 3. 註冊 Subflow 模組 ([handler.py](../../states/exceptions/handler.py))
在 `UnexpectedPopupRecoveryHandler.__init__` 註冊：
```python
self.register_subflow(MyPopupSubflow())
```

### 4. 新增行為單元測試 ([test_behavior_popup_recovery.py](../../tests/test_behavior_popup_recovery.py))
撰寫獨立單元測試驗證 `can_handle` 與 `execute` 點擊動作。
