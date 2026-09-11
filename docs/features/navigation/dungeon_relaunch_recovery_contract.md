# 地下城重啟復原與前置離場路由契約 (Dungeon Relaunch Recovery & Intent Latching Contract) 🏰

> 狀態：正式架構契約（Normative Contract）  
> 上位架構：[Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md)  
> 前置條件契約：[Precondition Contracts](../../architecture/precondition_contracts.md)（第 7.1 與 7.2 節）  
> 導航關聯契約：[Lobby Scene Contract](lobby_scene_contract.md)（Invariant 6）  
> 相關處理器：[ExploreHandler](../../../states/handlers/explore.py)、[GameStateMachine](../../../states/state_machine.py)  
> 驗證測試檔：[tests/test_dungeon_relaunch_recovery.py](../../../tests/test_dungeon_relaunch_recovery.py)

---

## 1. 範圍與責任 (Scope & Responsibility)

本契約規範系統在地下城探索過程中因異常崩潰、手動重啟或登入重連後，畫面客觀處於地下城內部時的場景定位、意圖鎖定（Intent Latching）、下樓交互與前置離場行為。

本契約約束：
- 全域定位（`detect_current_state`）對地下城物理錨點的客觀感知，杜絕因業務配置（`config`）不同而遮蔽地下城辨識。
- `ExploreHandler` 在探索與下樓決策中的領域自治，確保無論當前處於何種業務配置，探索處理器均能正確辨識並點擊下樓圖標 (`dungeons/gungeon_godown.png`) 與通關寶箱。
- 目標業務意圖（如普通關卡 `stage` 或領地古國 `golden_empire`）在未滿足 dispatch 前置條件時的鎖定保存與離場後原樣還原閉環。

---

## 2. 核心架構不變量 (Normative Invariants)

### Invariant 1：客觀場景主導與感知解耦保證 (Perceptual Scene Primacy Invariant)
- **原則**：依據 Precondition Contracts 第 6.3 條，場景感知以畫面物理特徵為單一真相，嚴禁用 FSM state 或 config 類型代替世界觀察。
- **保證**：
  1. 當畫面上觀測到地下城核心錨點（`dungeons/leave.png`、`dungeons/gungeon_godown.png`、`dungeons/dungeons_complete.png`）時，全域感知層保證判定為身處地下城，並轉移至 `STATE_DUNGEON_EXPLORING`。
  2. 全域感知檢驗（`dungeon_detection_features`）嚴禁因當前 `config` 標記為 `domain`、`stage` 或 `collect_only` 而略過地下城錨點檢驗。

### Invariant 2：探索處理器領域自治保證 (ExploreHandler Domain Autonomy Invariant)
- **原則**：`ExploreHandler` 是專屬 `SceneId.DUNGEON_EXPLORING` 的處理器，必須自主維護地下城探索順序，不得受外部不相干業務配置閹割。
- **保證**：
  1. `ExploreHandler` 執行的探索優先級清單中，必須包含下樓按鈕 (`dungeons/gungeon_godown.png`)、下樓確認 (`dungeons/gungeon_godown_confirm.png`) 與通關按鈕 (`dungeons/dungeons_complete.png`)。
  2. 若當前 `config` 傳入之 `explore_priorities` 未包含任何地下城有效模板（例如殘留領地模式之 `domains/golden_empire/explore_btn.png`），`ExploreHandler` 保證自主回退至標準離場優先級 (`EMERGENCY_DUNGEON_EXIT_PRIORITIES`)，絕不在地下城內嘗試比對非地下城模板。

### Invariant 3：下樓與進展交互優先於被動錨點保證 (Action-Over-Anchor Priority Invariant)
- **原則**：地下城每層左下角恆常存在離開按鈕 (`dungeons/leave.png`)。該圖標僅作為樓層起點與維護錨點，絕不具備推進探索之效果。
- **保證**：
  1. 在所有地下城探索優先級清單中，具備實質推進效果之交互模板（通關、彈窗確認、下樓確認、戰鬥房、開寶箱、選祝福、下樓按鈕）必須嚴格排列於 `dungeons/leave.png` 之前。
  2. `dungeons/leave.png` 必須置於清單最末位，僅在畫面無任何可交互按鈕時充當被動維護錨點，重置樓層過渡標記與防卡死計數，嚴禁排在下樓按鈕前阻斷探索進展。

### Invariant 4：意圖鎖定與對稱還原閉環保證 (Intent Latching & Definitive Restoration Invariant)
- **原則**：依據 Precondition Contracts 第 7.2 條，角色意外處於地下城時，非地下城目標業務意圖（如 `domain` 或 `stage`）之 dispatch 前置條件不成立，未滿足之前置條件不得銷毀意圖。
- **保證**：
  1. 進入 `STATE_DUNGEON_EXPLORING` 時，若當前配置非合格地下城探索路線，狀態機保證將原配置鎖定於 `self.dungeon_recovery_return_config`，並注入前置離場路由。若先前已存在鎖定意圖，嚴禁重複覆蓋。
  2. 唯有在觀測到確鑿離場證據（`dungeons_complete.png` 消失且出現大廳或城鎮錨點）時，`_finalize_dungeon_completion` 保證將鎖定之配置 100% 還原至 `self.config`，並轉移至 `STATE_NAVIGATING` 恢復原業務目標。

---

## 3. 地下城探索標準優先級順序表

所有地下城探索流程（常規地下城、混合模式地下城、每日模式地下城與重啟離場路由）統一遵循以下聲明式優先級：

| 順序 | 模板路徑 | 性質 | 動作 |
| :---: | :--- | :--- | :--- |
| 1 | `dungeons/dungeons_complete.png` | 通關結算 | 點擊領取通關寶箱並啟動離場閉環 |
| 2 | `common/confirm.png` / `common/continue.png` / `common/continue_gray.png` | 流程彈窗 | 點擊確認或繼續 |
| 3 | `dungeons/gungeon_godown_confirm.png` | 下樓確認 | 點擊確認下樓 |
| 4 | `common/ok.png` | 提示彈窗 | 點擊確定 |
| 5 | `common/quit.png` | 退出彈窗 | 點擊關閉遮擋介面 |
| 6 | `dungeons/Treasure.png` | 寶物事件 | 點擊發起寶箱子流程（單層記憶防重複） |
| 7 | `dungeons/skill_event.png` | 技能事件 | 點擊處理技能選擇 |
| 8 | `dungeons/dungeon_bless.png` | 祝福事件 | 點擊發起祝福子流程（單層記憶防重複） |
| 9 | `dungeons/gungeon_godown.png` | 下樓樓梯 | 點擊下樓並標記樓層過渡 |
| 10 | `dungeons/leave.png` | 起點錨點 | 被動維護探索狀態、重置過渡標記，不發送點擊 |

> [!IMPORTANT]
> **職責邊界澄清**：`dungeons/dungeon_fight.png` 為大廳前往地下城的備戰按鈕（`SceneType.DUNGEON_PREPARE`），由 [`navigation.py`](../../states/handlers/navigation.py) 負責點擊進入地下城。它**絕非**地下城內部地圖特徵，嚴禁納入內部探索特徵庫或重開復原特徵偵測中。
