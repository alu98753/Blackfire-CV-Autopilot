# 開發故事：大廳頁籤二維色相光環消歧與地下城導航卡死治理 🧭

> 日期：2026-09-10  
> 分支：`fix/lobby-tab-chromatic-disambiguation`  
> 成果契約：[Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)  
> 關鍵模組：[utils/scene_detector.py](../../utils/scene_detector.py), [states/handlers/navigation.py](../../states/handlers/navigation.py), [tests/test_entity_lobby_panel.py](../../tests/test_entity_lobby_panel.py)  

---

## 1. Purpose (目的)

在地下城切換與混合模式掛機中，系統出現「反覆點擊地下城頁籤按鈕但無法進入地下城選關」的嚴重卡死迴圈：
1. **模板相似度過高引發成對消歧失效**：
   - 實測地下城頁籤選中態模板 `dungeons/dungeon_after.png` (0.9444) 與未選中態 `dungeons/dungeon.png` (0.9281) 在開啟畫面上的匹配置信度差距僅有 `0.0163`。
   - 由於差值小於原本靜態門檻 `LOBBY_TAB_MARGIN = 0.02`，成對消歧判斷判定為未開啟 (`dungeon_select_open == False`)。
2. **決策層狂點與狀態顛簸**：
   - `NavigationHandler` 在 `mix_mode` 下觀察到 `not dungeon_select_open`，每一幀皆執行 `click(dungeons/dungeon.png)`。
   - 由於畫面早已處於地下城頁籤，點擊不會引起畫面改變，導致狀態機死鎖在原地。

---

## 2. Action (行動)

1. **實證物理幾何與色彩特徵分析**：
   - 對齊大廳全部 5 組按鈕（關卡、地下城、領地、領主、魔神）：中央雕紋在選中與未選中態完全一致，cross-match 置信度高達 0.85~0.94。
   - 唯一的客觀物理正交特徵為外環是否存在**紅色高飽和發光圓環 (Red Halo Ring)**。
2. **二維色相光環向量化算法 (`verify_tab_red_halo`)**：
   - 於 [utils/scene_detector.py](../../utils/scene_detector.py) 實作外環色相計算：
     - 在按鈕歸一化半徑 $r \in [0.75, 1.05]$ 區間建立圓環遮罩 (Ring Mask)。
     - 轉換至 HSV 色彩空間，過濾紅色高飽和像素 ($H \in [0, 12] \cup [165, 180], S \ge 70, V \ge 70$)。
     - 實測選中態紅光比率為 12.6%~15.6%，未選中態僅 0.3%~2.6%，分離度 >10%。
     - 訂定閾值為 7.0%，具備 >2x 的極高安全裕度。
3. **二維消歧裁決引擎 (`_evaluate_tab_active`)**：
   - 顯著差值快速裁決：$|\Delta c| \ge 0.025$ 時直接依分數判定。
   - 微差模糊區間啟用二維物理色相光環消歧：檢驗紅光比例，存在紅光即斷言為選中態，徹底消滅幽靈假陰性。
   - 全面替換 `_resolve_expected_lobby_tab` 與 `_resolve_full_relocalize` 中的布林判定。
4. **決策層防抖治理**：
   - 在 [states/handlers/navigation.py](../../states/handlers/navigation.py) 的頁籤點擊前注入 `_last_mix_tab_switch_time` 防抖（1.2 秒冷卻視窗）。
   - 增加動態屬性型別防護 (`isinstance(..., (int, float))`)，徹底杜絕 Mock 物件型別比較異常。
5. **基準解析度單一事實來源 (SSOT) 與自適應縮放工具抽離**：
   - 於 [config.py](../../config.py) 定義 `BASE_RESOLUTION_WIDTH = 1920.0` 與 `BASE_RESOLUTION_HEIGHT = 1080.0`。
   - 實作防禦性共用工具函式 `compute_screen_scale` 與 `compute_screen_scale_y`，全面替換 `vision/matcher.py`、`utils/scene_detector.py`、`states/handlers/navigation.py`、`diamond_collection.py`、`bag_cleaning.py`、`backpack_full_sorting.py`、`jewelry_workshop.py` 各處裸寫的 `1920` 與 `1080`。
   - 於 [tests/test_vision_matcher.py](../../tests/test_vision_matcher.py) 增加縮放工具的跨解析度與異常邊界測試。
6. **契約升格與 Future Work 登錄**：
   - 升格 [docs/features/navigation/lobby_scene_contract.md](../features/navigation/lobby_scene_contract.md) Invariant 1 為「成對差值主導與二維色相光環消歧保證」。
   - 於 [docs/todos/future_work.md](../todos/future_work.md) 登錄 Item 11：安全移動關卡頁籤模板至 `templates/stages/` 並更新路徑。

---

## 3. Result (結果)

- **微差邊界場景 100% 精準消歧**：
  - 在 $\Delta c = 0.0163$ 的微差情境下，紅光光環成功斷言 Active，無紅光精準斷言 Inactive，切頁死循環被徹底瓦解。
- **Magic Number 零容忍全面落地**：
  - 全專案 7 大核心模組徹底消滅 1920 裸數字，統一受 `config.compute_screen_scale` 約束與守護。
- **單元測試全數綠燈**：
  - [tests/test_vision_matcher.py](../../tests/test_vision_matcher.py) 5 個測試全數通過（含自適應縮放邊界防護測試）。
  - [tests/test_entity_lobby_panel.py](../../tests/test_entity_lobby_panel.py) 10 個測試全數通過。
  - [tests/test_scene_detector.py](../../tests/test_scene_detector.py) 13 個測試全數通過。
  - [tests/test_behavior_navigation.py](../../tests/test_behavior_navigation.py) 28 個測試全數通過。
  - [tests/test_behavior_bag_cleaning.py](../../tests/test_behavior_bag_cleaning.py) 6 個測試全數通過。
  - 聚焦領域測試共 62 個測試全數 PASS。

---

## 4. So What (核心價值)

1. **破除單一模板相似度盲點**：
   - 單純依賴灰階或邊緣模板比對無法解決「中央圖案 90% 相同、僅外圈有發光顏色差異」的物理 UI。引入第二維度（色相與幾何外環）構建了堅不可摧的判斷防線。
2. **遵守「感知與決策分離」與極簡原則**：
   - 不在 `NavigationHandler` 中隨意寫補釘，而是強化 `SceneDetector` 的客觀物理感知能力，維持單一職責與乾淨的分層架構。

---

## 5. Influence (後續影響)

- 地下城、領地、首領與普通關卡在大廳切頁導航時，無論動態光效或微小色差，皆能毫秒級精確識別選中狀態。
- 確立了全專案針對按鈕發光光暈等細緻 UI 狀態的二維色相向量化分析典範。
