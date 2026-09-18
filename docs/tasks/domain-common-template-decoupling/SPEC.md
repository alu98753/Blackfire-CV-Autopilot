# Task Specification: 領域通用模板與行為抽離 (Domain Common Template & Behavior Decoupling)

Status: Final

## 1. 摘要與背景 (Summary & Motivation)

先前版本中，領域主場景探索按鈕 (`explore_btn.png`) 與隨機挖寶事件三件套（`open.png`、`find_treasure.png`、`treasure.png`）被放置在 `templates/domains/golden_empire/` 目錄下，且程式碼多處寫死古國路徑，甚至將所有未註冊領域靜默 fallback 至 `GoldenEmpireStrategy`。此外，新增領域需要手動修改多個 Python 模組中硬編碼的靜態選項清單（如 `TIER4_DOMAIN_OPTIONS`、CLI 模式判斷條件、Fallback 路由白名單），並殘留無用的 `enable_golden_empire` 旗標。

實際上，上述按鈕與事件為整個領地系統（Domain Framework）之通用行為，適用於所有領域（Domain 1: 黃金古國、Domain 2: 淵獸之巢、Domain 3: 冷誓要塞等）。

本任務將這 4 個資源與行為自黃金古國徹底解耦，移入 `templates/domains/common/`，並進行 Bounded Extension：
1. 將 `config/defaults.toml` 確立為 Repository Domain Catalog SSOT（領域存在權威）。
2. 動態化 CLI 與 Daily Tier 4 領域探索發現，徹底清除靜態寫死選項與 KeyError 隱患。
3. 清除無用的 `enable_golden_empire` 歷史旗標。
4. 建立嚴格邊界：合法註冊領域走通用/特化策略，非法/打錯字領域一律 Fail-Fast，嚴禁猜測與偷帶古國身份。

## 2. 嚴格不變量 (Strict Invariants)

### 2.1 領域目錄與目錄權威不變量 (Domain Catalog Authority Invariant)
1. **Canonical Domain existence/catalog = unmerged repository defaults snapshot**：
   `config/defaults.toml` 中的 `[primary_modes.<mode_key>]`（且滿足 `type = "domain"`）為系統中合法領地的**唯一存在權威（Existence Authority）**。Existence validation 必須直接針對 unmerged repository defaults snapshot 判斷，絕不使用受 profile override 影響之 effective `PRIMARY_MODES` 作為存在權威。
2. **Effective runtime domain values = canonical domain + profile value overrides**：
   `config/defaults.toml` 定義能力與合法領域身分；`user_data/<profile>/config.toml` 僅能對已宣告領域進行數值覆寫（如 `bread_cost`、`enable_lord_boss`、`navigation_path` 等）。
   Profile 配置邊界受到嚴格結構核驗（Profile Structural Validation）：
   - 嚴禁在 Profile 新增未於 defaults catalog 宣告之全新模式 key；
   - 嚴禁修改 canonical mode 之結構性 `type`；
   - 嚴禁修改 canonical domain mode 之 `domain` 識別碼；
   - 任何違反上述結構不變量之行為一律 Fail-Fast 拋出明確例外。
3. **Registry 的特化派發定位**：
   Python 的 `DOMAIN_STRATEGIES` 僅為 **Specialized Behavior Override Registry**，絕非 Domain Catalog：
   - TOML 宣告且 Registry 有特化類別 ➔ 實例化特化策略（如 `GoldenEmpireStrategy`）；
   - TOML 宣告但 Registry 無特化類別 ➔ 實例化 `GenericDomainStrategy`，保有傳入之 `domain` 名稱與通用行為；
   - 未在 TOML 宣告的未知領域或打錯字（Typo） ➔ **Fail-Fast 拋出配置錯誤**，嚴禁靜默包裝為 `GenericDomainStrategy`，亦嚴禁 fallback 至 `GoldenEmpireStrategy`。

### 2.2 通用行為與職責邊界不變量 (Generic Architecture Invariant)
1. **通用行為獨立性**：Generic/common domain behavior 絕不得依賴 `GoldenEmpireStrategy` identity。
2. **古國特異職責邊界**：`GoldenEmpireStrategy` 僅為黃金古國專屬行為之持有者（如專屬卡片入口、專屬 Boss、專屬祭壇等）。
3. **消除古國 Fallback 耦合**：DomainExploreHandler 若未配置合法 domain 必須 Fail-Fast，不得預設回退為 `"golden_empire"`。

### 2.3 挖寶語意契約不變量 (Treasure Semantic Invariant)
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

### 2.4 路徑與設定 SSOT 不變量 (Path & Config SSOT Invariant)
1. 領域主場景探索按鈕之唯一正規路徑為 `domains/common/explore_btn.png`。
2. 領域隨機挖寶事件之唯一正規路徑為：
   - `domains/common/open.png` (免費開箱按鈕)
   - `domains/common/find_treasure.png` (事件視窗特徵)
   - `domains/common/treasure.png` (卡片/寶箱特徵)
3. 嚴禁在程式碼、配置、測試或註冊表中殘留或使用廢棄之 `domains/golden_empire/...` 舊路徑。
4. 嚴禁使用雙軌 fallback 機制遮蔽路徑漂移。
5. `ElementId.DOMAIN_EXPLORE_BTN` 唯一對應 `domains/common/explore_btn.png`。
6. `config/defaults.toml` 的 `[primary_modes.golden_empire].explore_priorities` 唯一配置 `domains/common/explore_btn.png`。
7. 徹底移除 `enable_golden_empire` 旗標，領域調度純粹由 `type == "domain"`、`domain` 與 `tier4_domain` 表達。

## 3. Architecture Roadmap & Phased Execution

### 3.1 職責邊界定位
- **Daily**：Scheduling / Activity Policy Owner，負責高層排程與各類活動啟用政策（包含 `enable_domain`、`enable_dungeon`、`enable_lord_boss` 等）。
- **Domain**：Execution SSOT，負責持有該領域執行所需之完整靜態配置（路徑、按鈕、成本、重試門檻等）。

### 3.2 階段藍圖與已實作契約 (Phase Roadmap & Implemented Contract)
- **Phase 1 (Domain Policy / SSOT Preparation - Implemented)**：
  - 引入通用活動開關 `enable_domain`（`defaults.activities` 與 `primary_modes.daily` 同步宣告）。
  - 建立 Daily Domain policy 矛盾核驗：`tier4_mode == "domain"` 時 `enable_domain` 必須為 `true`，且 `tier4_domain` 必須明確存在，違者 Fail-Fast（不依賴 `DEFAULT_TIER4_DOMAIN` 隱式填補）。
  - 確立 Domain Execution Required Contract（`DOMAIN_STRUCTURAL_REQUIRED_KEYS` 與 `CANONICAL_DOMAIN_COMMON_DEFAULTS`），使 Domain 配置具備自身完整性。
- **Phase 2 (Switch Domain Execution Ownership - Implemented Contract)**：
  - **Daily policy selects Domain**：Daily 為排程/活動政策持有者（Scheduler & Activity Policy Owner），負責選擇特定 Domain (`tier4_domain`)。
  - **Domain is execution-field SSOT**：被選定並經標準化之 effective Domain config 為執行欄位之唯一 SSOT（Execution Base），不再從 Daily deepcopy 上覆蓋欄位。
  - **Daily execution-like fields MUST NOT override Domain SSOT**：Daily 自身存在之同名或干擾性執行欄位（如 `navigation_path`, `lobby_start_btn`, `result_buttons`, `bread_cost` 等）嚴禁覆蓋或污染 Domain 執行路由。
  - **Daily scheduler state remains owned by `primary_config` / `_daily_activity_config()`**：Domain residency 期間，所有 Daily 排程與插隊政策（`enable_dungeon`, `dungeon_entries`, `greedy_dungeon`, 體力退避後冷卻喚醒復歸等）皆由 `primary_config` / `_daily_activity_config()` 獨立持有，不混入 Domain 執行配置。
  - **`enable_lord_boss` Dual Ownership**：
    - Daily 的 `primary_config.enable_lord_boss` 代表 Daily 整體排程是否啟用領主 Boss；
    - Domain 執行配置中的 `enable_lord_boss` 代表該領地探索期間是否允許領主 Boss 插隊；
    - 兩者職責徹底分離，互不干涉。
  - **`enable_domain` Strict Ownership**：`enable_domain` 僅存在於 Daily 政策，Domain 執行配置中嚴格排除 `enable_domain`。
  - **Seam Assembly**：移除 `DOMAIN_ROUTE_KEYS` 逐欄覆蓋機制，改由純函式 helper `build_domain_execution_route(daily_policy, selected_domain_config)` 完成最小排程脈絡與 Tier 4 標記附加。
- **Phase 3 (Cleanup Structural Fallbacks & Compatibility Duplications - Implemented Contract)**：
  - **Remove `DEFAULT_TIER4_DOMAIN` runtime fallback**：完全移除 `DEFAULT_TIER4_DOMAIN` 常數；`tier4_mode == "domain"` 時必須明確提供 `tier4_domain`，缺少時在 policy boundary 立即 Fail-Fast，絕不自動猜測或回退至 `golden_empire` 或第一個 domain。
  - **Remove `domain_tab_btn` & `domain_entry_btn` consumer fallbacks / inference**：NavigationHandler 不再硬編碼 `domain_tab_btn` 預設路徑，亦不再從 `navigation_path` 搜尋猜測 `domain_entry_btn`；結構欄位缺失直接在 normalization / validation 邊界 Fail-Fast。
  - **Sole Domain strategy identity (`domain`)**：`domain` 為唯一 execution strategy identity，徹底移除 `domain -> domain_name` identity compatibility fallback；若缺少 `domain`（即使存在純顯示欄位 `domain_name`）立即 Fail-Fast，不得拿 `domain_name` 當 strategy identity。
  - **Tighten `primary_config` ownership on Tier 4 route rebuild**：Daily Tier4 fallback rebuild 與套用嚴格要求合法 `primary_config` / policy owner，缺失時 Fail-Fast（拋出 `RuntimeError`），絕不靜默回退至 `mix` 或 `daily`。
  - **Single Authority for Domain defaults**：Domain consumer 端的規範預設值（`bread_cost`, `domain_reset_max_attempts`, `explore_priorities`, `result_buttons`, `enable_lord_boss`）統一且唯一由 `normalize_domain_execution_config()` SSOT 提供，consumer 端移除二次預設值 fallback。
  - **Audit Daily scheduling context & bounded compatibility context**：
    - Category A (Domain execution / 整理背包直接需要)：`keep_colors`, `disassemble_colors`。
    - Category B (排程器可自 `_daily_activity_config()` / `primary_config` 取得)：`enable_town_daily`, `enable_demon_lords`, `subflow_configs`。
    - Category C (過渡期/相容性處理器暫時自 `machine.config` 讀取之 bounded compatibility context)：`enable_dungeon`, `dungeon_names`, `dungeon_entries`, `cooldown_map`, `greedy_dungeon`, `greedy_allowed_indices`, `auto_resume_dungeon_on_cd`。
  - **Structural validation invariant**：Structural configuration errors are rejected at normalization / policy boundaries. Consumers do not infer missing Domain identity or paths. Canonical common defaults have one owner: Domain normalization. No Golden Empire / first-domain / Daily-route fallback may repair an invalid Domain execution configuration.

### 3.3 `enable_domain` 語意與 Invariant 契約
1. **語意定義**：`enable_domain` 代表 scheduler / Daily policy 是否允許調度 Domain 類活動。其與 `enable_dungeon`、`enable_lord_boss`、`enable_town_daily` 處於同等抽象層級。
2. **非 Domain 執行配置**：`enable_domain` 僅屬於 Daily / scheduler policy，嚴禁放入任何 `primary_modes.<domain>` 執行配置中。
3. **禁止領域特化旗標**：嚴禁建立 `enable_golden_empire`、`enable_abyss_nest` 等特定領域名稱之 activity switch。
4. **Contradiction Invariant**：
   - `tier4_mode == "domain"` 且 `enable_domain == false` ➔ 必須拋出 `ValueError` (Fail-Fast)，嚴禁靜默改為 stage 或 none。
   - `tier4_mode == "domain"` 但缺少或未指定 `tier4_domain` ➔ 必須拋出 `ValueError` (Fail-Fast)，嚴禁隱式回退至 `"golden_empire"`。

### 3.4 Domain Execution Required Contract & Schema
宣告一個 Canonical Domain 執行所需之最小契約：

#### Structural Required (缺少或無效則 Fail-Fast)
- `name = "<顯示名稱>"`：如 `"黃金古國"`、`"淵獸之巢"`，CLI 顯示與 Daily Tier 4 選單標籤唯一權威來源。
- `type = "domain"`：宣告為領域模式。
- `domain = "<領域識別碼>"`：如 `"golden_empire"`、`"abyss_nest"`，對應策略實體識別。
- `navigation_path = [...]`：由大廳進入領域之完整非空點擊路徑列表。
- `domain_tab_btn = "domains/Domains_entry.png"`：領地分頁未選中按鈕。
- `domain_tab_after_btn = "domains/Domains_entry_after.png"`：領地分頁已選中特徵。
- `domain_entry_btn = "domains/.../entry.png"`：該領地入口按鈕。
- `lobby_start_btn = "domains/common/start_btn.png"`：大廳起手按鈕。

#### Canonical Common Defaults (由標準化層一次產生)
- `bread_cost` (int, default: 3)
- `explore_priorities` (list[str], default: `["domains/common/explore_btn.png"]`)
- `result_buttons` (list[str], default: `["common/continue.png", "common/continue_gray.png"]`)
- `domain_reset_max_attempts` (int, default: 7)
- `enable_lord_boss` (bool, default: true; 屬 Domain execution policy field：表示在該領域探索時是否允許領主 Boss 插隊挑戰)

## 4. 非目標 (Non-goals)

- 不在本 task 將 legacy `DomainTreasureSubflow` 全面改寫為 one-tick/one-frame phased FSM。
- 不改動 domain scheduling priority 或 Tier 4 退守階梯順序。
- 不新增新的 domain-specific gameplay 行為或第二領地專屬美術資產。
- 不重構 `parse_arguments()` 與 `set_active_profile()` 的啟動時序。
- 不建立複雜的動態 plugin / registry framework。
- 不支援由 User Profile 憑空發明新領域。

## 5. 不確定性與後續工作 (Uncertainty / Follow-up)

- *Treasure Scene-only Recovery*：persistent treasure scene-only evidence currently lacks an explicit bounded escape/recovery owner; resolving long-lived paid/loading treasure states is deferred until the existing no-progress/recovery ownership is surveyed.

## 6. 驗收標準 (Acceptance Criteria)

1. `config/defaults.toml` 是 Domain existence authority。
2. Profile 只能 override repository-declared Domains，不可新增 Domain identity。
3. 新增 repository generic Domain 後，不需修改 Python mode/domain catalog。
4. `--mode <new-domain-mode>` 自動成為合法 CLI choice。
5. CLI presentation 不含 Golden-Empire-specific structural hardcode（麵包數動態讀取、help 描述泛型化）。
6. Daily Tier4 自動列出所有 canonical `type="domain"` modes。
7. Domain display label 取自 TOML `name`。
8. Invalid `tier4_domain` 不得因 static tuple 產生 `KeyError`；必須 deterministic validate (Fail-Fast)。
9. Tier4 fallback 正確帶入 domain navigation/runtime fields（包含 `lobby_start_btn`、`domain_entry_btn` 等），不殘留普通關卡起手按鈕。
10. `enable_golden_empire` 完全移除，無殘留 production 依賴。
11. Python `DOMAIN_STRATEGIES` 僅為 specialized behavior registry。
12. Canonical-declared、未專屬註冊 Domain ➔ `GenericDomainStrategy`，保留自身 `domain`。
13. Undeclared/typo Domain ➔ Fail-Fast 拋出錯誤，不得 generic fallback。
14. Existing Golden Empire direct / Daily Tier4 行為保持。
15. 不重構 profile bootstrap / argparse lifecycle。
16. 不建立大型 Domain plugin framework。
