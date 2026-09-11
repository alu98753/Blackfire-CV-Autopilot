觀察多餘的cv 判斷點 並思考是否可以合理移除 還是要等到scene detector 確立 才能逐步移除

1. 導航時的多於判斷
```
2026-09-10 22:56:00,531 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:01,103 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:01,104 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9192)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 22:56:01,248 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 22:56:01,258 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 22:56:02,570 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:02,800 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9590，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 22:56:03,023 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9431，相對亮度比: 1.08，座標: (1040, 94)
2026-09-10 22:56:03,559 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.3958, inact=0.4412, elapsed=0.281s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:04,737 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.188s
2026-09-10 22:56:05,953 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9172，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:06,025 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:06,798 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9172，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:07,353 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9172，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:07,355 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9172)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 22:56:07,464 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 22:56:07,473 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 22:56:08,677 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:09,118 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9692，相對亮度比: 1.01，座標: (1270, 124)
2026-09-10 22:56:09,627 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.3958, inact=0.4412, elapsed=0.281s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:10,799 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.172s
2026-09-10 22:56:12,066 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:12,921 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 22:56:14,035 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:14,271 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 22:56:14,473 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9692，相對亮度比: 1.01，座標: (1270, 124)
2026-09-10 22:56:14,967 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.3958, inact=0.4412, elapsed=0.266s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:16,138 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.156s
2026-09-10 22:56:17,622 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:18,504 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 22:56:19,657 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:19,868 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 22:56:20,063 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9885，相對亮度比: 1.01，座標: (1008, 180)
2026-09-10 22:56:21,733 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.6845, inact=0.6095, elapsed=1.438s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:22,911 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.7212，相對亮度比: 0.74，座標: (648, 715)
2026-09-10 22:56:23,381 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.7212，相對亮度比: 0.74，座標: (648, 715)
2026-09-10 22:56:23,739 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.7294，相對亮度比: 0.56，座標: (768, 722)
2026-09-10 22:56:24,034 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.7294，相對亮度比: 0.56，座標: (768, 722)
2026-09-10 22:56:24,638 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.7720，相對亮度比: 0.74，座標: (885, 714)
2026-09-10 22:56:25,295 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.7720，相對亮度比: 0.74，座標: (885, 714)
2026-09-10 22:56:25,618 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.7311，相對亮度比: 0.59，座標: (1006, 716)
2026-09-10 22:56:25,947 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 0.7924，相對亮度比: 0.60，座標: (1005, 716)
2026-09-10 22:56:25,949 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=4.203s
2026-09-10 22:56:27,377 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:28,527 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.6095，相對亮度比: 0.75，座標: (526, 715)
2026-09-10 22:56:28,528 [INFO] 🧭 尋路中：在畫面中找到 [common/select_stage.png] (信心度: 0.6095)，點擊按鈕中心座標 (527, 1818)。
2026-09-10 22:56:28,673 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 22:56:28,683 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 22:56:30,115 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 22:56:30,369 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 22:56:31,243 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 22:56:31,659 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 22:56:31,724 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:32,459 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9689，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 22:56:33,005 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9689，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 22:56:33,006 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9689)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 22:56:33,146 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 22:56:33,155 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 22:56:34,565 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:34,820 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 22:56:35,051 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9495，相對亮度比: 1.08，座標: (1040, 93)
2026-09-10 22:56:35,611 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.3958, inact=0.4412, elapsed=0.313s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:37,012 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.390s
2026-09-10 22:56:38,444 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9169，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:38,513 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:39,279 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9169，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:39,826 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9169，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:39,827 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9169)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 22:56:39,934 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 22:56:39,945 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 22:56:41,316 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 22:56:41,536 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 22:56:41,719 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 22:56:42,241 [INFO] [LobbyTabUpgrade] Expected tab 'stage' missed (act=0.3958, inact=0.4412, elapsed=0.297s); upgrading to FULL_RELOCALIZE
2026-09-10 22:56:43,399 [INFO] [FullRelocalize] reason=expected_tab_miss expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.156s
2026-09-10 22:56:44,547 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9191，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 22:56:44,607 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 22:56:44,793 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 22:56:44,992 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 22:56:45,539 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 22:56:45,541 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
```

2. 領麵包時期的多餘判斷

```

2026-09-10 23:10:39,801 [INFO] 🍞 定時領取：在大廳畫面，跳轉至 BREAD_COLLECTION。
2026-09-10 23:10:39,803 [INFO] 🔄 狀態轉移: COLLECT_ONLY -> BREAD_COLLECTION
2026-09-10 23:10:40,288 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 23:10:40,518 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9249，相對亮度比: 0.99，座標: (1109, 53)
2026-09-10 23:10:41,298 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 23:10:41,647 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 23:10:41,986 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 23:10:42,335 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-10 23:10:42,677 [INFO] 成功匹配模板 'domains/Domains_entry_after.png'！相似度: 0.8935，相對亮度比: 0.94，座標: (766, 717)
2026-09-10 23:10:42,978 [INFO] 成功匹配模板 'domains/Domains_entry.png'！相似度: 0.9496，相對亮度比: 1.00，座標: (768, 721)
2026-09-10 23:10:43,310 [INFO] 成功匹配模板 'load/Lord_entry_after.png'！相似度: 0.8910，相對亮度比: 0.93，座標: (888, 717)
2026-09-10 23:10:43,691 [INFO] 成功匹配模板 'load/Lord_entry.png'！相似度: 0.9850，相對亮度比: 1.00，座標: (885, 714)
2026-09-10 23:10:44,007 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.9044，相對亮度比: 0.94，座標: (1006, 716)
2026-09-10 23:10:44,299 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 0.9654，相對亮度比: 0.99，座標: (1005, 716)
2026-09-10 23:10:44,301 [INFO] [FullRelocalize] reason=legacy_or_unspecified expected_tab=None candidates=[('stage', '0.9811')] winner=stage is_conflict=False elapsed=3.328s
2026-09-10 23:10:44,527 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9249，相對亮度比: 0.99，座標: (1109, 53)
2026-09-10 23:10:44,530 [INFO] 🍞 領體力：在大廳偵測到體力按鈕 [0.9249]，點擊打開體力視窗。
2026-09-10 23:10:44,672 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:44,682 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:46,569 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 23:10:47,010 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:47,465 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:47,467 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 23:10:47,562 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:47,570 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:48,534 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 23:10:49,017 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:49,415 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:49,416 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 23:10:49,501 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:49,512 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:50,465 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 23:10:50,948 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:51,431 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:51,433 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 23:10:51,525 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:51,537 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:52,392 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 23:10:52,845 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:53,329 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 23:10:53,330 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 23:10:53,417 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:53,426 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:53,977 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9690，相對亮度比: 0.98，座標: (766, 451)
2026-09-10 23:10:53,981 [INFO] 🍞 領體力：偵測到體力確認按鈕 [0.9690]，點擊確認。
2026-09-10 23:10:54,073 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:54,081 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:54,910 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 23:10:54,912 [INFO] 🍞 領體力：偵測到退出體力按鈕 [common/quit.png] (0.9816)，嘗試點擊關閉視窗。
2026-09-10 23:10:55,014 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:55,020 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 23:10:56,029 [INFO] 🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。
2026-09-10 23:10:56,031 [INFO] 🔄 狀態轉移: BREAD_COLLECTION -> COLLECT_ONLY
2026-09-10 23:10:56,853 [INFO] 🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...
2026-09-10 23:10:56,993 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 23:10:57,003 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.p
```