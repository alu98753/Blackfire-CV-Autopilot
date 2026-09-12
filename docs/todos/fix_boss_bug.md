問題: 現在verify 他是否打滿的判斷有誤

具體而言 如果打滿 那僅有可能是他點開boss 的木牌後 要去按下 E:\Side_Project\BlackfireCrusade_tool\templates\stages\start.png 之後都沒反應才算
, 但這樣定或許也不准 關於次數的部分 實際上準確地看遊戲畫面上會有五個點 假設有打過 會是白點 沒打過會是黑點, 五個白點代表真的打完了。五個黑點代表完全沒打, 中間有1~4個白點代表打到中間沒打。我構想是??


先帶我了解目前的判定方式有問題在哪 定位問題

```
'！相似度: 0.9915，相對亮度比: 1.01，座標: (347, 411)
2026-09-12 08:16:34,101 [INFO] 🎯 [首領討伐] 偵測到第一個 Boss (起點) [lord_spider] (信心度: 0.9915)，已確立回歸最左側起點！
2026-09-12 08:16:34,559 [INFO] 成功匹配模板 'load/lord_spider.png'！相似度: 0.9915，相對亮度比: 1.01，座標: (347, 411)
2026-09-12 08:16:34,560 [INFO] 🔍 [首領討伐] 於畫面發現 Boss 卡片 [育母蜘蛛麗拉西亞] [0.9915]，檢查是否有冷卻木牌...
2026-09-12 08:16:34,613 [INFO] ℹ️ [CooldownDetector] 木牌模板最高匹配分數: 0.5460 (門檻: 0.58) ➔ 判定無冷卻木牌
2026-09-12 08:16:34,614 [INFO] 🎯 [首領討伐] 確認 Boss [育母蜘蛛麗拉西亞] 無冷卻木牌！進行點擊選擇討伐！
2026-09-12 08:16:34,766 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 08:16:34,771 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 08:16:36,358 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8920，相對亮度比: 0.68，座標: (1111, 915)
2026-09-12 08:16:36,780 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9840，相對亮度比: 1.00，座標: (988, 765)
2026-09-12 08:16:36,783 [INFO] 🚀 [首領討伐] 點擊開始戰鬥按鈕 [0.9840]，啟動 2.5 秒戰鬥進場驗證 [育母蜘蛛麗拉西亞]...
2026-09-12 08:16:36,909 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 08:16:36,919 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 08:16:39,994 [WARNING] ⚠️ [首領討伐] 點擊開始戰鬥 2.5 秒後未偵測到戰鬥特徵，且按鈕 [stages/start.png] 依然存在！判定 Boss [育母蜘蛛麗拉西亞] 次數已滿或無法挑戰。
2026-09-12 08:16:40,286 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9918，相對亮度比: 1.00，座標: (1277, 198)
2026-09-12 08:16:40,290 [INFO] 🚪 [首領討伐] 點擊卡片關閉按鈕 [common/quit.png] 退回大廳...
2026-09-12 08:16:40,291 [INFO] 👉 發起點擊 (1277, 221)，啟動「配對確認直到 [common/quit.png] 消失」輪詢閉環...
2026-09-12 08:16:40,443 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 08:16:40,450 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 08:16:41,133 [INFO] 🟢 [配對確認完成] 模板 [common/quit.png] 已徹底從畫面上消失！費時 0.59 秒。
2026-09-12 08:16:42,137 [INFO] 💾 [DailyManager] 已更新並儲存日常持久化狀態檔。
2026-09-12 08:16:42,137 [INFO] 🛡️ [DailyManager] 已手動將 Boss [育母蜘蛛麗拉西亞] 強制標記為今日已打滿 (completed_today: True)。
```