了解她莫名其妙觸發watch dog的原因 
1. 不知道為何之前90s可以但現在莫名其妙會太短
2. 這個時間應該要在toml可以配置


```
tor 1: True
2026-09-09 22:00:03,669 [INFO] 🎉 視窗已成功定位至指定螢幕並最大化！立即交由主狀態機接管。
2026-09-09 22:00:03,670 [INFO] 🔄 [GameRelaunchSubflow] 重啟完成！轉移狀態至 STATE_UNKNOWN 交由全域掃描與 LoginFlow 接管...
2026-09-09 22:00:03,670 [INFO] 🔄 狀態轉移: POPUP_RECOVERY -> UNKNOWN
2026-09-09 22:00:03,967 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-09 22:00:03,979 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-09 22:00:03,979 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-09 22:00:04,891 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.2901，座標: None
2026-09-09 22:00:04,949 [INFO] 🔍 [除錯] 比對尋路按鈕 'dungeons/dungeon.png'，最高相似度: 0.2266，座標: None
2026-09-09 22:00:05,875 [INFO] ❓ 未能辨識場景證據，保持 UNKNOWN 並等待下一幀 (1/5)。
2026-09-09 22:00:06,123 [INFO] 成功匹配模板 'login/login.png'！相似度: 0.9889，相對亮度比: 1.00，座標: (770, 393)
2026-09-09 22:00:06,124 [INFO] 🔑 偵測到遊戲登入主畫面 [login.png] (信心度: 0.9889)。
2026-09-09 22:00:06,354 [INFO] 成功匹配模板 'login/login_confirm.png'！相似度: 0.9409，相對亮度比: 0.99，座標: (767, 595)
2026-09-09 22:00:06,354 [INFO] 👉 成功定位「開始冒險」按鈕 [login_confirm.png] (信心度: 0.9409)，進行點擊...
2026-09-09 22:00:06,473 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-09 22:00:06,484 [INFO] 🎯 [DebugVisualizer] 已成功將紅色空心診斷標記 (ROI/BBox/Click) 寫入 debug_click.png
2026-09-09 22:00:06,576 [INFO] 🔍 [登入流程] 開始確認城鎮大門 [common/door.png] 是否可見 (Click Until 機制啟動)...
2026-09-09 22:00:10,626 [INFO] 成功匹配模板 'login/login.png'！相似度: 0.7832，相對亮度比: 1.07，座標: (770, 393)
2026-09-09 22:00:10,850 [INFO] ▶️ [登入流程 Click Until 第 2 次] 偵測到仍停留在登入畫面，採用相對座標再次點擊...
2026-09-09 22:00:10,911 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-09 22:00:10,919 [INFO] 🎯 [DebugVisualizer] 已成功將紅色空心診斷標記 (ROI/BBox/Click) 寫入 debug_click.png
2026-09-09 22:00:12,505 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.7985，相對亮度比: 0.11，座標: (68, 719)
2026-09-09 22:00:12,506 [INFO] 🟢 [登入流程] 登入後畫面載入完成！偵測到畫面特徵 [common/door.png] (相似度: 0.7985)，準備進入全域狀態定位！
2026-09-09 22:00:12,507 [INFO] 🔄 [登入流程] 畫面載入完畢，立即發起全域狀態定位 (detect_current_state)...
2026-09-09 22:00:12,547 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-09 22:00:12,561 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-09 22:00:12,561 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-09 22:00:13,839 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.7985，座標: None
2026-09-09 22:00:13,906 [INFO] 🔍 [除錯] 比對尋路按鈕 'dungeons/dungeon.png'，最高相似度: 0.2692，座標: None
2026-09-09 22:00:14,970 [INFO] ❓ 未能辨識場景證據，保持 UNKNOWN 並等待下一幀 (2/5)。
2026-09-09 22:00:15,216 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-09 22:00:15,227 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-09 22:00:15,227 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-09 22:00:15,403 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9464，相對亮度比: 0.98，座標: (766, 542)
2026-09-09 22:00:15,406 [INFO] 👉 [全域防護] 偵測到可能遮擋的彈窗按鈕 [common/confirm.png] (相似度: 0.9464)，優先點擊關閉...
2026-09-09 22:00:15,536 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-09 22:00:15,545 [INFO] 🎯 [DebugVisualizer] 已成功將紅色空心診斷標記 (ROI/BBox/Click) 寫入 debug_click.png
2026-09-09 22:00:16,416 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-09 22:00:16,425 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-09 22:00:16,426 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-09 22:00:17,923 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-09 22:00:17,924 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.9543，座標: (68, 719)
2026-09-09 22:00:17,924 [INFO] 🔄 狀態轉移: UNKNOWN -> NAVIGATING
2026-09-09 22:00:18,479 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8038，相對亮度比: 0.81，座標: (1115, 764)
2026-09-09 22:00:18,813 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-09 22:00:19,564 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-09 22:00:19,808 [INFO] 成功匹配模板 'diamond.png'！相似度: 0.9750，相對亮度比: 2.25，座標: (1107, 52)
2026-09-09 22:00:20,105 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=primary_enter_lobby progress=idle
2026-09-09 22:00:20,279 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-09 22:00:20,288 [INFO] 🎯 [DebugVisualizer] 已成功將紅色空心診斷標記 (ROI/BBox/Click) 寫入 debug_click.png
2026-09-09 22:00:23,819 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.4s deadline=3912.156 attempt=4
2026-09-09 22:00:24,898 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:25,848 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:26,036 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:26,743 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-09 22:00:27,032 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-09 22:00:27,081 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.7s deadline=3912.156 attempt=4
2026-09-09 22:00:27,541 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-09 22:00:27,543 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9805)，點擊按鈕中心座標 (649, 1818)。
2026-09-09 22:00:27,679 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-09 22:00:27,689 [INFO] 🎯 [DebugVisualizer] 已成功將紅色空心診斷標記 (ROI/BBox/Click) 寫入 debug_click.png
2026-09-09 22:00:28,843 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:29,917 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:30,151 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:30,969 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:31,295 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:31,354 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:31,586 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:32,498 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:33,530 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:33,737 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:34,596 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:34,938 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:34,998 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:35,251 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:36,245 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:37,265 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:37,484 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:38,236 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:38,556 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:38,619 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:38,860 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:39,814 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:40,795 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:41,011 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:41,756 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:42,085 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:42,141 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:42,395 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:43,428 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:44,544 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:45,636 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:45,974 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:46,035 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:46,286 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:47,281 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:48,423 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:48,640 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:49,401 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:49,754 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:49,819 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:50,047 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:50,964 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:51,901 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:52,087 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:52,776 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:53,088 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:53,137 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:53,342 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:54,205 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:55,103 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:55,283 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:00:55,977 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:56,268 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:56,320 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:56,523 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:00:57,341 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:58,339 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:00:59,280 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:00:59,568 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:00:59,621 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:00:59,850 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:00,786 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:01,781 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:01,995 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:02,753 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:03,115 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:03,183 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:03,439 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:04,300 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:05,222 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:05,416 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:06,180 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:06,479 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:06,531 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:06,735 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:07,613 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:08,494 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:08,680 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:09,450 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:09,791 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9443，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:09,847 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:10,113 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:11,025 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:12,030 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:12,216 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:12,916 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:13,241 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:13,301 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:13,604 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:14,580 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:15,629 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:15,881 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:16,764 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:17,130 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:17,196 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:17,485 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:18,559 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:19,728 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:19,979 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:20,877 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:21,277 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:21,342 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:21,603 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:22,573 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:23,602 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:23,815 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:24,563 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:24,888 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:24,947 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:25,193 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:26,118 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:27,117 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:27,338 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:28,108 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:28,456 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:28,519 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:28,776 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:29,785 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:30,788 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:30,995 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:31,759 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:32,097 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:32,156 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:32,392 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:33,448 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:34,582 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:35,630 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:35,955 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:36,017 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:36,253 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:37,281 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:38,364 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:38,594 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:39,412 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:39,754 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:39,823 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:40,068 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:40,891 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:41,826 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:42,010 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:42,718 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:43,029 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:43,087 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:43,316 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:44,161 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:45,073 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:45,257 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:46,033 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-09 22:01:46,403 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:46,468 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:46,709 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:47,740 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:48,703 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-09 22:01:48,895 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-09 22:01:49,589 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.8970，相對亮度比: 0.93，座標: (531, 712)
2026-09-09 22:01:49,873 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-09 22:01:49,936 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-09 22:01:50,158 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-09 22:01:50,206 [WARNING] ⚠️ [Watchdog] (第 1 次逾時) 狀態 [NAVIGATING] 已卡住逾時 92.3s (門檻 90.0s)，啟動特徵掃描與輕量復原！
2026-09-09 22:01:50,335 [INFO] 💾 [StateStash] 已暫存原狀態: NAVIGATING (原因: watchdog_timeout_NAVIGATING)
2026-09-09 22:01:50,335 [INFO] 🔄 狀態轉移: NAVIGATING -> POPUP_RECOVERY
2026-09-09 22:01:50,831 [INFO] 🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: 1/5 | 明暗度: 中央 48.4 / 邊框 46.9 (遮罩: False)
2026-09-09 22:01:51,812 [INFO] 🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: 2/5 | 明暗度: 中央 48.4 / 邊框 46.8 (遮罩: False)
2026-09-09 22:01:52,800 [INFO] 🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: 3/5 | 明暗度: 中央 48.4 / 邊框 46.9 (遮罩: False)
2026-09-09 22:01:53,807 [INFO] 🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: 4/5 | 明暗度: 中央 48.4 / 邊框 46.8 (遮罩: False)
2026-09-09 22:01:54,794 [INFO] 🛡️ [PopupRecovery] 啟動意外彈窗處置 | 嘗試: 5/5 | 明暗度: 中央 48.4 / 邊框 46.9 (遮罩: False)
2026-09-09 22:01:55,587 [ERROR] ❌ [PopupRecovery] 已達最大重試次數 (5)，彈窗救援無效！發起 GameRelaunchSubflow 強行重開自癒...
2026-09-09 22:01:55,587 [WARNING] 🚨 [GameRelaunchSubflow] 啟動嚴重卡死強行終止與重啟自癒閉環 (原因: popup_recovery_max_retries_exceeded)...

```