# 地下城重啟復原與前置離場路由契約 (Dungeon Relaunch Recovery & Intent Latching Contract) 🏰

> 狀態：正式架構契約（Normative Contract）  
> 上位架構：[Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md)  
> 前置條件契約：[Precondition Contracts](../../architecture/precondition_contracts.md)（第 7.1 與 7.2 節）  
> 導航關聯契約：[Lobby Scene Contract](lobby_scene_contract.md)（Invariant 6）  
> 相關處理器：[ExploreHandler](../../../states/handlers/explore.py)、[GameStateMachine](../../../states/state_machine.py)  
> 驗證測試檔：[tests/test_dungeon_relaunch_recovery.py](../../../tests/test_dungeon_relaunch_recovery.py)
>
> 術語與判讀：[Canonical Invariant Registry](../../architecture/canonical_invariant_registry.md)

---

## 1. 範圍與責任 (Scope & Responsibility)

本契約規範系統在地下城探索過程中因異常崩潰、手動重啟或登入重連後，畫面客觀處於地下城內部時的場景定位、意圖鎖定（Intent Latching）、下樓交互與前置離場行為。

本契約約束：
- 全域定位（`detect_current_state`）對地下城物理錨點的客觀感知，杜絕因業務配置（`config`）不同而遮蔽地下城辨識。
- `ExploreHandler` 在探索與下樓決策中的領域自治，確保無論當前處於何種業務配置，探索處理器均能正確辨識並點擊下樓圖標 (`dungeons/gungeon_godown.png`) 與通關寶箱。
- 目標業務意圖（如普通關卡 `stage` 或領地古國 `golden_empire`）在未滿足 dispatch 前置條件時的鎖定保存與離場後原樣還原閉環。

---

## 2. 核心架構不變量 (Normative Invariants)

除非外部協定或安全需求另有要求，模板清單、優先級索引、設定欄位與私有方法名稱皆是實作細節；以下規則與其可觀測結果才是本契約的長期約束。

### Invariant 1：客觀場景主導與感知解耦保證 (Perceptual Scene Primacy Invariant)
- **Scope**：登入、重啟或導航期間的地下城場景定位。
- **Rule**：世界場景 MUST 由客觀感知證據裁決；業務意圖、設定或既有狀態 MUST NOT 排除地下城感知。
- **Observable consequence**：系統重新進入或重啟於地下城時，會交由地下城流程處理，而非以原業務設定覆蓋畫面事實。
- **Allowed variation**：場景特徵、感知器、狀態名稱與設定模型可變更。
- **Verification**：`tests/test_dungeon_relaunch_recovery.py`。

### Invariant 2：探索處理器領域自治保證 (ExploreHandler Domain Autonomy Invariant)
- **Scope**：已確認地下城場景中的探索與離場決策。
- **Rule**：地下城的合法擁有人 MUST 維持可推進或安全離場的領域行為；不相干的業務設定 MUST NOT 令其改用非地下城操作。
- **Observable consequence**：殘留或不相容的設定不會使地下城流程停留在無法推進的操作集合。
- **Allowed variation**：處理器、優先級表示法、操作集合與 fallback 機制可變更。
- **Verification**：`tests/test_dungeon_relaunch_recovery.py`。

### Invariant 3：下樓與進展交互優先於被動錨點保證 (Action-Over-Anchor Priority Invariant)
- **Scope**：地下城內同時可觀測到推進操作與被動維護證據時。
- **Rule**：能推進或完成地下城的操作 MUST 優先於只用於定位或維護的被動證據；被動證據 MUST NOT 阻斷可觀測的進展操作。
- **Observable consequence**：流程不會因反覆處理定位錨點而忽略可用的下樓、確認或完成操作。
- **Allowed variation**：操作排序、互動特徵、錨點、過渡狀態與防卡死資料可變更。
- **Verification**：`tests/test_dungeon_relaunch_recovery.py`。

### Invariant 4：意圖鎖定與對稱還原閉環保證 (Intent Latching & Definitive Restoration Invariant)
- **Scope**：未滿足原業務前置條件卻觀測到地下城的復原流程。
- **Rule**：系統 MUST 保留原業務意圖，先完成地下城的前置離場；只有在觀測到離場後，才可恢復原意圖。尚未恢復的意圖 MUST NOT 被後續偵測重複覆寫。
- **Observable consequence**：意外進入地下城不會遺失原任務，也不會在仍位於地下城時提前恢復原任務。
- **Allowed variation**：意圖保存媒介、離場證據、路由注入與狀態交接可變更。
- **Verification**：`tests/test_dungeon_relaunch_recovery.py`。

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
