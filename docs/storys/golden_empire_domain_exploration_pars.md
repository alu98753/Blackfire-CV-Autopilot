# 黃金古國領地探索模式與自適應退避架構 (Golden Empire Domain Exploration PARS)

---

## 🎯 Purpose (目的)

為《Blackfire Crusade》擴充全新主掛機模式——**「領地模式：黃金古國」**（`golden_empire`）。
在該模式下，系統需支援：
1. 自動導航進場（大門 ➔ 領地選單 ➔ 黃金古國 ➔ 啟動探索）。
2. 主場景循環探索（消耗 3 麵包）。
3. 遭遇挖寶事件時執行免費單次開箱、領取確認並退出返回。
4. 遭遇不可戰勝之強敵 Boss（如黃金君王、精靈秘銀妖婆等）時執行「主動放棄戰鬥」且不計入單場戰敗。
5. 遭遇常規戰鬥戰敗時支援獨立單場最多 5 次重試 (`domain_max_defeat: 5`)。
6. 背包已滿、定時領鑽石/體力或食物不足（`no_bread2.png`）時，具備精確的「優先關閉子視窗 ➔ 退回大廳 ➔ 回城鎮 ➔ 自動重新進場/定時待機」自癒閉環。

---

## 🚀 Action (行動)

1. **策略模式架構解耦 ([states/domains/base_domain.py](../../states/domains/base_domain.py), [states/domains/golden_empire.py](../../states/domains/golden_empire.py))**：
   - 建立 `BaseDomainStrategy` 抽象基礎類別與 `DomainExploreHandler`，將領地特定邏輯（挖寶、專屬按鈕）抽離為策略模組，維持狀態機單一職責與可擴充性。
2. **領域強敵處置與單場戰敗獨立計數 ([states/handlers/battle.py](../../states/handlers/battle.py), [states/handlers/result.py](../../states/handlers/result.py))**：
   - 實作 `nemesis_templates` 處置子流程：偵測到設定檔指定的領域強敵（`golden_king`、`elf_mythril_hag`、`undead_altalim`、`human_golden_tulakh`）時，依據 `nemesis_action` 執行暫停手動接管或點擊設定 ➔ 放棄挑戰 ➔ 安全退出，且保持 `defeat_count = 0`，退回後自動重新導航進場。
   - 每次進入戰鬥時獨立計算 `defeat_count`，支援 `domain_max_defeat: 5` 次重試上限。
3. **通用子視窗回退與背包滿退場閉環 ([states/handlers/navigation.py](../../states/handlers/navigation.py), [states/handlers/domain_explore.py](../../states/handlers/domain_explore.py))**：
   - 當 `need_diamond_collection` 或需要回城時，若畫面開著子卡片視窗（`common/quit.png`），優先關閉子視窗露出大廳底層，再點擊 `goback_town.png`，防止遮罩阻擋。
   - 領地內背包滿且無彈窗時，主動點擊 `domains/common/exit_to_lobby.png` ➔ 導航回城觸發 `STATE_BAG_CLEANING` ➔ 清理完畢後自動重新進場。
4. **多樣式食物不足彈窗支援 ([states/stamina_flow.py](../../states/stamina_flow.py))**：
   - 擴充 `handle_insufficient_stamina` 支援雙樣式彈窗（普通地下城 `no_bread.png` + `cancel.png`；黃金古國 `no_bread2.png` + `confirm.png`）。
   - 感知 `no_bread2.png` 語意後點擊確認關閉，並順暢銜接 `exit_to_lobby.png` ➔ `goback_town.png` ➔ `STATE_COLLECT_ONLY` 退避。
5. **啟動器與配置整合 ([main.py](../../main.py), [run.bat](../../run.bat), [config/defaults.toml](../../config/defaults.toml))**：
   - 在 `run.bat` 新增選項 `7) 領地模式：黃金古國`；支援 `--mode domain --domain golden_empire` 命令列啟動。
   - 支援 `auto_bread` 與 `auto_diamond` 開關配置。

---

## 📊 Result (結果)

* **全套單元測試防護網**：全套 **521 項** 行為與單元測試全數 **100% 綠燈通過 (OK)**！
* **新增測試模組**：
  - `tests/test_behavior_golden_empire.py`（11 項領地行為測試）
  - `tests/test_behavior_navigation.py`（新增子視窗回退行為測試）
* **文檔與範本同步**：
  - 建立 [`templates/domains/golden_empire/README.md`](../../README.md) 完整記載 15 項特徵圖規格。
  - 同步更新專案 [`README.md`](../README.md)。

---

## 💡 So What (核心價值)

* **模組化領地架構**：未來若官方開放「第二領地」或「活動古國」，僅需新增繼承 `BaseDomainStrategy` 的策略檔與 TOML 配置，即可零代碼侵入擴充。
* **高強健自癒閉環**：將「避戰撤退」、「子視窗遮罩回退」、「食物不足雙彈窗」、「背包滿回城整理」收斂為狀態機底層通用行為，掛機穩定度與容錯能力大幅提升。

---

## 🔮 Influence (影響與後續)

* 本架構確立了跨場景退避（LIFO 介面回退）與策略注入的最佳實踐，後續開發新建築或活動時可直接復用此規範。
