# 重構場景定位 (Scene Recognition) 與導航 (Navigation) 解耦實作計畫與規格書 (Spec)

本計畫旨在解耦原本過於龐大且職責混雜的 [navigation.py](../../states/handlers/navigation.py)，抽離出專屬的 **場景定位辨識器 (`SceneDetector`)** 與結構化 **`SceneInfo`** 資料物件，實現「**定位歸定位、導航歸導航**」的單一職責架構 (Single Responsibility Principle)。

## 待完成

還有以下場景需要定位

1.  在town 還有 珠寶店 血祭壇 , 酒館(抽英雄  每個要各自用各自的圖片定位(可以從--subflow看)

假設在這些房子裡面 但要回town 可以用 
[exitfromhouse_and_to_town.png](../../templates/town_building/exitfromhouse_and_to_town.png) 判斷在內部 並點後 就會回town


2. 打lord 的時候 怎麼知道現在確實在大廳 且 lord ,可以用[Lord_entry.png](../../templates/load/Lord_entry.png)[Lord_entry_after.png](../../templates/load/Lord_entry_after.png)[lord_spectre.png](../../templates/load/lord_spectre.png)[lord_spider.png](../../templates/load/lord_spider.png)  和gobacktown 來確認

---

## 🎯 重構核心目標

1. **職責分離 (Separation of Concerns)**：
   - `SceneDetector` 只負責「看」（畫面範本比對、頁籤辨識與狀態診斷），產出 `SceneInfo`，絕不進行點擊或狀態轉移。
   - `NavigationHandler` 只負責「走」（讀取 `SceneInfo` 診斷結果發射點擊或切換 State）。
2. **單一事實來源 (Single Source of Truth)**：
   - 解決散落於 `navigation.py` 各處的 `matcher.match()` 圖案硬編碼比對問題。
3. **100% 零破壞性相容**：
   - 在完整的 280 項行為測試防護網保護下完成，保證外顯 behavior 完全不受影響。

---

## 📐 Technical Specification (詳細規格書：各 SceneType 判定依據與優先順序)

`SceneDetector.detect(screen_img, machine_state=None, machine=None)` 將嚴格按照以下 **優先級階層 (Priority Order)** 進行判斷：

```
[階段 0: 彈窗/視窗] ➔ [階段 1: 地下城內部] ➔ [階段 2: 備戰對話框] ➔ [階段 3: 城鎮與大廳指標] ➔ [階段 4: 頁籤互斥與模板備援]
```

### 各 `SceneType` 精確判定細節對照表

| SceneType | 依據與圖檔 (Templates / State Flags) | OpenCV 閾值 (Threshold) | 原始碼對照與判定邏輯 |
| :--- | :--- | :--- | :--- |
| **`POPUP_TASK_COMPLETE`** | `task_complete.png` | `threshold = 0.75` | 原 `navigation.py` L171。<br>**全域最高優先**：畫面上出現任務獎勵完成彈窗，優先攔截。 |
| **`WINDOW_DIAMOND`** | `machine.diamond_window_opened` | 狀態標記位 (`True`) | 原 `navigation.py` L231。<br>記憶體標記鑽石視窗已開啟。 |
| **`WINDOW_BREAD`** | `machine.bread_window_opened` | 狀態標記位 (`True`) | 原 `navigation.py` L237。<br>記憶體標記體力視窗已開啟。 |
| **`IN_DUNGEON`** | `dungeons/leave.png`<br>`dungeons/dungeon_bless.png`<br>`dungeons/Treasure.png`<br>`dungeons/gungeon_godown.png` | `threshold = 0.80`<br>(僅當 `config.type` 包含 `dungeon`/`mix`) | 原 `navigation.py` L183-189。<br>匹配到上述任一內部特徵，代表已進入戰鬥/探索地圖內部。 |
| **`DUNGEON_PREPARE`** | `dungeons/dungeon_fight.png` | `threshold = 0.80`<br>(僅當 `config.type` 包含 `dungeon`/`mix`) | 原 `navigation.py` L193-199。<br>畫面上出現出擊戰鬥按鈕，但尚未看見 `leave.png` 等內部圖案。 |
| **`TOWN`** | `common/door.png` (大門)<br>`diamond.png` (領鑽石) | `threshold = 0.80` | 原 `navigation.py` L244-247。<br>匹配到大門或鑽石圖示，判定在城鎮主畫面。當為城鎮時，頁籤皆強制的為未開啟 (`False`)。 |
| **`LOBBY_STAGE`** | 1. 基礎標誌：`goback_town.png` 或 `common/bread.png`<br>2. 頁籤與備援：`common/select_stage_after.png` 或 `config.stage_templates` | 基礎 `0.80`<br>頁籤互斥 `0.70`<br>`margin = 0.02`<br>關卡模板 `0.75` | 原 `navigation.py` L249-295。<br>大廳指標存在且非城鎮。頁籤比對使用 `match_mutually_exclusive_tabs`，`stage_after` 比 `dungeon_after` 信心度高出 0.02 且 $\ge 0.70$；或掃描到 `stage_templates` 中之關卡封面。 |
| **`LOBBY_DUNGEON`** | 1. 基礎標誌：`goback_town.png` 或 `common/bread.png`<br>2. 頁籤與備援：`dungeons/dungeon_after.png` 或 `config.dungeon_entries` / `common/locked_entry.png` | 基礎 `0.80`<br>頁籤互斥 `0.70`<br>`margin = 0.02`<br>入口 `0.60`<br>鎖定 `0.75` | 原 `navigation.py` L249-295 & L415-430。<br>大廳指標存在且非城鎮。`dungeon_after` 信心度顯著高於 `stage_after`；或配對到地下城入口卡片 (`dungeon_entries`) 或 `locked_entry.png`。 |
| **`LOBBY_OTHER`** | 基礎標誌：`goback_town.png` 或 `common/bread.png` | `threshold = 0.80` | 原 `navigation.py` L249-253。<br>大廳指標存在，但既未選中普通關卡頁籤，也未選中地下城頁籤（例如在其他子頁面）。 |
| **`UNKNOWN`** | 無匹配項目 | N/A | 無法比對到任何上述標誌，屬於動畫切換中、讀條或未知 UI 視窗。 |

---

## 💻 資料結構與模組 API 規格

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

class SceneType(Enum):
    TOWN = auto()                 # 城鎮主畫面
    LOBBY_STAGE = auto()          # 活動大廳 - 普通關卡頁籤開啟
    LOBBY_DUNGEON = auto()        # 活動大廳 - 地下城頁籤開啟
    LOBBY_OTHER = auto()          # 活動大廳 - 其他頁籤
    IN_DUNGEON = auto()           # 地下城內部戰鬥/探索中
    DUNGEON_PREPARE = auto()      # 地下城備戰畫面 (戰鬥開始按鈕)
    POPUP_TASK_COMPLETE = auto() # 任務完成彈窗
    WINDOW_DIAMOND = auto()       # 鑽石領取視窗已開啟
    WINDOW_BREAD = auto()         # 體力領取視窗已開啟
    UNKNOWN = auto()              # 未知/切換中

@dataclass
class SceneInfo:
    scene_type: SceneType
    is_town: bool = False
    is_lobby: bool = False
    is_in_dungeon: bool = False
    is_dungeon_prepare: bool = False
    active_tabs: List[str] = field(default_factory=list) # ["stage"], ["dungeon"]
    matched_elements: Dict[str, Tuple[Tuple[int, int], float]] = field(default_factory=dict)
```

---

## 🛠️ Proposed Changes

### 1. 新增場景定位模組 [scene_detector.py](../../utils/scene_detector.py)
- 實作 `SceneType`、`SceneInfo` 與 `SceneDetector`。

### 2. 新增定位單元測試 [test_scene_detector.py](../../tests/test_scene_detector.py)
- 針對 `SceneDetector` 各診斷分支進行獨立驗證。

### 3. 重構尋路分發器 [navigation.py](../../states/handlers/navigation.py)
- 注入 `SceneDetector`，將 `handle()` 內的傳統散落比對升級為讀取 `SceneInfo` 的高階分發判斷。

---

## 🧪 Verification Plan

### Automated Tests
1. **執行全新 SceneDetector 單元測試**：
   ```bash
   .venv\Scripts\python -m unittest tests.test_scene_detector
   ```
2. **執行行為測試防護網 (280/280 PASS)**：
   ```bash
   .venv\Scripts\python -m unittest tests.test_behavior_navigation
   .venv\Scripts\python -m unittest discover tests
   ```

### Manual Verification
- 審查 `navigation.py` 代碼結構與行數，確認無重複的比對邏輯並大幅降低複雜度。