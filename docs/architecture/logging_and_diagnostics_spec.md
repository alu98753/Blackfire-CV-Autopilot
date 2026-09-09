# 日誌分級、診斷遙測與輪轉保存架構規格 (Logging, Diagnostics & Rotation Spec) 📜

> 依據架構規範：[Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md) 與 [.agents/AGENTS.md](../../.agents/AGENTS.md)  
> 建立日期：2026-09-09  
> 狀態：正式架構規格 (Active Architecture Spec)

---

## 1. 核心原則與背景 (Core Principles)

本專案為支援 24/7 長時間全自動運行的遊戲自動化 Agent，日誌系統必須兼顧以下三大核心要求：
1. **終端潔淨度 (Console Hygiene)**：預設一般掛機情況下，不得被高頻循環（每秒數次的比對、像素差、座標）洗屏，避免重要狀態機轉移被淹沒。
2. **事故可追溯性 (Incident Traceability)**：夜間掛機發生卡死、未預期彈窗或重開機時，必須在磁碟上有完整的歷史記錄供隔日排查。
3. **角色與天數隔離 (Profile & Daily Isolation)**：雙開、多開與沙盒環境下的日誌嚴格分離；每日午夜 00:00 自動切換檔案，且自動維護 7 天生命週期以防硬碟空間被佔滿。

---

## 2. 全域日誌層級精確定義 (Global Log Level Taxonomy)

本專案依據 [Greenfield-lite Architecture v1](project_arch_greenfield_lite_v1.md) 之核心原則（單幀不可變 Snapshot、單一 InFlightAction、有界復原階梯 Bounded Recovery），定義以下 4 種標準日誌層級：

| 層級 (Level) | 架構對應職責 (Architectural Role) | 允許出現的情境與範例 (Examples) | 嚴禁出現的反模式 (Anti-patterns) |
| :--- | :--- | :--- | :--- |
| **`DEBUG`** | **高頻遙測、微觀判定與感知指標**<br>（對應架構：Scoped Perception 內部比對、Snapshot 建立、Action 等待 postcondition、BattleSession 內部黑盒特徵追蹤） | <ul><li>每輪模板比對最高相似度與座標（`conf: 0.684`）</li><li>**高頻特徵遙測：血條紅色像素數與即時變化（`sig: 1842, diff: 3`）**</li><li>InFlightAction 等待驗證中（單 tick 重試、deadline 倒數）</li><li>OCR 文字辨識邊界、耗時與快取命中日誌</li><li>DetectorRegistry 各 Profile 耗時與掃描模板數量指標</li></ul> | 🚫 嚴禁放置巨觀業務決策與狀態轉移（避免關閉 DEBUG 時無法追蹤任務流程）。 |
| **`INFO`** | **巨觀狀態轉移、已確認之動作進展與 Intent 完成**<br>（對應架構：ActiveIntent 切換、InFlightAction postcondition 成立、業務工作完成） | <ul><li>狀態機跳轉：`🔄 狀態轉移: NAVIGATING -> BATTLE`</li><li>動作確認生效：`👉 偵測到 [開始按鈕]，已執行點擊並通過後置驗證`</li><li>Intent 完成：`BreadIntent` / `DiamondIntent` 領取完畢、OCR 核銷完成</li><li>定時事件與排程：跨越 08:05 重置、定時領體力/鑽石觸發</li><li>模式切換與 Profile 熱重載回報</li></ul> | 🚫 **嚴禁放置高頻迴圈產生的數據**。<br>🚫 嚴禁未經 postcondition 驗證之無效重複點擊洗屏。 |
| **`WARNING`** | **有界復原階梯 (Recovery 1~5) 之自癒處置與資源警示**<br>（對應架構：有界重試內之自癒、關閉彈窗、重新定位、Intent Defer、原地戰鬥重置） | <ul><li>保護性攔截：關閉未知或遮擋彈窗（Dismiss Overlay）</li><li>重新定位與退避：未知場景退避回城（Relocalize Scene）</li><li>工作暫緩：體力不足觸發 `StaminaRetreat`，暫緩日常並退避至 `COLLECT_ONLY`（Intent Defer）</li><li>資源警示：`🎒 背包已滿`、地下城門票耗盡</li><li>卡死自癒：**戰鬥血條卡死達 30 秒，觸發原地「重新開始戰鬥」子流程（<= 2 次）**</li><li>暫時性異常：畫面截圖短暫失敗、視窗暫時找不到但仍在重試上限內</li></ul> | 🚫 嚴禁將正常完成的業務標記為 WARNING。<br>🚫 嚴禁將超出重試上限的重開標為 WARNING。 |
| **`ERROR`** | **超限升級 (Recovery 6~7) 與不可逆嚴重故障**<br>（對應架構：超出重試上限升級 ProcessPort.relaunch 或交由 Supervisor 重啟） | <ul><li>**戰鬥卡死原地重試超過上限（> 2 次），升級殺進程重開（`battle_stall_max_retries_exceeded`）**</li><li>戰鬥超過 900 秒 Hard Timeout，觸發 relaunch</li><li>連續截圖失敗達上限，觸發進程重開</li><li>連續找不到視窗達到 5 次，發起 GameRelaunchSubflow</li><li>OCR 核心引擎損毀無法載入、未捕獲的例外拋出</li></ul> | 🚫 嚴禁將仍在有界重試上限內的自癒步驟標記為 ERROR。 |

---

## 3. 戰鬥卡死感知與像素差異決策 (Battle Stall Telemetry)

### 3.1 黑盒戰鬥觀測原則
依據 Greenfield-lite v1 第 4.8 節，戰鬥過程對外視為黑盒，由 `BattleSession` 擁有逾時與卡死邊界：
- **高頻即時像素差（`DEBUG`）**：
  主迴圈預設每秒執行 2 次，每輪計算之 `diff = abs(curr_signature - last_signature)` 嚴格以 `logging.debug()` 輸出，平日不造成終端洗屏。
- **自癒觸發事件化彙整（`WARNING`）**：
  連續達 30 秒血條無顯著變化判定卡死時，升級為 `logging.warning()` 並一次性附帶最後的紅血像素統計與差異數值：
  ```text
  🚨 [戰鬥卡死自癒] 偵測到血條連續 30.0 秒無顯著變化 (當前紅血像素: 1840, 最後 diff: 3 < 門檻 25)！執行原地「重新開始戰鬥」子流程 (第 1/2 次)...
  ```

---

## 4. 每日日誌輪轉與儲存架構 (Daily Rotation & Retention)

### 4.1 Profile 隔離儲存路徑
日誌儲存嚴格綁定角色 Profile 目錄：
```text
user_data/
├── <profile>/
│   ├── config.toml
│   └── logs/
│       ├── app.log              <-- 當前運行即時寫入的日誌
│       ├── app.log.2026-09-08   <-- 歷史歸檔日誌
│       └── app.log.2026-09-09
```

### 4.2 00:00 午夜自動換檔與 7 天保留
- 採用標準庫 `logging.handlers.TimedRotatingFileHandler`：
  - `when="midnight", interval=1`：每日 00:00 自動將前一日檔案命名歸檔，並建立今日新檔案，進程不需重啟。
  - `backupCount=7`：自動維護滾動窗口，只保留最近 **7 天** 的歷史日誌，過期檔案由底層自動清理。
  - `encoding="utf-8"`：保證 Windows 繁體中文與 Emoji 字符不發生編碼錯誤。

### 4.3 雙通道並存架構 (Dual-Channel Output)
系統 Root Logger 同步註冊兩個 Handler：
1. **Console StreamHandler**：即時輸出至使用者 CLI 終端機，層級由互動選單/命令列指定（預設 `INFO`）。
2. **Rotating FileHandler**：持久化至 `user_data/<profile>/logs/app.log`，確保 24/7 離線掛機記錄完整不丟失。

---

## 5. 配置覆蓋優先級 (Configuration Precedence)

$$\text{CLI 引數 (--log-level)} > \text{終端機選單互動 (Enter 保留)} > \text{Profile config.toml} > \text{全域 defaults.toml}$$

- **全域預設 ([config/defaults.toml](../../config/defaults.toml))**：
  ```toml
  [global]
  log_level = "INFO"
  log_retention_days = 7
  ```
- **Profile 持久化 ([user_data/\<profile\>/config.toml](../../user_data/native/config.toml))**：
  使用者的選擇會自動透過 `update_profile_config` 增量儲存，下次啟動自動帶入。
