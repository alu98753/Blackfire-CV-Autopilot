# 模組化活動與混合調度 (Modular Activity Scheduling) 架構規格書 🏛️

## 1. 架構背景與設計哲學

本架構重構了原本互斥的單一模式，升級為**「以 `COLLECT_ONLY` (定時領取待機) 為基底底座，自由疊加啟用 (Enableable) 週期性任務 (Boss / 地下城 / 城鎮日常)，並將消耗體力的普通關卡打怪解耦為可選模組」**的高強健調度系統。

核心優勢：
- **體力零浪費**：在預設或不打小怪的設定下，當 Boss 與地下城皆處於冷卻時，系統**自動回到城鎮待機 (`COLLECT_ONLY`)**，絕不強制浪費體力刷普通關卡。
- **主動喚醒機制**：在城鎮待機期間，持續監控已啟用的 Boss 與地下城 CD，一旦冷卻結束即刻自動喚醒並轉移至對應流程。

---

## 2. 三層活動調度優先級 (Three-Tier Activity Priorities)

```mermaid
graph TD
    subgraph 🛡️ Tier 0: 永遠運作的內建基底 (Built-in Baseline)
        T0_Bread["🍞 定時領體力 (每 30 分鐘)"]
        T0_Diamond["💎 定時領鑽石 (每 2 小時)"]
        T0_Idle["💤 原地待機 (Collect Only) - 所有任務冷卻時的兜底狀態"]
    end

    subgraph ⚡ Tier 1~3: 週期性低耗體/高收益模組 (Toggleable Periodic Activities)
        T1_Town["🏛️ 每日城鎮速領 (enable_town_daily)<br>神秘寶箱 / 酒館招募 / 血之祭壇 / 珠寶加工"]
        T2_Boss["👑 首領領主討伐 (enable_lord_boss)<br>育母蜘蛛 (1hr CD) / 古代惡靈 (2hr CD)，耗 0 體力"]
        T3_Dungeon["🏰 地下城探索 (enable_dungeon)<br>石窟 / 地穴 / 森林 / 遺跡 / 冰雪 (5~30min CD)，耗 5~10 體力"]
        T3_Quest["📋 懸賞告示牌與動態任務 (enable_quests)<br>主動接單與執行懸賞目標"]
    end

    subgraph ⚔️ Tier 4: 消耗體力的推圖打怪 (Optional Stamina Consumer)
        T4_Stage["🌾 普通關卡打怪 (enable_stage_farming)<br>黃金古國 / 冰凍峽谷 / 蒼穹平原等連續推圖刷裝<br>⚠️ 僅在明確想消耗體力時勾選啟用"]
    end

    T1_Town -->|冷卻/完成| T2_Boss
    T2_Boss -->|冷卻/完成| T3_Dungeon
    T3_Dungeon -->|冷卻/完成| T3_Quest
    T3_Quest -->|冷卻/完成| CheckStage{是否啟用<br>enable_stage_farming?}
    CheckStage -->|是| T4_Stage
    CheckStage -->|否 (純待機)| T0_Idle
    T4_Stage -->|體力不足/退避| T0_Idle
```

---

## 3. 活動開關配置矩陣 (Activity Switches)

在 [config.py](../../config.py) 中透過 `DEFAULT_ACTIVITIES` 定義：

| 活動開關 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `auto_diamond` | `True` | 內建定時領鑽石 (每 2 小時) |
| `auto_bread` | `True` | 內建定時領體力 (每 30 分鐘) |
| `enable_lord_boss` | `True` | 啟用首領領主討伐 (育母蜘蛛、古代惡靈) |
| `enable_dungeon` | `True` | 啟用地下城探索 (黏糊糊石窟、冰雪洞窟等) |
| `enable_town_daily` | `True` | 啟用每日城鎮速領 (寶箱/抽英雄/祭壇/珠寶) |
| `enable_quests` | `False` | 啟用懸賞告示牌與動態任務 |
| `enable_stage_farming` | `False` | 是否在冷卻時前往普通關卡刷怪 (預設關閉保護體力) |

---

## 4. 相關模組與測試保護

* **狀態機核心**：[GameStateMachine](../../states/state_machine.py) 之 `evaluate_next_activity()`
* **待機與喚醒**：[CollectOnlyHandler](../../states/handlers/collect_only.py)
* **導航與頁籤**：[NavigationHandler](../../states/handlers/navigation.py)
* **行為測試**：[test_behavior_modular_activities.py](../../tests/test_behavior_modular_activities.py)、[test_behavior_navigation.py](../../tests/test_behavior_navigation.py)
