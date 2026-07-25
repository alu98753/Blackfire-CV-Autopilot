# 每日懸賞任務 (Daily Quest Scheduler) 自動化架構與技術棧研究報告 📜🤖

本報告針對 《Blackfire Crusade》 每日懸賞任務的「自動點擊領取」、「畫面/任務內容辨識」與「動態指令排程與維護 (Dynamic CLI Task Scheduler)」進行深度的技術棧探討與架構設計。

---

## 📸 懸賞任務素材與場景分析 (Daily Quest Archetypes)

歸檔素材目錄位於 `templates/town_building/bulletin_board/Daily_task/`，分析懸賞任務可歸納為以下 4 大經典類型：

| 任務名稱範例 | 任務描述 / 目標條件 | 對應的腳本啟動指令與模式 (`main.py` CLI) | 優先級 / 合併策略 |
| :--- | :--- | :--- | :--- |
| **1. 史萊姆王的毀滅** | 踏入黏糊糊的石窟，擊敗史萊姆王 x 1 | `.venv\Scripts\python main.py --mode dungeon` (選擇 1: 黏糊糊的石窟) | 地下城專屬 (高優先，CD 中可掛起) |
| **2. 擊敗冰元素** | 在寒冷地區擊敗冰元素 x 10 | `.venv\Scripts\python main.py --mode stage` (選擇 6: 冰雪洞窟, 第一小關 first) | 普通關卡標的 |
| **3. 清除野豬** | 破壞農田與村莊，消滅野豬 x 10 | `.venv\Scripts\python main.py --mode stage` (選擇 1: 蒼穹平原, 魔王關 final) | 普通關卡標的 |
| **4. 擊殺首領** | 追蹤並擊殺首領 x 5 | 可由任何 `dungeon` 通關或 `stage` 的 `final` 魔王關覆蓋 | **相容性任務** (可與其他關卡任務重疊推進) |
| **5. 清除骷髏 / 熊** | 消滅骷髏 / 熊 x 10 | 對應關卡 (如 Level 2 荒蕪岩地 / Level 3 古樹森林) | 普通關卡標的 |

---

## 🛠️ 技術棧可行性與評估 (Technical Stack Evaluation)

針對「任務辨識 (Perception)」與「動態指令維護 (Planning & Scheduling)」，我們評估了以下三種技術路線：

### 1. 感知層技術棧 (Perception: OCR vs. Vision LLM)

| 技術方案 | 執行延遲 | 成本與資源 | 準確度與強健性 | 適用場景 |
| :--- | :--- | :--- | :--- | :--- |
| **A. 本地 EasyOCR / RapidOCR** | ⚡ **~50ms** | 0 成本，純 CPU 運算 | 優秀 (繁體中文文本清晰時)，需圖像裁切與預處理 | 定點懸賞面板文字辨識 |
| **B. Vision LLM (Gemini 2.0 Flash / GPT-4o-mini API)** | 🐢 **~800ms** | 極低 API 費用 | 💯 **100% 語意理解**，完全無懼介面變動或特殊字體 | 複雜非結構化任務說明 |

### 2. 排程層技術棧 (Planner: Keyword Rule Engine vs. LLM Dynamic Agent)

#### 方案一：硬編碼關鍵字正則映射 (Keyword & Regex Rule Engine)
- **原理**：使用 Regex / 關鍵字映射字典（如 `r"(史萊姆王|黏糊糊的石窟)" => ("dungeon", 1)`）。
- **優勢**：極速、100% 可預測、不消耗 API token、單元測試極易驗證。
- **劣勢**：遊戲新增未知任務時需擴充字典。

#### 方案二：LLM 語意動態 Agent 排程 (LLM Dynamic Quest Agent)
- **原理**：將任務標題與說明文字打包輸入給 LLM (系統 Prompt 帶入腳本所有支援的 CLI 選項與地圖資料庫)，由 LLM 自動輸出 JSON 格式的執行鏈 (`ExecutionPlan`)。
- **優勢**：無需維護字典，即使遊戲出現新文案（例如：「寒霜霸主」）LLM 也能自動推理出需打冰雪洞窟魔王關。
- **劣勢**：依賴網路 API，需有 Structured Output 驗證防範幻覺 (Hallucination)。

#### 方案三 (推薦最佳解)：混合雙引擎架構 (Hybrid Perception & Planning Architecture) 🏆
- **主路徑 (Fast Path - Local Engine)**：優先使用在地端 EasyOCR + 關鍵字字典 (Regex Mapping) 進行 0 毫秒極速比對。
- **備用/自學習路徑 (Fallback Path - LLM Agent)**：當關鍵字字典比對失敗（遇到未登記的新任務）時，自動調用 LLM 進行語意解析，並自動將解析結果**快取更新至本機字典**中！

---

## 📐 架構設計與動態任務佇列維護 (Dynamic Maintain Workflow)

為了實現「領取任務 ➔ 動態建立腳本指令 ➔ 執行並動態 Maintain 佇列」，系統架構設計如下：

```mermaid
flowchart TD
    A[進入城鎮懸賞任務介面] --> B[領取所有懸賞任務]
    B --> C[擷取懸賞任務列表畫面]
    C --> D[OCR / VLM 解析任務內容]
    D --> E{關鍵詞字典匹配?}
    E -- 匹配成功 --> F[生成 TaskNode (規則映射)]
    E -- 匹配失敗 --> G[呼叫 LLM 語意 Agent 解析 JSON]
    G --> H[寫入本機快取字典] --> F
    F --> I[動態建構 ExecutionQueue 任務佇列]
    I --> J[依序執行任務腳本 (dungeon / stage / mix)]
    J --> K{檢查任務完成標誌?}
    K -- 未完成 --> J
    K -- 已完成 --> L[從佇列彈出 TaskNode]
    L --> M{佇列是否全空?}
    M -- 否 --> J
    M -- 是 --> N[返城領取獎勵，全流程完成 🎉]
```

### 動態佇列與任務合併優化 (Task Merging Strategy)：
- **相容性任務合併 (Task Piggybacking)**：
  - 例如同時有 `擊殺首領 x 5` 與 `史萊姆王 x 1`。
  - 腳本在執行 `史萊姆王 (dungeon 1)` 時，自動算作 1 次首領擊殺；後續在打普通關卡魔王關 (`stage final`) 時，可同時推進首領擊殺進度，避免重複打無效關卡！

---

## 🚀 階段性實作規劃 Todo List (Implementation Roadmap)

- [x] **Phase 1: 懸賞任務對照與動態排程器 (Task 2)**
  - [x] **素材歸檔**：將 5 張真實每日懸賞任務截圖歸檔存至 [Daily_task](file:///e:/Side_Project/BlackfireCrusade_tool/templates/town_building/bulletin_board/Daily_task) 目錄。
  - [x] **語意映射器 (`QuestMapper`)**：實作 [quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py)，將文字/目標反向解析為標準 `TaskNode` 與 CLI 啟動指令。
  - [x] **動態佇列維護器 (`QuestScheduler`)**：實作 [quest_scheduler.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_scheduler.py)，維護任務佇列與併行計算 (Task Piggybacking)。
  - [x] **單元測試驗證**：在 [test_quest_mapper_and_scheduler.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_quest_mapper_and_scheduler.py) 完成對照測試 (100% PASS)。

- [x] **Phase 2: 懸賞告示牌面板自動點擊與辨識 (Task 1)**
  - [x] **告示牌建築定位與進入**：在城鎮畫面左上 1/4 區域掃描 `bulletin_board.png` 點擊進入懸賞告示牌介面。
  - [x] **條件式重置與任務接取**：掃描並點擊 `reset.png`，逐列鎖定最上方未接任務 (`task.png`) 點擊右側 `accept_task.png`。
  - [x] **懸賞列表 EasyOCR 視覺解析**：使用 EasyOCR (`['ch_tra', 'en']`) 進行 ROI 放大 2 倍預處理與標題精確提取。
  - [x] **相對優勢過濾與任務已滿防護**：相對比對 `task_after.png` 跳過已接取任務，點擊 `accept_task.png` 後判斷 `task_already_full.png` 自動 `confirm` 離場。

- [x] **Phase 3: 端到端自動化閉環整合 (End-to-End Integration)**
  - [x] **佇列接管與調度**：領取任務後自動寫入 `user_data/daily_status.json` 的 `accepted_quests`，供 `QuestScheduler` 生成動態任務佇列。
  - [x] **持久化與單元測試閉環**：完全整合至 `DailyManager` 08:05 重置機制與單元測試套件 (100% PASS)。
