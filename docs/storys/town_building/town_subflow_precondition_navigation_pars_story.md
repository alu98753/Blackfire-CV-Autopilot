# 城鎮子流程前置條件導航與背包退場循環修復開發故事 (PARS Story) 🧭

本文件記錄 《Blackfire Crusade》 自動化工具在 `fix/chest-precondition-navigation` 分支中，**每日 5 大城鎮子流程前置條件導航 (Town Subflow Precondition Navigation)** 與 **背包清理退出死循環修復** 的問題分析、重構行動、驗證結果與架構價值，遵循 **PARS 框架** 撰寫。

---

## 1. 🎯 Purpose (目的)

### 痛點與核心問題
1. **城鎮任務過早派發 (Premature Dispatch)**：
   原本啟動每日任務佇列（如 `chest`, `hero_draw`, `blood_altar`, `bulletin_board`, `jewelry_workshop`）時，系統在首幀擷取前就直接換掉 FSM 狀態與配置（如強制切為 `CHEST`），假設畫面已在城鎮。若角色實際身處戰鬥、結算、領地或登入頁，會導致非預期卡死或盲目點擊。
2. **無紅點無效點擊與判定缺失**：
   當城鎮建築物今日福利已領取或無新懸賞（無紅點）時，系統缺乏前置攔截，仍重複點進建築物，甚至造成誤判完成。
3. **切場景黑屏假陽性**：
   在畫面黑屏過渡時，模板匹配容易因缺乏亮度過濾而產生誤匹配。
4. **背包清理退出死循環 (Reopen Loop)**：
   背包清理完成後，若直接觸發後續城鎮子流程（如祭壇+珠寶），狀態未及時交回 `NAVIGATING`，導致主迴圈殘留背包狀態並重複開包。
5. **看門狗誤殺長子流程**：
   深淵魔王 (`STATE_DEMON_LORDS`) 流程較長且缺乏 UI 進度心跳，容易被 60 秒看門狗判定為卡死中斷。

---

## 2. ⚡ Action (行動)

### A. 前置條件導航與感知三層架構
1. **城鎮入口契約集中註冊 ([states/town_subflow_registry.py](../../../states/town_subflow_registry.py))**：
   - 建立 `TownSubflowSpec`，統一聲明五大任務的 `REACH_TOWN` 目標、建築範本與紅點需求（`requires_red_dot=True`）。
2. **純感知模組 ([states/town_subflow_perception.py](../../../states/town_subflow_perception.py))**：
   - 獨立職責：只觀察城鎮錨點（門、鑽石）、目標建築與紅點證據，絕不產生點擊副作用。
   - 引入 `TOWN_ANCHOR_BRIGHTNESS_THRESHOLD = 0.35`，徹底杜絕場景切換黑屏瞬間的模板誤匹配。
3. **前置條件控制器與多幀防抖 ([states/town_subflow_navigation.py](../../../states/town_subflow_navigation.py))**：
   - 任務佇列在未抵達城鎮前保持 `STATE_NAVIGATING`，由 `NavigationTable` 的 `REACH_TOWN_EDGES` 負責導航。
   - 實作無紅點安全結案：若建築已確認無紅點，直接標記 `completed_today = True` 並平滑推進下一個任務。
   - 實作多幀防抖 (Debounce) 確認，防止過渡動畫誤判。

### B. 狀態機與調度修復 ([states/state_machine.py](../../../states/state_machine.py))
1. **優先全域彈窗攔截**：`task_complete` 與 `backpack_full` 優先於城鎮導航意圖，防止搶點。
2. **背包退場移交修復 ([states/handlers/bag_cleaning.py](../../../states/handlers/bag_cleaning.py))**：
   背包清理完成退出時，明確呼叫 `transition_to(STATE_NAVIGATING)`，徹底解決重開死循環。
3. **08:05 重置與搶佔防護**：
   重置時正確還原 `primary_config`；待處理城鎮佇列存在時限制 Boss 喚醒搶佔；排除 `exit_battle` 誤判為城鎮。

### C. 看門狗心跳與視覺門檻強化
1. **看門狗保護 ([states/exceptions/watchdog.py](../../../states/exceptions/watchdog.py), [demon_lords.py](../../../states/handlers/demon_lords.py))**：
   將 `STATE_DEMON_LORDS` 納入 90s 長任務白名單，並在關鍵 UI 節點埋入 `notify_ui_progress` 心跳。
2. **裝備顏色分類器防冷灰石塊 ([vision/color_classifier.py](../../../vision/color_classifier.py))**：
   提高藍色 HSV 門檻 ($S \ge 110, V \ge 70$) 與投票閾值 (400)，排除 UI 冷灰石塊邊框 (S=55, V=51) 假陽性。
3. **第六章關卡範本裁切 ([templates/stages/six_stage.png](../../../templates/stages/six_stage.png))**：
   去除頂部陰影干擾，底頁比對信心度自 0.79 提升至 0.97。

### D. 完整測試套件建立
- 新增 [tests/test_town_subflow_precondition_navigation.py](../../../tests/test_town_subflow_precondition_navigation.py)（27 個聚焦單元測試，涵蓋前置導航、紅點判定、有界 Defer 與黑屏過濾）。
- 同步更新背包、看門狗、顏色分類器與導航行為測試。

---

## 3. 📊 Result (結果)

1. **單元測試全數通過**：
   - 專屬前置條件測試套件 `tests.test_town_subflow_precondition_navigation` 27/27 綠燈通過。
   - 看門狗豁免與 Demon Lords 心跳測試 100% 通過。
   - 裝備色彩分類器冷灰邊框測試 100% 通過。
2. **狀態機行為穩健**：
   - 每日任務佇列無論從戰鬥、大廳、領地或選關啟動，均能安全導航至城鎮並按紅點狀態準確核銷，不再出現過早派發卡死。
   - 背包清理後順暢銜接後續流水線，重開循環徹底消除。

---

## 4. 💡 So What (核心價值)

- **狀態機與導航契約解耦**：徹底終結以往「先假設身處正確場景再祈求畫面吻合」的脆弱邏輯，轉型為「以客觀證據感知前置條件 ➔ 條件滿足才派發」的高韌性架構。
- **統一 REACH_TOWN 安全樞紐**：將回城導航收斂至共用路由表，避免各 Handler 重複撰寫 `goback_town` 點擊。

---

## 5. 🔮 Influence (影響與後續)

- 為下一階段將「體力退避 (`stamina_retreat`)」、「定時領鑽石 (`COLLECT_DIAMOND`)」與「Boss 流程 (`lord_boss`, `demon_lords`)」納入統一前置條件導航體系奠定了堅實標準。
