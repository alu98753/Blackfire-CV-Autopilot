# 待辦事項與未來優化規劃 (Future Work & Project TODOs) 📋

本文件彙整《黑火遠征》專案的所有**待辦事項 (Active TODOs)**、**暫時擱置需求 (Shelved)** 與**已解決/已驗證項目 (Completed & Verified)**，作為長期維護與疊代之單一清單。

---
## 已經完成 正在觀察

- 應該要有個設定 filter 不能做的任務 我想法是根據不同模式 用toml 追蹤最高上限關卡 這樣就可以filter掉後面的
- 像是stage 若只有到冰雪洞窟 那冰雪洞窟以上的任務就要filter(在接完任務後)
dengeon同理

- [x]關卡等沒看到 要向左滑動到底 直到看到第一關

- [x] 現在商人適用次數 應該改成金錢擁有數 (已完成)

- [x] 驚嘆號排除橘色的任務點 只接受紅色的每日領取點 (已完成)

- [x] 關卡小關卡 (1, 5/mid, 6, 10/final) 通用化與零截圖擴充：以通用 `boss_skull.png` 與頂部 (`first_stage.png`) / 底部 (`six_stage.png`) 視覺閉環，實現全章節（含 Stage 7+）全量子關卡免截圖支援 (已完成)
- [x] 然後朱王與朱厚的問題是 判斷任務完成的部分的ocr可能框框太小沒有正確識別任務 (暫時完成 有加入debug圖片 待觀察)
- [x] 地下城通關狀態早產與大廳導航迷航已閉環修復 (已升格至 [Precondition Contracts 7.1](../architecture/precondition_contracts.md#71-活動與地下城通關離場後置條件閉環契約-activity--dungeon-exit-postcondition-contract) 與 [Lobby Scene Contract Invariant 6](../features/navigation/lobby_scene_contract.md#invariant-6導航地下城客觀特徵自癒彈回保證-dungeon-re-entrant-guard-invariant))
- [x] 重開登入全域感知解耦與地下城交棒前置離場路由已閉環修復 (已升格至 [Precondition Contracts 7.2](../architecture/precondition_contracts.md#72-重開登入全域感知解耦與前置離場路由契約-game-relaunch-world-perception--prerequisite-route-injection-contract) 與 PARS 故事 [2026-09-11_login_flow_dungeon_handover_and_global_perception_story.md](../storys/2026-09-11_login_flow_dungeon_handover_and_global_perception_story.md))

### Daily

1. 整理文件
2. 清理skill

要讓我可以安心整天不用看的前提

- [x] daily 四個都做得好
  目前blood ok
  抽英雄ok
  chest ok
  任務版 ok

- [x] **Daily 模式退避進入 `COLLECT_ONLY` 後，地下城冷卻結束無法定時回歸** ([state_machine_bug.md](state_machine_bug.md))
  - 待機喚醒機制與型態判斷缺陷導致地下城冷卻就緒後無法自動喚醒復歸；已由 commit 8d4ce03、0626e03 搭配本次 fix/stamina-retreat-dungeon-resume 閉環驗證完成。
- [x] **`COLLECT_ONLY` 期間定時領完體力竟擅自跑去打 Tier 4 關卡** ([collect_only_bug.md](collect_only_bug.md))
  - 退避待機期間領完體力應回城鎮等待，不應破壞待機節奏偷跑去刷關卡；地下城喚醒路由純潔化與冷卻復歸閉環已於 fix/stamina-retreat-dungeon-resume 完成。

### Navigation

- [x] 選關與地下城向右翻頁/滑動過慢且比對過多無關圖片 ([navigation_slow_bug.md](navigation_slow_bug.md)) 以在6cea216ce112f0b584c0f3c1efde22b81bb38811 完成

## 📌 一、 進行中與待開發項目 (Active TODOs)


1.3.8應該完成了 需要檢查

我能否單獨用subflow 測試 這個功能?

1. 背包滿了跑(整理背包 獻計寫 進珠寶店前再次整理背包 進珠寶店賣東西)  這應該已經坐在我的程式裡面了?

==

選卡bug: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-11 01:09:00,476 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-11 01:09:01,071 [INFO] 🧭 [子流程] 開始執行「領取祝福」階段式子流程...
2026-09-11 01:09:02,982 [INFO] 🧭 [子流程-選卡-Fallback] 點擊畫面第一個選擇按鈕 (0.9474) 座標: (765, 1636)
2026-09-11 01:09:03,109 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png

有成功進入獻計 有成功整理背包 有成功賣東西 那不能保證什麼 還要測試什麼?

### Daily

- [ ] 驗證橘紅雙點共存功能在daily正常
- [ ] 基本上 我現在在逐漸重構成沒有while死等流程的方式,但當電腦或是遊戲本體較為卡頓的時候會導致腳本無效的推進流程(但之前while因為有等所以叫沒有觸發該問題) 要思考怎麼根本解決(所有流程都會遇到該問題)

要讓我可以安心整天不用看的前提：
- 核心契約：[城鎮任務流水線佇列契約](../features/town_building/pipeline.md) (已完成雙軌解耦、獨立 bag_tidy 與後置條件驗證契約)
- 長期架構 RFC：[模式與活動大一統規格書](activity_mode_consolidation_spec.md) (統一名詞為 ActivityPlan/Activity/Intent，徹底消除 Mode 與 Subflow 歷史割裂)
- [x] **1. 背包滿後觸發珠寶店/血之祭壇時，背包未關閉即跳轉懸賞導致全域卡死** ([bag_jewelry_workshop_bug.md](bag_jewelry_workshop_bug.md))
  - 核心原因為「背包後續維護」與「每日子流程」未徹底切分；已於 `fix/bag-and-daily-subflow-decoupling` 分支解耦，背包整理升格為一級獨立子流程 `BagTidyHandler` 並以消失閉環確認關閉；珠寶店具備 4 秒進店點擊遺失自癒與殘留覆蓋層清理。詳細見 [城鎮任務流水線佇列](../features/town_building/pipeline.md)。
- [x] **3. 懸賞告示牌尚未進入建築（還在背包/其他過渡畫面）就開始誤判任務** ([bag_bug.md](bag_bug.md))
  - 告示牌處理器增加 `_is_inside_bulletin_board` 排他性專屬正交錨點 (`reset.png` / `task.png` / `task_after.png`) 門禁；見 `quit.png` 但非告示牌時判定為干擾覆蓋層並點擊關閉自癒，絕不誤判任務與吞噬懸賞。詳細見 [每日懸賞任務報告](../features/daily_task/daily_task_architecture_report.md#3-告示牌進場排他性正交錨點契約-building-entry-unique-anchor-invariant)。
- [ ] **4. 定時領體力打不開視窗觸發 DEFER 時，被誤當成 Blocking 導致主排程活鎖** ([daily_quest_dungeon_priority_spec.md](daily_quest_dungeon_priority_spec.md))
- [ ] **7. 領主 Boss(Lord) 與深淵魔王(Demon Lord) 穩定運行與材料防護**
  - lord, demon lord 不被其他activity搶掉，可以正常打完。
  - demon 的石頭如果不夠目前會怎麼做？假設黃色的沒了會都用紫色的？需要考慮加入去商店買材料（順便買競技場門票）的功能。
- [x] **8. 血之祭壇 (Blood Altar) 判定被紅點掠過問題** ([bag_bug.md](bag_bug.md))
  - blood building 徹底拆分為日常任務速領 (`blood_altar`，需紅點) 與 戰後背包滿時的獻祭 (`blood_sacrifice`，不查紅點)，避免已無紅點時獻祭被意外跳過，且不污染 `daily_status.json`。規格詳見 [城鎮任務流水線佇列](../features/town_building/pipeline.md)。
- 釐清 Daily Complete 與 Defer 的判斷依據
  - daily complete 的條件寫好了，那現在 defer 判斷的依據有哪些？

### 商店

- [ ] **10. 珠寶店商人金幣耗盡防護與通知**

  - 假設大家的金錢"都"低於某個數值 (預設 1000)，則珠寶店不開放進入 (不可以賣東西，可用 `shop_money_notenough` 的 flag 標註)。
  - 此時發送訊息給使用者 (哪個帳號、商店目前剩餘金額、請盡速回來買賣等訊息，通訊方式待定)。
  - 以上做完應該就可以掛機個兩天；接著會遇到商人沒錢的問題，所以要跟他買東西以及製作東西 (大宗)。

### 資源與模板路徑重構 (Template Assets Reorganization)

- [ ] 安全移動關卡頁籤模板至 `templates/stages/` 並更新引用路徑**
  - 將 [common/select_stage.png](../templates/common/select_stage.png) 與 [common/select_stage_after.png](../templates/common/select_stage_after.png) 安全移動至 `templates/stages/`（與 `dungeons/`、`domains/`、`load/`、`demon_lords/` 保持一致的目錄結構）。
  - 同步更新 `utils/scene_types.py` (`LOBBY_TAB_DEFINITIONS`)、相關 Handler 與所有測試案例中的引用路徑。

### Navigation

- [ ] **[FW-NAV-01] 推進 Scoped Perception (`DetectorRegistry`) 全面遷移，根除 `SceneDetector` 中所有殘留的 `config_type` 硬特判** ([scoped_perception_migration.md](scoped_perception_migration.md))
  - **當前進度與階段成果**：
    - ✅ **已完成 (fix/login-flow-dungeon-handover)**：徹底刪除原步驟 1 主動路徑 `is_dungeon_mode = config_type in ["dungeon", "mix"]` 硬特判與步驟 3.5 過渡期後備防禦；將地下城、戰鬥與結算客觀特徵登錄至 `SCENE_ANCHOR_SPECS`。
    - ⏳ **待完成殘留**：[`utils/scene_detector.py:326-328, 393-420`](../../utils/scene_detector.py#L393-L420) 仍有 `config_type` 與步驟 5 的「大廳卡片模板備援掃描 (`allow_card_fallback`)」，需待獨立議題將卡片與玩法感知徹底移出全域感知並封裝入 `ScopedDetector`。

- [ ] **2. 導航 90 秒逾時觸發 Watchdog 強制殺進程重開，且重啟後反覆卡死陷入死循環** ([watchdog.md](watchdog.md))
- 模式 `mix` 解耦
  - 現在模式 `mix` 應該不需要，而是應該由場景驅動；但現在 `daily` 是構建在 `mix` 之上，不好拆，要一個一個來。

- navigation, state machine都超過千行 且有多處邏輯一樣。
  - 分析原因並思考怎麼用BDI重構 以達到300行

### .agent

- 審核 `state_machine_development` skill 規範對齊
  - `state_machine_development` 這個 skill 在說什麼？有沒有違反 [project_arch_greenfield_lite_v1.md](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/docs/architecture/project_arch_greenfield_lite_v1.md) 的？需要同步。

### Battle & Result

- [ ] 緊急: fix_dungeon_go_town.md

- [x] 戰鬥血條靜止卡死自癒重啟機制 ([battle_stall_recovery_spec.md](battle_stall_recovery_spec.md))已完成「設定 ➔ 重新開始戰鬥」的快速自癒, 尚未更新文件 應刪除 該spe.md視情況納入contract

- [ ] refactor: 強敵比對退出戰鬥的功能現在寫的位置與名稱有誤導性,不應該限定為domains的強敵 而是所有的戰鬥都可以使用的功能

- 戰鬥結算與地下城通關閉環重構 ([result_todo.md](result_todo.md) / [RFC: 重構 Result 為 BattleResult](rfc_rename_result_to_battle_result.md))
  - 釐清並對齊架構語意：`STATE_RESULT` 實質為專屬戰鬥結算的 `STATE_BATTLE_RESULT`。
  - 解耦 `should_exit_battle` 複合條件，按「安全點搶佔、任務完成、資源退避、定時政策」分流維護。
- 戰鬥系統固定點擊探索
  - 因為已有所有角色的資料，實際上可以做戰鬥系統；因為點擊是固定位置就不需要 CV，只需要專注在戰鬥。

### Exception

- [ ] 在每天的最後一次開發後 檢驗當天的開發如果有錯誤遇到要重開 能否準確寫入具語意話的debug訊息到 各自的 user_data\<profile>\runtime\incidents

### Town

- [ ]對可合成之有價值材料 加入 bag maintenance 的流程中 在賣掉之前先做起來而不賣掉(subflow_configs.bag_maintenance)
- [ ] 

### DEV

- [ ] RFC: 測試跑太慢且while部分不符合BDI架構 (docs/todos/test_redundent.md)
  

### 1. 🔔 異常暫停與中斷即時通知 (Discord / LINE Webhook Notification)
- **需求背景**：當腳本在長掛機或黃金古國領地探索中進入手動暫停（Manual Pause）、觸發 Watchdog 卡死救援、或體力耗盡轉入退避模式時，能夠第一時間通報使用者。
- **規劃方向**：
  - 在 `config.py` 或 TOML 設定中增加 Webhook URL 配置。
  - 於 `GameStateMachine` 觸發暫停、異常重開與模式切換時，非同步發送訊息至 Discord 頻道或 LINE Notify。

### 2. 📦 分析如何變現
- **需求背景**：評估未來是否封裝為獨立 `.exe`、GUI 介面或 Web 儀表板，降低無 Python 環境用戶的使用門檻。
- **規劃方向**：
  - 現階段專注於掛機穩定性與核心邏輯完善；後續評估 PyInstaller / Nuitka 打包或 Electron / Tauri 介面封裝。

### 3. 🎨 終端 Config 設定呈現方式優化 (UI Presentation Overhaul)
- **需求背景**：目前 config.toml（一列一列），排版冗長且直觀度不足。

### 4. 🏛️ 全域架構審查與 AGENTS.md 規範對齊 (Technical Debt & Rule Auditing)
- **需求背景**：依據 `AGENTS.md` 的 5 大極簡原則與工程規範，全面排查既有代碼中的架構隱患，避免長期積累技術債。
- **熱重載架構與分界規範**：詳細分層設計請參閱 [runtime_config_hot_reload_architecture.md](../architecture/runtime_config_hot_reload_architecture.md)。

依據 **「檔案 300 行、方法 60 行、巢狀 3 層、感知與決策分離」** 原則，排查出以下亟待重構的核心檔案與對應職責：

| 檔案路徑 | 當前行數 | 規範限制 | 違反原則與架構隱患 |
| :--- | :---: | :---: | :--- |
| [`states/state_machine.py`](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py) | **1,593 行** | 300 行 | **嚴重超標**。狀態機身兼「狀態流轉」、「OCR 管理」、「全域例外處理」與「黃金古國/每日子流程協調」，職責過度混雜。 |
| [`states/handlers/navigation.py`](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py) | **907 行** | 300 行 | **嚴重超標**。雖抽離出 `SceneDetector`，但內部包含大量關卡滾動、島嶼點擊、頁籤切換等複雜巢狀分枝。 |
| [`utils/daily_manager.py`](file:///e:/Side_Project/BlackfireCrusade_tool/utils/daily_manager.py) | **614 行** | 300 行 | **超標**。同時管理 Date Tag 重置、Boss CD、懸賞進度與未知任務正名，應拆分為獨立 Manager。 |


### 5. ⚡ 沙盒環境 (Sandboxie-Plus) 運行延遲分析 (Sandbox Performance Analysis)
- **需求背景**：觀察到在 Sandboxie 沙盒實例中運行的腳本，反應速度與幀率相較原生主機實例有微幅延遲與變慢現象。
- **規劃方向**：
  - 分析 Win32 API 跨沙盒發送訊息 (`PostMessage` / `SendMessage`) 之 IPC 轉發開銷與焦點延遲。
  - 評估 `ScreenCapturer`（`mss` / `BitBlt`）在沙盒隔離視窗下的截圖幀率與延遲。
  - 測試多實例 CPU 競爭與進程優先級（Priority Boost）對沙盒實例的提速效果。

### 6. 🧠 記憶體洩漏與長期掛機效能衰減分析 (Memory Leak & Resource Health)
- **需求背景**：排查 24/7 長時間掛機時，是否有記憶體持續累積（Memory Leak）、GDI 物件未釋放或造成電腦逐漸變慢的問題。
- **規劃方向**：
  - 使用 `tracemalloc` / `memory_profiler` 監控長途運轉時 OpenCV `cv2.Mat` 影像矩陣、EasyOCR 辨識快取與 Win32 HWND / DC 控制代碼之生命週期。
  - 檢查主迴圈常駐物件與例外重試閉環是否有未被 GC 回收的暫存物件，確保連續數天掛機時資源保持恆定（Zero Leak）。

### 7. 🔄 長期掛機定期安全重啟服務 (Periodic Process & Game Restart Service)
- **需求背景**：長時間掛機（特別是 Sandboxie 沙盒環境或 Steam WebHelper 連續運行多日）會因 Chromium 網頁快取與沙盒虛擬化 I/O 堆積大量記憶體（實測 3 天可膨脹至 3.5GB+）。
- **規劃方向**：
  - 設計低負載或任務空檔（如 Boss 冷卻期間、每日重置時段）的自動重啟流程。
  - 支援自動優雅退出遊戲與 Steam、重置進程/釋放快取後，自動拉起遊戲並無縫接續狀態機掛機，維持系統 24/7 輕量穩定運行。

---

## ⏸️ 二、 暫時擱置與備用項目 (Shelved / Postponed)

> 💡 **說明**：以下項目經架構評估或已被現有更完善之機制覆蓋，暫時予以擱置，保留記錄以備未來參考。

### 1. 🔒 戰鬥結算稀有戰利品自動背包鎖定
- **原始構想**：在戰鬥結束結算畫面（`continue` 處）同時偵測到「獲得戰利品」時，前往背包進行特定裝備的鎖定防護。
- **擱置原因**：此功能目前已由**「背包 18 格 HSV 色彩分類與貴重品階反選保留機制」**完整覆蓋（藍/紫/橘/紅自動保留，灰/綠自動分解/銷毀），無需再額外進入背包點擊鎖定。

### 2. 📱 iPad 遠端操控 PC 腳本
- **原始構想**：使用 Windows PC 遠端控制 iPad 上的遊戲進行自動化。
- **擱置原因**：專案專注於 Steam PC 視窗端高解析度、高幀率與後台非搶占式掛機，目前無行動裝置跨端需求。

### 3. 🔄 城鎮點錯重來與容錯退回機制
- **原始構想**：手動或意外點錯建築時的全局重來。
- **擱置原因**：各城鎮 Handler 與子流程目前均已建立獨立的退場按鈕與 `exitfromhouse_and_to_town.png` 安全退回城鎮路徑。

### 4. 🛡️ 地下城誤入非目標地圖防呆容錯
- **原始構想**：手動按錯或誤入非目標地下城地圖時，偵測並點擊退出按鈕安全返回大廳重開。
- **擱置原因**：目前的 `mix` 混合模式、自適應卡片定位與貪婪選關已能全自動接管選關流程，無人工誤點問題。

---

## ✅ 三、 已解決與完成項目 (Completed & Verified)

### 1. 🛡️ 看門狗與例外自癒子系統 (Exception Watchdog & Game Relaunch)
*(詳細架構分析與除錯筆記請參閱 [exception_subsystem_architecture.md](../architecture/exception_subsystem_architecture.md))*
- [已完成並驗證] **5 次重試失敗直接重開自癒**：在 [UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py) 中，當 5 次嘗試仍無法消除畫面障礙時，直接喚起 `GameRelaunchSubflow` 殺進程並重啟遊戲。
- [已完成並驗證] **狀態轉移防抖與時間戳保護**：在 [GameStateMachine.transition_to](../../states/state_machine.py) 增加 `if self.current_state != new_state` 狀態防抖，防止相同狀態重複刷新 `last_state_change` 導致 Watchdog 失效。
- [已完成並驗證] **長任務真實進度回報 (`notify_ui_progress`)**：背包清理、長途出售與翻頁時定時回報有效 UI 進度，徹底消除假陽性卡死。
- [已完成並驗證] **COLLECT_ONLY 待機動態 CD 逾時與視窗崩潰檢查**：支援動態 CD 逾時保護與 HWND 遺失自動重啟。
- [已完成並驗證] **導航狀態 Watchdog 90 秒寬鬆門檻**：將 `STATE_NAVIGATING` 放寬至 90 秒，排除選關卡卡片與翻頁導航誤判。
- [已完成並驗證] **全螢幕意外彈窗對接 (Watchdog & Popup Recovery)**：支援輪盤 (`WheelOfFortuneSubflow`)、掃蕩盒 (`RaidBoxSubflow`) 與全域關閉 (`GenericAntiStuckSubflow`) 雙層救援。

### 2. 🎮 多實例與長掛機支援 (Multi-Instance & Long-Running AFK)
- [已完成並驗證] **Sandboxie-Plus Steam 雙開掛機與多實例目標選擇**：支援自動掃描本機/沙盒視窗（`[#] Blackfire Crusade [#]`）、互動選單以及 `--target` 快速參數。(參見指南 [sandboxie_dual_instance_guide.md](../guides/sandboxie_dual_instance_guide.md) 與 PARS 故事 [sandboxie_dual_instance_pars_story.md](../storys/sandboxie_dual_instance_pars_story.md))。
- [已完成並驗證] **5 天長掛機 3 大架構支柱**：
  1. **狀態持久化 ([DailyManager](../../utils/daily_manager.py))**：所有完成子流程與 08:05 重置週期自動記錄於 [daily_status.json](../../user_data/native/daily_status.json)，斷線重啟無縫接續進度。
  2. **全局看門狗與自癒修復 ([Watchdog](../../states/exceptions/watchdog.py) & [UnexpectedPopupRecoveryHandler](../../states/exceptions/handler.py))**：逾時自動清除遮擋或重啟。
  3. **點擊消失驗證閉環 (`click_and_wait_until_gone`)**：關鍵按鈕點擊後持續輪詢確認消失，防止狀態過早推進。
- [已完成並驗證] **長時間運轉資源與記憶體無洩漏** (1,000 次循環僅微增 1.09MB)。
- [已完成並驗證] **CPU 低功耗睡眠控管** (參見指南 [cpu_optimization.md](../guides/cpu_optimization.md))。
- [已完成並驗證] **Mode-Agnostic 地下城斷線與遊戲重開自癒** (全模式辨識 `dungeons/leave.png` 起點恢復探索)。

### 3. 🎯 視覺比對與座標適配 (Vision & Adaptive Coordinates)
- [已完成並驗證] **關卡選關優先按相似度而非亮度比例過濾**：解決選第 4 關誤點第 2 關周邊背景的 Bug。
- [已完成並驗證] **全域「任務完成」彈窗動態 Scale 適配**：領取按鈕依視窗高度比例動態縮放，解決非 1080p 解析度下點擊無效問題。
- [已完成並驗證] **領鑽石退出按鈕 Hover 焦點與消失確認**：後台點擊增加 `WM_MOUSEMOVE` 穩定焦點，持續比對 `quit.png` 消失後才轉移狀態。
- [已完成並驗證] **按鈕點擊消失驗證閉環 (`click_and_wait_until_gone`)**：防止過早推進狀態。
- [已完成並驗證] **地下城寶箱確認防黏住重試與消失閉環**：`Get_tresure_comfirm.png` 改為每 0.25 秒重新辨識，持續存在逾 0.75 秒自動重點，確認消失後方轉向退出按鈕，並受 10 秒子流程總上限保護。

### 4. ⚔️ 掛機模式與流水線調度 (Pipelines & Modes)
- [已完成並驗證] **地下城全冷卻瀑布流混合模式 (`mix`)**：副本全在冷卻中時自動切換至 Stage 刷關，CD 結束即時切回地下城。
- [已完成並驗證] **體力耗盡全域自動退避 (`collect_only`)**：彈出 `no_bread.png` 時自動關閉彈窗，退回城鎮切換至待機模式 4.0 小時，結束後自動恢復原模式。
- [已完成並驗證] **單一權威來源 (SSOT) 與 Fail-Fast 配置**：所有模式配置由 `config.py` 驅動，參數缺失時立即拋出防禦性例外中斷。
- [已完成並驗證] **每日任務 08:05 四階梯流水線 (`DailyMasterPipeline`)**：
  - Tier 1: 城鎮速領 (寶箱 `chest` ➔ 抽卡 `hero_draw` ➔ 祭壇 `blood_altar` ➔ 珠寶 `jewelry_workshop`)。
  - Tier 2: 領主 Boss 討伐 (`lord_boss` 蜘蛛/惡靈計時器搶佔)。
  - Tier 3: 懸賞告示牌與動態任務 (`bulletin_board`)。
  - Tier 4: 動態退守刷關。
- [已完成並驗證] **背包已滿 18 格標題中心錨定與 2 格 (279px) 精準像素 Drag 位移銷毀**。
- [已完成並驗證] **地下城索引全面統一為 1-based (消除 0-indexed 歷史包袱)**：
  - 徹底將地下城編號由 `0..5` 統一為 `1..6`，全面對齊關卡 `1..6`。
  - 消除所有 `+ 1` / `- 1` 混亂轉換與認知衝突；更新 `defaults.toml` (`max_dungeon = 6`、`greedy_allowed_indices = [1..6]`、`cooldown_map` 鍵值 `1..6`)。
  - 同步重構 `config/quest_rules.json`、`utils/quest_mapper.py`、`utils/quest_scheduler.py`、`cli/dungeon_setup.py`、`states/state_machine.py`、`states/handlers/navigation.py`。
  - 11 個單元測試套件已 100% 綠燈通過驗證。
