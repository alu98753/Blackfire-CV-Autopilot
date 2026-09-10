問題描述
這是背包滿了之後 到珠寶加工場的邏輯
具體而言
他打開背包之後
不知道有沒有清理(看起來沒有)

但是接著他觸發
2026-09-10 11:24:45,203 [WARNING] 💎 [珠寶加工廠] 防護攔截 - 處於 [ENTERED_BUILDING] 階段但畫面上已看見城鎮大門 [common/door.png] (0.9403)，結束出售流程。

導致他沒有進去珠寶加工廠賣東西,就直接跳過 跳去關卡懸賞任務,然後 因為背包沒有先關閉 所以導致卡死

我不確定這邊是
1. 珠寶店一定有bug
2. 背包沒關閉也是bug
3. 去執行任務時precondition 沒有滿足不知道是不是bug (這邊的precondition我們好像還沒設計)


log:


售)
2026-09-10 11:24:36,224 [INFO] 📌 剩餘待執行子流程 (0 個): []
2026-09-10 11:24:36,225 [INFO] ============================================================
2026-09-10 11:24:36,225 [INFO] 🧭 [城鎮流水線] 已建立 REACH_TOWN precondition intent；入口成立前保留目前活動 config。
2026-09-10 11:24:36,759 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8150，相對亮度比: 0.81，座標: (1115, 764)
2026-09-10 11:24:37,110 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9567，相對亮度比: 1.00，座標: (68, 719)
2026-09-10 11:24:38,797 [INFO] 🎯 [城鎮流水線] Town precondition 已成立，派發 [jewelry_workshop] -> [JEWELRY_WORKSHOP]。
2026-09-10 11:24:38,797 [INFO] 🔄 狀態轉移: NAVIGATING -> JEWELRY_WORKSHOP
2026-09-10 11:24:40,952 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9567，相對亮度比: 1.00，座標: (68, 719)
2026-09-10 11:24:40,954 [INFO] 💎 [城鎮商店] 進入前執行城鎮背包預先整理，優先開啟背包...
2026-09-10 11:24:41,161 [INFO] 成功匹配模板 'common/bag_text.png'！相似度: 0.9363，相對亮度比: 1.00，座標: (1231, 760)
2026-09-10 11:24:41,163 [INFO] 🎒 背包清理：優先偵測到背包入口文字「物品欄」 [0.9363]，點擊打開背包。
2026-09-10 11:24:41,341 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:24:41,350 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:24:42,910 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:42,911 [INFO] 💎 [城鎮商店] 進入前執行城鎮背包預先整理，優先開啟背包...
2026-09-10 11:24:44,395 [INFO] 💎 [城鎮商店] 於城鎮發現目標商店 [煉金小屋] (town_building/alchemy_hut/alchemy_hut.png) (記錄金幣: None, 信心度: 0.9229)，點擊進入...
2026-09-10 11:24:44,538 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:24:44,548 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:24:45,200 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:45,203 [WARNING] 💎 [珠寶加工廠] 防護攔截 - 處於 [ENTERED_BUILDING] 階段但畫面上已看見城鎮大門 [common/door.png] (0.9403)，結束出售流程。
2026-09-10 11:24:45,203 [INFO] 💎 [商店出售結算] 經全頁面雙向掃描，背包無商品需要出售。
2026-09-10 11:24:45,208 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-10 11:24:45,208 [INFO] ✅ [DailyManager] 記錄通用子流程 [jewelry_workshop] 今日已完成。
2026-09-10 11:24:45,212 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-10 11:24:45,212 [INFO] 💎 [DailyManager] 商店 [alchemy_hut] 訪問次數已更新: 26 次
2026-09-10 11:24:45,212 [INFO] 🔄 狀態轉移: JEWELRY_WORKSHOP -> NAVIGATING
2026-09-10 11:24:45,212 [INFO] 🔄 [GameStateMachine 動態調度] ⚔️ 執行關卡懸賞任務 [清除熊] (進度: 2/20) ➔ 即時自動切換至目標配置: 懸賞任務 - 古樹森林 (final) (任務: 清除熊)
2026-09-10 11:24:45,212 [INFO] ✅ [城鎮流水線] 子流程 [jewelry_workshop] 已離開 active slot。
2026-09-10 11:24:45,214 [INFO] ============================================================
2026-09-10 11:24:45,215 [INFO] 🎉 【城鎮流水線 - 全部完成】 🎉
2026-09-10 11:24:45,215 [INFO] 恢復主掛機模式配置: [每日懸賞任務]
2026-09-10 11:24:45,215 [INFO] ============================================================
2026-09-10 11:24:45,216 [INFO] 🔄 [GameStateMachine 動態調度] ⚔️ 執行關卡懸賞任務 [清除熊] (進度: 2/20) ➔ 即時自動切換至目標配置: 懸賞任務 - 古樹森林 (final) (任務: 清除熊)
2026-09-10 11:24:45,628 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:45,998 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:46,811 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:47,236 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=primary_enter_lobby progress=idle
2026-09-10 11:24:47,366 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:24:47,378 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:24:47,818 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:48,176 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:49,016 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:49,428 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=2.0s deadline=9606.234 attempt=1
2026-09-10 11:24:49,841 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:50,218 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:51,090 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:51,457 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.0s deadline=9606.234 attempt=1
2026-09-10 11:24:51,834 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:52,210 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:53,110 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:53,501 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.0s deadline=9606.234 attempt=1
2026-09-10 11:24:53,617 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:24:53,626 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:24:54,040 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:54,354 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:55,114 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:55,510 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.8s deadline=9612.484 attempt=2
2026-09-10 11:24:55,900 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:56,296 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:57,020 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:57,411 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.7s deadline=9612.484 attempt=2
2026-09-10 11:24:57,794 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:24:58,151 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:59,047 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:24:59,437 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.7s deadline=9612.484 attempt=2
2026-09-10 11:24:59,566 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:24:59,575 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:24:59,982 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:00,342 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:01,317 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:01,757 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=2.1s deadline=9618.421 attempt=3
2026-09-10 11:25:02,181 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:02,592 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:03,559 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:03,956 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.3s deadline=9618.421 attempt=3
2026-09-10 11:25:04,368 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:04,750 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:05,752 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:06,214 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.5s deadline=9618.421 attempt=3
2026-09-10 11:25:06,371 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:06,381 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:06,916 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:07,365 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:08,314 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:08,804 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=2.3s deadline=9625.234 attempt=4
2026-09-10 11:25:09,224 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:09,592 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:10,365 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:10,722 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.2s deadline=9625.234 attempt=4
2026-09-10 11:25:11,087 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:11,469 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:12,379 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:12,755 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.3s deadline=9625.234 attempt=4
2026-09-10 11:25:12,898 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:12,910 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:13,376 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:13,743 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:14,565 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:14,994 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=2.0s deadline=9631.765 attempt=5
2026-09-10 11:25:15,397 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:15,776 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:16,589 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:16,903 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.9s deadline=9631.765 attempt=5
2026-09-10 11:25:17,248 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:17,546 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:18,228 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:18,534 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.5s deadline=9631.765 attempt=5
2026-09-10 11:25:18,656 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:18,665 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:19,083 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:19,373 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:20,058 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:20,372 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.6s deadline=9637.515 attempt=6
2026-09-10 11:25:20,738 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:21,063 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:21,747 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:22,072 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.3s deadline=9637.515 attempt=6
2026-09-10 11:25:22,426 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:22,732 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:23,437 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:23,767 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.0s deadline=9637.515 attempt=6
2026-09-10 11:25:23,886 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:23,896 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:24,316 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:24,643 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:25,365 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:25,706 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9642.750 attempt=7
2026-09-10 11:25:26,086 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:26,438 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:27,202 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:27,533 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.5s deadline=9642.750 attempt=7
2026-09-10 11:25:27,873 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:28,171 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:28,832 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:29,152 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.2s deadline=9642.750 attempt=7
2026-09-10 11:25:29,266 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:29,273 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:29,681 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:29,967 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:30,605 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:30,907 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.5s deadline=9648.125 attempt=8
2026-09-10 11:25:31,228 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:31,531 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:32,257 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:32,574 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.2s deadline=9648.125 attempt=8
2026-09-10 11:25:32,892 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:33,171 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:33,830 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:34,137 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.8s deadline=9648.125 attempt=8
2026-09-10 11:25:34,472 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:34,770 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:35,460 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:35,776 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.4s deadline=9648.125 attempt=8
2026-09-10 11:25:35,897 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:35,906 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:36,296 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:36,585 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:37,322 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:37,664 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9654.750 attempt=9
2026-09-10 11:25:37,985 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:38,268 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:38,934 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:39,252 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.3s deadline=9654.750 attempt=9
2026-09-10 11:25:39,565 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:39,853 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:40,514 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:40,835 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=4.8s deadline=9654.750 attempt=9
2026-09-10 11:25:41,159 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:41,446 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:42,094 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:42,406 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=6.4s deadline=9654.750 attempt=9
2026-09-10 11:25:42,537 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:42,548 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:43,003 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:43,301 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:44,005 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:44,321 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9661.406 attempt=10
2026-09-10 11:25:44,658 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:44,952 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:45,672 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:45,984 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.3s deadline=9661.406 attempt=10
2026-09-10 11:25:46,309 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:46,597 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:47,289 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:47,646 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.0s deadline=9661.406 attempt=10
2026-09-10 11:25:47,772 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:47,787 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:48,262 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:48,600 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:49,341 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:49,666 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.8s deadline=9666.640 attempt=11
2026-09-10 11:25:49,990 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:50,292 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:51,010 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:51,348 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.5s deadline=9666.640 attempt=11
2026-09-10 11:25:51,698 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:51,988 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:52,694 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:53,016 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.1s deadline=9666.640 attempt=11
2026-09-10 11:25:53,132 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:53,142 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:53,588 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:53,934 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:54,621 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:54,966 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9672.000 attempt=12
2026-09-10 11:25:55,293 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:55,585 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:56,274 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:56,588 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.3s deadline=9672.000 attempt=12
2026-09-10 11:25:56,930 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:57,223 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:57,924 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:58,245 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.0s deadline=9672.000 attempt=12
2026-09-10 11:25:58,366 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:25:58,373 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:25:58,794 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:25:59,125 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:25:59,863 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:00,191 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9677.218 attempt=13
2026-09-10 11:26:00,514 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:00,841 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:01,549 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:01,864 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.4s deadline=9677.218 attempt=13
2026-09-10 11:26:02,193 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:02,484 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:03,204 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:03,535 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.1s deadline=9677.218 attempt=13
2026-09-10 11:26:03,650 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:26:03,659 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:26:04,074 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:04,387 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:05,152 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:05,481 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.7s deadline=9682.515 attempt=14
2026-09-10 11:26:05,806 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:06,104 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:06,795 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:07,109 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.3s deadline=9682.515 attempt=14
2026-09-10 11:26:07,441 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:07,748 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:08,435 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:08,758 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=5.0s deadline=9682.515 attempt=14
2026-09-10 11:26:08,884 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:26:08,894 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:26:09,326 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:09,636 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:10,422 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)
2026-09-10 11:26:10,763 [INFO] [IntentRouting] intent=primary_navigation scene=town action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=1.8s deadline=9687.750 attempt=15
2026-09-10 11:26:11,116 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9945，相對亮度比: 1.01，座標: (1113, 74)
2026-09-10 11:26:11,434 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9403，相對亮度比: 0.62，座標: (68, 719)