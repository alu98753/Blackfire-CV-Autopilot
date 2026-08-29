# PARS 開發故事：懸賞任務對照解耦與 24/7 跨日自動自癒機制 🚀

## 📝 PARS 5 大要素

### 1. Purpose (目的)
解決自動化腳本在 24/7 長時間連軸運作 (Long-running Daemon) 下，當開發者於文字編輯器補充新懸賞任務、錯別字或關卡規則時，因硬編碼於 `.py` 導致必須重開程序的痛點。同時實現跨日 08:05 重置與告示牌任務更新時，歷史 `unknown_quests` 可全自動自癒晉升並自動多階梯排序。

---

### 2. Action (行動)

1. **資料解耦與 Git 版控**：
   - 將對照資料庫自 `utils/quest_mapper.py` 抽離，建立受 Git 版控追蹤的 [config/quest_rules.json](../../../config/quest_rules.json)。
   - 在 JSON 內建 `_doc` 說明區塊，詳列地下城 `0~4`、關卡 Level `1~6` 與子關卡對照表。

2. **零停機動態熱重載 (Hot Reload) & ValueError 防呆**：
   - 於 `QuestMapper` 透過 nanosecond 級別之 `os.path.getmtime()` 比對時間戳。開發者存檔即秒級感知載入新規則，無需重開程序。
   - 若 `config/quest_rules.json` 缺失或 JSON 解析無效，直接拋出 `ValueError` 顯式警示。

3. **跨日自癒與多階梯自動排序**：
   - 於 [DailyManager.check_and_reset_daily()](../../../utils/daily_manager.py#L214) 與 [update_bulletin_board_quests()](../../../utils/daily_manager.py#L387) 觸發 `reevaluate_unknown_quests()`。
   - 晉升任務與當日任務融合後，統一傳送至 `mapper.sort_quests()` 依 `[確定性 > 彈窗核銷 ➔ 地下城/關卡 ➔ index/level 大者優先]` 多階梯規則全域排序。

---

### 3. Result (結果)
- **單元測試全綠**：全套 302 個單元測試全數 100% 通過 (`Ran 302 tests in 221.708s, OK`)。
- **雙態與熱重載驗證**：`test_dynamic_hot_reload_from_quest_rules_json` 與 `test_cross_day_reset_and_update_quests_full_flow` 100% 通過驗證。

---

### 4. So What (核心價值)
徹底解除了 24/7 長跑腳本維護任務資料庫需重開程序的限制，同時避免了跨日任務遺失與無序問題，極大地提升了系統運行的自動化韌性與工程品質。

---

### 5. Influence (影響)
本模組實作的 `os.path.getmtime()` 動態熱重載與 Git 版控解耦架構，為專案中其他動態設定檔（如 Boss 冷卻配置、裝備品質過濾等）提供了可複製的最佳工程實踐範本。
