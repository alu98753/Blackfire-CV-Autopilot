# Notification System & Standalone Testing Guide 📢

本文件說明本專案六角架構通知系統 ([`runtime/notifier.py`](../../../runtime/notifier.py)) 的配置方式、架構設計以及免啟動遊戲的獨立實體測試方法。

---

## 一、 配置層級與真理源 (SSOT & Precedence)

通知系統支援多層級配置覆蓋，優先順序由高至低如下：

1. **環境變數**：`DISCORD_WEBHOOK_URL`（最高優先級，適用於 CI/CD 或 Docker 環境）
2. **Profile 專屬覆蓋 ([`user_data/<profile>/config.toml`](../../../user_data/native/config.toml))**：
   ```toml
   [notification.discord]
   enabled = true
   webhook_url = "https://discord.com/api/webhooks/..."
   ```
3. **全域預設 ([`config/defaults.toml`](../../../config/defaults.toml))**：
   ```toml
   [notification]
   [notification.discord]
   enabled = true
   webhook_url = ""
   timeout_seconds = 3.0
   ```

目前原生實例 (`user_data/native/config.toml`) 與沙盒實例 (`user_data/sandbox/config.toml`) 均已預先配置專屬的 Discord Webhook URL。

---

## 二、 獨立實體傳訊測試 (Standalone Testing & Dry-Run)

本通知系統設計完全與遊戲視窗與 Steam 啟動流程解耦，且**預設為 Dry-Run 預覽模式**（不送出任何網路封包），唯有明確附帶 `--live` 旗標時才會真正執行 HTTP POST 到 Discord。

### 方式 1：Dry-Run 格式預覽（預設安全，零網路干擾）

不需要開啟遊戲，也不會打擾 Discord 伺服器，只在終端機輸出即時渲染的 JSON Payload 預覽：

```powershell
.venv\Scripts\python main.py --profile native --test-notify all
.venv\Scripts\python main.py --profile native --test-notify milestone1
.venv\Scripts\python main.py --profile native --test-notify milestone2
.venv\Scripts\python main.py --profile native --test-notify deadline
```

### 方式 2：真實網路發送（明確指定 `--live`）

當需要人工檢驗 Discord 頻道上的排版與顏色時，加上 `--live` 旗標：

```powershell
.venv\Scripts\python main.py --profile native --test-notify all --live
.venv\Scripts\python main.py --profile native --test-notify milestone1 --live
.venv\Scripts\python main.py --profile native --test-notify milestone2 --live
.venv\Scripts\python main.py --profile native --test-notify deadline --live
```

### 方式 3：使用底層模組直接測試

若想跳過 Profile 讀取，直接測試特定 Webhook URL：

```powershell
.venv\Scripts\python -m runtime.notifier --url "https://discord.com/api/webhooks/..." --type milestone1 --live
```

---

## 三、 通知類型與 Embed 訊息格式

系統通知嚴格遵循 [`docs/todos/feat-daily-status-notifier.md`](../../todos/feat-daily-status-notifier.md) 的語意契約：

| 類型 | 視覺標籤 | 顏色代碼 | 語意定義 |
| :--- | :--- | :--- | :--- |
| **Milestone Notification** | `AUTOMATION_HEALTHY` | 綠色 (`0x2ECC71`) | 宣告特定業務階段達成，系統運作正常，無需人工介入 (`NO_ACTION_REQUIRED`)。 |
| **Operator Action Required** | `OPERATOR_ACTION_REQUIRED` | 紅色 (`0xE74C3C`) | 宣告自動自癒階梯耗盡，發生不可恢復故障，需要操作員接管遠端。 |

---

## 四、 執行緒安全與網路故障防護

1. **Non-blocking 背景執行**：日常業務呼叫 `notify_milestone()` 或 `notify_alarm()` 預設採 Daemon 執行緒非同步發送，主迴圈零等待。
2. **有界超時與錯誤吞吐**：HTTP 請求預設設置 `timeout_seconds = 3.0`。若遇到 Discord 伺服器離線、網路斷線或 URL 失效，系統僅記錄 `logging.warning`，**絕不拋出例外，絕不干擾遊戲主狀態機調度**。
