背景描述:

當我在地下城探索中restart的時候 他沒辦法正確接續流程,原因是他無法配對下樓的記號 並按下去 我不知道為何(但他可以匹配到leave.png 這個地下橙特徵)

時間點 發生在sandbox 的log 0912 00:38 左右

```
tifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 00:38:05,203 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 00:38:10,119 [INFO] [FullRelocalize] reason=legacy_or_unspecified expected_tab=None candidates=[] winner=None is_conflict=False elapsed=1.125s
2026-09-12 00:38:11,680 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9653，相對亮度比: 0.99，座標: (64, 717)
2026-09-12 00:38:11,681 [INFO] 🟢 [登入流程] 登入後畫面載入完成！全域感知識別世界場景 [SceneId.DUNGEON_EXPLORING]，交由主狀態機接管！
2026-09-12 00:38:11,682 [INFO] 🔄 [登入流程] 畫面載入完畢，立即發起全域狀態定位 (detect_current_state)...
2026-09-12 00:38:11,805 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-12 00:38:11,814 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-12 00:38:11,815 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-12 00:38:13,506 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.3956，座標: None
2026-09-12 00:38:13,564 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/Domains_entry.png'，最高相似度: 0.3583，座標: None
2026-09-12 00:38:13,626 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/golden_empire/entry.png'，最高相似度: 0.1201，座標: None
2026-09-12 00:38:13,676 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/common/start_btn.png'，最高相似度: 0.4921，座標: None
2026-09-12 00:38:14,014 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9653，相對亮度比: 0.99，座標: (64, 717)
2026-09-12 00:38:14,015 [INFO] 🏰 全域定位：偵測到地下城內部特徵 [dungeons/leave.png] (信心度: 0.9653)，鎖定地下城探索狀態！
2026-09-12 00:38:14,016 [INFO] 🔄 狀態轉移: UNKNOWN -> EXPLORING
2026-09-12 00:38:14,390 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:14,863 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:15,375 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:16,277 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:16,613 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
```