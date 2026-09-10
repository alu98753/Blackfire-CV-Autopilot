問題描述:
他在背包滿了之後 會去清理背包接著跑 blood_altar 跟 jewelry_workshop

但是 blood出現bug, 具體而言bloodalter 有兩個不同的情境
第一個是每日任務 他領完之後紅點會消失 因此可以判定該任務完成 就不會再次進入 這個邏輯目前沒問題
但是第二個是獻祭血 目前這兩個任務沒有區隔方式導致當我想要獻祭血時 會因為共用每日任務 的邏輯導致獻祭被意外跳過


2026-09-10 11:27:09,774 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:27:10,417 [INFO] 🟢 [配對確認完成] 模板 [common/quit.png] 已徹底從畫面上消失！費時 0.55 秒。
2026-09-10 11:27:11,419 [INFO] 🏛️ [城鎮/關卡背包清理] 背包清理完成，立即觸發城鎮任務流水線佇列...
2026-09-10 11:27:11,420 [INFO] 🏛️ [城鎮流水線] 背包清理完成，構建城鎮任務佇列...
2026-09-10 11:27:11,420 [INFO] ============================================================
2026-09-10 11:27:11,421 [INFO] 🏛️ 【城鎮任務流水線 - 任務總覽儀表板】 🏛️
2026-09-10 11:27:11,421 [INFO] ============================================================
2026-09-10 11:27:11,421 [INFO]   1. [blood_altar] 血之祭壇獻祭       : 🟢 待執行 (Enabled)
2026-09-10 11:27:11,422 [INFO]   2. [jewelry_workshop] 珠寶加工廠出售      : 🟢 待執行 (Enabled)
2026-09-10 11:27:11,422 [INFO] ============================================================
2026-09-10 11:27:11,422 [INFO] ============================================================
2026-09-10 11:27:11,422 [INFO] 🎯 [城鎮流水線進度] 彈出並切換至任務: [blood_altar] (血之祭壇獻祭)
2026-09-10 11:27:11,423 [INFO] 📌 剩餘待執行子流程 (1 個): ['jewelry_workshop']
2026-09-10 11:27:11,423 [INFO] ============================================================
2026-09-10 11:27:11,423 [INFO] 🧭 [城鎮流水線] 已建立 REACH_TOWN precondition intent；入口成立前保留目前活動 config。
2026-09-10 11:27:11,424 [INFO] 🔄 狀態轉移: BAG_CLEANING -> NAVIGATING
2026-09-10 11:27:12,737 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-10 11:27:16,371 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 11:27:16,381 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 11:27:16,474 [INFO] [TownSubflowNavigation] flow=blood_altar scene=lobby action=return_town reason=town_subflow_return_to_town
2026-09-10 11:27:21,595 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9996，相對亮度比: 1.00，座標: (85, 917)
2026-09-10 11:27:24,417 [INFO] 成功匹配模板 'town_building/Blood_Altar/Blood_Altar.png'！相似度: 0.9775，相對亮度比: 1.01，座標: (634, 760)
2026-09-10 11:27:24,696 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_red_dot_blood_altar.png
2026-09-10 11:27:24,705 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_red_dot_blood_altar.png
2026-09-10 11:27:24,717 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_red_dot_crop_blood_altar.png
2026-09-10 11:27:24,725 [INFO] 🔍 [RedDotDebug] [blood_altar] 建築下方無可領取紅點 (最高相似度: 0.4419 < 門檻: 0.60)，已產出除錯診斷圖: debug_red_dot_blood_altar.png
2026-09-10 11:27:24,728 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-10 11:27:24,728 [INFO] ✅ [DailyManager] 記錄通用子流程 [blood_altar] 今日已完成。
2026-09-10 11:27:24,728 [INFO] ✅ [城鎮流水線] [blood_altar] 入口無紅點，確認今日已完成，標記 completed_today = True。
2026-09-10 11:27:24,728 [INFO] ✅ [城鎮流水線] 子流程 [blood_altar] 已離開 active slot。
2026-09-10 11:27:24,730 [INFO] ============================================================
2026-09-10 11:27:24,730 [INFO] 🎯 [城鎮流水線進度] 彈出並切換至任務: [jewelry_workshop] (珠寶加工廠出售)
2026-09-10 11:27:24,730 [INFO] 📌 剩餘待執行子流程 (0 個): []
2026-09-10 11:27:24,731 [INFO] ============================================================
2026-09-10 11:27:24,731 [INFO] 🧭 [城鎮流水線] 已建立 REACH_TOWN precondition intent；入口成立前保留目前活動 config。
2026-09-10 11:27:26,021 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9996，相對亮度比: 1.00，座標: (85, 917)
2026-09-10 11:27:28,367 [INFO] 🎯 [城鎮流水線] Town precondition 已成立