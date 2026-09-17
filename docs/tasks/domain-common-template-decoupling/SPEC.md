# Task Specification: 領域通用模板與行為抽離 (Domain Common Template & Behavior Decoupling)

Status: Final

## 1. 摘要與背景 (Summary & Motivation)

先前版本中，領域主場景探索按鈕 (`explore_btn.png`) 與隨機挖寶事件三件套（`open.png`、`find_treasure.png`、`treasure.png`）被放置在 `templates/domains/golden_empire/` 目錄下，且程式碼（`GoldenEmpireStrategy`、`scene_snapshot.py`、`state_machine.py`、`navigation.py`、`battle.py`、`result.py`）多處寫死古國路徑。

實際上，上述按鈕與事件為整個領地系統（Domain Framework）之通用行為，適用於所有領地（Domain 1: 黃金古國、Domain 2: 淵獸之巢、Domain 3: 冷誓要塞等）。

本任務將這 4 個資源與行為自黃金古國徹底解耦，移入 `templates/domains/common/`，並依據 Greenfield-lite v1 架構規範建立獨立通用模組 `DomainTreasureSubflow` 與升級 `BaseDomainStrategy`。

## 2. 嚴格不變量 (Strict Invariants)

1. **路徑 SSOT 不變量 (Path SSOT Invariant)**：
   - 領域主場景探索按鈕之唯一正規路徑為 `domains/common/explore_btn.png`。
   - 領域隨機挖寶事件之唯一正規路徑為：
     - `domains/common/open.png` (免費開箱按鈕)
     - `domains/common/find_treasure.png` (事件視窗特徵)
     - `domains/common/treasure.png` (卡片/寶箱特徵)
   - 嚴禁在程式碼、配置、測試或註冊表中殘留或使用廢棄之 `domains/golden_empire/...` 舊路徑。
   - 嚴禁使用雙軌 fallback 機制遮蔽路徑漂移。

2. **語意契約不變量 (Semantic Contract Invariant)**：
   - `ElementId.DOMAIN_EXPLORE_BTN` 唯一對應 `domains/common/explore_btn.png`。
   - `config/defaults.toml` 的 `[primary_modes.golden_empire].explore_priorities` 唯一配置 `domains/common/explore_btn.png`。

3. **職責分離不變量 (Separation of Concerns Invariant)**：
   - 通用挖寶開箱閉環邏輯（`open.png` ➔ `confirm.png` ➔ `quit.png`）封裝於 `DomainTreasureSubflow`。
   - `BaseDomainStrategy` 預設提供通用探索按鈕與通用隨機事件分發；子類領地（如 `GoldenEmpireStrategy`）僅需繼承即可自動具備探索與開箱能力。
   - 特定領地策略僅保留該領地獨有特徵（如卡片入口、專屬 Boss 配置、專屬隨機事件覆寫）。

## 3. 變更範圍 (Scope)

- **資產移動**：
  - `templates/domains/golden_empire/explore_btn.png` ➔ `templates/domains/common/explore_btn.png`
  - `templates/domains/golden_empire/open.png` ➔ `templates/domains/common/open.png`
  - `templates/domains/golden_empire/find_treasure.png` ➔ `templates/domains/common/find_treasure.png`
  - `templates/domains/golden_empire/treasure.png` ➔ `templates/domains/common/treasure.png`
- **代碼層**：
  - `states/domains/treasure_subflow.py`：新增通用隨機挖寶處理器。
  - `states/domains/base_domain.py`：預設通用探索按鈕與隨機事件委派。
  - `states/domains/golden_empire.py`：瘦身，繼承通用基類。
  - `states/domains/__init__.py`：導出 `DomainTreasureSubflow`。
  - `utils/scene_snapshot.py`：`ElementId.DOMAIN_EXPLORE_BTN` 對齊至 `domains/common/explore_btn.png`。
  - `config/defaults.toml`：`explore_priorities` 對齊至 `domains/common/explore_btn.png`。
  - `states/state_machine.py`、`states/handlers/navigation.py`、`states/handlers/battle.py`、`states/handlers/result.py`：主場景錨點全面對齊至 `domains/common/explore_btn.png`。
- **測試層**：
  - `tests/test_domain_common_behavior.py`：新增通用探索與開箱測試，以及嚴格 SSOT 不變量掃描測試。
  - `tests/test_behavior_golden_empire.py`：更新路徑與斷言。
