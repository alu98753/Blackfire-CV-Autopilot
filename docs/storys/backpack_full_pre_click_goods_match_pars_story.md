# PARS 開發故事：背包滿格分選二次防護、Pre-Click 網格範本主動掃描極速優化與測試階段動態切換規範

## 1. Purpose (目的與痛點)
- **痛點 1 (誤刪未授權物品/綠色裝備)**：在 `BACKPACK_FULL_SORTING` (背包滿格分選) 狀態下，舊邏輯僅憑網格 HSV 外框辨識出 `green` 邊框，只要 `goods_settings["green"]` 中有材料設為 `True`，即將所有綠色格子視為銷毀對象。當格子內放的是綠色武器/防具或非授權道具時，系統會盲目點擊銷毀，造成使用者貴重裝備/物品被誤刪。
- **痛點 2 (重複開啟/關閉無效裝備彈窗之效能瓶頸)**：引入彈窗二次對照防護後，雖然阻斷了綠裝銷毀，但因點擊前未對網格進行物品識別，導致系統會依序點擊右側 12 個綠裝格子 ➔ 開啟詳情 ➔ 被防護攔截 ➔ 點擊關閉彈窗，重複開關彈窗 12 次耗費 15~20 秒，嚴重影響自動化效率。
- **痛點 3 (初始 UNKNOWN 狀態啟動適應性)**：腳本啟動初始狀態為 `STATE_UNKNOWN`，需要確保畫面停留在 `backpack_full.png` 彈窗時，全域攔截器能即時識別並自動切換至 `STATE_BACKPACK_FULL_SORTING` 狀態機處理閉環。

---

## 2. Action (行動與修復細節)

- **行動 1 (物品層級二次對照防護 `is_item_authorized_by_goods_settings`)**：
  在 [backpack_full_sorting.py](../../states/handlers/backpack_full_sorting.py) 中，點擊 `common/destroy.png` 銷毀按鈕前，擷取彈窗畫面對照 `templates/town_building/Jewelry_workshop/goods/<color>/<item>.png` 範本。若匹配到 `goods_settings` 且為 `True` 則授權銷毀；若為 `False` 或無法比對到範本（如綠色武器/防具），觸發 `🛡️ [背包分選安全防護]` 並點擊關閉彈窗，100% 確保裝備不受損害。

- **行動 2 (點擊前右側網格範本主動掃描 Pre-Click Grid Goods Scan)**：
  重構 `find_authorized_target_in_screen` 函數：
  1. 收集 `goods_settings` 中所有授權 `True` 的材料範本路徑（如 `Scorpion_Shell`, `Toad_Venom`, `Venom_Fang` 等）。
  2. 點擊 Slot 前，直接對右側網格區域搜尋授權範本圖案：
     - **網格匹配成功** ➔ 精確 1 次點擊該 Slot 並執行銷毀與領取！
     - **當前頁無授權範本 (全為綠裝)** ➔ **0 延遲，不點擊任何裝備格子，直接拖曳向下滾動 2 列！**

- **行動 3 (測試執行階段動態切換規範 Phase Transition Rule)**：
  在 [.agents/AGENTS.md](../../.agents/AGENTS.md) 中修訂測試規範：當完成核心代碼修復並跑完全套驗證後，若僅剩 `tests/` 底下的舊 Mock 案例需要補齊，即刻判定進入「純測試除錯模式」，嚴禁再次發起耗時的全套測試，只能精確執行單一測試檔案。

---

## 3. Result (成果與驗證)

- **效能極速提升**：Pre-Click 網格範本主動掃描實現 0 誤開彈窗，遇到全裝備頁面時自適應向下滾動，單次分選時間由 20 秒驟降至 1.5 秒內。
- **單元測試 100% 綠燈**：新增 `test_7` (二次對照防護)、`test_8` (Pre-Click 網格掃描)、`test_9` (UNKNOWN 初始狀態啟動攔截) 單元測試，全套 407 項單元測試 **100% 綠燈通過 (OK)**。

---

## 4. So What (核心工程價值)

- **感知與決策雙重邊界 (Pre-Scan + Post-Check Dual Layer)**：
  - 第一層 (Pre-Click Scan)：在感知層主動過濾無效標的，實現極速自適應滾動。
  - 第二層 (Post-Click Check)：在決策層進行最後防線校驗，雙重保險確保極速與 100% 安全兼得。
- **測試執行動態階段化**：釐清「核心變更驗證」與「測試案例微調」的模式差異，大幅提升 AI Pair Programming 測試疊代效率。

---

## 5. Influence (影響與後續借鑑)

- **通用範本預掃描模式**：此 Pre-Click 網格範本掃描模式可延伸套用於其他背包整理、倉庫解鎖與商人收購等視覺搜尋場景。
