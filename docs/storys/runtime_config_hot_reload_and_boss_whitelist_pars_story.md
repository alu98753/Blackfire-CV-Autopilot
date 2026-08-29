# 執行期 Profile 設定熱重載與首領討伐白名單重構開發故事 (PARS Framework) 📝

## 1. Purpose (目的)
在多實例與日常掛機情境下，使用者於腳本執行期間手動修改 `user_data/<profile>/config.toml`（例如將關卡由 `final` 改為第 6 關 `six`，或將 Boss 討伐目標改為僅打蜘蛛 `lord_spider`），終端機雖跳出 `[HotReload]` 重載通知，但腳本依然維持啟動時的舊關卡與全部 Boss 輪詢。排查發現核心障礙在於：
1. 狀態機啟動時記錄的 `runtime_config_overrides` 快取把 TOML 新值蓋掉。
2. 關卡圖片路徑未隨宣告式 TOML 設定動態重新解析。
3. 首領討伐缺乏顆粒化目標選取機制，依賴頂層 `completed_today` 標記導致決策脫節。

## 2. Action (行動)
1. **徹底移除啟動差異覆蓋快取**：在 [GameStateMachine](../../states/state_machine.py) 中將 `self.runtime_config_overrides` 設為空字典，確立 Profile TOML 為單一真值來源 (SSOT)。
2. **動態關卡路徑重構 (`_apply_tier4_stage_selection`)**：每次安全點熱重載時，根據最新 `tier4_stage_level` 與 `tier4_sub_stage` 重新計算 `stage_target` 與 `stage_navigation_path`。
3. **實例領取策略動態同步 (`_sync_runtime_collection_policies`)**：安全點動態同步 `enable_bread`、`need_bread_collection` 與 `need_diamond_collection` 旗標。
4. **新增首領討伐白名單 (`lord_boss_targets`)**：
   - 於 `defaults.toml` 與 Profile TOML 支援清單配置（如 `["lord_spider"]` 或 `[]`）。
   - 於狀態機提供集中決策入口 `get_available_selected_lord_bosses()` 與 `has_available_selected_lord_boss()`，以「TOML 白名單 ∩ JSON 待打 Boss」統一所有排程、待機喚醒、領地插隊與結果頁決策。
   - 子流程期間由 `primary_config` 繼承白名單，防止跨狀態遺失使用者政策。
   - 移除 JSON 頂層 `completed_today`，改由各 Boss 討伐次數動態即時計算。
5. **架構規範文檔化**：撰寫 [runtime_config_hot_reload_architecture.md](../architecture/runtime_config_hot_reload_architecture.md)，並與 [future_work.md](../todos/future_work.md) 建立重構排程連結。
6. **編寫全套單元與整合測試**：更新 [test_behavior_runtime_config_refresh.py](../../tests/test_behavior_runtime_config_refresh.py) 與 [test_profile_config_overlay.py](../../tests/test_profile_config_overlay.py)，涵蓋真實 TOML 檔案熱重載與白名單過濾行為。

## 3. Result (結果)
- **100% 動態即時生效**：修改 `user_data/<profile>/config.toml` 後，下一個主迴圈安全點即時切換目標關卡、地下城、活動開關與 Boss 目標，無需重啟腳本。
- **測試全面綠燈**：所有行為測試、首領討伐測試、日常排程與 Profile 覆蓋測試均 100% 通過（581 tests OK）。

## 4. So What (核心價值)
- **消除雙重真相 (Dual Source of Truth)**：徹底廢除「啟動 overrides 快取」與「TOML 檔案」打架的架構隱患。
- **顆粒化業務決策**：首領討伐從「粗暴的二元開關」升級為「支援個別 Boss 白名單的精確調度」，提升自動化掛機彈性。

## 5. Influence (影響)
- 為後續 `main.py` 抽離 `cli_menu.py` 與 `state_machine.py` 抽離 `config_resolver.py` 奠定清晰的職責分界。
- 專案所有模式與子流程未來均遵循「Profile TOML 為單一真值來源 + 安全點集中解析」的統一規範。
