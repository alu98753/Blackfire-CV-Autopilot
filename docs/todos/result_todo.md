# Greenfield-lite M7 子切片：戰鬥結算與地下城通關閉環 (Result & Dungeon Exit)

> **關聯規格**：[`docs/architecture/project_arch_greenfield_lite_v1.md`](../architecture/project_arch_greenfield_lite_v1.md)  
> **關聯交接**：[`docs/architecture/greenfield_lite_implementation_handoff.md`](../architecture/greenfield_lite_implementation_handoff.md)  
> **目標**：以 Greenfield-lite 架構的純淨方式，解決「戰鬥結算點完 Continue 後卡頓 11 秒超時退回 UNKNOWN，無法順暢點擊 dungeons_complete 退出」的架構問題。

---

## 一、核心架構釐清與邊界定義

### 1. 場景語意界限 (Scene Semantic Boundary)
* **`SceneId.RESULT`（戰鬥結算彈窗）**：
  * **純粹指「單場戰鬥（Battle）結束後的勝負結算彈窗」**（VICTORY / DEFEAT，包含經驗值、金幣與掉落物展示，底部有 `common/continue.png`）。
  * 包含所有模式（普通關卡、地下城、首領戰、深淵魔王）的單場戰鬥勝負。
  * **`RESULT` Profile 僅能感知結算彈窗本身**（`continue.png`、`retry.png`、`defeat.png`），**絕對禁止**掃描地下城地圖元素。
* **`SceneId.DUNGEON_EXPLORING`（地下城探索場景）**：
  * **`dungeons/dungeons_complete.png` 100% 屬於地下城探索場景**，代表「地下城最終層 Boss 討伐完成後在地圖上顯現的通關大寶箱/完成圖示」。
  * 它不是結算彈窗的一部分，而是結算彈窗關閉後，在地圖上承接通關退場的遊戲物件。

---

## 二、多模式結算問題：並非每次 RESULT 都回到 DUNGEON_EXPLORING

### 問題根源
在遊戲中，單場戰鬥結算點擊 `continue.png` 後，後續場景取決於當前運行的業務模式：
1. **地下城（Dungeon）** ➔ 關閉彈窗，回到地圖：`SceneId.DUNGEON_EXPLORING`（小怪層出現下樓箭頭，Boss 層出現 `dungeons_complete.png`）。
2. **普通關卡（Stage）** ➔ 關閉彈窗，進入再戰/離場選擇：出現 `stages/retry.png` 或 `exit_battle.png`。
3. **首領討伐（Lord Boss）** ➔ 關閉彈窗，直接回到首領選擇面板：`SceneId.LORD_SELECT`。
4. **深淵魔王（Demon Lords）** ➔ 關閉彈窗，直接回到魔王選擇面板：`SceneId.DEMON_LORD_SELECT`。
5. **領地探索（Domain）** ➔ 關閉彈窗，回到領地地圖：`SceneId.DOMAIN_EXPLORE`。

因此，**點擊 `CLICK_CONTINUE` 的 Postcondition 絕不能寫死為 `SceneId.DUNGEON_EXPLORING`**。

### 架構解決方案：語意化 Postcondition (`RESULT_DISMISSED`)
依據 Greenfield-lite 的「One turn, one decision」與「單幀不可變 Snapshot」：
* **`CLICK_CONTINUE` 的唯一職責**：將「戰鬥結算彈窗關閉，離開 RESULT 場景」。
* **驗證後置條件 (`PostconditionId.RESULT_DISMISSED`)**：
  下一幀畫面**「不再是 `SceneId.RESULT`，且成功轉移至任何已知合法的業務目標場景」**：
  ```python
  VALID_POST_RESULT_SCENES = {
      SceneId.DUNGEON_EXPLORING,
      SceneId.LOBBY,
      SceneId.STAGE_SELECT,
      SceneId.LORD_SELECT,
      SceneId.DEMON_LORD_SELECT,
      SceneId.DOMAIN_EXPLORE,
  }
  ```
* **職責接力**：
  只要彈窗成功消除，下一幀由感知層識別出**具體新場景**（例如識別為 `DUNGEON_EXPLORING`），隨後交由該場景在 `NavigationTable` 中宣告的專屬 Edge 進行下一步決策。

---

## 三、失敗處理與有界重試機制 (Bounded Failure Handling)

如果發出 `CLICK_CONTINUE` 或 `COMPLETE_DUNGEON` 後點擊未生效，Greenfield-lite 的因果處置如下：

```text
發出 Action (attempt=1)
  │
  ├─ 下一幀檢測 (約 50ms) ➔ 畫面未變 (仍為 RESULT)
  │    └─ now < deadline (5.0s) ➔ ProgressStatus.WAITING (不發任何新動作，等待過場動畫定格)
  │
  ├─ 若 5.0 秒持續未變 ➔ ProgressStatus.TIMED_OUT
  │    └─ 下一輪 Tick 重新檢視 Snapshot ➔ 發動 ACTION_TIMEOUT_RETRY (attempt=2)
  │
  └─ 連續重試滿 3 次 (action_max_attempts) 仍失敗 ➔ 判定為遊戲卡死/假死
       └─ 升級至 ProcessPort.relaunch() (重啟遊戲並自癒恢復)
```

**架構保證**：絕不使用 `while` 迴圈連續連點，絕不在 Handler 內 `time.sleep`，完全由單幀 Snapshot 與 monotonic clock 進行無阻斷有界觀測。

---

## 四、改動全貌與架構分層（共 6 個檔案）

依據 Greenfield-lite 資料流：
`Capture` ➔ `Perception (Snapshot)` ➔ `Policy (NavigationTable)` ➔ `Decision` ➔ `InFlightAction` ➔ `Postcondition 驗證`

| 分層 | 檔案 | 改動內容 |
| :--- | :--- | :--- |
| **1. 契約定義** | [`utils/scene_snapshot.py`](../utils/scene_snapshot.py) | 新增 `ElementId.CONTINUE` 與 `ElementId.DUNGEONS_COMPLETE`，並在 template map 建立映射 |
| **2. 感知排程** | [`utils/detector_registry.py`](../utils/detector_registry.py) | 在 `RESULT` profile 允許 `continue.png`；在 `DUNGEON_SELECT` / `DUNGEON` profile 允許 `dungeons_complete.png`（嚴格分層） |
| **3. 意圖與決策** | [`states/navigation_intent.py`](../states/navigation_intent.py) | 定義語意動作：`ActionId.CLICK_CONTINUE`、`ActionId.COMPLETE_DUNGEON`，以及通用後置條件 `PostconditionId.RESULT_DISMISSED` |
| **4. 宣告式路由** | [`states/navigation_table.py`](../states/navigation_table.py) | 註冊兩條確定性的 `NavigationEdge`（結算退出 ➔ 地圖；地圖通關 ➔ 大廳） |
| **5. 行動與進展** | [`states/navigation_progress.py`](../states/navigation_progress.py) | 實作 `RESULT_DISMISSED` 與 `LOBBY` 驗證；在通關確認的 Commit Point 提交通關計數與冷卻設定 |
| **6. Handler 接線** | [`states/handlers/result.py`](../states/handlers/result.py) | 移除私有 `subflow_step` 與內部 while 輪詢，改為消費 Snapshot 與 Navigation 決策 |

---

## 五、具體代碼規格

### 1. 契約層：[`utils/scene_snapshot.py`](../utils/scene_snapshot.py)
```python
class ElementId(str, Enum):
    # ...
    CONTINUE = "continue"
    DUNGEONS_COMPLETE = "dungeons_complete"

_ELEMENT_TEMPLATE_MAP = {
    # ...
    "common/continue.png": ElementId.CONTINUE,
    "dungeons/dungeons_complete.png": ElementId.DUNGEONS_COMPLETE,
}
```

### 2. 感知排程層：[`utils/detector_registry.py`](../utils/detector_registry.py)
確保 Scoped Perception 職責明確：
```python
# continue.png 屬於戰鬥結算元素
if template_name in {"common/continue.png", "stages/retry.png", "exit_battle.png"}:
    return DetectorGroup.RESULT

# dungeons_complete.png 屬於地下城探索元素
if template_name.startswith("dungeons/"):
    return DetectorGroup.DUNGEON
```
* `DetectionProfileId.RESULT` 允許 `DetectorGroup.RESULT` 與 `DetectorGroup.SAFETY`。
* `DetectionProfileId.DUNGEON_SELECT` / 地下城探索允許 `DetectorGroup.DUNGEON`。

### 3. 意圖與後置條件：[`states/navigation_intent.py`](../states/navigation_intent.py)
```python
class ActionId(str, Enum):
    # ...
    CLICK_CONTINUE = "click_continue"
    COMPLETE_DUNGEON = "complete_dungeon"

class PostconditionId(str, Enum):
    # ...
    RESULT_DISMISSED = "result_dismissed"  # 結算彈窗關閉且進入合法新場景
    LOBBY_OR_DOOR = "lobby_or_door"        # 回到大廳或看見大門

class ReasonCode(str, Enum):
    # ...
    PRIMARY_RESULT_CONTINUE = "primary_result_continue"
    PRIMARY_DUNGEON_COMPLETE = "primary_dungeon_complete"
```

### 4. 路由表：[`states/navigation_table.py`](../states/navigation_table.py)
```python
V1_NAVIGATION_EDGES = (
    # ... 原有 Edge ...
    
    # 邊 1：結算畫面見 continue -> 點擊 continue -> 期望彈窗關閉轉移至業務場景
    NavigationEdge(
        intent_id=IntentId.PRIMARY_NAVIGATION,
        source=SceneId.RESULT,
        target=SceneId.UNKNOWN,  # 目的地由後續具體業務場景接管
        required_element=ElementId.CONTINUE,
        action=ActionId.CLICK_CONTINUE,
        postcondition=PostconditionId.RESULT_DISMISSED,
        reason=ReasonCode.PRIMARY_RESULT_CONTINUE,
    ),
    
    # 邊 2：地下城通關畫面見 dungeons_complete -> 點擊完成 -> 期望回到大廳
    NavigationEdge(
        intent_id=IntentId.PRIMARY_NAVIGATION,
        source=SceneId.DUNGEON_EXPLORING,
        target=SceneId.LOBBY,
        required_element=ElementId.DUNGEONS_COMPLETE,
        action=ActionId.COMPLETE_DUNGEON,
        postcondition=PostconditionId.LOBBY_OR_DOOR,
        reason=ReasonCode.PRIMARY_DUNGEON_COMPLETE,
    ),
)
```

### 5. 進展驗證與業務副作用提交：[`states/navigation_progress.py`](../states/navigation_progress.py)
```python
@staticmethod
def _postcondition_met(expected, scene):
    # ...
    if expected == PostconditionId.RESULT_DISMISSED:
        # 結算彈窗已關閉，且當前幀已屬於任一合法業務場景
        return scene.scene in {
            SceneId.DUNGEON_EXPLORING,
            SceneId.LOBBY,
            SceneId.STAGE_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
            SceneId.DOMAIN_EXPLORE,
        }
    if expected == PostconditionId.LOBBY_OR_DOOR:
        from utils.scene_snapshot import ElementId
        return scene.scene == SceneId.LOBBY or scene.has(ElementId.DOOR)
    return False
```
* **業務副作用提交 (Commit Point)**：
  當 `COMPLETE_DUNGEON` 的後置條件 `LOBBY_OR_DOOR` 驗證通過時，由進展提交鉤子（Hook）執行地下城通關次數累加 (`run_count += 1`) 與動態冷卻時間寫入，保證「點擊不等於成功，畫面確認回到大廳才提交進度」。