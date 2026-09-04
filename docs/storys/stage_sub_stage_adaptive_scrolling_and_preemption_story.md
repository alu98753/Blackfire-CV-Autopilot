# 關卡小關自適應雙向滾動與 Tier 4 地下城插隊解耦開發故事（PARS Framework）

## Purpose (目的)

1. **關卡小關滾動死鎖與單向滾動痛點**：原本小關導航 (`_select_sub_stage`) 僅支援由上往下滾動 (`scroll_down`)，若目標小關位於視窗上方（例如小關列表中目前在後段而目標在前端），腳本會不斷往下滑動直至超時重試。且缺乏純領域導航決策與滑動座標計算抽象，代碼存在重複的硬編碼滑動邏輯。
2. **Tier 4 關卡長駐模式插隊阻斷痛點**：在 Daily Tier 4 退守選擇普通關卡 (`stage`) 後，`build_tier4_fallback_config` 過去未完全將 `enable_dungeon` 與純關卡模式解耦，導致在 stage 長駐期間週期地下城冷卻結束時無法及時離場插隊，陷入關卡循環死鎖。

## Action (行動)

1. **抽離純領域小關導航器 (`SubStageListNavigator`)**：
   - 於 `utils/sub_stage_navigator.py` 建立獨立領域物件 `SubStageListNavigator`，基於小關名稱（`easy`, `normal`, `hard`, `very_hard`, `nightmare`, `hell`, `inferno`, `abyss`, `apocalypse`, `chaos`, `middle` 等）建立 Rank 映射。
   - 計算目前畫面可見小關的最小/最大 Rank 與目標 Rank，自動推導滾動方向（`ScrollDirection.DOWN` 或 `ScrollDirection.UP`）。
   - 封裝 Client 座標系下的 200px 拖曳起點與終點計算 (`calculate_drag_points`)。
   - 提供有界恢復決策 (`decide_action`)，當達到 `sub_stage_scroll_max_attempts` 上限時自動切換為 fallback 點擊畫面中心第一個小關。
2. **重構 NavigationHandler 統一小關滑動**：
   - 整合 `_handle_sub_stage_scroll`，以 `SubStageListNavigator` 取代分散於各處的 hardcoded 滑動邏輯，恪守 DRY 原則。
   - 透過 `defaults.toml` 引入 `sub_stage_scroll_max_attempts = 5` 配置。
3. **解耦 Tier 4 退守配置與地下城插隊**：
   - 於 `utils/tier4_config.py` 確保 `build_tier4_fallback_config` 在 stage 退守模式下忠實保留 `enable_dungeon` 開關狀態。
   - 於 `states/state_machine.py` 擴展 `is_daily_pipeline_active`，納入 `is_tier4_fallback`，確保退守期間活動調度與插隊檢查持續生效。
   - 於 `states/handlers/result.py` 支援 Tier 4 關卡長駐模式下，當 `enable_dungeon=True` 且週期地下城冷卻結束時主動觸發離場插隊。
4. **行為測試全面覆蓋**：
   - 新增 `tests/test_sub_stage_navigator.py`（8 個獨立單元測試），驗證 rank 排序、雙向滾動推導、座標計算與有界上限。
   - 擴充 `tests/test_behavior_navigation.py`，驗證小關上滑、下滑及上限恢復點擊。
   - 擴充 `tests/test_behavior_daily_dungeon_toggle.py` 與 `tests/test_behavior_daily_tier4.py`，驗證 enable_dungeon 啟用時地下城插隊與禁用時持續戰鬥行為。

## Result (結果)

- 小關導航支援上滑與下滑雙向自適應滾動，不再出現向下滑到底的死循環。
- Tier 4 關卡退守掛機時，週期地下城冷卻完畢後能順暢退出關卡並插隊執行地下城，執行完畢再回到關卡掛機。
- 專屬領域單元測試 65 項測試全部綠燈通過 (`Ran 65 tests in 27.215s ... OK`)。

## So What (核心價值)

將「視覺畫面比對/點擊執行」與「導航滾動策略/座標推導」徹底解耦。`SubStageListNavigator` 作為無副作用的純邏輯模組，大幅降低狀態機複雜度，同時使 Tier 4 長駐退守模式真正與週期活動調度器合為一體。

## Influence (影響)

後續若有新加入的小關難度階級，僅需於 `SubStageListNavigator` 擴充 Rank 字典即可直接支援雙向導航與邊界保護；Tier 4 架構亦奠定了未來擴充其他週期副本與長駐路由安全插隊的統一範式。
