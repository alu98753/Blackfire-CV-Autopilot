# 《黑火遠征》技術與系統文檔庫 (Documentation Index) 📚

本目錄包含《黑火遠征》自動化腳本之全域架構設計、業務功能規格、操作指引、開發歷史故事與待辦筆記。

---

## 🏛️ 全域核心文檔 (Core SSOT)

* 🧩 **[系統組件與架構要素清單](system_components_index.md)** (`system_components_index.md`)
  * 專案中所有的 Entity (靜態實體)、State (業務狀態)、Data (動態數據) 與 Exception (閉環自癒) 之單一正確來源 (SSOT)。
* 🧠 **[領域知識與介面規則指南](knowledge.md)** (`knowledge.md`)
  * 畫面狀態判斷邊界、操作行為規則與模式導航之核心知識庫。

---

## 📂 文檔分類目錄

### 1. 🏗️ 系統架構與設計 ([docs/architecture/](architecture/))
專案核心子系統設計、狀態流轉、視覺感知與控制流架構：
* [scene_recognition_and_navigation.md](architecture/scene_recognition_and_navigation.md)：場景定位辨識器 (`SceneDetector`) 與導航分發解耦設計。
* [mix_mode_architecture.md](architecture/mix_mode_architecture.md)：地下城與普通關卡混合模式 (Mix Mode) 動態瀑布流切換架構。
* [exception_subsystem_architecture.md](architecture/exception_subsystem_architecture.md)：雙層救援機制 + 重開遊戲兜底之例外處理子系統。
* [sub_skill_architecture_report.md](architecture/sub_skill_architecture_report.md)：子技能與被動效果系統架構分析。
* [meta_datas_field_authority_analysis.md](architecture/meta_datas_field_authority_analysis.md)：Godot `meta_datas.tres` 底層遊戲資料庫欄位權威分析。
* [pause_resume_control_spec.md](architecture/pause_resume_control_spec.md)：熱鍵暫停/恢復控制規格與主迴圈狀態同步。

---

### 2. ⚔️ 業務功能手冊 ([docs/features/](features/))
各業務領域功能規格與子流程說明：
* **每日任務與懸賞管線** ([features/daily_task/](features/daily_task/))：
  * [daily8.md](features/daily_task/daily8.md)：每日任務自動化與 08:05 定時觸發架構。
  * [daily_task_architecture_report.md](features/daily_task/daily_task_architecture_report.md)：懸賞任務架構技術報告。
  * [quest_mapping_rules_report.md](features/daily_task/quest_mapping_rules_report.md)：懸賞任務 EasyOCR 清洗與地下城/關卡對應規則。
* **城鎮建築子流程** ([features/town_building/](features/town_building/))：
  * [Blood_Altar.md](features/town_building/Blood_Altar.md)：血之祭壇領血與獻祭流程。
  * [Jewelry_workshop.md](features/town_building/Jewelry_workshop.md)：珠寶加工廠商品白名單出售。
  * [pipeline.md](features/town_building/pipeline.md)：城鎮建築子流程調度流水線。
* **戰鬥與資源流**：
  * [dungeon_flow.md](features/dungeon_flow.md)：地下城探索、卡片冷卻與戰鬥流程。
  * [bag_color_classification.md](features/bag_color_classification.md)：背包物品顏色品質分類與銷毀保留規則。
  * [stamina_retreat_feature.md](features/stamina_retreat_feature.md)：體力耗盡全域自動退避待機機制。

---

### 3. 📖 操作與掛機指南 ([docs/guides/](guides/))
使用者實機操作、效能調校與開發入門：
* [getting_started_dev_guide.md](guides/getting_started_dev_guide.md)：開發起手式、OpenCV 視覺原理與架構思維。
* [background_hang_guide.md](guides/background_hang_guide.md)：Windows 後台模擬掛機指南。
* [sandboxie_dual_instance_guide.md](guides/sandboxie_dual_instance_guide.md)：Sandboxie-Plus Steam 雙開掛機指南。
* [battle_speed_guide.md](guides/battle_speed_guide.md)：戰鬥加速與畫面幀率指引。
* [hero_summon_guide.md](guides/hero_summon_guide.md)：酒館英雄免費招募與抽卡指引。
* [cpu_optimization.md](guides/cpu_optimization.md)：CPU 低功耗睡眠控管與效能優化。
* [fail_fast_config_guide.md](guides/fail_fast_config_guide.md)：Fail-Fast 配置與單一權威來源 (SSOT) 指南。

---

### 4. 📝 PARS 開發故事專區 ([docs/storys/](storys/))
依據 `AGENTS.md` 規範收錄的所有功能與修復之 PARS (Purpose, Action, Result, So What, Influence) 開發故事：
* [daily_task/](storys/daily_task/)：懸賞管線、規則解耦、場景搶佔故事。
* [town_building/](storys/town_building/)：英雄分解、珠寶批量出售故事。
* [backpack_grid_calibration/](storys/backpack_grid_calibration/)：背包 18 格標題中心錨定與校準故事。
* 以及各項核心系統重構與修復故事（參見 [storys/ 目錄](storys/)）。

---

### 5. 📌 待辦事項與臨時草稿專區 ([docs/todos/](todos/))
集中收納待辦事項、測試暫存計畫與除錯草稿：
* [future_work.md](todos/future_work.md)：待辦事項、長掛機注意事項與未來規劃。
* [test_dev_temp.md](todos/test_dev_temp.md)：輕量化行為測試防護網建構矩陣。
* [resource_record.md](todos/resource_record.md)：資源消耗與抽卡草稿紀錄。
