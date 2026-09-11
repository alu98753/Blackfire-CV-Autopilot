fix :去領麵包(在lobby) 不需要檢測那麼多東西

```
outing] intent=collect_bread scene=stage_select action=open_bread reason=bread_entry_ready progress=idle
2026-09-12 00:05:52,502 [INFO] 🔄 狀態轉移: NAVIGATING -> BREAD_COLLECTION
2026-09-12 00:05:54,939 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-12 00:05:55,316 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-12 00:05:56,540 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (664, 908)
2026-09-12 00:05:57,044 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9310，相對亮度比: 1.07，座標: (657, 911)
2026-09-12 00:05:57,506 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9163，相對亮度比: 0.96，座標: (810, 909)
2026-09-12 00:05:57,941 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9760，相對亮度比: 1.01，座標: (811, 911)
2026-09-12 00:05:58,392 [INFO] 成功匹配模板 'domains/Domains_entry_after.png'！相似度: 0.9016，相對亮度比: 0.95，座標: (958, 913)
2026-09-12 00:05:58,781 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.9598，相對亮度比: 1.01，座標: (960, 919)
2026-09-12 00:05:59,191 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8854，相對亮度比: 0.94，座標: (1111, 914)
2026-09-12 00:05:59,666 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.9584，相對亮度比: 1.01，座標: (1106, 910)
2026-09-12 00:06:00,078 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.9399，相對亮度比: 0.94，座標: (1257, 914)
2026-09-12 00:06:00,574 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1256, 913)
2026-09-12 00:06:00,578 [INFO] [FullRelocalize] reason=legacy_or_unspecified expected_tab=None candidates=[('stage', '0.9999')] winner=stage is_conflict=False elapsed=4.500s
2026-09-12 00:06:01,022 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-12 00:06:01,025 [INFO] 🍞 領體力：在大廳偵測到體力按鈕 [1.0000]，點擊打開體力視窗。
2026-09-12 00:06:01,189 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 00:06:01,202 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 00:06:03,444 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9943，相對亮度比: 1.00，座標: (1272, 285)
2026-09-12 00:06:03,448 [INFO] 🍞 領體力：偵測到退出體力按鈕 [common/quit.png] (0.9943)，嘗試點擊關閉視窗。
2026-09-12 00:06:03,576 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 00:06:03,585 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 00:06:04,911 [INFO] 🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。
2026-09-12 00:06:04,911 [INFO] 🔄 狀態轉移: BREAD_COLLECTION -> NAVIGATING
```