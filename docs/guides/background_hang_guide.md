# 雙螢幕環境後台掛機與定位技術指南 🖥️

本指南記載了在雙螢幕（延伸螢幕）環境下，實現不干擾實體滑鼠進行自動化掛機的技術方案評估與設計細節。

---

## 方案一：虛擬機器 (VM) 隔離方案（免程式碼變更）

### 1. 運作原理
利用虛擬化軟體（如 VMware Workstation Player、VirtualBox 或 Windows 內建的 Hyper-V）在電腦中開闢一個虛擬作業系統。將遊戲與 Python 掛機腳本部署於虛擬機內運行。

### 2. 優缺點分析
* **優點**：
  * **零改動成本**：腳本維持使用當前已通過所有測試的 PyAutoGUI 控制，不需要重構任何滑鼠點擊與截圖 API。
  * **完全隔離**：虛擬機擁有獨立的虛擬顯示卡與虛擬滑鼠，在內部點擊與拖曳完全不影響宿主機的實體滑鼠游標。
  * **可後台最小化**：虛擬機視窗可以直接最小化，或拉到第二螢幕的背景。
* **缺點**：
  * 系統資源消耗較大（通常需要額外分配 2~4 GB 記憶體與 2 核心 CPU）。

---

## 方案二：Windows API 後台控制方案 (PostMessage)

這是直接在主系統上實現「不搶占滑鼠」的開發方案。需要將實體操作（PyAutoGUI）升級為後台視窗控制訊息（Win32 API）。

### 1. 跨多螢幕 (延伸螢幕) 的動態定位
當使用者在主螢幕與第二螢幕之間隨意拖曳遊戲視窗、甚至調整顯示器的上下左右佈局時，程式可利用 Windows 原生 API 進行動態定位：
* **`win32gui.FindWindow(None, title)`**：取得遊戲視窗控制代碼 `hwnd`。
* **`win32gui.GetWindowRect(hwnd)`**：獲取視窗在虛擬螢幕座標系下的絕對邊界 `(left, top, right, bottom)`。不論遊戲在主螢幕還是延伸螢幕（例如在左邊螢幕呈現負數，或在右邊螢幕呈現大於主解析度的數值），此坐標均為系統中的真實絕對位置。
* **`win32api.MonitorFromWindow(hwnd, flags)`**：動態辨識視窗當前最主要座落於哪一個顯示器 `hMonitor` 上。
* **`win32api.GetMonitorInfo(hMonitor)`**：讀取該螢幕的資訊，包含設備名稱（如 `\\.\DISPLAY1` 為主螢幕，`\\.\DISPLAY2` 為延伸螢幕）、總解析度範圍等。

### 2. 後台點擊模擬 (Win32 PostMessage)
* 原理：不移動作業系統全域的滑鼠游標，而是將滑鼠點擊事件以 Windows 訊息直接發送給遊戲視窗句柄。
* 實作細節：
  ```python
  # 相對於遊戲視窗客戶區的相對座標 (x, y)
  lParam = win32api.MAKELONG(relative_x, relative_y)
  
  # 發送按下滑鼠左鍵訊息
  win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
  time.sleep(0.04) # 保留 40ms 的物理間隔防漏點
  # 發送釋放滑鼠左鍵訊息
  win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
  ```
* 缺點：若遊戲屬於硬體加速（如 Direct3D、Vulkan）或安全防護較嚴格的 Steam PC 遊戲，可能不接受 `PostMessage` 後台滑鼠訊息。

### 3. 多螢幕後台截圖的挑戰與解決方案
* 當遊戲位於延伸螢幕，或被其他視窗遮擋時，普通的 PyAutoGUI 截圖會失效。
* **解決方案**：
  * **前台截圖 + 跨螢幕裁剪 (保險方案)**：只要遊戲不被完全遮擋，即使放在延伸螢幕，仍然可以使用跨螢幕絕對座標 `GetWindowRect` 來擷取對應區域。
  * **Win32 拷貝 DC (後台方案)**：使用 `GetWindowDC(hwnd)` 與 `BitBlt` 進行後台視窗渲染表面拷貝。此方法即使視窗在後台被遮住，依然可以拿到最新的遊戲畫面（但若視窗被最小化則會停止渲染，部分 Unity 遊戲在 `BitBlt` 下會截出黑底，需透過實機測試驗證）。
