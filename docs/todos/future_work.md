# 待辦事項與未來優化規劃 (Future Work & Project TODOs) 📋

本文件彙整《黑火遠征》專案的所有**待辦事項 (Active TODOs)**、**暫時擱置需求 (Shelved)** 與**已解決/已驗證項目 (Completed & Verified)**，作為長期維護與疊代之單一清單。

---

## 📌 一、 進行中與待開發項目 (Active TODOs)

### 1. 🔔 異常暫停與中斷即時通知 (Discord / LINE Webhook Notification)
- **需求背景**：當腳本在長掛機或黃金古國領地探索中進入手動暫停（Manual Pause）、觸發 Watchdog 卡死救援、或體力耗盡轉入退避模式時，能夠第一時間通報使用者。
- **規劃方向**：
  - 在 `config.py` 或 TOML 設定中增加 Webhook URL 配置。
  - 於 `GameStateMachine` 觸發暫停、異常重開與模式切換時，非同步發送訊息至 Discord 頻道或 LINE Notify。

### 2. 📦 分析如何變現
- **需求背景**：評估未來是否封裝為獨立 `.exe`、GUI 介面或 Web 儀表板，降低無 Python 環境用戶的使用門檻。
- **規劃方向**：
  - 現階段專注於掛機穩定性與核心邏輯完善；後續評估 PyInstaller / Nuitka 打包或 Electron / Tauri 介面封裝。

### 3. 🎨 終端 Config 設定呈現方式優化 (CLI / UI Presentation Overhaul)
- **需求背景**：目前 config.toml（一列一列），排版冗長且直觀度不足。

### 4. 🏛️ 全域架構審查與 AGENTS.md 規範對齊 (Technical Debt & Rule Auditing)
- **需求背景**：依據 `AGENTS.md` 的 5 大極簡原則與工程規範，全面排查既有代碼中的架構隱患，避免長期積累技術債。

法 60 行、巢狀 3 層、感知與決策分離」** 原則，排查出以下亟待重構的核心檔案：

| 檔案路徑 | 當前行數 | 規範限制 | 違反原則與架構隱患 |
| :--- | :---: | :---: | :--- |
| [`states/state_machine.py`](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py) | **1,593 行** | 300 行 | **嚴重超標**。狀態機身兼「狀態流轉」、「OCR 管理」、「全域例外處理」與「黃金古國/每日子流程協調」，職責過度混雜。 |
| [`states/handlers/navigation.py`](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py) | **907 行** | 300 行 | **嚴重超標**。雖抽離出 `SceneDetector`，但內部包含大量關卡滾動、島嶼點擊、頁籤切換等複雜巢狀分枝。 |
| [`main.py`](file:///e:/Side_Project/BlackfireCrusade_tool/main.py) | **783 行** | 300 行 | **超標**。主入口包含了 CLI 互動選單、Profile TOML 回寫、引數解析與多實例綁定，應抽離出 `cli_menu.py`。 |
| [`utils/daily_manager.py`](file:///e:/Side_Project/BlackfireCrusade_tool/utils/daily_manager.py) | **614 行** | 300 行 | **超標**。同時管理 Date Tag 重置、Boss CD、懸賞進度與未知任務正名，應拆分為獨立 Manager。 |
| 舊巨型測試包 (`test_behavioral_scenarios.py`, `test_state_machine_logic.py`) | **2,831 行 / 2,543 行** | 輕量化切分 | 違反 `AGENTS.md` 第 6 條「按業務領域輕量化拆分測試包 (Domain Slicing)」原則，存在舊的大型單體測試包。 |

### 5. ⚡ 沙盒環境 (Sandboxie-Plus) 運行延遲分析 (Sandbox Performance Analysis)
- **需求背景**：觀察到在 Sandboxie 沙盒實例中運行的腳本，反應速度與幀率相較原生主機實例有微幅延遲與變慢現象。
- **規劃方向**：
  - 分析 Win32 API 跨沙盒發送訊息 (`PostMessage` / `SendMessage`) 之 IPC 轉發開銷與焦點延遲。
  - 評估 `ScreenCapturer`（`mss` / `BitBlt`）在沙盒隔離視窗下的截圖幀率與延遲。
  - 測試多實例 CPU 競爭與進程優先級（Priority Boost）對沙盒實例的提速效果。

### 6. 🧠 記憶體洩漏與長期掛機效能衰減分析 (Memory Leak & Resource Health)
- **需求背景**：排查 24/7 長時間掛機時，是否有記憶體持續累積（Memory Leak）、GDI 物件未釋放或造成電腦逐漸變慢的問題。
- **規劃方向**：
  - 使用 `tracemalloc` / `memory_profiler` 監控長途運轉時 OpenCV `cv2.Mat` 影像矩陣、EasyOCR 辨識快取與 Win32 HWND / DC 控制代碼之生命週期。
  - 檢查主迴圈常駐物件與例外重試閉環是否有未被 GC 回收的暫存物件，確保連續數天掛機時資源保持恆定（Zero Leak）。

---

## ⏸️ 二、 暫時擱置與備用項目 (Shelved / Postponed)

> 💡 **說明**：以下項目經架構評估或已被現有更完善之機制覆蓋，暫時予以擱置，保留記錄以備未來參考。

### 1. 🔒 戰鬥結算稀有戰利品自動背包鎖定
- **原始構想**：在戰鬥結束結算畫面（`continue` 處）同時偵測到「獲得戰利品」時，前往背包進行特定裝備的鎖定防護。
- **擱置原因**：此功能目前已由**「背包 18 格 HSV 色彩分類與貴重品階反選保留機制」**完整覆蓋（藍/紫/橘/紅自動保留，灰/綠自動分解/銷毀），無需再額外進入背包點擊鎖定。

### 2. 📱 iPad 遠端操控 PC 腳本
- **原始構想**：使用 Windows PC 遠端控制 iPad 上的遊戲進行自動化。
- **擱置原因**：專案專注於 Steam PC 視窗端高解析度、高幀率與後台非搶占式掛機，目前無行動裝置跨端需求。

### 3. 🔄 城鎮點錯重來與容錯退回機制
- **原始構想**：手動或意外點錯建築時的全局重來。
- **擱置原因**：各城鎮 Handler 與子流程目前均已建立獨立的退場按鈕與 `exitfromhouse_and_to_town.png` 安全退回城鎮路徑。

### 4. 🛡️ 地下城誤入非目標地圖防呆容錯
- **原始構想**：手動按錯或誤入非目標地下城地圖時，偵測並點擊退出按鈕安全返回大廳重開。
- **擱置原因**：目前的 `mix` 混合模式、自適應卡片定位與貪婪選關已能全自動接管選關流程，無人工誤點問題。

---

## ✅ 三、 已解決與完成項目 (Completed & Verified)

### 1. 🛡️ 看門狗與例外自癒子系統 (Exception Watchdog & Game Relaunch)
*(詳細架構分析與除錯筆記請參閱 [exception_subsystem_architecture.md](../architecture/exception_subsystem_architecture.md))*
- [已完成並驗證] **5 次重試失敗直接重開自癒**：在 [UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py) 中，當 5 次嘗試仍無法消除畫面障礙時，直接喚起 `GameRelaunchSubflow` 殺進程並重啟遊戲。
- [已完成並驗證] **狀態轉移防抖與時間戳保護**：在 [GameStateMachine.transition_to](../../states/state_machine.py) 增加 `if self.current_state != new_state` 狀態防抖，防止相同狀態重複刷新 `last_state_change` 導致 Watchdog 失效。
- [已完成並驗證] **長任務真實進度回報 (`notify_ui_progress`)**：背包清理、長途出售與翻頁時定時回報有效 UI 進度，徹底消除假陽性卡死。
- [已完成並驗證] **COLLECT_ONLY 待機動態 CD 逾時與視窗崩潰檢查**：支援動態 CD 逾時保護與 HWND 遺失自動重啟。
- [已完成並驗證] **導航狀態 Watchdog 90 秒寬鬆門檻**：將 `STATE_NAVIGATING` 放寬至 90 秒，排除選關卡卡片與翻頁導航誤判。
- [已完成並驗證] **全螢幕意外彈窗對接 (Watchdog & Popup Recovery)**：支援輪盤 (`WheelOfFortuneSubflow`)、掃蕩盒 (`RaidBoxSubflow`) 與全域關閉 (`GenericAntiStuckSubflow`) 雙層救援。

### 2. 🎮 多實例與長掛機支援 (Multi-Instance & Long-Running AFK)
- [已完成並驗證] **Sandboxie-Plus Steam 雙開掛機與多實例目標選擇**：支援自動掃描本機/沙盒視窗（`[#] Blackfire Crusade [#]`）、互動選單以及 `--target` 快速參數。(參見指南 [sandboxie_dual_instance_guide.md](../guides/sandboxie_dual_instance_guide.md) 與 PARS 故事 [sandboxie_dual_instance_pars_story.md](../storys/sandboxie_dual_instance_pars_story.md))。
- [已完成並驗證] **5 天長掛機 3 大架構支柱**：
  1. **狀態持久化 ([DailyManager](../../utils/daily_manager.py))**：所有完成子流程與 08:05 重置週期自動記錄於 [daily_status.json](../../user_data/native/daily_status.json)，斷線重啟無縫接續進度。
  2. **全局看門狗與自癒修復 ([Watchdog](../../states/exceptions/watchdog.py) & [UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py))**：逾時自動清除遮擋或重啟。
  3. **點擊消失驗證閉環 (`click_and_wait_until_gone`)**：關鍵按鈕點擊後持續輪詢確認消失，防止狀態過早推進。
- [已完成並驗證] **長時間運轉資源與記憶體無洩漏** (1,000 次循環僅微增 1.09MB)。
- [已完成並驗證] **CPU 低功耗睡眠控管** (參見指南 [cpu_optimization.md](../guides/cpu_optimization.md))。
- [已完成並驗證] **Mode-Agnostic 地下城斷線與遊戲重開自癒** (全模式辨識 `dungeons/leave.png` 起點恢復探索)。

### 3. 🎯 視覺比對與座標適配 (Vision & Adaptive Coordinates)
- [已完成並驗證] **關卡選關優先按相似度而非亮度比例過濾**：解決選第 4 關誤點第 2 關周邊背景的 Bug。
- [已完成並驗證] **全域「任務完成」彈窗動態 Scale 適配**：領取按鈕依視窗高度比例動態縮放，解決非 1080p 解析度下點擊無效問題。
- [已完成並驗證] **領鑽石退出按鈕 Hover 焦點與消失確認**：後台點擊增加 `WM_MOUSEMOVE` 穩定焦點，持續比對 `quit.png` 消失後才轉移狀態。
- [已完成並驗證] **按鈕點擊消失驗證閉環 (`click_and_wait_until_gone`)**：防止過早推進狀態。

### 4. ⚔️ 掛機模式與流水線調度 (Pipelines & Modes)
- [已完成並驗證] **地下城全冷卻瀑布流混合模式 (`mix`)**：副本全在冷卻中時自動切換至 Stage 刷關，CD 結束即時切回地下城。
- [已完成並驗證] **體力耗盡全域自動退避 (`collect_only`)**：彈出 `no_bread.png` 時自動關閉彈窗，退回城鎮切換至待機模式 4.0 小時，結束後自動恢復原模式。
- [已完成並驗證] **單一權威來源 (SSOT) 與 Fail-Fast 配置**：所有模式配置由 `config.py` 驅動，參數缺失時立即拋出防禦性例外中斷。
- [已完成並驗證] **每日任務 08:05 四階梯流水線 (`DailyMasterPipeline`)**：
  - Tier 1: 城鎮速領 (寶箱 `chest` ➔ 抽卡 `hero_draw` ➔ 祭壇 `blood_altar` ➔ 珠寶 `jewelry_workshop`)。
  - Tier 2: 領主 Boss 討伐 (`lord_boss` 蜘蛛/惡靈計時器搶佔)。
  - Tier 3: 懸賞告示牌與動態任務 (`bulletin_board`)。
  - Tier 4: 動態退守刷關。
- [已完成並驗證] **背包已滿 18 格標題中心錨定與 2 格 (279px) 精準像素 Drag 位移銷毀**。
