# PARS Story: Debug 產出物集中化與武器進度分析規範 📝

## 1. Purpose (目的)
- 解決專案內散落於根目錄的 `debug_*.png` 診斷影像污染工作區與 Git 狀態的問題，建立統一收攏至 `scratch/debug/` 的機制與安全路徑檢驗模組。
- 為玩家推進卡關提供量化依據，系統化梳理武器升級石（Weapon Shards）獲取管道、鍛造分解配方與冰凍峽谷 VI~VIII 關卡的數值與掉落特性。

---

## 2. Action (行動)
1. **建立集中化 Debug 產物管理模組**：
   - 建立 [`utils/debug_artifacts.py`](../../utils/debug_artifacts.py)，提供 `debug_image_path()` 與 `write_debug_image()` 統一介面，強制收納至 `scratch/debug/debug_*.png` 並自動建立目錄。
   - 遷移所有調用端（包含 [`states/debug/visualizer.py`](../../states/debug/visualizer.py)、[`states/handlers/bag_cleaning.py`](../../states/handlers/bag_cleaning.py)、[`states/handlers/backpack_full_sorting.py`](../../states/handlers/backpack_full_sorting.py)、[`states/handlers/bulletin_board.py`](../../states/handlers/bulletin_board.py)、[`utils/cooldown_detector.py`](../../utils/cooldown_detector.py)、[`utils/quest_ocr_extractor.py`](../../utils/quest_ocr_extractor.py) 與診斷腳本）。
   - 建立專屬 Skill [`.agents/skills/debug-artifact-management/SKILL.md`](../../.agents/skills/debug-artifact-management/SKILL.md) 與單元測試 [`tests/test_debug_artifacts.py`](../../tests/test_debug_artifacts.py)。
2. **武器升級石與進度指南體系建立**：
   - 新增 [`docs/guides/weapon_upgrade_shards_guide.md`](../guides/weapon_upgrade_shards_guide.md)，全盤梳理武器石來源、白/綠/藍武器鍛造分解量產法與飾品工坊 4:1 晉升流程。
   - 更新 [`meta_data/Game_docs/My_progress/我目前的資訊.md`](../../meta_data/Game_docs/My_progress/我目前的資訊.md)，深度剖析冰凍峽谷 VI~VIII 關卡掉落與經驗機制。

---

## 3. Result (結果)
- **測試驗證**：全套單元測試 577 個案例全數通過 (`OK, skipped=14`)，無任何 Regression。
- **工作區純淨度**：所有除錯截圖與視覺化產物 100% 寫入 `.gitignore` 的 `scratch/debug/`，根目錄保持乾淨。
- **文檔完整性**：產出武器升級石完整指南與進度分析，提供清晰明確的掛機與鍛造決策。

---

## 4. So What (核心價值)
- **工程衛生 (Engineering Hygiene)**：透過統一 Helper 與路徑檢驗，杜絕跨模組各自為政硬編碼除錯檔名的技術債。
- **決策精確度**：依據底層元數據提供客觀量化分析，避免玩家在零裝備掉落或低效關卡無效掛機。

---

## 5. Influence (影響)
- 後續所有視覺化模組（如 OCR 偵錯、網格校準、冷卻偵測）皆須強制透過 `debug_artifacts` 介面輸出，納入全域開發規範。
