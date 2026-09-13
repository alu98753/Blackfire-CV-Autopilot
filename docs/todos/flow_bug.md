我明明有設計 pop and push 的flow 但是當我指定只做 subflow 的時候 不知道為何他依然會去領鑽石跟麵包 思考怎麼修正


```
============================================================
常用啟動模式選單：
 1. 每日懸賞任務 (Daily Master 推薦): --backend --mode daily
 2. 混合模式 (副本 + 推關退守):       --backend --mode mix
 3. 貪婪地下城模式:                 --backend --mode dungeon
 4. 普通關卡模式:                 --backend --mode stage
 5. 背包整理模式:                 --backend --mode bag_clean
 6. 定時領取體力與鑽石:           --backend --mode collect_only
 7. 領地探索模式 (黃金古國):         --backend --mode golden_empire
 8. Dev 城鎮子流程獨立測試:       --subflow 選單 (獨立測試單一建築)
 9. 查看遊戲理智公約:             顯示防制衝動消費心態指引
------------------------------------------------------------
參數說明：
 --mode [名稱]      : 設定運行主模式 (daily / mix / dungeon / stage / golden_empire)
 --target [目標]    : 雙開指定視窗 (1 / 2 / native / sandbox)
 --subflow [子任務]  : 發起獨立子流程測試 (chest / blood_altar / lord_boss)
 --backend          : 啟用後台點擊與截圖 (推薦)
 --interval [秒]    : 偵測時間間隔 (預設: 0.5)
============================================================

請輸入選單編號 [1-9] 或自訂參數 (直接 Enter 預設為 1: Daily Master): --backend --subflow bulletin_board

Select target instance for this supervised run:
  1. Native Steam - default
  2. Sandbox Steam
Target [1-2]: 2

[*] 正在啟動腳本，參數: --backend --subflow bulletin_board --target sandbox --profile sandbox
[*] Hotkeys: Ctrl+Space pause/resume; Ctrl+C restarts; Ctrl+Shift+Q stops and returns to this menu.
------------------------------------------------------------
2026-09-13 12:18:41,270 [INFO] [Supervisor] Starting bot process: E:\Side_Project\BlackfireCrusade_tool\.venv\Scripts\python.exe E:\Side_Project\BlackfireCrusade_tool\main.py --backend --subflow bulletin_board --target sandbox --profile sandbox --incident-session-id a96f646c-d7a4-46de-8658-185064416c60
2026-09-13 12:18:42,406 [INFO] ⚙️ [ProfileConfig] 成功套用角色專屬覆蓋配置: user_data/sandbox/config.toml

請選擇終端機日誌顯示等級 (Log Level)：
 1) INFO    - 標準模式 (推薦：顯示狀態轉移、重要事件、警告與錯誤) [目前偏好]
 2) DEBUG   - 除錯模式 (顯示完整細節：模板比對分數、像素差異、OCR 座標與耗時)
 3) WARNING - 靜音模式 (僅在發生異常、背包滿、卡死重試時提示)
 4) ERROR   - 極致安靜 (僅在系統崩潰或致命錯誤時輸出)
請輸入數字 [1-4] (直接 Enter 保留 1):
🛠️ [Dev 測試模式] 直接發起城鎮子流程: ['bulletin_board'] (免選關卡，直通城鎮)

請選擇要【保留/領取】的最低裝備品質（該品質及以上皆會被保留，背包滿時優先拿取）：
 1) 綠色 (優秀)
 2) 藍色 (精良) - 目前 TOML 預設
 3) 紫色 (史詩)
 4) 橘黃色 (傳奇)
請輸入數字 [1-4] (直接 Enter 保留 2):

請選擇可【大量分解】的最高裝備品質（該品質及以下在大廳時會被自動大量分解）：
 1) 灰色 (普通)
 2) 綠色 (優秀)
 3) 藍色 (精良)
 4) 紫色 (史詩) - 目前 TOML 預設
 5) 橘黃色 (傳奇)
請輸入數字 [1-5] (直接 Enter 保留 4):
2026-09-13 12:18:47,134 [INFO] [SteamGameLauncher] 開始執行 ensure_game_ready 檢查與啟動流程 (force_relaunch=False)...
2026-09-13 12:18:47,135 [INFO] ✅ 視窗已開啟，執行視窗定位與最大化全螢幕...
2026-09-13 12:18:47,135 [INFO] 🔍 [ScreenCapturer Debug] 視窗 HWND: 1051532, 當前 Rect: (-8, -8, 1928, 1040), 中心點: (960, 516), 已最大化: True | 目標 Monitor 2 範圍: (0, 0)~(1920, 1080), 已在目標螢幕: True
2026-09-13 12:18:47,135 [INFO] ✅ [ScreenCapturer] 遊戲視窗已在 Monitor 2 上且已處於最大化狀態。
2026-09-13 12:18:47,136 [INFO] 🎉 視窗已成功定位至指定螢幕並最大化！立即交由主狀態機接管。
============================================================
 🚀 Blackfire Crusade 自動掛機輔助腳本啟動 🚀
============================================================
[*] 目標視窗標題: [#] Blackfire Crusade [#] (HWND: 0x100b8c)
[*] 目標顯示器編號: Monitor 2 (由 Profile TOML 指定)
[*] 畫面偵測間隔: 0.5 秒
[*] 當前掛機模式: 懸賞告示牌 (mix)
============================================================
[*] 自動領體力功能: 啟用 (啟動時與每 30 分鐘執行一次)
============================================================
2026-09-13 12:18:47,138 [INFO] 📂 [DailyManager] 成功載入日常持久化狀態檔: user_data\sandbox\daily_status.json
2026-09-13 12:18:47,144 [WARNING] ⚠️ 懸賞任務 '惡靈的終章' 無法對應到已知規則庫 (未定義任務)，回傳 None 紀錄至 unknown_quests。
2026-09-13 12:18:47,145 [INFO] 📂 [DailyManager] 成功綁定角色狀態檔: user_data/sandbox/daily_status.json
2026-09-13 12:18:47,164 [INFO] ⚙️ [OCR Preload] 正在背景預熱載入 EasyOCR 辨識模型 (['ch_tra', 'en'])...
2026-09-13 12:18:47,169 [INFO] 📦 [PopupRecovery] 已註冊 Exception Subflow: wheel_of_fortune_subflow
2026-09-13 12:18:47,169 [INFO] 📦 [PopupRecovery] 已註冊 Exception Subflow: raid_box_subflow
2026-09-13 12:18:47,170 [INFO] ============================================================
2026-09-13 12:18:47,170 [INFO] 🏛️ 【城鎮任務流水線 - 任務總覽儀表板】 🏛️
2026-09-13 12:18:47,171 [INFO] ============================================================
2026-09-13 12:18:47,171 [INFO]   1. [bulletin_board] 懸賞告示牌        : 🟢 待執行 (Enabled)
2026-09-13 12:18:47,171 [INFO] ============================================================
2026-09-13 12:18:47,172 [INFO] ============================================================
2026-09-13 12:18:47,172 [INFO] 🎯 [城鎮流水線進度] 彈出並切換至任務: [bulletin_board] (懸賞告示牌)
2026-09-13 12:18:47,173 [INFO] 📌 剩餘待執行子流程 (0 個): []
2026-09-13 12:18:47,173 [INFO] ============================================================
2026-09-13 12:18:47,173 [INFO] 🧭 [城鎮流水線] 已建立 REACH_TOWN precondition intent；入口成立前保留目前活動 config。
[+] 初始化成功！請確認您的遊戲視窗非最小化，且維持在畫面上。
[+] 快捷鍵提示：在終端機或遊戲視窗按 [Ctrl + Space] 隨時暫停/繼續；按 [Ctrl + C] 終止程式。
[*] 將在 3 秒後開始偵測...
2026-09-13 12:18:50,359 [INFO] 🔄 [HotReload] 已動態套用 config/exception_features.json
2026-09-13 12:18:50,641 [INFO] ⏰ 距離上次領鑽石已滿 120 分鐘，觸發自動領鑽石。
2026-09-13 12:18:50,671 [INFO] ⏰ 距離上次領體力已滿 30 分鐘，觸發自動領體力。
2026-09-13 12:18:51,085 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-13 12:18:51,101 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-13 12:18:51,102 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-13 12:18:53,367 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9996，相對亮度比: 1.00，座標: (85, 917)
2026-09-13 12:18:53,370 [INFO] 🔄 狀態轉移: UNKNOWN -> NAVIGATING
2026-09-13 12:18:55,441 [INFO] ⚙️ 正在載入 EasyOCR 辨識模型 (['ch_tra', 'en']) (使用 CPU)...
2026-09-13 12:18:55,443 [WARNING] Using CPU. Note: This module is much faster with a GPU.
2026-09-13 12:18:57,122 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9996，相對亮度比: 1.00，座標: (85, 917)
2026-09-13 12:18:57,488 [INFO] 成功匹配模板 'diamond.png'！相似度: 0.9999，相對亮度比: 2.26，座標: (1385, 66)
2026-09-13 12:18:57,725 [INFO] [IntentRouting] intent=collect_diamond scene=town action=open_diamond reason=diamond_entry_ready progress=idle
2026-09-13 12:18:57,726 [INFO] 🔄 狀態轉移: NAVIGATING -> DIAMOND_COLLECTION
2026-09-13 12:18:58,084 [INFO] 成功匹配模板 'diamond.png'！相似度: 0.9999，相對亮度比: 2.26，座標: (1385, 66)
2026-09-13 12:18:58,087 [INFO] 💎 領鑽石：在畫面偵測到鑽石按鈕 [0.9999]，點擊打開領取畫面。
2026-09-13 12:18:58,323 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 12:18:58,330 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 12:18:59,990 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.00，座標: (1629, 205)
2026-09-13 12:19:00,276 [INFO] 💎 領鑽石：無免費按鈕，累計檢測次數: 1/3...
2026-09-13 12:19:00,586 [INFO] 💎 領鑽石：未偵測到任何彈窗內元素，累計未發現次數: 1/3...
2026-09-13 12:19:01,095 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.00，座標: (1629, 205)
2026-09-13 12:19:01,418 [INFO] 💎 領鑽石：無免費按鈕，累計檢測次數: 2/3...
E:\Side_Project\BlackfireCrusade_tool\.venv\Lib\site-packages\torch\ao\nn\quantized\dynamic\modules\rnn.py:162: UserWarning: torch.quantize_per_tensor, torch.quantize_per_channel and other quantized tensor creation functions that produce tensors with dtype torch.quint8, torch.qint8, and torch.qint32 are deprecated and will be removed in a future PyTorch release. Please see https://github.com/pytorch/pytorch/issues/184982 for more information. (Triggered internally at C:\actions-runner\_work\pytorch\pytorch\aten\src\ATen\quantized\Quantizer.cpp:116.)
  w_ih = torch.quantize_per_tensor(
2026-09-13 12:19:01,771 [INFO] 💎 領鑽石：未偵測到任何彈窗內元素，累計未發現次數: 1/3...
2026-09-13 12:19:01,964 [INFO] ✅ [OCR Preload] EasyOCR 辨識模型預熱載入完成！
2026-09-13 12:19:02,326 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.00，座標: (1629, 205)
2026-09-13 12:19:02,573 [INFO] 💎 領鑽石：無免費按鈕，累計檢測次數: 3/3...
2026-09-13 12:19:02,573 [INFO] 💎 領鑽石：鑽石視窗已開啟且連續 3 幀無免費按鈕 (處於冷卻)，開始精確讀取冷卻倒數時間...
E:\Side_Project\BlackfireCrusade_tool\.venv\Lib\site-packages\torch\utils\data\dataloader.py:759: UserWarning: 'pin_memory' argument is set as true but no accelerator is found, then device pinned memory won't be used.
  super().__init__(loader)
2026-09-13 12:19:04,356 [INFO] 💎 領鑽石：成功辨識出精確剩餘時間: "00:37:04" (37 分 4 秒，信心度: 0.6369)
2026-09-13 12:19:04,357 [INFO] ⏰ 已將下一次自動領鑽石排程推遲到 2224 秒後。
2026-09-13 12:19:04,357 [INFO] 💎 領鑽石：偵測到退出按鈕 [common/quit.png] (0.9816)，嘗試點擊關閉視窗。
2026-09-13 12:19:04,504 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 12:19:04,513 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 12:19:05,229 [INFO] 💎 領鑽石：退出按鈕已消失，確認視窗已關閉。領鑽石流程結束。
2026-09-13 12:19:05,230 [INFO] 🔄 狀態轉移: DIAMOND_COLLECTION -> NAVIGATING
2026-09-13 12:19:08,459 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9996，相對亮度比: 1.00，座標: (85, 917)
2026-09-13 12:19:08,859 [INFO] 成功匹配模板 'diamond.png'！相似度: 0.9999，相對亮度比: 2.26，座標: (1385, 66)
2026-09-13 12:19:09,086 [INFO] [IntentRouting] intent=collect_bread scene=town action=enter_lobby reason=bread_enter_lobby progress=idle
2026-09-13 12:19:09,307 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 12:19:09,316 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 12:19:14,014 [INFO] [FullRelocalize] reason=uncommitted_route expected_tab=None candidates=[] winner=None is_conflict=False elapsed=1.578s
2026-09-13 12:19:14,089 [INFO] [IntentRouting] intent=collect_bread scene=unknown action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.7s deadline=64296.484 attempt=1
2026-09-13 12:19:17,258 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-13 12:19:17,596 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-13 12:19:18,577 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (664, 908)
2026-09-13 12:19:19,001 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9310，相對亮度比: 1.07，座標: (657, 911)
2026-09-13 12:19:19,425 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9163，相對亮度比: 0.96，座標: (810, 909)
2026-09-13 12:19:19,845 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9760，相對亮度比: 1.01，座標: (811, 911)
2026-09-13 12:19:20,292 [INFO] 成功匹配模板 'domains/Domains_entry_after.png'！相似度: 0.9016，相對亮度比: 0.95，座標: (958, 913)
2026-09-13 12:19:20,663 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.9598，相對亮度比: 1.01，座標: (960, 919)
2026-09-13 12:19:21,076 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8854，相對亮度比: 0.94，座標: (1111, 914)
2026-09-13 12:19:21,499 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.9584，相對亮度比: 1.01，座標: (1106, 910)
2026-09-13 12:19:21,906 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.9399，相對亮度比: 0.94，座標: (1257, 914)
2026-09-13 12:19:22,314 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1256, 913)
2026-09-13 12:19:22,316 [INFO] [FullRelocalize] reason=uncommitted_route expected_tab=None candidates=[('stage', '0.9999')] winner=stage is_conflict=False elapsed=4.156s
2026-09-13 12:19:22,394 [INFO] [IntentRouting] intent=collect_bread scene=stage_select action=open_bread reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=13.0s deadline=64296.484 attempt=1
2026-09-13 12:19:22,395 [INFO] 🔄 狀態轉移: NAVIGATING -> BREAD_COLLECTION
2026-09-13 12:19:24,638 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-13 12:19:24,986 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-13 12:19:25,969 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (664, 908)
2026-09-13 12:19:26,400 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9310，相對亮度比: 1.07，座標: (657, 911)
2026-09-13 12:19:26,830 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9163，相對亮度比: 0.96，座標: (810, 909)
2026-09-13 12:19:27,233 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9760，相對亮度比: 1.01，座標: (811, 911)
2026-09-13 12:19:27,671 [INFO] 成功匹配模板 'domains/Domains_entry_after.png'！相似度: 0.9016，相對亮度比: 0.95，座標: (958, 913)
2026-09-13 12:19:28,040 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.9598，相對亮度比: 1.01，座標: (960, 919)
2026-09-13 12:19:28,444 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8854，相對亮度比: 0.94，座標: (1111, 914)
2026-09-13 12:19:28,867 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.9584，相對亮度比: 1.01，座標: (1106, 910)
2026-09-13 12:19:29,269 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.9399，相對亮度比: 0.94，座標: (1257, 914)
2026-09-13 12:19:29,712 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1256, 913)
2026-09-13 12:19:29,716 [INFO] [FullRelocalize] reason=legacy_or_unspecified expected_tab=None candidates=[('stage', '0.9999')] winner=stage is_conflict=False elapsed=4.172s
2026-09-13 12:19:30,071 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-13 12:19:30,074 [INFO] 🍞 領體力：在大廳偵測到體力按鈕 [1.0000]，點擊打開體力視窗。
2026-09-13 12:19:30,245 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 12:19:30,254 [INFO] 🎯 [DebugVisu
```