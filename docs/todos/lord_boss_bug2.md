
Q: 這邊 lord boss的bug是 他典籍boss卡變厚 ,沒有成功點開,或是點開後沒有成功按下去戰鬥(fight.png) 因此沒有進入戰鬥 但她卻把這以為是無法打boss強制完成 語意上不正確 觀測的也不精準

```
] 成功匹配模板 'load/lord_spider.png'！相似度: 0.9915，相對亮度比: 1.01，座標: (347, 411)
2026-09-14 08:10:55,023 [INFO] 🔍 [首領討伐] 於畫面發現 Boss 卡片 [育母蜘蛛麗拉西亞] [0.9915]，檢查是否有冷卻木牌...
2026-09-14 08:10:55,051 [INFO] ℹ️ [CooldownDetector] 木牌模板最高匹配分數: 0.5460 (門檻: 0.58) ➔ 判定無冷卻木牌
2026-09-14 08:10:55,051 [INFO] 🎯 [首領討伐] 確認 Boss [育母蜘蛛麗拉西亞] 無冷卻木牌！進行點擊選擇討伐！
2026-09-14 08:10:55,144 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-14 08:10:55,151 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-14 08:10:56,117 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8920，相對亮度比: 0.68，座標: (1111, 915)
2026-09-14 08:10:56,372 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9840，相對亮度比: 1.00，座標: (988, 765)
2026-09-14 08:10:56,374 [INFO] 🚀 [首領討伐] 點擊開始戰鬥按鈕 [0.9840]，啟動非阻塞戰鬥進場驗證 [育母蜘蛛麗拉西亞]...
2026-09-14 08:10:56,471 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-14 08:10:56,477 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-14 08:10:59,538 [WARNING] ⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [stages/start.png] 依然存在！判定 Boss [育母蜘蛛麗拉西亞] 次數已滿或無法挑戰。
2026-09-14 08:10:59,693 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9918，相對亮度比: 1.00，座標: (1277, 198)
2026-09-14 08:10:59,697 [INFO] 🚪 [首領討伐] 點擊卡片關閉按鈕 [common/quit.png] 退回大廳...
2026-09-14 08:10:59,697 [INFO] 👉 發起點擊 (1277, 221)，啟動「配對確認直到 [common/quit.png] 消失」輪詢閉環...
2026-09-14 08:10:59,788 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-14 08:10:59,794 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-14 08:11:00,308 [INFO] 🟢 [配對確認完成] 模板 [common/quit.png] 已徹底從畫面上消失！費時 0.42 秒。
2026-09-14 08:11:01,310 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-14 08:11:01,310 [INFO] 🛡️ [DailyManager] 已手動將 Boss [育母蜘蛛麗拉西亞] 強制標記為今日已打滿 (completed_today: True)。
2026-09-14 08:11:01,311 [INFO] 🔄 狀態轉移: LORD_BOSS -> NAVIGATING
2026-09-14 08:11:01,311 [INFO] ✅ [城鎮流水線] 子流程 [lord_boss] 已離開 active slot。
```