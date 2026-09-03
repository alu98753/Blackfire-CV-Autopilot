# 每日懸賞任務與 Daily Master Pipeline 自動化架構報告 📜🤖

本報告針對 《Blackfire Crusade》 每日任務與懸賞體系的「自動領取」、「任務內容辨識」與「Daily Master Pipeline 全域動態排程」進行深度的技術棧探討與架構設計。

---

## 📸 懸賞任務素材與場景分析 (Daily Quest Archetypes)

歸檔素材目錄位於 `templates/town_building/bulletin_board/Daily_task/`，懸賞任務歸納為以下 4 大經典類型：

| 任務名稱範例 | 任務描述 / 目標條件 | 對應的動態排程指令與模式 | 優先級 / 處理策略 |
| :--- | :--- | :--- | :--- |
| **1. 史萊姆王的毀滅** | 踏入黏糊糊的石窟，擊敗史萊姆王 x 1 | 懸賞主模式 `.venv\Scripts\python main.py --mode daily` 自動派發地下城 1 | 地下城專屬 (高優先，冷卻時自動跳過先打其他任務) |
| **2. 擊敗冰元素** | 在寒冷地區擊敗冰元素 x 10 | `--mode daily` 自動派發關卡 (6 冰凍峽谷 first) | 普通關卡標的 |

| **3. 清除野豬** | 消滅野豬 x 10 | `--mode daily` 自動派發關卡 (1 蒼穹平原 final) | 普通關卡標的 |
| **4. 擊殺首領** | 追蹤並擊殺首領 x 5 | 可由任何 `dungeon` 通關或 `stage` 的 `final` 魔王關覆蓋 | **相容性任務** (可與其他關卡任務重疊推進) |
| **5. 清除骷髏 / 樹人** | 消滅骷髏 / 樹人 x 10 | 自動對照地下城 (3: 神秘遺跡 / 2: 森林迷宮) | 地下城優先專屬 |

---

## 🛠️ 技術棧可行性與評估 (Technical Stack Evaluation)

### 1. 感知層技術棧 (Perception: Local OCR vs. Vision LLM)

| 技術方案 | 執行延遲 | 成本與資源 | 準確度與強健性 | 適用場景 |
| :--- | :--- | :--- | :--- | :--- |
| **A. 本地 EasyOCR / RapidOCR** 🏆 | ⚡ **~50ms** | 0 成本，純 CPU 運算 | 優秀 (繁體中文文本清晰時)，已實作 2 倍 ROI 預處理 | 定點懸賞面板文字辨識 |
| **B. Vision LLM (Gemini 2.0 Flash / GPT-4o-mini API)** | 🐢 **~800ms** | 極低 API 費用 | 💯 **100% 語意理解** | 複雜非結構化未定義新任務說明 |

### 2. 排程層技術棧 (Planner: Master Pipeline + Multi-tier Priority Engine)

#### 四階梯全域動態優先級 (Master Priority Hierarchy)：
1. **Tier 1: 一極優先 (每日一次性城鎮速領)**：`chest` (寶箱) ➔ `hero_draw` (抽卡) ➔ `blood_altar` (祭壇獻祭 + 珠寶賣裝)。
2. **Tier 2: 二極優先 (領主 Boss 討伐 `lord_boss`)**：優先級大於 `bulletin_board`！具備蜘蛛 (1hr) / 惡靈 (2hr) 冷卻倒數與 5 次上限維護；當冷卻到期且尚有場次，**戰鬥結算回到大廳時立刻搶先插隊討伐 Boss！**
3. **Tier 3: 三極優先 (懸賞告示牌與動態任務 `bulletin_board`)**：告示牌取卡與 8 個懸賞任務佇列多階梯排序執行。
4. **Tier 4: 四極長駐（玩家 Profile 路由）**：週期活動暫無可執行項目時，依玩家選擇長駐 `stage` 或 `domain`；目前領地支援黃金古國。地下城與 Lord 預設啟用，冷卻完成後會插隊。


---

## 📐 Daily Master Pipeline 架構流程圖 (Workflow)

```mermaid
flowchart TD
    A[啟動 python main.py --mode daily] --> B{DailyManager 檢查 Tier 1 城鎮速領?}
    B -- 有未領項目 --> C[連貫執行 chest -> hero_draw -> blood_altar] --> B
    B -- Tier 1 已全完成 --> D{檢查 Tier 2 Lord Boss 可用狀態?}
    D -- Boss CD 完成且場次<5 --> E[搶先插隊執行 lord_boss 討伐] --> D
    D -- 無可用 Boss / CD 中 --> F{檢查 Tier 3 懸賞告示牌與任務?}
    F -- 有未接任務 --> G[進入告示牌取卡 EasyOCR 辨識 accepted_quests] --> H[QuestScheduler 多階梯排序調度]
    F -- 懸賞任務進行中 --> H
    H --> I[執行戰鬥任務 (dungeon / stage)]
    I --> J{戰鬥結算回到大廳: 是否有 Boss CD 剛到期?}
    J -- 是 (Boss ready) --> E
    J -- 否 --> K{懸賞任務是否全數 completed?}
    K -- 否 --> H
    K -- 是 (100% 完成) --> L{Tier 4 玩家設定}
    L -- stage --> M[指定大關與小關]
    L -- domain --> N[指定領地: 黃金古國]
    M --> J
    N --> J
```

---

## 🏛️ CLI 模式分工規範 (CLI Usage Rules)

- **主運作模式 (`--mode daily`)**：
  日常全自動長途掛機運作的**唯一主要入口**。所有速領、Boss 倒數討伐、懸賞佇列與退守關卡皆由全域動態流水線接管。

- **Dev 獨立測試旗標 (`--subflow <name>`)**：
  **僅供開發者在單體測試或除錯時使用**。單獨測試指定子流程，測試完畢自動結束程式：
  - `python main.py --backend --subflow chest` (獨立測試寶箱)
  - `python main.py --backend --subflow lord_boss` (獨立測試打 Boss)

---

## 🚀 實作完成清單 (Implementation Status)

- [x] **Phase 1: 懸賞對照與動態排程器**：實作 `QuestMapper` 與 `QuestScheduler` 多階梯排序 (100% PASS)。
- [x] **Phase 2: 告示牌自動領取與 OCR 辨識**：EasyOCR 2 倍 ROI 預處理與相對優勢過濾 (`task_after.png`)。
- [x] **Phase 3: Daily Master Pipeline 四階梯全域串接**：
  - [x] 整合 `chest` ➔ `hero_draw` ➔ `blood_altar` 速領。
  - [x] 實作 `lord_boss` 倒數計時器維護與**戰鬥結束即時搶先插隊機制** (優先級 > `bulletin_board`)。
  - [x] 實作懸賞任務全完結後自動退守 **5) 冰雪洞窟** 與 **6-1 關卡**。
  - [x] 完成全套單元與串接測試套件 `tests/test_daily_pipeline_orchestration.py` (193 項測試 100% PASS 綠燈)。
