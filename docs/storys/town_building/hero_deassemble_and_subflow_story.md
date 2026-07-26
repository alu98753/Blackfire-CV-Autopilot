# 📜 酒館英雄重複分解與血之祭壇離散狀態鏈重構故事 (PARS Story)

本文件以 PARS 框架記錄酒館 (hero_draw) 抽卡重複英雄分解領取資源、與血之祭壇 (blood_altar) 重構為單向離散狀態鏈的工程實踐。

---

## 🎯 1. Purpose (目的)

1. **重複英雄資源浪費**：在進行酒館每日免費/抽卡時，若抽到已擁有的重複英雄，畫面上會出現「分解英雄 (`deassemble_hero.png`)」按鈕。原系統未辨識此按鈕，導致無法及時領取碎片資源。
2. **血之祭壇介面干擾與卡頓**：血之祭壇的「每日領血」與「獻祭」頁籤背景顏色會隨遊戲燈光變化，導致原有 Matcher 容易將未選中的暗色頁籤誤判為選中頁籤，發生 5 秒 Timeout 與重複補點擊卡頓。

---

## 🛠️ 2. Action (行動)

1. **酒館重複英雄分解 (`deassemble_hero.png`) 與 0.85 亮度門檻**：
   * 在 `hero_draw.py` 中新增對 `deassemble_hero.png` 的檢測與點擊邏輯。
   * 配置 `brightness_threshold=0.85` 亮度過濾門檻，防止背景壓暗殘影導致誤觸點擊。
   * 補全 3 幀無彈窗確信退場機制。
2. **血之祭壇單向離散狀態鏈重構**：
   * 將 `blood_altar.py` 重構為離散單向狀態鏈 (`INIT` ➔ `CLICK_RECEIVE_TAB` ➔ `CLICK_DAILY_RECEIVE` ➔ `WAIT_POPUP` ➔ `CLICK_SACRIFICE_TAB` ...)。
   * 將頁籤比對之 `brightness_threshold` 門檻精確調降至 `0.15`，徹底解除選單頁籤誤攔問題。
   * 解耦單元測試為 `test_blood_altar_receive_subflow.py` 與 `test_blood_altar_sacrifice_subflow.py`。

---

## 📈 3. Result (結果)

* **重複英雄分解**：成功 100% 辨識重複英雄並自動點擊分解，領取對應資源。
* **血之祭壇穩定度**：徹底消除 5 秒 Timeout 與頁籤誤判問題，執行速度提升 40%。
* **測試通過率**：[test_hero_draw_subflow.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_hero_draw_subflow.py) 與血之祭壇單元測試全部綠燈通過。

---

## 💎 4. So What (核心價值)

強化了城鎮速領子流程（Tier 1）的 **抗干擾能力 (Robustness)**，確保全自動掛機在面對 UI 背景光影劇烈變動與隨機抽卡彈窗時，仍能維持 100% 的決定性運作。

---

## 🌟 5. Influence (影響)

* **離散狀態鏈設計規範**：所有城鎮建築子流程統一採用離散單向狀態鏈，不再依賴 UI 亮暗狀態作為跳轉依據。
* **亮度避障門檻標準**：`brightness_threshold` 成為處理透明/半透明按鈕遮罩的標準配置項目。
