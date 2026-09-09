# 日誌分級準則與 CLI 偏好設定架構規格 (Logging Hygiene & CLI Preference Spec) 📜

> 依據架構規範：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md) 與 [AGENTS.md](../../.agents/AGENTS.md)  
> 建立日期：2026-09-09  
> 狀態：草案規劃 (Draft Spec)

---

## 1. 問題定義與目標 (Problem Statement & Goals)

1. **日誌缺乏動態分級與自定義能力**：
   - 目前 [main.py](../../main.py) 與 [state_machine.py](../../states/state_machine.py) 硬編碼 `logging.basicConfig(level=logging.INFO)`。
   - 使用者無法於啟動時切換「除錯詳細日誌 (`DEBUG`)」或「極致安靜模式 (`WARNING`)」。
   - 缺乏像關卡、裝備品質那樣能**自動記憶上次偏好**（持久化於 Profile TOML）的機制。
2. **缺乏全域統一的 Log Level 定義規範**：
   - AI 開發者容易將高頻細節（如每幀的比對信心度、像素差）隨手打在 `INFO`，造成掛機終端機洗屏，淹沒真正的狀態轉移。
   - 需要在專案級規範（`.agents/AGENTS.md`）中明確定界 `DEBUG`、`INFO`、`WARNING`、`ERROR`。
3. **戰鬥卡死像素差異 (Battle Stall Pixel Diff) 的輸出定位**：
   - 戰鬥血條靜止卡死檢測每輪迴圈（0.5 秒）都會計算紅血像素變化 `diff = abs(curr - last)`。
   - 需要界定該像素日誌的正確層級歸屬（`DEBUG` vs `INFO`），避免破壞終端潔淨度。

---

## 2. 全域日誌層級精確定義 (Global Log Level Taxonomy)

本專案依據 [Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md) 之核心原則（單幀不可變 Snapshot、單一 InFlightAction、有界復原階梯 Bounded Recovery），定義以下 4 種標準日誌層級：

| 層級 (Level) | 架構對應職責 (Architectural Role) | 允許出現的情境與範例 (Examples) | 嚴禁出現的反模式 (Anti-patterns) |
| :--- | :--- | :--- | :--- |
| **`DEBUG`** | **高頻遙測、微觀判定與感知指標**<br>（對應架構：Scoped Perception 內部比對、Snapshot 建立、Action 等待 postcondition、BattleSession 內部黑盒特徵追蹤） | <ul><li>每輪模板比對最高相似度與座標（`conf: 0.684`）</li><li>**高頻特徵遙測：血條紅色像素數與即時變化（`sig: 1842, diff: 3`）**</li><li>InFlightAction 等待驗證中（單 tick 重試、deadline 倒數）</li><li>OCR 文字辨識邊界、耗時與快取命中日誌</li><li>DetectorRegistry 各 Profile 耗時與掃描模板數量指標</li></ul> | 🚫 嚴禁放置巨觀業務決策與狀態轉移（避免關閉 DEBUG 時無法追蹤任務流程）。 |
| **`INFO`** | **巨觀狀態轉移、已確認之動作進展與 Intent 完成**<br>（對應架構：ActiveIntent 切換、InFlightAction postcondition 成立、業務工作完成） | <ul><li>狀態機跳轉：`🔄 狀態轉移: NAVIGATING -> BATTLE`</li><li>動作確認生效：`👉 偵測到 [開始按鈕]，已執行點擊並通過後置驗證`</li><li>Intent 完成：`BreadIntent` / `DiamondIntent` 領取完畢、OCR 核銷完成</li><li>定時事件與排程：跨越 08:05 重置、定時領體力/鑽石觸發</li><li>模式切換與 Profile 熱重載回報</li></ul> | 🚫 **嚴禁放置高頻迴圈產生的數據**。<br>🚫 嚴禁未經 postcondition 驗證之無效重複點擊洗屏。 |
| **`WARNING`** | **有界復原階梯 (Recovery 1~5) 之自癒處置與資源警示**<br>（對應架構：有界重試內之自癒、關閉彈窗、重新定位、Intent Defer、原地戰鬥重置） | <ul><li>保護性攔截：關閉未知或遮擋彈窗（Dismiss Overlay）</li><li>重新定位與退避：未知場景退避回城（Relocalize Scene）</li><li>工作暫緩：體力不足觸發 `StaminaRetreat`，暫緩日常並退避至 `COLLECT_ONLY`（Intent Defer）</li><li>資源警示：`🎒 背包已滿`、地下城門票耗盡</li><li>卡死自癒：**戰鬥血條卡死達 30 秒，觸發原地「重新開始戰鬥」子流程（<= 2 次）**</li><li>暫時性異常：畫面截圖短暫失敗、視窗暫時找不到但仍在重試上限內</li></ul> | 🚫 嚴禁將正常完成的業務標記為 WARNING。<br>🚫 嚴禁將超出重試上限的重開標為 WARNING。 |
| **`ERROR`** | **超限升級 (Recovery 6~7) 與不可逆嚴重故障**<br>（對應架構：超出重試上限升級 ProcessPort.relaunch 或交由 Supervisor 重啟） | <ul><li>**戰鬥卡死原地重試超過上限（> 2 次），升級殺進程重開（`battle_stall_max_retries_exceeded`）**</li><li>戰鬥超過 900 秒 Hard Timeout，觸發 relaunch</li><li>連續截圖失敗達上限，觸發進程重開</li><li>連續找不到視窗達到 5 次，發起 GameRelaunchSubflow</li><li>OCR 核心引擎損毀無法載入、未捕獲的例外拋出</li></ul> | 🚫 嚴禁將仍在有界重試上限內的自癒步驟標記為 ERROR。 |

---

## 3. 戰鬥重新開始與像素差異 (Battle Stall Pixel Diff) 決策

### 核心問題：像素差異是 `INFO` 還是 `DEBUG`？

> **結論：高頻即時像素差屬於標準的 `DEBUG`；僅在判定卡死觸發自癒時，以彙整數據附帶於 `WARNING`。**

#### 詳細理由與工程考量：
1. **呼叫頻率與終端潔淨度**：
   - 戰鬥主迴圈 `run_main_loop` 預設 `--interval 0.5`（每秒 2 次）。
   - 一場普通戰鬥通常持續 30 至 120 秒，意味著會執行 60 至 240 次 `is_hp_stalled()` 檢測。
   - 若在 `INFO` 層級印出 `diff: 3 (threshold: 25)`，終端機每秒會跳出 2 行日誌，一場戰鬥產生上百行垃圾日誌，完全洗掉狀態轉移與自動戰鬥等關鍵事件。
2. **正確的實作模式**：
   - **在每輪檢測中（`BattleSession` 或 `BattleHandler`）**：
     ```python
     logging.debug(
         "[BattleStall] HP signature: %d (prev: %s, diff: %d, stalled: %.1fs/%.1fs)",
         current_signature,
         str(self.last_hp_signature),
         diff,
         stalled_duration,
         timeout_seconds,
     )
     ```
   - **在達到 30 秒門檻判定卡死時（升級為 `WARNING`）**：
     ```python
     logging.warning(
         "🚨 [戰鬥卡死自癒] 偵測到血條連續 %.1f 秒無顯著變化 (當前像素: %d, 最後 diff: %d < 門檻 25)！執行原地「重新開始戰鬥」子流程 (第 %d/%d 次)...",
         stall_cfg["timeout_seconds"],
         hp_sig,
         last_diff,
         curr_attempts + 1,
         max_retries,
     )
     ```
   - **獨立測試/驗證腳本（`utils/battle_stall_detector.py`）**：
     - 若作為獨立入口執行（`python utils/battle_stall_detector.py`），屬於開發者診斷工具，可直接使用 `print()` 輸出單張圖片的診斷結果。

---

## 4. CLI 日誌等級自定義與偏好記憶設計 (CLI Architecture)

### 4.1 優先級順序 (Precedence)
$$\text{CLI 引數 (--log-level)} > \text{終端機選單互動 (Enter 保留上次)} > \text{Profile 專屬 config.toml} > \text{全域 defaults.toml}$$

### 4.2 終端機互動選單文案設計
在使用者選擇完模式與關卡後（或啟動第一時間），展示清晰的日誌層級選單：

```text
============================================================
請選擇終端機日誌顯示等級 (Log Level)：
 1) INFO    - 標準模式 (推薦：顯示狀態轉移、重要事件、警告與錯誤) - 目前偏好
 2) DEBUG   - 除錯模式 (顯示完整細節：模板比對分數、像素差異、OCR 座標與耗時)
 3) WARNING - 靜音模式 (僅在發生異常、背包滿、卡死重試時提示)
 4) ERROR   - 極致安靜 (僅在系統崩潰或致命錯誤時輸出)
請輸入數字 [1-4] (直接 Enter 保留 1): 
============================================================
```

- **Enter 預設**：自動高亮當前 Profile 記錄的偏好（若無則預設 `1) INFO`）。
- **持久化**：使用者切換為 `2` (DEBUG) 後，立即呼叫 `update_profile_config(get_active_profile(), {"global": {"log_level": "DEBUG"}})` 寫入 `user_data/<profile>/config.toml`。
- **自動化無阻斷**：當 `--resume`（Supervisor 重啟）或帶有 `--log-level` 命令列參數時，**完全不跳出互動提示**，自動套用偏好。

### 4.3 涉及修改之模組架構

1. **[config/defaults.toml](../../config/defaults.toml)**：
   在 `[global]` 區塊定義預設值：
   ```toml
   [global]
   log_level = "INFO" # 可選: "DEBUG", "INFO", "WARNING", "ERROR"
   ```
2. **[config.py](../../config.py)**：
   - 增加 `get_log_level() -> str`：安全讀取 Active Profile 的 `[global].log_level`，預設 fallback 至 `defaults.toml`。
   - 增加 `apply_log_level(level: str) -> None`：動態調整 Root Logger 的 level，並確保 handlers 生效。
3. **[cli/arguments.py](../../cli/arguments.py)**：
   - 新增 `--log-level` 參數，支援傳入 `DEBUG`, `INFO`, `WARNING`, `ERROR`。
4. **[cli/mode_setup.py](../../cli/mode_setup.py)**（或獨立 `cli/log_setup.py`）：
   - 新增 `setup_log_level_config(args, is_resume=False)` 處理終端機提示與偏好持久化。
5. **[main.py](../../main.py)**：
   - 在決定 profile 後呼叫 `setup_log_level_config` 並即刻套用 `apply_log_level`。

---

## 5. `.agents/AGENTS.md` 規範增補方案 (Rule Integration)

在專案規則文件 [.agents/AGENTS.md](../../.agents/AGENTS.md) 中，規劃增補下列規範：

### A. 新增第 11 節：「日誌分級與終端潔淨規範 (Logging Hygiene & Level Guidelines)」
- **高頻遙測入 DEBUG**：凡每幀執行、迴圈內部（頻率高於 1 秒一次）之數值（比對相似度、像素數量、像素差異、座標定位），一律使用 `logging.debug()`，嚴禁使用 `logging.info()`。
- **關鍵決策入 INFO**：狀態機狀態跳轉（`STATE_NAVIGATING -> STATE_BATTLE`）、點擊動作確認、重大業務完成（領取日常、OCR 核銷完成）使用 `logging.info()`。
- **可自癒異常入 WARNING**：遮擋彈窗攔截、連續截圖失敗重試、戰鬥卡死自癒重啟、背包滿等保護機制使用 `logging.warning()`。
- **不可自癒故障入 ERROR**：重試超限升級重開、引擎損毀、未捕獲異常使用 `logging.error()`。

### B. 更新第 10 節：「提交前自審清單 (Pre-Commit Self-Review)」
增補檢查項目：
```markdown
7. ☐ 日誌層級審查：高頻迴圈/比對細節是否使用 `logging.debug`？（嚴禁在 `INFO` 輸出每秒重複日誌造成洗屏）
```

---

## 6. 驗收標準 (Acceptance Criteria)

1. **純文件階段**：
   - 本 Spec 定稿於 `docs/todos/log_levels_and_cli_preference_spec.md`。
   - `.agents/AGENTS.md` 完成規則增補，約束未來所有 AI 協作開發。
2. **實作階段（待使用者確認後執行）**：
   - 終端機互動輸入日誌層級，能正確持久化至 `user_data/<profile>/config.toml`。
   - 下次啟動（或不同 profile 啟動）能正確帶出該帳號上次偏好。
   - `--resume` 與 `--log-level` 能跳過互動提示直接套用。
   - 戰鬥血條卡死檢測中的 `diff` 正確以 `logging.debug` 記錄，在一般 INFO 模式下不洗屏，而在 DEBUG 模式下能清晰追蹤每輪像素變化。
