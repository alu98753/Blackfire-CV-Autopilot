# PARS 開發故事：Sandboxie-Plus 雙開支援與多視窗自動化枚舉 🪟🎮

---

## 🎯 Purpose (開發目的)
在《黑火遠征》(Blackfire Crusade) 長期掛機中，單一 Steam 帳號僅有一份進度存檔。使用者擁有兩組 Steam 帳號並希望在同一台電腦上同時雙開掛機。
本任務目標為：
1. 驗證並建立基於 **Sandboxie-Plus** 的 Steam 雙帳號存檔隔離機制。
2. 擴充自動化架構，使腳本能自動辨識、枚舉所有在線遊戲實例（區分本機 vs 沙盒），並在 CLI 提供互動選單與參數快速指定，達成多實例精準綁定。

---

## 🛠️ Action (執行動作)

1. **實體路徑與存檔隔離深度檢測**：
   - 深入分析 Godot 引擎 (`libgodotsteam`) 的存檔結構，確認 Sandboxie-Plus 將沙盒實例的 `app_userdata\Blackfire Crusade` 與 Steam `userdata` 完整重導向至 `C:\Sandbox\...`，實現 100% 存檔物理隔離。
2. **多視窗枚舉與實例識別 (`utils/window.py`)**：
   - 實作 `find_all_game_windows()`：運用 `OpenInputDesktop` 與 `EnumDesktopWindows` 掃描桌面頂層視窗，擷取 HWND、PID、Client 解析度，並利用標題 `[#]` 標記辨識沙盒實例。
   - 擴充 `WindowHandle`：支援顯式傳入 `hwnd` 進行常態鎖定，並在 handle 失效時自動 fallback 至標題查找。
   - 實作 `select_game_window()`：支援 `--target` 參數（`sandbox`/`native`/`1`/`2`/`0xHWND`）與互動選單。
3. **控制器與啟動流程分層接線**：
   - 更新 [`ScreenCapturer`](../capture/screen.py) 與 [`MouseController`](../actions/mouse.py)，支援注入指定 `hwnd`。
   - 更新 [`SteamGameLauncher`](../utils/steam_launcher.py)，使 `is_game_open()` 支援指定 HWND 檢查，避免已開啟沙盒視窗時誤觸發 steam 直連啟動。
   - 重構 [`main.py`](../main.py) 與 [`run.bat`](../run.bat)，將視窗實例確認移至啟動第一順位。

---

## 📊 Result (成果與驗證)

1. **單元測試全數通過**：
   - 於 [`tests/test_window_handle.py`](../tests/test_window_handle.py) 新增 11 項測試案例，驗證顯式 HWND 綁定、沙盒標籤識別、CLI 參數選定與互動 prompt 流程，全數綠燈。
2. **實機雙開環境即時驗證**：
   - 同時運行本機 Steam (PID: 11128, HWND: `0x2707A8`) 與沙盒 Steam (PID: 10452, HWND: `0x0E0A96`)。
   - 腳本透過 `--target sandbox` / `--target native` 皆能精確鎖定正確視窗並順利獲取畫面。

---

## 💡 So What (價值與效益)

1. **零硬體負擔的雙帳號掛機**：相比資源消耗極大的虛擬機 (VM)，Sandboxie-Plus 幾乎零 CPU/RAM 損耗，大幅提升同機多開掛機的流暢度。
2. **操作零認知負擔**：單開時無感直接進入；雙開時自動以清晰格式列出 PID 與解析度選單，防呆且直覺。

---

## 🚀 Influence (後續影響與指引)

1. **多實例同時運行支援**：目前已具備視窗與 PID 鎖定能力，後續若要支援「兩隻腳本同時在同一台電腦並行掛機」，可結合 `PostMessage` 背景點擊徹底免除滑鼠焦點競爭。
2. **文檔更新**：完整操作與技術架構已整理於 [`docs/sandboxie_dual_instance_guide.md`](../sandboxie_dual_instance_guide.md)。
