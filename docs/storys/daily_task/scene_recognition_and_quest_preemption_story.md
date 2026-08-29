# 📜 場景辨識解耦、懸賞高優先搶佔與血之祭壇重構故事 (PARS Story)

本文件以 PARS 框架記錄 `refactor/scene-recognition-and-navigation-decoupling` 分支中實現的「場景定位與導航解耦 (`SceneDetector`)」、「懸賞高優先度冷卻搶佔離場」以及「血之祭壇 Clean Architecture 重構」等核心工程改動。

---

## 🎯 1. Purpose (目的)

本分支主要解決以下三大核心痛點與架構需求：
1. **導航與感知混雜 (High Coupling)**：原 [navigation.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py) 龐大且職責混雜，既要進行畫面比對又要發射點擊，違背感知與決策分離原則。
2. **懸賞冷卻搶佔與滿批次誤判 (Scheduler & Result Bug)**：低優先度關卡懸賞執行中時，若高優先度地下城冷卻到期，系統因 `is_current_task_batch_completed()` 標的物錯位導致誤判定為「續戰場次」並重複點擊再戰；且無高優先度冷卻到期之離場觸發機制。
3. **血之祭壇狀態機彈窗混亂 (Blood Altar State Flaws)**：舊血之祭壇邏輯缺乏清晰 Phase 控制，領水與彈窗清理易產生死鎖。

---

## 🛠️ 2. Action (行動)

1. **`SceneDetector` 與 `SceneType` 感知與決策徹底分離**：
   * 在 [utils/scene_detector.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/scene_detector.py) 抽離純粹畫面診斷器 `SceneDetector`，僅負責觀察畫面並傳回結構化 `SceneInfo`。
   * [NavigationHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py) 僅根據 `SceneType` 做跳轉與動作發射，不再現場比對圖片。
2. **懸賞任務高優先度搶佔與當前任務批次鎖定**：
   * 在 [utils/quest_scheduler.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_scheduler.py) 新增 `find_task_node_by_config()` 與 `has_higher_priority_task_ready()`。
   * 傳入 `current_config` 至 `is_current_task_batch_completed()`，100% 精確鎖定「當前正在打的任務」計算 4/8/10 滿批次離場條件。
   * 在 [state_machine.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py) 的 `apply_tier4_fallback_config()` 標記 `is_tier4_fallback = True`，確保當處於 Tier 4 退守模式且 Tier 3 懸賞冷卻結束時，在 [ResultHandler.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/result.py) 能立即觸發離場搶佔。
3. **血之祭壇 5-Phase 解耦與 3 幀彈窗確信**：
   * 將 [blood_altar.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/blood_altar.py) 重構為單向狀態機 Pipeline (`INIT` ➔ `ENTERED_BUILDING` ➔ `RECEIVE_TAB_OPEN` ➔ `HANDLING_RECEIVE_POPUPS` ➔ `SACRIFICE_MENU_OPEN`)。
   * 引入連續 3 幀無彈窗確信機制，徹底杜絕領水與獻祭彈窗殘留死鎖。
4. **Google Standard 5 大輕量化行為測試防護網**：
   * 依據 Google 軟體工程規範，建立 5 大領域行為測試包 ([test_dev_temp.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/test_dev_temp.md))，不測試內部實作，僅斷言公開行為與轉移。

---

## 📈 3. Result (結果)

* **全域測試綠燈**：全套單元測試 296 個案例 **100% PASS (OK)**。
* **行為測試防護網**：5 大領域行為測試包 280 個案例全數通過，防護網覆蓋率達 **88%**。
* **搶佔與離場導航**：蛤蟆任務打滿 8 次與高優先度地下城冷卻結束時，100% 成功離場切換，無任何重複無效點擊再戰。

---

## 💎 4. So What (核心價值)

* 貫徹 Karpathy Rules「感知與決策分離」與 Karpathy 極簡架構原則。
* 為懸賞任務與日常流水線提供了高可靠、可自我修復 (Self-Healing) 的多階梯搶佔排程機制，避免浪費遊戲體力與時間。

---

## 🌟 5. Influence (影響)

* `SceneDetector` 成為全專案畫面感知的單一事實來源 (Single Source of Truth)。
* 輕量化領域行為測試與 PARS 開發故事成為本專案未來所有 Feature/Fix 分支開發與 Merge 收尾的標準 SOP。
