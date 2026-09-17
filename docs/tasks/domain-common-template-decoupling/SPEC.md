# Task Specification: 領域通用模板與行為抽離 (Domain Common Template & Behavior Decoupling)

Status: Final

## 1. 摘要與背景 (Summary & Motivation)

先前版本中，領域主場景探索按鈕 (`explore_btn.png`) 與隨機挖寶事件三件套（`open.png`、`find_treasure.png`、`treasure.png`）被放置在 `templates/domains/golden_empire/` 目錄下，且程式碼多處寫死古國路徑，甚至將所有未註冊領域靜默 fallback 至 `GoldenEmpireStrategy`。

實際上，上述按鈕與事件為整個領地系統（Domain Framework）之通用行為，適用於所有領域（Domain 1: 黃金古國、Domain 2: 淵獸之巢、Domain 3: 冷誓要塞等）。

本任務將這 4 個資源與行為自黃金古國徹底解耦，移入 `templates/domains/common/`，並依據 Greenfield-lite v1 架構規範建立獨立通用模組 `DomainTreasureSubflow` 與通用領域策略 `GenericDomainStrategy`，使通用行為完全獨立於 `GoldenEmpireStrategy`。

## 2. 嚴格不變量 (Strict Invariants)

### 2.1 架構與領域不變量 (Architecture Invariant)
1. **通用行為獨立性**：Generic/common domain behavior 絕不得依賴 `GoldenEmpireStrategy` identity。
2. **古國特異職責邊界**：`GoldenEmpireStrategy` 僅為黃金古國專屬行為之持有者（如專屬卡片入口、專屬 Boss、專屬祭壇等）。
3. **消除靜默回退**：未註冊或尚未具備專屬策略之合法領域（如 `abyss_beast_nest`），工廠方法 `get_domain_strategy()` 必須回傳 `GenericDomainStrategy` 並保留其自身 `domain_name`，嚴禁靜默 fallback 至 `GoldenEmpireStrategy`，避免引起每 tick 策略無效重建。

### 2.2 挖寶語意契約不變量 (Treasure Semantic Invariant)
1. **特徵集合契約**：
   - `domains/common/open.png`
   - `domains/common/find_treasure.png`
   - `domains/common/treasure.png`
   三者皆屬於 `DomainTreasureSubflow` 的 common treasure evidence contract。
2. **行動與場景證據分工**：
   - `open.png` 為直接 **actionable evidence**，觸發單次免費開箱、確認與退出閉環。
   - `find_treasure.png` 與 `treasure.png` 為 **treasure-scene evidence**，代表畫面已進入挖寶事件。
3. **Unknown never guesses**：
   若畫面僅觀測到 `find_treasure.png` / `treasure.png` 場景證據但未出現合法免費 `open.png`（如正在加載或僅剩付費寶箱），Handler 必須認領本 frame（判定事件已命中），**嚴禁猜測座標點擊寶箱或付費項目**，亦不得盲點穿透至底層探索按鈕，保持安全等待下一輪觀測。

### 2.3 路徑 SSOT 不變量 (Path SSOT Invariant)
1. 領域主場景探索按鈕之唯一正規路徑為 `domains/common/explore_btn.png`。
2. 領域隨機挖寶事件之唯一正規路徑為：
   - `domains/common/open.png` (免費開箱按鈕)
   - `domains/common/find_treasure.png` (事件視窗特徵)
   - `domains/common/treasure.png` (卡片/寶箱特徵)
3. 嚴禁在程式碼、配置、測試或註冊表中殘留或使用廢棄之 `domains/golden_empire/...` 舊路徑。
4. 嚴禁使用雙軌 fallback 機制遮蔽路徑漂移。
5. `ElementId.DOMAIN_EXPLORE_BTN` 唯一對應 `domains/common/explore_btn.png`。
6. `config/defaults.toml` 的 `[primary_modes.golden_empire].explore_priorities` 唯一配置 `domains/common/explore_btn.png`。

## 3. 非目標 (Non-goals)

- 不在本 task 將 legacy `DomainTreasureSubflow` 全面改寫為 one-tick/one-frame phased FSM（維持目前 `click_and_wait_until_gone` 與定格觀察機制）。
- 不改動 domain scheduling priority 或 Tier 4 退守階梯順序。
- 不新增新的 domain-specific gameplay 行為或第二領地完整導航。
- 不重構無關的 battle / navigation / daily scheduler。

## 4. 變更範圍 (Scope)

- **資產移動**：
  - `templates/domains/golden_empire/explore_btn.png` ➔ `templates/domains/common/explore_btn.png`
  - `templates/domains/golden_empire/open.png` ➔ `templates/domains/common/open.png`
  - `templates/domains/golden_empire/find_treasure.png` ➔ `templates/domains/common/find_treasure.png`
  - `templates/domains/golden_empire/treasure.png` ➔ `templates/domains/common/treasure.png`
- **代碼層**：
  - `states/domains/treasure_subflow.py`：新增通用隨機挖寶處理器，實作 actionable + scene evidence。
  - `states/domains/generic_domain.py`：新增通用領域策略 `GenericDomainStrategy`。
  - `states/domains/base_domain.py`：預設通用探索按鈕與隨機事件委派。
  - `states/domains/golden_empire.py`：瘦身，繼承通用基類。
  - `states/domains/__init__.py`：導出通用類別，工廠方法移除古國 fallback。
  - `utils/scene_snapshot.py`：`ElementId.DOMAIN_EXPLORE_BTN` 對齊至 `domains/common/explore_btn.png`。
  - `config/defaults.toml`：`explore_priorities` 對齊至 `domains/common/explore_btn.png`。
  - `states/state_machine.py`、`states/handlers/navigation.py`、`states/handlers/battle.py`、`states/handlers/result.py`：主場景錨點全面對齊至 `domains/common/explore_btn.png`。
- **測試層**：
  - `tests/test_domain_common_behavior.py`：涵蓋 Generic strategy、Treasure evidence 語意與 SSOT 不變量。
  - `tests/test_behavior_golden_empire.py`：對齊通用路徑與斷言。

## 5. 驗收標準 (Acceptance Criteria)

1. `GoldenEmpireStrategy` 不再作為 unknown domain fallback。
2. Generic domain 能保留自己的 `domain_name`。
3. Generic domain 可直接繼承 common explore + common treasure behavior。
4. `find_treasure.png` / `treasure.png` 具備 runtime test coverage，不只是磁碟檔案存在。
5. 看到 treasure scene evidence 但沒有 free `open.png` 時，認領事件且不發出未知 click。
6. Golden Empire 既有 open → confirm → quit 行為維持。
7. repository 中不得存在舊 `domains/golden_empire/explore_btn.png`、`open.png`、`find_treasure.png`、`treasure.png` 的 runtime/config/test 參照。
8. 嚴格不使用 fallback 雙軌 template path。
