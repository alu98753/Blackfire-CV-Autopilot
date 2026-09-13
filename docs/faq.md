# 掛機腳本與運行維護常見問題 (FAQ)

本文件說明使用該腳本時的常見問答。

---

## 一、程式碼更新與執行期生效 (Code Reload & Runtime)

### Q1：點開 `run.bat` 後，如果在啟動腳本前修改了 `main.py` 或其他 `.py` 程式碼，能吃到更新嗎？
可以。

`run.bat` 是一個 Windows 批次檔，在選單停駐（等待輸入選項或按 Enter）時，Python 直譯器尚未啟動。當確認選單並進入執行階段時，批次檔才會調用 `python.exe` 建立全新的子進程。Python 直譯器是在進程啟動時讀取磁碟上的 `.py` 檔案並編譯載入，因此在點下啟動前所做的代碼修改都會正常生效。

### Q2：使用 `Ctrl+Shift+Q` 退出並重新啟動後，能吃到代碼更新嗎？
可以。

`Ctrl+Shift+Q` 是專用的手動退出熱鍵。觸發時，`main.py` 工作進程會回傳專用退出代碼（Exit Code 75），外部的 `runtime.supervisor` 守護進程收到後會乾淨結束，整個 Python 進程完全終止並釋放資源，控制權交回 `run.bat` 的重新啟動詢問選單。若在選單處按 Enter 重新啟動，會啟動全新的 Python 進程，重新載入磁碟上的所有程式碼，因此會吃到最新修改。

同理，若在運行中按下 `Ctrl+Q`（快速熱重啟），Supervisor 會終止舊子進程並透過 `subprocess.Popen` 啟動新的 Python 子進程，同樣會重新讀取磁碟檔案。

唯一的例外是：若 Python 程式正在持續運行中，尚未終止或重開進程，已載入記憶體的 Python 模組不會自動動態重載。

---

## 二、進程控制與熱鍵操作 (Process & Hotkeys)

### Q3：想完全退出掛機程式，不要觸發自動重啟，應該如何操作？
請使用鍵盤熱鍵 `Ctrl+Shift+Q`。

Supervisor 具備崩潰自癒與行程重啟機制，直接按下 `Ctrl+C` 會被視為中斷恢復請求（Exit Code 42），Supervisor 會自動嘗試重新拉起進程。若要徹底停止掛機，請按下 `Ctrl+Shift+Q`，程式會回到批次檔選單，此時在終端輸入 `Q` 即可安全離開。

### Q4：掛機常用全域熱鍵有哪些？
* `Ctrl + Space`：暫停或繼續目前的自動化操作。
* `Ctrl + Q`：要求 Supervisor 立即以快取設定快速熱重啟 Worker（保留目前執行目標與 profile）。
* `Ctrl + Shift+Q`：手動完全退出 Worker 與 Supervisor，安全返回 `run.bat` 主選單。

---

## 三、故障排除與排錯 (Troubleshooting)

### Q5：執行 `run.bat` 時出現 `'instance' is not recognized` 或類似語法錯誤？
通常表示使用了舊版或換行格式異常的 `run.bat`。請關閉該終端視窗，確認工作區最新檔案後重新雙擊執行 `run.bat`，避免在已經出錯的同一個終端 session 繼續執行。

### Q6：啟動後一開始就顯示 `heartbeat stale`（心跳過期）警示？
Supervisor 目前只採納本次子進程啟動後所寫入的心跳時間戳記。若啟動時出現此警示，請檢查啟動參數是否帶有相符的 `--target` 與 `--profile`，並確認對應實例的心跳檔案（如 `scratch/runtime/heartbeat_native.json`）具備正常寫入權限。
