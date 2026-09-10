# 地下城切換頁籤死循環 Bug 診斷日誌

> 關聯規格：[lobby_tab_active_disambiguation_spec.md](lobby_tab_active_disambiguation_spec.md)  
> 核心問題：`dungeons/dungeon_after.png` (0.9444) 與 `dungeons/dungeon.png` (0.9281) 差值 0.0163 < 0.02，導致成對消歧失敗判定為未開啟，進而在大廳中每幀重複點擊切頁按鈕。

## 1. 現場日誌證據

```text
on_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 20:02:37,165 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-10 20:02:37,223 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:37,491 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-10 20:02:37,492 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9805) 切換至地下城頁籤！
2026-09-10 20:02:37,618 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:37,625 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:38,839 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:39,888 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:40,068 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:02:40,671 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:02:40,939 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:40,990 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:41,262 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:41,264 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:02:41,394 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:41,403 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:42,594 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:43,630 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:43,838 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:02:44,464 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:02:44,741 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:44,795 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:45,062 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:45,063 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:02:45,196 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:45,205 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:46,375 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:47,416 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:47,585 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:02:48,189 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:02:48,453 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:48,508 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:48,777 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:48,778 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:02:48,906 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:48,915 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:50,115 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:51,194 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:51,357 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:02:51,970 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:02:52,239 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:52,293 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:52,561 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:52,563 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:02:52,681 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:52,689 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:53,883 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:55,050 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:55,223 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:02:55,825 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:02:56,099 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:56,151 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:02:56,417 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:02:56,419 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:02:56,545 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:02:56,554 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:02:57,714 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:58,892 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:02:59,210 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:03:00,097 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:03:00,555 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:03:00,625 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:03:00,919 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:03:00,921 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:03:01,049 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:03:01,057 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:03:02,221 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:03:03,325 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:03:03,499 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 20:03:04,117 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 20:03:04,461 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:03:04,509 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 20:03:04,804 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-10 20:03:04,805 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [冰雪洞窟, 獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9281) 切換至地下城頁籤！
2026-09-10 20:03:04,926 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 20:03:04,933 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 20:03:06,194 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 20:03:07,226 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209
```