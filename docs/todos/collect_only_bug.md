# Spec / Bug Analysis: 體力退避 (COLLECT_ONLY) 期間地下城冷卻結束喚醒後誤入 Tier 4 Stage 刷怪問題分析與修復規格

- **狀態**：分析完畢 / 待實作修復 (Ready for Implementation)
- **類別**：Bug Fix / Architecture Invariant Alignment
- **影響範圍**：體力退避機制 (`stamina_retreat`)、定時待機處理器 (`CollectOnlyHandler`)、全域活動調度器 (`evaluate_next_activity`)、導航處理器 (`NavigationHandler`)、探索處理器 (`ExploreHandler`)
- **相關核心檔案**：
  - [states/state_machine.py](../../states/state_machine.py) (`evaluate_next_activity`, `build_dungeon_resume_route`)
  - [states/handlers/navigation.py](../../states/handlers/navigation.py) (`handle`, `_switch_to_stage_or_back`, `_enter_collect_only_after_dungeon_cooldown`)
  - [states/handlers/explore.py](../../states/handlers/explore.py) (`handle` 通關退出轉移邏輯)
  - [states/handlers/collect_only.py](../../states/handlers/collect_only.py) (`handle` 地下城喚醒復歸)
  - [tests/test_behavior_stamina_retreat.py](../../tests/test_behavior_stamina_retreat.py)
  - [tests/test_daily_pipeline_stamina_retreat.py](../../tests/test_daily_pipeline_stamina_retreat.py)

---

## 1. 原始問題描述 (User Problem Statement)

> **問題描述**：我明明在 collectonly 中 還有 5 個小時，但是我設定打地下城沒錯，他定時去打地下城也是正確的。但是 tier4 當 collectonly 的時候應該被 disable。
> 
> **但為何她還去打 tier4 的 stage？**

---

## 2. 核心結論與問題直答 (Executive Summary & Direct Answer)

### Q: 為何在 `COLLECT_ONLY`（體力退避倒數中）還會去打 Tier 4 的 Stage？

**A: 系統在「地下城冷卻結束臨時喚醒 ➔ 打完通關 ➔ 所有地下城再度全冷卻」的環節上，發生了嚴重的調度斷鏈與路由污染，導致系統誤以為自己處於常態混合掛機模式（Mix Mode），從而在活動大廳主動點擊切換至普通關卡頁籤並發起戰鬥。**

具體發生的連環邏輯斷點如下：

```text
[體力退避中 5h40m (COLLECT_ONLY)]
       │
       ▼ (地下城 6 冰雪洞窟冷卻結束)
[CollectOnlyHandler.handle()]
       │ 呼叫 build_dungeon_resume_route()
       ▼
【斷點 1：路由污染】臨時路由被錯誤蓋上 type="mix"、is_tier4_fallback=True，
                  更注入了 Tier 4 關卡路徑 (第 7 關遺忘荒地)，且未顯式關閉 enable_stage_farming=False！
       │
       ▼ (轉移至 NAVIGATING ➔ 進入地下城 6 戰鬥並通關)
[ExploreHandler 通關結算 (13:34:09)]
       │ 冰雪洞窟進入 30m 冷卻，獸人地堡仍在冷卻中 ➔ 地下城全冷卻！
       ▼
【斷點 2：調度死巷】轉入 STATE_NAVIGATING 觸發 evaluate_next_activity()。
                  調度器檢查 stamina_retreat_start_time 存在，但因 has_available_dungeon() 為 False，
                  竟然直接 return False！既未切回 COLLECT_ONLY，亦未發起回城動作！
       │
       ▼ (狀態機被遺棄在 STATE_NAVIGATING 且身處活動大廳)
[NavigationHandler.handle() (13:34:17)]
       │ 讀取當前路由 (被污染的 mix + is_tier4_fallback)
       ▼
【斷點 3：導航退避盲目】NavigationHandler 發現是 mix 模式且全冷卻，
                      enable_stage_farming 因 is_tier4_fallback 預設為 True (完全未檢查 stamina_retreat_start_time)，
                      於是點擊 common/select_stage.png 切換普通關卡頁籤，並依據路由中的路徑直奔第 7 關魔王關！
       │
       ▼
[無效戰鬥死循環 (13:37 ~ 13:41)]
       進入 Stage 7 開打，結算退出後又被 NavigationHandler 送進 Stage 7，
       直到 7 分鐘後地下城 7 (獸人地堡) 冷卻結束才觸發插隊，打完後又再度落回 Stage 7！
```

---

## 3. 實機執行日誌還原與關鍵時間點剖析 (Execution Trace Timeline)

對照本文件附錄之實機執行日誌，可清楚還原出事故的完整時間線：

| 時間戳記 | 當前狀態與情境 | 關鍵日誌輸出 | 系統內部決策與行為分析 |
|---|---|---|---|
| **13:25:37** | `COLLECT_ONLY` | `⏳ [體力退避狀態] collect_only 模式已執行 79 分鐘。距離回到原掛機模式 [每日懸賞任務] 還剩: 5小時40分47秒。` | 體力退避機制運作正常，背景計時器持續倒數，原模式為每日懸賞任務。 |
| **13:25:58** | `BREAD_COLLECTION` | `🍞 定時領取：在城鎮畫面，點擊入口 [common/door.png] 進入大廳以領取體力。` | 觸發每 5 分鐘一次的定時領取麵包子流程。 |
| **13:26:17** | `COLLECT_ONLY` | `🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。` ➔ `🔄 狀態轉移: BREAD_COLLECTION -> COLLECT_ONLY` ➔ `點擊 [goback_town.png] 返回城鎮` | 領取完畢後，正確點擊 `goback_town.png` 退回城鎮，維繫 `COLLECT_ONLY`。 |
| **13:31:55** | `COLLECT_ONLY` | `🔄 [冷卻結束復歸] 偵測到地下城冷卻結束，暫時離開 collect_only 切回刷地下城！` ➔ `🔄 狀態轉移: COLLECT_ONLY -> UNKNOWN` | 地下城 6（冰雪洞窟）冷卻結束。`CollectOnlyHandler` 呼叫 `build_dungeon_resume_route()` 建立執行路由並發起狀態轉移。 |
| **13:31:58** | `NAVIGATING` | `🔄 [Activity Scheduler] 體力退避期間地下城冷卻已結束 ➔ 保留地下城復歸路由，不套用 Tier 4 Domain fallback。` | **【轉折點 A】** 進入導航，`evaluate_next_activity` 確認冰雪洞窟可打，保留了該 resume 路由。 |
| **13:32:09 ~ 13:34:08** | `NAVIGATING` ➔ `EXPLORING` ➔ `BATTLE` | `🧭 混合模式：地下城已就緒... 點擊 [dungeons/dungeon.png]` ➔ `選擇進入 [冰雪洞窟]` ➔ 通關 `dungeons_complete.png` | 成功進入冰雪洞窟，領取祝福、開寶箱、戰鬥推進，並於 13:34:08 通關。 |
| **13:34:09** | `EXPLORING` ➔ `NAVIGATING` | `⏳ 貪婪地下城：設定 [冰雪洞窟] (#6) 進入 30 分鐘冷卻期。`<br>`⏳ [混合模式] 地下城全冷卻！各副本冷卻情形: [冰雪洞窟]: 冷卻中 (30 分 0 秒), [獸人地堡]: 冷卻中 (6 分 39 秒) ➔ 無可用地下城，將退守切換至普通關卡 (Stage)。`<br>`🔄 狀態轉移: EXPLORING -> NAVIGATING` | **【致命轉折點 1】** 地下城全冷卻。`ExploreHandler` 輸出硬編碼之「將退守切換至普通關卡」，並將狀態機切至 `STATE_NAVIGATING`。 |
| **13:34:09 ~ 13:34:10** | `NAVIGATING` | *(無進一步調度日誌)* | **【致命轉折點 2】** `transition_to(STATE_NAVIGATING)` 觸發 `evaluate_next_activity()`。但調度器在 `stamina_retreat_start_time` 存在且地下城全冷卻時，**直接 `return False`**，未切換回 `COLLECT_ONLY`，亦未點擊回城！ |
| **13:34:17** | `NAVIGATING` | `🧭 混合模式：地下城全冷卻 (冷卻情形: [冰雪洞窟]: 冷卻中 (29 分 51 秒), [獸人地堡]: 冷卻中 (6 分 30 秒))，在活動大廳點擊 [common/select_stage.png] (0.9266) 切換至普通關卡頁籤！` | **【致命轉折點 3】** `NavigationHandler.handle()` 接手。因當前路由有 `type="mix"` 與 `is_tier4_fallback=True`，且未檢查體力退避狀態，直接點擊 `common/select_stage.png` 切換關卡頁籤！ |
| **13:37:18 ~ 13:37:35** | `NAVIGATING` ➔ `LOBBY` ➔ `BATTLE` | `🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png]` ➔ `點擊 [stages/boss_skull.png]` ➔ `Lobby start button [stages/start.png] detected; clicking.` ➔ `🔄 狀態轉移: LOBBY -> BATTLE` | 導航器依照路由中殘留的 Tier 4 關卡設定，一路導航至第 7 關荒地魔王關發起點擊並進入戰鬥！ |
| **13:37:35 ~ 13:41:15** | `BATTLE` ➔ `RESULT` ➔ `NAVIGATING` | 戰鬥結束 ➔ 結算退出 ➔ 重新導航 ➔ 再次進 Stage 7 戰鬥 | 在體力退避期間陷入 Stage 7 刷怪死循環（甚至在無體力/低體力下嘗試點擊 start 戰鬥）。 |
| **13:41:16** | `RESULT` | `🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。` | 獸人地堡（#7）冷卻剛好結束，結算處理器觸發插隊退出，重新切回地下城。 |
| **13:42:31 ~ 13:45:34** | `NAVIGATING` ➔ `EXPLORING` ➔ `BATTLE` | 成功進入獸人地堡並打完通關。 | 打完第 88 次地下城，獸人地堡進入 35 分鐘冷卻。 |
| **13:45:34** | `EXPLORING` ➔ `NAVIGATING` | `⏳ [混合模式] 地下城全冷卻！各副本冷卻情形: [冰雪洞窟]: 冷卻中 (18 分 35 秒), [獸人地堡]: 冷卻中 (35 分 0 秒) ➔ 無可用地下城，將退守切換至普通關卡 (Stage)。` | 獸人地堡打完後再度全冷卻，**歷史完全重演**！ |
| **13:45:43** | `NAVIGATING` | `🧭 混合模式：地下城全冷卻... 在活動大廳點擊 [common/select_stage.png] 切換至普通關卡頁籤！` | **再度點擊 `select_stage.png`，再度前往 Stage 7 打魔王關！** |

---

## 4. 深度根因分析 (Deep-Dive Root Causes)

經程式碼追查，此問題由四層架構與邏輯缺陷疊加造成：

### 根因 1：`evaluate_next_activity()` 的退避調度死巷 (Scheduler Dead-End)
- **檔案位置**：[states/state_machine.py](../../states/state_machine.py#L2141-L2157)
- **代碼現況**：
  ```python
  if getattr(self, "stamina_retreat_start_time", None) is not None:
      dungeon_enabled = activity_cfg.get(
          "enable_dungeon", cfg.get("enable_dungeon", True)
      )
      if not dungeon_enabled:
          return False

      if not self.has_available_dungeon(target_config=activity_cfg):
          return False  # ⚠️ 致命問題點：直接 return False！
  ```
- **分析**：
  在 commit `0626e03` 中，為了防止體力退避期間被 Tier 4 Domain 覆蓋，增加了上述判斷。
  然而，作者僅考慮了「地下城可用時喚醒」，卻完全忽略了**「地下城打完／不可用時該去哪裡」**！
  當 `not self.has_available_dungeon()` 時，它直接執行了 `return False`。
  這意味著全域調度器宣告放棄決策，但**既沒有將狀態轉移至 `STATE_COLLECT_ONLY`，也沒有切回待機配置，更沒有點擊 `goback_town.png` 退回城鎮**。狀態機被赤裸裸地丟在 `STATE_NAVIGATING` 與活動大廳畫面中。

### 根因 2：`build_dungeon_resume_route()` 路由污染與職責越權 (Route Contamination)
- **檔案位置**：[states/state_machine.py](../../states/state_machine.py#L1406-L1420)
- **代碼現況**：
  ```python
  def build_dungeon_resume_route(self, source_config=None):
      policy = self._daily_activity_config()
      base = policy if (policy and policy.get("enable_dungeon")) else (source_config or self.config or {})
      route = deepcopy(base)
      route["type"] = "mix"
      route["enable_dungeon"] = True
      route["is_tier4_fallback"] = True  # ⚠️ 混入 Tier 4 身分
      route["navigation_path"] = ["common/door.png", "dungeons/dungeon.png"]
      if "dungeon_entries" not in route and "daily" in GAME_CONFIGS:
          route["dungeon_entries"] = deepcopy(GAME_CONFIGS["daily"].get("dungeon_entries", []))
          route["dungeon_names"] = deepcopy(GAME_CONFIGS["daily"].get("dungeon_names", []))
      self._apply_tier4_stage_selection(route)    # ⚠️ 注入 Tier 4 關卡路徑 (Level 7)！
      self._apply_tier4_dungeon_selection(route)
      return route
  ```
- **分析**：
  此函式的唯一目標本應是：**「在待機或退避期間，臨時建立一份僅供探索地下城的乾淨單一執行路由」**。
  但實作上卻做過了頭：
  1. 將其類型設為 `"mix"`。
  2. 將其標記為 `is_tier4_fallback = True`。
  3. 呼叫 `_apply_tier4_stage_selection(route)`，主動把使用者的 Tier 4 關卡（如 Level 7 魔王關）塞進該路由的 `stage_entry` 與 `stage_navigation_path`。
  4. 未顯式關閉 `enable_stage_farming`。
  這份路由本質上是一顆「定時炸彈」：一旦地下城全冷卻，它立刻就會變身為 Tier 4 Stage 關卡刷怪路由！

### 根因 3：`NavigationHandler` 關卡退守對體力退避狀態毫無感知 (Retreat-Blind Navigation)
- **檔案位置**：[states/handlers/navigation.py](../../states/handlers/navigation.py#L532-L545, #L1040-L1056)
- **代碼現況**：
  ```python
  # states/handlers/navigation.py:1042
  mode_t = self.machine.config.get("type")
  default_farm = True if (mode_t in ["mix", "stage", "daily"] or self.machine.config.get("is_tier4_fallback", False)) else False
  if not self.machine.config.get("enable_stage_farming", default_farm):
      self._enter_collect_only_after_dungeon_cooldown(...)
      return

  # 無可用地下城，退守普通關卡：若尚未處於普通關卡頁籤，點擊 select_stage.png 切換！
  status_str, _ = self.machine.get_dungeon_cooldown_status()
  pos_st, conf_st = self.matcher.match(screen_img, "common/select_stage.png", threshold=0.60)
  if pos_st and not stage_select_open:
      logging.info(f"🧭 混合模式：地下城全冷卻... 點擊 [common/select_stage.png] 切換至普通關卡頁籤！")
      self.mouse.click(rect["left"] + pos_st[0], rect["top"] + pos_st[1])
      time.sleep(0.3)
      return
  ```
- **分析**：
  在 `NavigationHandler` 的兩處全冷卻退守判定中（`handle` 與 `_switch_to_stage_or_back`）：
  - 均以 `default_farm` 作為 `enable_stage_farming` 的 fallback。
  - 因為當前路由被設為 `type="mix"` 且 `is_tier4_fallback=True`，`default_farm` 算出來必定為 `True`。
  - **整段邏輯完全沒有檢查 `stamina_retreat_start_time` 是否存在！**
  - 在體力退避期間，常規關卡打怪是必定需要消耗體力（麵包）的。體力不足時去打關卡本就是自相矛盾；但導航器卻盲目點擊 `select_stage.png` 啟動尋路。

### 根因 4：`ExploreHandler` 通關結算時硬編碼之「無可用地下城將退守普通關卡」
- **檔案位置**：[states/handlers/explore.py](../../states/handlers/explore.py#L94-L105)
- **分析**：
  通關結算時，`ExploreHandler` 只依據 `self.machine.config.get("type") == "mix"` 判定全冷卻時「無可用地下城，將退守切換至普通關卡 (Stage)」，完全無視這場戰鬥是否源自於體力退避期間的臨時喚醒，並無腦轉移至 `STATE_NAVIGATING`。

---

## 5. 架構契約與核心不變量 (System Invariants & Architectural Contract)

依據專案全域架構指南 [project_arch_greenfield_lite_v1.md](../architecture/project_arch_greenfield_lite_v1.md) 與 [AGENTS.md](../../.agents/AGENTS.md)，確立下列三條不可動搖之核心契約：

### 不變量 1：體力退避最高優先與常規關卡禁絕律 (Stamina Retreat Supremacy Invariant)
> **當且僅當 `stamina_retreat_start_time is not None`（或系統處於體力退避期間），常規關卡刷怪 (`enable_stage_farming`) 必須被絕對禁用 (`False`)。**
- 體力退避的唯一目的就是「體力不足，休眠回體」。
- 退避期間僅允許執行**不消耗體力**的特定排程活動（如定時領體力/鑽石、無門票/獨立冷卻之地下城挑戰）。
- 嚴禁在體力退避期間發起任何普通關卡（Stage）戰鬥。

### 不變量 2：臨時喚醒路由職責有界律 (Bounded Scope for Temporary Resume Routes)
> **從 `COLLECT_ONLY`（無論是純待機或體力退避）因特定冷卻活動就緒而喚醒的執行路由，其能力邊界僅限於該特定活動本身。**
- `build_dungeon_resume_route()` 產生的路由，其目標唯有「挑戰可打的地下城」。
- 該路由嚴禁攜帶普通關卡尋路設定 (`stage_entry`, `stage_navigation_path` 等必須為空或禁用)。
- 該路由必須明確宣告 `enable_stage_farming = False` 與 `tier4_mode = "none"`。

### 不變量 3：冷卻耗盡即時歸位律 (Instant Return on Cooldown Exhaustion)
> **當臨時喚醒之地下城通關或所有允許之地下城再次進入冷卻時，系統必須立即發起城鎮返回閉環（點擊 `goback_town.png`）並轉移至 `STATE_COLLECT_ONLY`。**
- 不得滯留在活動大廳。
- 不得落入其他常態懸賞或 Tier 4 關卡退守。
- 必須保留原本的 `stamina_retreat_start_time` 與 `original_config`，持續等待退避時間結束或下一個地下城冷卻結束。

---

## 6. 修復方案與模組實作規格 (Target Implementation Specifications)

### 規格 1：重構 `build_dungeon_resume_route()` 確保路由純潔
- **檔案**：[states/state_machine.py](../../states/state_machine.py)
- **修正重點**：
  1. 明確設定 `route["enable_stage_farming"] = False`。
  2. 明確設定 `route["tier4_mode"] = "none"`。
  3. 移除 `self._apply_tier4_stage_selection(route)`，嚴禁注入任何 Stage 關卡尋路目標。
  4. 標記專屬屬性 `route["is_dungeon_temporary_resume"] = True`。
  5. 僅保留地下城尋路與對齊相關參數 (`navigation_path = ["common/door.png", "dungeons/dungeon.png"]`)。

### 規格 2：修復 `evaluate_next_activity()` 體力退避冷卻復歸死巷
- **檔案**：[states/state_machine.py](../../states/state_machine.py)
- **修正重點**：
  在檢查 `stamina_retreat_start_time is not None` 的區塊中：
  - 若 `self.has_available_dungeon(target_config=activity_cfg)` 為 `True`：
    - 載入純淨的 `dungeon_route` 並回傳 `True`。
  - 若 `not self.has_available_dungeon(...)`（無地下城可打或全冷卻）：
    - **不可只單純 `return False`！**
    - 檢查當前狀態，若不在 `COLLECT_ONLY`（例如剛從地下城通關出來進入 `NAVIGATING`）：
      - 記錄日誌：`⏳ [Activity Scheduler] 體力退避期間地下城已全冷卻 ➔ 恢復城鎮待機與 COLLECT_ONLY 狀態。`
      - 轉移至 `self.transition_to(self.STATE_COLLECT_ONLY)`。
    - 回傳 `False`。

### 規格 3：強化 `NavigationHandler` 全冷卻退守的體力退避防護網
- **檔案**：[states/handlers/navigation.py](../../states/handlers/navigation.py)
- **修正重點**：
  在 `NavigationHandler.handle()` (約 L1040) 以及 `_switch_to_stage_or_back()` (約 L530) 的地下城全冷卻處理中：
  1. 增加前置條件檢查：
     ```python
     is_in_retreat = getattr(self.machine, "stamina_retreat_start_time", None) is not None
     is_temp_resume = bool(self.machine.config.get("is_dungeon_temporary_resume", False))
     ```
  2. 若 `is_in_retreat or is_temp_resume`：
     - 強制 `is_stage_farming = False`。
     - 觸發 `self._enter_collect_only_after_dungeon_cooldown(screen_img, rect, "體力退避期間地下城全冷卻，禁止切換至普通關卡")`。
     - 點擊 `goback_town.png` 返回城鎮並切入 `STATE_COLLECT_ONLY`。
     - 立即 `return`，絕對不執行點擊 `common/select_stage.png`。

### 規格 4：優化 `ExploreHandler` 通關後的語意日誌
- **檔案**：[states/handlers/explore.py](../../states/handlers/explore.py)
- **修正重點**：
  在 `ExploreHandler.handle()` 偵測到通關（約 L95）時：
  - 檢查若 `self.machine.stamina_retreat_start_time is not None` 且 `not avail_names`：
    - 日誌輸出改為：`⏳ [體力退避] 地下城全冷卻！將返回城鎮繼續維持體力退避待機 (COLLECT_ONLY)。`
    - 避免誤導性的「將退守切換至普通關卡 (Stage)」。

---

## 7. 測試規格與驗證矩陣 (Test Specifications & Verification Matrix)

依據專案測試規範，修復後須由最小相關的單元測試檔案驗證下列行為，保持 100% 綠燈：

### 測試群組 A：`tests/test_behavior_stamina_retreat.py`
1. **`test_dungeon_cooldown_exhaustion_during_retreat_clicks_goback_town_and_enters_collect_only`**：
   - **Given**：處於體力退避倒數中 (`stamina_retreat_start_time` 存在)，當前路由為地下城臨時喚醒路由 (`type="mix"` 或 `is_dungeon_temporary_resume=True`)，畫面上看到 `goback_town.png`。
   - **When**：地下城全冷卻 (`has_available_dungeon() == False`)，觸發 `NavigationHandler.handle()`。
   - **Then**：
     - 斷言點擊 `goback_town.png` 座標。
     - 斷言絕對未點擊 `common/select_stage.png`。
     - 斷言狀態轉移至 `STATE_COLLECT_ONLY`。
     - 斷言 `config["type"]` 被重設為 `collect_only`。

2. **`test_stage_farming_strictly_prohibited_during_stamina_retreat`**：
   - **Given**：`stamina_retreat_start_time` 設定，即使傳入之 config 包含 `enable_stage_farming=True` 與 `is_tier4_fallback=True`。
   - **When**：觸發 `_switch_to_stage_or_back()` 或全冷卻檢查。
   - **Then**：斷言不切換至 Stage 頁籤，而是呼叫 `_enter_collect_only_after_dungeon_cooldown`。

### 測試群組 B：`tests/test_daily_pipeline_stamina_retreat.py`
1. **`test_evaluate_next_activity_returns_to_collect_only_when_all_dungeons_cooldown_in_retreat`**：
   - **Given**：`stamina_retreat_start_time` 設定，當前狀態為 `STATE_NAVIGATING`（模擬地下城打完剛回到大廳）。
   - **When**：所有允許之地下城均在冷卻中，觸發 `evaluate_next_activity()`。
   - **Then**：
     - 斷言狀態機自動轉移至 `STATE_COLLECT_ONLY`。
     - 斷言回傳 `False`（無活動可調度，退回待機）。
     - 斷言原始 `stamina_retreat_start_time` 完全未受干擾。

2. **`test_build_dungeon_resume_route_sanitization`**：
   - **Given**：呼叫 `machine.build_dungeon_resume_route(daily_policy)`。
   - **Then**：
     - 斷言 `route["enable_stage_farming"] == False`。
     - 斷言 `route["tier4_mode"] == "none"`。
     - 斷言 `route` 不含普通關卡路徑或不執行 `_apply_tier4_stage_selection`。
     - 斷言包含有效的地下城尋路與 entry 設定。

---

## 8. 附錄：原始重現執行日誌 (Raw Execution Trace)

<details>
<summary>點擊展開完整原始日誌 (1580+ Lines Trace)</summary>

```

2026-09-10 13:21:39,174 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:22:40,957 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:23:42,373 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:24:44,077 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:25:37,689 [INFO] ⏳ [體力退避狀態] collect_only 模式已執行 79 分鐘。距離回到原掛機模式 [每日懸賞任務] 還剩: 5小時40分47秒。
2026-09-10 13:25:45,015 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:25:58,319 [INFO] ⏰ 距離上次領體力已滿 5 分鐘，觸發自動領體力。
2026-09-10 13:25:59,373 [INFO] 🍞 定時領取：在城鎮畫面，點擊入口 [common/door.png] 進入大廳以領取體力。
2026-09-10 13:25:59,563 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:25:59,574 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:02,639 [INFO] 🍞 定時領取：在大廳畫面，跳轉至 BREAD_COLLECTION。
2026-09-10 13:26:02,640 [INFO] 🔄 狀態轉移: COLLECT_ONLY -> BREAD_COLLECTION
2026-09-10 13:26:03,151 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:26:03,389 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.8828，相對亮度比: 0.99，座標: (1110, 54)
2026-09-10 13:26:04,227 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:26:04,598 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:26:04,849 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.8828，相對亮度比: 0.99，座標: (1110, 54)
2026-09-10 13:26:04,851 [INFO] 🍞 領體力：在大廳偵測到體力按鈕 [0.8828]，點擊打開體力視窗。
2026-09-10 13:26:04,994 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:05,005 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:06,973 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:26:07,479 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:07,990 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:07,992 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:26:08,092 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:08,104 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:09,104 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:26:09,573 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:10,123 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:10,123 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:26:10,228 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:10,241 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:11,254 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:26:11,737 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:12,200 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:12,202 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:26:12,311 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:12,321 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:13,299 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:26:13,836 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:14,342 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:26:14,343 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:26:14,439 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:14,449 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:14,992 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9690，相對亮度比: 0.98，座標: (766, 451)
2026-09-10 13:26:14,995 [INFO] 🍞 領體力：偵測到體力確認按鈕 [0.9690]，點擊確認。
2026-09-10 13:26:15,107 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:15,119 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:16,146 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:26:16,149 [INFO] 🍞 領體力：偵測到退出體力按鈕 [common/quit.png] (0.9816)，嘗試點擊關閉視窗。
2026-09-10 13:26:16,271 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:16,283 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:17,340 [INFO] 🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。
2026-09-10 13:26:17,340 [INFO] 🔄 狀態轉移: BREAD_COLLECTION -> COLLECT_ONLY
2026-09-10 13:26:18,186 [INFO] 🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...
2026-09-10 13:26:18,328 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:26:18,339 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:26:46,036 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:27:46,478 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:28:46,832 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:29:47,873 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:30:37,959 [INFO] ⌛ [定時待機狀態] 運作中。距離下一次 💎 鑽石: 7分53秒，🍞 體力: 39秒 | 👑 Boss: 36分56秒。
2026-09-10 13:30:48,329 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:31:18,312 [INFO] ⏰ 距離上次領體力已滿 5 分鐘，觸發自動領體力。
2026-09-10 13:31:19,361 [INFO] 🍞 定時領取：在城鎮畫面，點擊入口 [common/door.png] 進入大廳以領取體力。
2026-09-10 13:31:19,549 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:19,559 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:22,614 [INFO] 🍞 定時領取：在大廳畫面，跳轉至 BREAD_COLLECTION。
2026-09-10 13:31:22,615 [INFO] 🔄 狀態轉移: COLLECT_ONLY -> BREAD_COLLECTION
2026-09-10 13:31:23,176 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:31:23,443 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9298，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:31:24,380 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:31:24,750 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:31:24,991 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9298，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:31:24,994 [INFO] 🍞 領體力：在大廳偵測到體力按鈕 [0.9298]，點擊打開體力視窗。
2026-09-10 13:31:25,145 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:25,159 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:27,184 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:31:27,721 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:28,289 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:28,289 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:31:28,417 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:28,428 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:29,435 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:31:29,928 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:30,436 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:30,437 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:31:30,533 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:30,543 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:31,508 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:31:32,020 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:32,520 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:32,521 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:31:32,627 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:32,638 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:33,640 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:31:34,157 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:34,672 [INFO] 成功匹配模板 'common/bread_collection.png'！相似度: 0.9356，相對亮度比: 1.01，座標: (878, 537)
2026-09-10 13:31:34,673 [INFO] 🍞 領體力：偵測到領體力按鈕 [common/bread_collection.png] (信心度: 0.9356)，進行點擊領取。
2026-09-10 13:31:34,773 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:34,782 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:35,347 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9690，相對亮度比: 0.98，座標: (766, 451)
2026-09-10 13:31:35,348 [INFO] 🍞 領體力：偵測到體力確認按鈕 [0.9690]，點擊確認。
2026-09-10 13:31:35,448 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:35,460 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:36,403 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9816，相對亮度比: 1.01，座標: (1018, 221)
2026-09-10 13:31:36,404 [INFO] 🍞 領體力：偵測到退出體力按鈕 [common/quit.png] (0.9816)，嘗試點擊關閉視窗。
2026-09-10 13:31:36,497 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:36,509 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:37,525 [INFO] 🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。
2026-09-10 13:31:37,527 [INFO] 🔄 狀態轉移: BREAD_COLLECTION -> COLLECT_ONLY
2026-09-10 13:31:38,413 [INFO] 🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...
2026-09-10 13:31:38,554 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:31:38,564 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:31:49,069 [INFO] 💓 [心跳防斷線] 偵測到閒置已滿 1 分鐘，執行城鎮地圖微幅水平拖曳以維持伺服器連線活躍...
2026-09-10 13:31:55,993 [WARNING] 🔄 [冷卻結束復歸] 偵測到地下城冷卻結束，暫時離開 collect_only 切回刷地下城！(退避總剩餘時間持續倒數中...)
2026-09-10 13:31:55,994 [INFO] 🔄 狀態轉移: COLLECT_ONLY -> UNKNOWN
2026-09-10 13:31:56,636 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-10 13:31:56,645 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-10 13:31:56,646 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-10 13:31:58,866 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-10 13:31:58,867 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.9543，座標: (68, 719)
2026-09-10 13:31:58,868 [INFO] 🔄 狀態轉移: UNKNOWN -> NAVIGATING
2026-09-10 13:31:58,869 [INFO] 🔄 [Activity Scheduler] 體力退避期間地下城冷卻已結束 ➔ 保留地下城復歸路由，不套用 Tier 4 Domain fallback。
2026-09-10 13:31:59,473 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8038，相對亮度比: 0.81，座標: (1115, 764)
2026-09-10 13:31:59,813 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-10 13:32:01,007 [INFO] 成功匹配模板 'common/door.png'！相似度: 0.9543，相對亮度比: 0.99，座標: (68, 719)
2026-09-10 13:32:01,345 [INFO] 成功匹配模板 'diamond.png'！相似度: 0.9750，相對亮度比: 2.25，座標: (1107, 52)
2026-09-10 13:32:01,743 [INFO] [IntentRouting] intent=primary_navigation scene=town action=enter_lobby reason=primary_enter_lobby progress=idle
2026-09-10 13:32:01,922 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:32:01,932 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:32:05,613 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=none reason=in_flight_action_waiting progress=waiting in_flight=enter_lobby expected=lobby age=3.6s deadline=17240.781 attempt=1
2026-09-10 13:32:06,608 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:08,009 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:08,227 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:32:09,020 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:32:09,355 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:32:09,425 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=7.4s deadline=17240.781 attempt=1
2026-09-10 13:32:09,782 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-10 13:32:09,783 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 就緒 (可打), [獸人地堡]: 冷卻中 (8 分 38 秒) | 判定可挑戰: [冰雪洞窟])，在活動大廳點擊 [dungeons/dungeon.png] (0.9805) 切換至地下城頁籤！
2026-09-10 13:32:09,931 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:32:09,941 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:32:11,326 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:12,732 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:12,965 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:32:13,792 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:32:14,177 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:32:14,234 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:14,509 [INFO] 成功匹配模板 'dungeons/Slime_entry.png'！相似度: 0.9851，相對亮度比: 0.99，座標: (283, 344)
2026-09-10 13:32:14,510 [INFO] Card list aligned: tab=dungeon first_card=dungeons/Slime_entry.png confidence=0.9851
2026-09-10 13:32:16,428 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:32:16,429 [INFO] ⏳ 貪婪地下城：[獸人地堡] 處於冷卻中，剩餘 511 秒，跳過。
2026-09-10 13:32:16,429 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:32:20,533 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:21,800 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:22,027 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:32:22,906 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:32:23,293 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:32:23,354 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:25,179 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:32:25,181 [INFO] ⏳ 貪婪地下城：[獸人地堡] 處於冷卻中，剩餘 503 秒，跳過。
2026-09-10 13:32:25,181 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:32:29,301 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:30,605 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:30,821 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:32:31,660 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:32:32,013 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:32:32,082 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:34,164 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:32:34,164 [INFO] ⏳ 貪婪地下城：[獸人地堡] 處於冷卻中，剩餘 494 秒，跳過。
2026-09-10 13:32:34,164 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:32:38,460 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:39,818 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:39,996 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:32:40,696 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:32:40,991 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:32:41,043 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:42,829 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:32:42,829 [INFO] ⏳ 貪婪地下城：[獸人地堡] 處於冷卻中，剩餘 485 秒，跳過。
2026-09-10 13:32:42,829 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:32:46,817 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:48,183 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:32:49,212 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:32:49,538 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:32:49,593 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:51,337 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:32:51,337 [INFO] ⏳ 貪婪地下城：[獸人地堡] 處於冷卻中，剩餘 476 秒，跳過。
2026-09-10 13:32:51,367 [INFO] ℹ️ [CooldownDetector] 木牌模板最高匹配分數: 0.5476 (門檻: 0.58) ➔ 判定無冷卻木牌
2026-09-10 13:32:51,373 [INFO] 🧭 貪婪地下城：[冰雪洞窟] 亮骨頭匹配相似度: 0.9620 (閾值: 0.75)
2026-09-10 13:32:51,373 [INFO] 👉 貪婪地下城：選擇進入 [冰雪洞窟]，點擊座標 (1124, 1439)。
2026-09-10 13:32:51,513 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:32:51,524 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:32:52,207 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9887，相對亮度比: 1.01，座標: (1024, 164)
2026-09-10 13:32:52,536 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:32:53,631 [INFO] 成功匹配模板 'dungeons/dungeon_fight.png'！相似度: 0.9518，相對亮度比: 0.99，座標: (765, 597)
2026-09-10 13:32:53,632 [INFO] 🧭 尋路中：在畫面上找到地下城戰鬥開始按鈕 [dungeons/dungeon_fight.png] (信心度: 0.9518)，點擊進入地下城。
2026-09-10 13:32:53,744 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:32:53,752 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:32:57,921 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:32:58,341 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:32:59,896 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9653，相對亮度比: 0.99，座標: (64, 717)
2026-09-10 13:32:59,897 [INFO] 🧭 尋路中偵測到地下城內部按鈕 [dungeons/leave.png] (信心度: 0.9653)，判定已進入地下城，轉移至 DUNGEON_EXPLORING。
2026-09-10 13:32:59,897 [INFO] 🔄 狀態轉移: NAVIGATING -> EXPLORING
2026-09-10 13:33:01,825 [INFO] 成功匹配模板 'dungeons/dungeon_bless.png'！相似度: 0.9492，相對亮度比: 1.00，座標: (1154, 414)
2026-09-10 13:33:01,827 [INFO] 👉 偵測到接受祝福圖示 [dungeons/dungeon_bless.png]，信心度: 0.9492，進行點擊並啟動「領取祝福」子流程。
2026-09-10 13:33:02,002 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:02,012 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:02,608 [INFO] 🧭 [子流程] 開始執行「領取祝福」階段式子流程...
2026-09-10 13:33:04,435 [INFO] 🧭 [子流程-選卡-Fallback] 點擊畫面第一個選擇按鈕 (0.9474) 座標: (765, 1636)
2026-09-10 13:33:04,540 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:04,551 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:05,557 [INFO] 🧭 [子流程-確定領取] 偵測到確定按鈕 [common/ok.png] (0.9295)，進行點擊 (766, 1564)。
2026-09-10 13:33:05,656 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:05,666 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:06,510 [INFO] 🧭 [子流程-退出] 偵測到退出按鈕 [common/quit.png] (0.9814)，點擊關閉視窗。
2026-09-10 13:33:06,619 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:06,631 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:07,226 [INFO] ✅ 領取祝福子流程回傳成功，將本層祝福狀態標記為 True 並記錄時間。
2026-09-10 13:33:09,021 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:09,023 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:09,189 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:09,199 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:09,843 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9513，相對亮度比: 1.02，座標: (848, 462)
2026-09-10 13:33:09,846 [INFO] 👉 偵測到探險事件 [common/confirm.png]，信心度: 0.9513，點擊處理。
2026-09-10 13:33:09,945 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:09,956 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:11,920 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:11,922 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:12,101 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:12,111 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:13,969 [INFO] 成功匹配模板 'dungeons/Treasure.png'！相似度: 0.9615，相對亮度比: 0.99，座標: (1151, 451)
2026-09-10 13:33:13,971 [INFO] 🧭 偵測到新樓層探索事件，提前結束下樓過渡期並重設探索記憶。
2026-09-10 13:33:13,971 [INFO] 👉 偵測到寶箱地圖格 [dungeons/Treasure.png]，信心度: 0.9615，進行點擊並啟動「開啟寶箱」子流程。
2026-09-10 13:33:14,133 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:14,145 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:14,739 [INFO] 📦 [子流程] 開始執行「開啟寶箱」子流程...
2026-09-10 13:33:15,028 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.9721，相對亮度比: 1.00，座標: (769, 529)
2026-09-10 13:33:15,030 [INFO] 📦 [子流程] 偵測到獲得寶物按鈕 'dungeons/Get_tresure.png'，相似度: 0.9721，進行點擊。
2026-09-10 13:33:15,145 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:15,156 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:16,563 [INFO] 成功匹配模板 'dungeons/Get_tresure_comfirm.png'！相似度: 0.7805，相對亮度比: 0.88，座標: (767, 525)
2026-09-10 13:33:16,564 [INFO] 📦 [子流程] 偵測到獲得寶物確認按鈕 'dungeons/Get_tresure_comfirm.png'，相似度: 0.7805，開始閉環點擊直到按鈕消失。
2026-09-10 13:33:16,565 [INFO] 👉 發起點擊 (768, 1628)，啟動「配對確認直到 [dungeons/Get_tresure_comfirm.png] 消失」輪詢閉環...
2026-09-10 13:33:16,686 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:16,698 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:17,125 [INFO] 🟢 [配對確認完成] 模板 [dungeons/Get_tresure_comfirm.png] 已徹底從畫面上消失！費時 0.33 秒。
2026-09-10 13:33:20,248 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:20,250 [INFO] [Treasure subflow] Completion verified by [dungeons/gungeon_godown.png] (confidence: 0.9530).
2026-09-10 13:33:22,069 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:22,071 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:22,246 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:22,260 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:24,236 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:24,238 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:24,385 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:24,395 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:24,949 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:24,952 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:33:24,952 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:33:25,849 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:25,852 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:33:26,005 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:26,016 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:26,213 [INFO] ⚔️ 戰鬥進行中... 已持續 1 秒
2026-09-10 13:33:34,602 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9594，相對亮度比: 0.98，座標: (765, 525)
2026-09-10 13:33:34,839 [INFO] 成功匹配模板 'common/continue_gray.png'！相似度: 0.9678，相對亮度比: 1.01，座標: (761, 511)
2026-09-10 13:33:34,949 [INFO] 🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [common/continue_gray.png]，信心度: 0.9678
2026-09-10 13:33:35,067 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:35,078 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:35,171 [INFO] 🔄 狀態轉移: BATTLE -> EXPLORING
2026-09-10 13:33:35,712 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:33:36,223 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9515，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:33:36,226 [INFO] 👉 偵測到探險事件 [common/continue.png]，信心度: 0.9515，點擊處理。
2026-09-10 13:33:36,330 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:36,340 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:38,362 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:38,364 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:38,542 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:38,554 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:40,564 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:40,566 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:40,742 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:40,753 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:41,360 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:41,362 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:33:41,363 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:33:42,310 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:42,311 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:33:42,481 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:42,489 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:50,749 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9594，相對亮度比: 0.98，座標: (765, 525)
2026-09-10 13:33:50,976 [INFO] 成功匹配模板 'common/continue_gray.png'！相似度: 0.9678，相對亮度比: 1.01，座標: (761, 511)
2026-09-10 13:33:51,099 [INFO] 🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [common/continue_gray.png]，信心度: 0.9678
2026-09-10 13:33:51,207 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:51,218 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:51,312 [INFO] 🔄 狀態轉移: BATTLE -> EXPLORING
2026-09-10 13:33:51,862 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:33:52,373 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9499，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:33:52,375 [INFO] 👉 偵測到探險事件 [common/continue.png]，信心度: 0.9499，點擊處理。
2026-09-10 13:33:52,496 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:52,507 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:54,533 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:54,536 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:54,699 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:54,711 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:56,592 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:33:56,594 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:33:56,765 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:56,775 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:33:57,290 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:57,292 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:33:57,293 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:33:58,174 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:33:58,176 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:33:58,328 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:33:58,337 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:34:06,410 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9594，相對亮度比: 0.98，座標: (765, 525)
2026-09-10 13:34:06,631 [INFO] 成功匹配模板 'common/continue_gray.png'！相似度: 0.9678，相對亮度比: 1.01，座標: (761, 511)
2026-09-10 13:34:06,758 [INFO] 🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [common/continue_gray.png]，信心度: 0.9678
2026-09-10 13:34:06,875 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:34:06,885 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:34:06,978 [INFO] 🔄 狀態轉移: BATTLE -> EXPLORING
2026-09-10 13:34:07,543 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:34:08,249 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9499，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:34:08,252 [INFO] 👉 偵測到探險事件 [common/continue.png]，信心度: 0.9499，點擊處理。
2026-09-10 13:34:08,370 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:34:08,381 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:34:08,951 [INFO] 成功匹配模板 'dungeons/dungeons_complete.png'！相似度: 0.9307，相對亮度比: 1.00，座標: (766, 722)
2026-09-10 13:34:08,952 [INFO] 🎉 偵測到【地下城通關結束】(dungeons/dungeons_complete.png)，信心度: 0.9307，點擊退出。
2026-09-10 13:34:09,116 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:34:09,126 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:34:09,220 [INFO] 📊 已完成第 86 次地下城通關！
2026-09-10 13:34:09,221 [INFO] ⏳ 貪婪地下城：設定 [冰雪洞窟] (#6) 進入 30 分鐘冷卻期。
2026-09-10 13:34:09,221 [INFO] ⏳ [混合模式] 地下城全冷卻！各副本冷卻情形: [冰雪洞窟]: 冷卻中 (30 分 0 秒), [獸人地堡]: 冷卻中 (6 分 39 秒) ➔ 無可用地下城，將退守切換至普通關卡 (Stage)。
2026-09-10 13:34:09,221 [INFO] 🔄 狀態轉移: EXPLORING -> NAVIGATING
2026-09-10 13:34:12,937 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:13,822 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:34:14,703 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:16,008 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:16,233 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:17,064 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:34:17,445 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:34:17,507 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:17,901 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9266，相對亮度比: 0.99，座標: (526, 715)
2026-09-10 13:34:17,901 [INFO] 🧭 混合模式：地下城全冷卻 (冷卻情形: [冰雪洞窟]: 冷卻中 (29 分 51 秒), [獸人地堡]: 冷卻中 (6 分 30 秒))，在活動大廳點擊 [common/select_stage.png] (0.9266) 切換至普通關卡頁籤！
2026-09-10 13:34:18,042 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:34:18,051 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:34:19,378 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:20,681 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:20,888 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:21,709 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:22,076 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:22,146 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:22,414 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:34:24,334 [INFO] Resetting shared card list: tab=stage first_card=stages/level1_sky_plains.png attempt=1/7
2026-09-10 13:34:26,528 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:27,872 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:28,886 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:29,228 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:29,287 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:29,528 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:34:31,450 [INFO] Resetting shared card list: tab=stage first_card=stages/level1_sky_plains.png attempt=2/7
2026-09-10 13:34:33,638 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:34,865 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:35,046 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:35,730 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:36,084 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:36,148 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:36,398 [INFO] 成功匹配模板 'stages/level1_sky_plains.png'！相似度: 0.9757，相對亮度比: 1.00，座標: (277, 385)
2026-09-10 13:34:36,399 [INFO] Card list aligned: tab=stage first_card=stages/level1_sky_plains.png confidence=0.9757
2026-09-10 13:34:36,724 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:34:37,175 [INFO] ⌛ 尋路中：目標關卡 [stages/level7_forgotten_wasteland.png] 暫時未出現在畫面上，等待載入與穩定中...
2026-09-10 13:34:37,991 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:39,329 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:39,575 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:40,394 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:40,692 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:40,745 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:41,122 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:34:41,521 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 1/6 次...
2026-09-10 13:34:45,543 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:46,898 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:47,132 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:47,969 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:48,304 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:48,359 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:48,724 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:34:49,126 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 2/6 次...
2026-09-10 13:34:53,187 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:54,442 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:34:54,655 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:34:55,473 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:34:55,840 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:34:55,906 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:34:56,316 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:34:56,747 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 3/6 次...
2026-09-10 13:35:00,882 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:35:02,314 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:35:02,538 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:35:03,378 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:35:03,739 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:35:03,803 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:35:04,196 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:35:04,660 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 4/6 次...
2026-09-10 13:35:08,779 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:35:10,109 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:35:10,335 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:35:11,168 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:35:11,512 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:35:11,569 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:35:11,928 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:35:12,563 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9677，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:35:12,997 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9677，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:35:12,999 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9677)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:35:13,141 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:13,153 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:13,638 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9406，相對亮度比: 1.08，座標: (1040, 94)
2026-09-10 13:35:13,901 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:15,102 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:15,337 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:35:15,544 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9406，相對亮度比: 1.08，座標: (1040, 94)
2026-09-10 13:35:17,143 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9159，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:35:17,212 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:35:17,984 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9159，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:35:18,466 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9159，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:35:18,467 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9159)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:35:18,569 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:18,578 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:19,021 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:35:19,317 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:20,689 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:20,917 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:35:21,116 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:35:22,528 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:35:22,586 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:35:22,833 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:35:23,043 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:35:23,579 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:35:23,583 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:35:23,703 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:23,714 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:24,217 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:35:24,547 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:25,843 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:26,037 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:35:26,225 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:35:26,419 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.8394，相對亮度比: 1.04，座標: (884, 548)
2026-09-10 13:35:26,474 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:35:26,474 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:35:26,823 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:35:27,135 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:28,813 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:29,049 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:35:29,264 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:35:29,482 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:35:29,484 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:35:29,715 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:35:29,716 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:35:29,835 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:29,850 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:30,370 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:35:30,724 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:35:32,095 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:35:32,098 [INFO] Lobby start button is still visible after 2.4s; retrying click.
2026-09-10 13:35:32,265 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:32,274 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:33,898 [INFO] Battle feature [common/auto.png] detected (confidence 0.9949); entering BATTLE.
2026-09-10 13:35:33,898 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:35:34,562 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:35:34,565 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:35:34,725 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:34,738 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:34,932 [INFO] ⚔️ 戰鬥進行中... 已持續 1 秒
2026-09-10 13:35:46,005 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:35:46,677 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:35:46,679 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:35:47,391 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:35:47,740 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:35:49,481 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:35:49,481 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:35:49,571 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:49,579 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:50,140 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:35:50,142 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.47 秒。
2026-09-10 13:35:51,485 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:35:52,157 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:35:52,476 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:35:52,477 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:35:52,580 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:52,589 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:53,193 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:35:53,695 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:35:53,696 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:35:53,804 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:53,815 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:54,406 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:35:54,901 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:35:55,375 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:35:55,375 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:35:55,465 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:55,474 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:56,073 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 3.39 秒。
2026-09-10 13:35:57,431 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:35:58,667 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:35:58,827 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:35:58,828 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:35:58,939 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:35:58,948 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:35:59,502 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.46 秒。
2026-09-10 13:36:00,504 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:36:01,500 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.51，座標: (64, 726)
2026-09-10 13:36:02,781 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.51，座標: (64, 726)
2026-09-10 13:36:02,965 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.51，座標: (1109, 54)
2026-09-10 13:36:03,675 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.51，座標: (531, 712)
2026-09-10 13:36:04,003 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8872，相對亮度比: 0.49，座標: (648, 713)
2026-09-10 13:36:04,058 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:36:04,421 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8557，相對亮度比: 0.55，座標: (526, 715)
2026-09-10 13:36:05,139 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9691，相對亮度比: 0.51，座標: (1293, 329)
2026-09-10 13:36:05,624 [WARNING] ⚠️ 模板 'stages/level7_forgotten_wasteland.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:36:05,677 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:36:06,612 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:36:07,901 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:36:08,136 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:36:08,879 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:36:09,215 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:36:09,272 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:36:09,639 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:36:10,318 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:36:10,813 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:36:10,815 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9696)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:36:10,963 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:10,973 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:11,455 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9605，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:36:11,782 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:13,111 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:13,327 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.8329，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:36:13,519 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9605，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:36:14,990 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9185，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:36:15,051 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:36:15,511 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9330，相對亮度比: 1.03，座標: (563, 576)
2026-09-10 13:36:15,942 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9185，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:36:16,401 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9185，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:36:16,403 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9185)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:36:16,503 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:16,515 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:17,008 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:36:17,338 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:18,639 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:18,867 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:36:19,060 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:36:20,621 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:36:20,686 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:36:20,948 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:36:21,125 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:36:21,679 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:36:21,681 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:36:21,788 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:21,799 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:22,302 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:36:22,626 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:23,949 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:24,148 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:36:24,342 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:36:24,566 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.8319，相對亮度比: 1.04，座標: (884, 549)
2026-09-10 13:36:24,627 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:36:24,627 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:36:25,016 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:36:25,276 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:26,508 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:26,728 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:36:26,927 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:36:27,159 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:36:27,161 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:36:27,345 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:36:27,347 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:36:27,442 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:27,453 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:27,896 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:36:28,189 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:36:29,479 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:36:29,481 [INFO] Lobby start button is still visible after 2.1s; retrying click.
2026-09-10 13:36:29,654 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:29,663 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:31,246 [INFO] Battle feature [common/auto.png] detected (confidence 0.9948); entering BATTLE.
2026-09-10 13:36:31,246 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:36:31,905 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9948，相對亮度比: 0.60，座標: (1200, 55)
2026-09-10 13:36:31,907 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:36:32,058 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:32,068 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:32,982 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:36:32,984 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:36:33,138 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:33,151 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:35,054 [INFO] ⚔️ 戰鬥進行中... 已持續 3 秒
2026-09-10 13:36:49,289 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:36:49,915 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:36:49,916 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:36:50,721 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:36:51,127 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:36:52,904 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:36:52,905 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:36:53,016 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:53,027 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:53,599 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:36:53,601 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.48 秒。
2026-09-10 13:36:54,991 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:36:55,788 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:36:56,166 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:36:56,166 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:36:56,267 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:56,279 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:56,897 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:36:57,451 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:36:57,451 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:36:57,560 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:57,571 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:58,149 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:36:58,678 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:36:58,678 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:36:58,783 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:36:58,794 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:36:59,383 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 3.01 秒。
2026-09-10 13:37:00,795 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:37:02,256 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:37:02,459 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:37:02,460 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:37:02,576 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:02,591 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:03,226 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.54 秒。
2026-09-10 13:37:04,229 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:37:05,230 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.56，座標: (64, 726)
2026-09-10 13:37:06,625 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.56，座標: (64, 726)
2026-09-10 13:37:06,854 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.56，座標: (1109, 54)
2026-09-10 13:37:07,634 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.56，座標: (531, 712)
2026-09-10 13:37:07,912 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.54，座標: (648, 713)
2026-09-10 13:37:07,964 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:37:08,291 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 0.60，座標: (526, 715)
2026-09-10 13:37:08,896 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.56，座標: (1293, 329)
2026-09-10 13:37:09,401 [WARNING] ⚠️ 模板 'stages/level7_forgotten_wasteland.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:37:09,463 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:37:10,450 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:37:11,737 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:37:11,963 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:37:12,814 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:37:13,153 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:37:13,210 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:37:13,586 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:37:14,227 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9688，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:37:14,660 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9688，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:37:14,661 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9688)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:37:14,791 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:14,801 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:15,291 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9595，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:37:15,617 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:16,952 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:17,176 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:37:17,355 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9595，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:37:18,761 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:37:18,831 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:37:19,360 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9350，相對亮度比: 1.03，座標: (563, 576)
2026-09-10 13:37:19,866 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:37:20,450 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:37:20,451 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9193)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:37:20,559 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:20,571 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:21,069 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:37:21,411 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:22,605 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:22,987 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:37:24,366 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:37:24,426 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:37:24,689 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:37:24,893 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:37:25,466 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:37:25,467 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:37:25,571 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:25,581 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:26,079 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:37:26,391 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:27,631 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:27,856 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:37:28,055 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:37:28,281 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.8988，相對亮度比: 1.02，座標: (882, 545)
2026-09-10 13:37:28,347 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:37:28,349 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:37:28,746 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:37:29,103 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:30,583 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:30,810 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:37:31,038 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:37:31,284 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:37:31,285 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:37:31,532 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:37:31,535 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:37:31,644 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:31,652 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:32,093 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:37:32,402 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:37:33,693 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:37:33,694 [INFO] Lobby start button is still visible after 2.2s; retrying click.
2026-09-10 13:37:33,857 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:33,870 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:35,467 [INFO] Battle feature [common/auto.png] detected (confidence 0.9949); entering BATTLE.
2026-09-10 13:37:35,467 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:37:36,067 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:37:36,068 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:37:36,225 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:36,237 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:36,430 [INFO] ⚔️ 戰鬥進行中... 已持續 0 秒
2026-09-10 13:37:50,486 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:37:50,785 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:37:50,786 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:37:51,479 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:37:51,842 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:37:53,600 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:37:53,600 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:37:53,695 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:53,705 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:54,264 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:37:54,267 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.47 秒。
2026-09-10 13:37:55,682 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:37:56,503 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:37:56,791 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:37:56,791 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:37:56,891 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:56,901 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:57,454 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:37:57,928 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:37:58,407 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:37:58,407 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:37:58,506 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:58,516 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:37:59,134 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:37:59,625 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:37:59,625 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:37:59,752 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:37:59,762 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:00,377 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 3.38 秒。
2026-09-10 13:38:01,813 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:38:03,201 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:38:03,393 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:38:03,394 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:38:03,513 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:03,522 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:04,059 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.44 秒。
2026-09-10 13:38:05,061 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:38:06,058 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.50，座標: (64, 726)
2026-09-10 13:38:07,540 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.50，座標: (64, 726)
2026-09-10 13:38:07,777 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.50，座標: (1109, 54)
2026-09-10 13:38:08,550 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.50，座標: (531, 712)
2026-09-10 13:38:08,909 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8871，相對亮度比: 0.48，座標: (648, 713)
2026-09-10 13:38:08,976 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:38:09,368 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8554，相對亮度比: 0.53，座標: (526, 715)
2026-09-10 13:38:10,105 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9678，相對亮度比: 0.50，座標: (1293, 329)
2026-09-10 13:38:10,619 [WARNING] ⚠️ 模板 'stages/level7_forgotten_wasteland.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:38:10,680 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:38:11,669 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:38:13,065 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:38:13,290 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:38:14,121 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:38:14,488 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:38:14,557 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:38:14,947 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:38:15,676 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9682，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:38:16,167 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9682，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:38:16,168 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9682)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:38:16,314 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:16,325 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:16,867 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9596，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:38:17,198 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:18,484 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:18,682 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:38:18,851 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9596，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:38:20,355 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9190，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:38:20,418 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:38:20,847 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9368，相對亮度比: 1.02，座標: (563, 576)
2026-09-10 13:38:21,219 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9190，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:38:21,739 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9190，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:38:21,741 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9190)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:38:21,850 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:21,860 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:22,396 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:38:22,738 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:24,124 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:24,344 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:38:24,549 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:38:25,988 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9193，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:38:26,050 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:38:26,319 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:38:26,531 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:38:27,099 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:38:27,102 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:38:27,215 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:27,226 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:27,723 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:38:28,014 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:29,299 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:29,521 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:38:29,741 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:38:29,978 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.8993，相對亮度比: 1.02，座標: (881, 544)
2026-09-10 13:38:30,048 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:38:30,049 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:38:30,430 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:38:30,747 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:32,231 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:32,429 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:38:32,614 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:38:32,812 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:38:32,814 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:38:33,005 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:38:33,006 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:38:33,107 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:33,116 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:33,543 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:38:33,839 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:38:35,177 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9569，相對亮度比: 1.16，座標: (877, 541)
2026-09-10 13:38:35,181 [INFO] Lobby start button is still visible after 2.2s; retrying click.
2026-09-10 13:38:35,347 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:35,358 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:36,945 [INFO] Battle feature [common/auto.png] detected (confidence 0.9948); entering BATTLE.
2026-09-10 13:38:36,946 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:38:37,573 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9948，相對亮度比: 0.60，座標: (1200, 55)
2026-09-10 13:38:37,575 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:38:37,709 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:37,721 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:37,914 [INFO] ⚔️ 戰鬥進行中... 已持續 0 秒
2026-09-10 13:38:38,650 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:38:38,652 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:38:38,817 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:38:38,828 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:38:56,788 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:38:57,432 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:38:57,433 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:38:58,101 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:38:58,415 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:39:00,217 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:39:00,217 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:39:00,328 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:00,339 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:00,911 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:39:00,912 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.48 秒。
2026-09-10 13:39:02,265 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:39:03,019 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:39:03,369 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:39:03,370 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:39:03,476 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:03,486 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:04,097 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:39:04,607 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:39:04,608 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:39:04,712 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:04,721 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:05,307 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:39:05,854 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:39:05,855 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:39:05,940 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:05,949 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:06,538 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 2.96 秒。
2026-09-10 13:39:07,849 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:39:09,231 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:39:09,432 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:39:09,432 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:39:09,543 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:09,553 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:10,120 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.47 秒。
2026-09-10 13:39:11,121 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:39:11,982 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.51，座標: (64, 726)
2026-09-10 13:39:13,228 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.51，座標: (64, 726)
2026-09-10 13:39:13,448 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9722，相對亮度比: 0.51，座標: (1109, 54)
2026-09-10 13:39:14,274 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.51，座標: (531, 712)
2026-09-10 13:39:14,613 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8873，相對亮度比: 0.49，座標: (648, 713)
2026-09-10 13:39:14,678 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:39:15,061 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8561，相對亮度比: 0.55，座標: (526, 715)
2026-09-10 13:39:15,779 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.51，座標: (1293, 329)
2026-09-10 13:39:16,277 [WARNING] ⚠️ 模板 'stages/level7_forgotten_wasteland.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:39:16,329 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:39:17,303 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:39:18,629 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:39:18,854 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:39:19,664 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:39:20,007 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:39:20,061 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:39:20,447 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:39:21,140 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (1293, 329)
2026-09-10 13:39:21,670 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (1293, 329)
2026-09-10 13:39:21,671 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9655)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:39:21,802 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:21,813 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:22,305 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.8231，相對亮度比: 1.20，座標: (1064, 67)
2026-09-10 13:39:22,631 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:24,051 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:24,479 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.8231，相對亮度比: 1.20，座標: (1064, 67)
2026-09-10 13:39:26,059 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9132，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:39:26,120 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:39:26,905 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9132，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:39:27,418 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9132，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:39:27,419 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9132)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:39:27,527 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:27,535 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:28,045 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:39:28,380 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:29,776 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:30,199 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:39:31,776 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9174，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:39:31,829 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:39:32,054 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:39:32,242 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:39:32,716 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:39:32,717 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:39:32,816 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:32,828 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:33,317 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:39:33,653 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:34,919 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:35,125 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:39:35,303 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:39:35,507 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.8334，相對亮度比: 1.04，座標: (884, 548)
2026-09-10 13:39:35,574 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:39:35,576 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:39:35,971 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:39:36,293 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:37,784 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:37,975 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.8212，相對亮度比: 0.39，座標: (1109, 53)
2026-09-10 13:39:38,152 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:39:38,358 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:39:38,360 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:39:38,562 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:39:38,564 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:39:38,661 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:38,673 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:39,107 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:39:39,398 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:39:40,814 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:39:40,816 [INFO] Lobby start button is still visible after 2.3s; retrying click.
2026-09-10 13:39:40,979 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:40,991 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:42,461 [INFO] Battle feature [common/auto.png] detected (confidence 0.9948); entering BATTLE.
2026-09-10 13:39:42,461 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:39:42,974 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9948，相對亮度比: 0.60，座標: (1200, 55)
2026-09-10 13:39:42,976 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:39:43,125 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:43,136 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:43,330 [INFO] ⚔️ 戰鬥進行中... 已持續 0 秒
2026-09-10 13:39:44,119 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:39:44,124 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:39:44,297 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:44,307 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:55,180 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:39:55,559 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:39:55,559 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:39:56,519 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:39:56,920 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:39:58,753 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:39:58,754 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:39:58,866 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:39:58,876 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:39:59,519 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:39:59,521 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.55 秒。
2026-09-10 13:40:00,970 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:40:02,028 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:40:02,441 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:40:02,443 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:40:02,580 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:02,599 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:03,255 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:40:03,822 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:40:03,823 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:40:03,945 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:03,958 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:04,568 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:40:05,104 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:40:05,105 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:40:05,205 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:05,216 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:05,871 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 3.18 秒。
2026-09-10 13:40:07,254 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:40:08,691 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:40:08,867 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:40:08,867 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:40:08,964 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:08,974 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:09,524 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.46 秒。
2026-09-10 13:40:10,525 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:40:11,380 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.49，座標: (64, 726)
2026-09-10 13:40:12,569 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.49，座標: (64, 726)
2026-09-10 13:40:12,755 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9720，相對亮度比: 0.50，座標: (1109, 54)
2026-09-10 13:40:13,508 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.50，座標: (531, 712)
2026-09-10 13:40:13,783 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8872，相對亮度比: 0.48，座標: (648, 713)
2026-09-10 13:40:13,832 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:40:14,198 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8561，相對亮度比: 0.53，座標: (526, 715)
2026-09-10 13:40:14,898 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9676，相對亮度比: 0.50，座標: (1293, 329)
2026-09-10 13:40:15,391 [WARNING] ⚠️ 模板 'stages/level7_forgotten_wasteland.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:40:15,453 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:40:16,423 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:40:17,598 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:40:17,788 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:40:18,601 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:40:18,961 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:40:19,021 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:40:19,401 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:40:20,106 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:40:20,546 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9696，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:40:20,547 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9696)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:40:20,683 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:20,692 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:21,178 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9519，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:40:21,464 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:22,982 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:23,236 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:40:23,460 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9519，相對亮度比: 1.05，座標: (1033, 102)
2026-09-10 13:40:25,217 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:25,277 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:40:25,715 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9347，相對亮度比: 1.01，座標: (562, 576)
2026-09-10 13:40:26,123 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:26,605 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:26,606 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9192)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:40:26,717 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:26,728 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:27,288 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:40:27,635 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:29,097 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:29,395 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:40:29,611 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:40:31,202 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:31,265 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:40:31,580 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:40:31,811 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:40:32,400 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:40:32,402 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:40:32,522 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:32,531 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:32,995 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:40:33,322 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:34,591 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:34,815 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:40:35,038 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:40:36,532 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:36,596 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:40:37,662 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:38,262 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9192，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:40:38,264 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9192)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:40:38,378 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:38,389 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:38,879 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:40:39,198 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:40,779 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:41,000 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:40:41,205 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:40:41,426 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:40:41,480 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:40:41,481 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:40:41,871 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:40:42,206 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:43,736 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:43,951 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:40:44,135 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:40:44,368 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:40:44,371 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:40:44,664 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:40:44,665 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:40:44,792 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:44,803 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:45,336 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:40:45,691 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:40:47,121 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:40:47,122 [INFO] Lobby start button is still visible after 2.5s; retrying click.
2026-09-10 13:40:47,282 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:47,291 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:48,984 [INFO] Battle feature [common/auto.png] detected (confidence 0.9949); entering BATTLE.
2026-09-10 13:40:48,986 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:40:49,532 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:40:49,533 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:40:49,686 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:40:49,697 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:40:49,892 [INFO] ⚔️ 戰鬥進行中... 已持續 0 秒
2026-09-10 13:41:04,467 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9712，相對亮度比: 0.98，座標: (765, 652)
2026-09-10 13:41:04,994 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue.png] (信心度: 0.9712)，切換至結算狀態。
2026-09-10 13:41:04,994 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:41:05,724 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8737，相對亮度比: 1.01，座標: (766, 651)
2026-09-10 13:41:06,093 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:41:07,679 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:41:07,905 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:41:07,905 [INFO] 👉 發起點擊 (766, 1755)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:41:08,011 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:08,025 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:08,671 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:41:08,673 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.55 秒。
2026-09-10 13:41:10,009 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8611，相對亮度比: 0.76，座標: (766, 651)
2026-09-10 13:41:10,611 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:41:10,785 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 2 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:41:11,131 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue_gray.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:41:11,133 [INFO] 👉 發起點擊 (762, 1742)，啟動「配對確認直到 [common/continue_gray.png] 消失」輪詢閉環...
2026-09-10 13:41:11,238 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:11,249 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:11,839 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:41:12,341 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:41:12,853 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9678)，持續等待淡出...
2026-09-10 13:41:12,854 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:41:12,958 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:12,968 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:13,616 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9503)，持續等待淡出...
2026-09-10 13:41:14,100 [INFO] ⌛ [配對確認中] 模板 [common/continue_gray.png] 仍存在於畫面上 (相似度: 0.9680)，持續等待淡出...
2026-09-10 13:41:14,101 [INFO] 🔄 [自動補點] 模板 [common/continue_gray.png] 在 1.0 秒內未消失，對當前目標位置 (762, 1614) 重新發起點擊...
2026-09-10 13:41:14,198 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:14,210 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:14,819 [INFO] 🟢 [配對確認完成] 模板 [common/continue_gray.png] 已徹底從畫面上消失！費時 3.48 秒。
2026-09-10 13:41:16,227 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.9655，相對亮度比: 1.00，座標: (833, 651)
2026-09-10 13:41:16,665 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:41:17,619 [INFO] 👉 [結算 Step 2] 畫面上已無 continue/confirm，且終局按鈕 (retry/exit) 已顯現，確信 continue 階段結束，切換至 FINAL_MATCH！
2026-09-10 13:41:17,816 [INFO] 👉 [結算子流程 Step 3] 離場條件成立 (第 4/8/10 場或需領獎)，發現離場按鈕 [exit_battle.png] (0.9655)，點擊退出戰鬥 (配對確認直到消失)...
2026-09-10 13:41:17,817 [INFO] 👉 發起點擊 (834, 1754)，啟動「配對確認直到 [exit_battle.png] 消失」輪詢閉環...
2026-09-10 13:41:17,919 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:17,929 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:18,528 [INFO] 🟢 [配對確認完成] 模板 [exit_battle.png] 已徹底從畫面上消失！費時 0.50 秒。
2026-09-10 13:41:19,531 [INFO] 🔄 狀態轉移: RESULT -> NAVIGATING
2026-09-10 13:41:19,532 [INFO] 🔄 [Activity Scheduler] 體力退避期間地下城冷卻已結束 ➔ 保留地下城復歸路由，不套用 Tier 4 Domain fallback。
2026-09-10 13:41:20,451 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.52，座標: (64, 726)
2026-09-10 13:41:21,806 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9208，相對亮度比: 0.52，座標: (64, 726)
2026-09-10 13:41:22,018 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.53，座標: (1109, 54)
2026-09-10 13:41:22,838 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9810，相對亮度比: 0.53，座標: (531, 712)
2026-09-10 13:41:23,184 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8873，相對亮度比: 0.51，座標: (648, 713)
2026-09-10 13:41:23,248 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:41:23,595 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9804，相對亮度比: 0.53，座標: (648, 715)
2026-09-10 13:41:23,597 [INFO] 🧭 混合模式：地下城已就緒 (冷卻情形: [冰雪洞窟]: 冷卻中 (22 分 45 秒), [獸人地堡]: 就緒 (可打) | 判定可挑戰: [獸人地堡])，在活動大廳點擊 [dungeons/dungeon.png] (0.9804) 切換至地下城頁籤！
2026-09-10 13:41:23,730 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:41:23,742 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:41:25,085 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:26,425 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:27,341 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:41:27,611 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:41:27,662 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:41:27,708 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:41:29,639 [INFO] Resetting shared card list: tab=dungeon first_card=dungeons/Slime_entry.png attempt=1/7
2026-09-10 13:41:31,804 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:33,124 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:33,320 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:41:34,027 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:41:34,353 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:41:34,417 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:41:34,468 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:41:36,405 [INFO] Resetting shared card list: tab=dungeon first_card=dungeons/Slime_entry.png attempt=2/7
2026-09-10 13:41:38,580 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:39,956 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:40,190 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:41:41,055 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:41:41,427 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:41:41,495 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:41:41,829 [INFO] 成功匹配模板 'dungeons/Slime_entry.png'！相似度: 0.9813，相對亮度比: 0.99，座標: (283, 344)
2026-09-10 13:41:41,836 [INFO] Card list aligned: tab=dungeon first_card=dungeons/Slime_entry.png confidence=0.9813
2026-09-10 13:41:43,827 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:41:43,828 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:41:48,165 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:50,156 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:41:50,444 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:41:51,576 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:41:52,028 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:41:52,093 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:41:54,667 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:41:54,667 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:41:58,913 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:00,781 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:01,093 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:42:02,057 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:42:02,439 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:42:02,518 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:42:04,807 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:42:04,808 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:42:08,942 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:10,692 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:10,944 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:42:11,948 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:42:12,364 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:42:12,432 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:42:14,677 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:42:14,680 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:42:18,617 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:19,913 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:20,148 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:42:21,037 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:42:21,419 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:42:21,481 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:42:23,235 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:42:23,236 [INFO] 🧭 [卡片導航] 目標在右側，執行向左滑動翻頁...
2026-09-10 13:42:27,375 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:28,601 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:42:28,821 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:42:29,545 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:42:29,886 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:42:29,949 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:42:31,765 [INFO] 🧭 貪婪地下城：偵測到地下城選關介面，執行入口對齊與選關。
2026-09-10 13:42:31,814 [INFO] ℹ️ [CooldownDetector] 木牌模板最高匹配分數: 0.4557 (門檻: 0.58) ➔ 判定無冷卻木牌
2026-09-10 13:42:31,821 [INFO] 🧭 貪婪地下城：[獸人地堡] 亮骨頭匹配相似度: 0.9301 (閾值: 0.75)
2026-09-10 13:42:31,821 [INFO] 👉 貪婪地下城：選擇進入 [獸人地堡]，點擊座標 (1248, 1440)。
2026-09-10 13:42:31,961 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:31,971 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:32,679 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9887，相對亮度比: 1.01，座標: (1024, 164)
2026-09-10 13:42:32,969 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:42:34,103 [INFO] 成功匹配模板 'dungeons/dungeon_fight.png'！相似度: 0.9518，相對亮度比: 0.99，座標: (765, 597)
2026-09-10 13:42:34,104 [INFO] 🧭 尋路中：在畫面上找到地下城戰鬥開始按鈕 [dungeons/dungeon_fight.png] (信心度: 0.9518)，點擊進入地下城。
2026-09-10 13:42:34,228 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:34,242 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:38,852 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:42:39,316 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:42:40,905 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9687，相對亮度比: 0.98，座標: (64, 717)
2026-09-10 13:42:40,906 [INFO] 🧭 尋路中偵測到地下城內部按鈕 [dungeons/leave.png] (信心度: 0.9687)，判定已進入地下城，轉移至 DUNGEON_EXPLORING。
2026-09-10 13:42:40,907 [INFO] 🔄 狀態轉移: NAVIGATING -> EXPLORING
2026-09-10 13:42:42,766 [INFO] 成功匹配模板 'dungeons/dungeon_bless.png'！相似度: 0.9492，相對亮度比: 1.00，座標: (1154, 414)
2026-09-10 13:42:42,767 [INFO] 👉 偵測到接受祝福圖示 [dungeons/dungeon_bless.png]，信心度: 0.9492，進行點擊並啟動「領取祝福」子流程。
2026-09-10 13:42:42,924 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:42,938 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:43,531 [INFO] 🧭 [子流程] 開始執行「領取祝福」階段式子流程...
2026-09-10 13:42:45,304 [INFO] 🧭 [子流程-選卡-Fallback] 點擊畫面第一個選擇按鈕 (0.9474) 座標: (765, 1636)
2026-09-10 13:42:45,415 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:45,426 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:46,506 [INFO] 🧭 [子流程-確定領取] 偵測到確定按鈕 [common/ok.png] (0.9295)，進行點擊 (766, 1564)。
2026-09-10 13:42:46,613 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:46,626 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:47,506 [INFO] 🧭 [子流程-退出] 偵測到退出按鈕 [common/quit.png] (0.9814)，點擊關閉視窗。
2026-09-10 13:42:47,614 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:47,626 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:48,221 [INFO] ✅ 領取祝福子流程回傳成功，將本層祝福狀態標記為 True 並記錄時間。
2026-09-10 13:42:50,276 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:42:50,279 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:42:50,427 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:50,435 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:51,045 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.8787，相對亮度比: 1.05，座標: (850, 464)
2026-09-10 13:42:51,047 [INFO] 👉 偵測到探險事件 [common/confirm.png]，信心度: 0.8787，點擊處理。
2026-09-10 13:42:51,144 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:51,156 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:53,148 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:42:53,150 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:42:53,307 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:53,318 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:55,134 [INFO] 成功匹配模板 'dungeons/Treasure.png'！相似度: 0.9615，相對亮度比: 0.99，座標: (1151, 451)
2026-09-10 13:42:55,136 [INFO] 🧭 偵測到新樓層探索事件，提前結束下樓過渡期並重設探索記憶。
2026-09-10 13:42:55,136 [INFO] 👉 偵測到寶箱地圖格 [dungeons/Treasure.png]，信心度: 0.9615，進行點擊並啟動「開啟寶箱」子流程。
2026-09-10 13:42:55,291 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:55,300 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:55,895 [INFO] 📦 [子流程] 開始執行「開啟寶箱」子流程...
2026-09-10 13:42:56,209 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.9721，相對亮度比: 1.00，座標: (769, 529)
2026-09-10 13:42:56,211 [INFO] 📦 [子流程] 偵測到獲得寶物按鈕 'dungeons/Get_tresure.png'，相似度: 0.9721，進行點擊。
2026-09-10 13:42:56,324 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:56,333 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:57,733 [INFO] 成功匹配模板 'dungeons/Get_tresure_comfirm.png'！相似度: 0.7973，相對亮度比: 1.06，座標: (767, 527)
2026-09-10 13:42:57,735 [INFO] 📦 [子流程] 偵測到獲得寶物確認按鈕 'dungeons/Get_tresure_comfirm.png'，相似度: 0.7973，開始閉環點擊直到按鈕消失。
2026-09-10 13:42:57,736 [INFO] 👉 發起點擊 (768, 1630)，啟動「配對確認直到 [dungeons/Get_tresure_comfirm.png] 消失」輪詢閉環...
2026-09-10 13:42:57,849 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:42:57,857 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:42:58,292 [INFO] 🟢 [配對確認完成] 模板 [dungeons/Get_tresure_comfirm.png] 已徹底從畫面上消失！費時 0.34 秒。
2026-09-10 13:43:01,166 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:01,894 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:02,604 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:03,314 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:04,040 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:04,756 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:05,526 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:06,304 [INFO] 成功匹配模板 'dungeons/Get_tresure.png'！相似度: 0.8173，相對亮度比: 0.96，座標: (769, 527)
2026-09-10 13:43:06,606 [WARNING] 📦 [子流程] 開啟寶箱子流程超時結束。
2026-09-10 13:43:06,607 [WARNING] [Treasure subflow] Completion was not verified; keeping the floor treasure eligible for retry.
2026-09-10 13:43:07,273 [INFO] 成功匹配模板 'common/confirm.png'！相似度: 0.9667，相對亮度比: 0.98，座標: (766, 523)
2026-09-10 13:43:07,275 [INFO] 👉 偵測到探險事件 [common/confirm.png]，信心度: 0.9667，點擊處理。
2026-09-10 13:43:07,389 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:07,404 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:09,298 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:43:09,300 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:43:09,455 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:09,465 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:11,187 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:43:11,189 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:43:11,327 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:11,334 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:11,836 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:43:11,839 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:43:11,839 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:43:12,719 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:43:12,721 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:43:12,856 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:12,865 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:13,059 [INFO] ⚔️ 戰鬥進行中... 已持續 1 秒
2026-09-10 13:43:27,788 [INFO] ⚔️ [戰鬥進展] 偵測到血條產生顯著變化 (diff=1496, 停滯 5.7s 解除)，戰鬥正常推進中！
2026-09-10 13:43:28,652 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9499，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:43:29,011 [INFO] 🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [common/continue.png]，信心度: 0.9499
2026-09-10 13:43:29,116 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:29,129 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:29,224 [INFO] 🔄 狀態轉移: BATTLE -> EXPLORING
2026-09-10 13:43:29,799 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:43:30,345 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9499，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:43:30,348 [INFO] 👉 偵測到探險事件 [common/continue.png]，信心度: 0.9499，點擊處理。
2026-09-10 13:43:30,449 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:30,459 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:32,320 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:43:32,322 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:43:32,479 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:32,489 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:34,660 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:43:34,663 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:43:34,835 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:34,849 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:35,433 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:43:35,435 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:43:35,437 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:43:36,227 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:43:36,228 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:43:36,357 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:43:36,366 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:43:58,309 [INFO] ⚔️ [戰鬥進展] 偵測到血條產生顯著變化 (diff=1669, 停滯 6.2s 解除)，戰鬥正常推進中！
2026-09-10 13:44:01,761 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9594，相對亮度比: 0.98，座標: (765, 525)
2026-09-10 13:44:02,006 [INFO] 成功匹配模板 'common/continue_gray.png'！相似度: 0.9678，相對亮度比: 1.01，座標: (761, 511)
2026-09-10 13:44:02,129 [INFO] 🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [common/continue_gray.png]，信心度: 0.9678
2026-09-10 13:44:02,239 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:02,251 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:02,344 [INFO] 🔄 狀態轉移: BATTLE -> EXPLORING
2026-09-10 13:44:02,961 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:44:03,513 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9502，相對亮度比: 0.60，座標: (765, 525)
2026-09-10 13:44:03,514 [INFO] 👉 偵測到探險事件 [common/continue.png]，信心度: 0.9502，點擊處理。
2026-09-10 13:44:03,635 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:03,645 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:05,593 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:44:05,594 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:44:05,746 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:05,759 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:07,821 [INFO] 成功匹配模板 'dungeons/gungeon_godown.png'！相似度: 0.9530，相對亮度比: 1.00，座標: (767, 718)
2026-09-10 13:44:07,823 [INFO] 🧭 偵測到下樓按鈕 [dungeons/gungeon_godown.png]，信心度: 0.9530，點擊下樓並開始本層記憶冷卻。
2026-09-10 13:44:07,992 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:08,002 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:08,588 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:44:08,591 [INFO] ⚔️ 偵測到戰鬥已真正開始（出現 auto 按鈕，相似度: 0.9949），進入戰鬥狀態！
2026-09-10 13:44:08,591 [INFO] 🔄 狀態轉移: EXPLORING -> BATTLE
2026-09-10 13:44:09,444 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:44:09,445 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:44:09,608 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:09,618 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:13,834 [INFO] ⚔️ 戰鬥進行中... 已持續 5 秒
2026-09-10 13:44:22,981 [INFO] ⚔️ [戰鬥進展] 偵測到血條產生顯著變化 (diff=574, 停滯 5.9s 解除)，戰鬥正常推進中！
2026-09-10 13:44:33,524 [INFO] 成功匹配模板 'defeat.png'！相似度: 0.9782，相對亮度比: 0.98，座標: (756, 413)
2026-09-10 13:44:33,525 [INFO] 💀 偵測到戰敗畫面 [0.9782]，戰鬥結束！切換至結算狀態。
2026-09-10 13:44:33,525 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:44:34,652 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:44:36,415 [INFO] 成功匹配模板 'defeat.png'！相似度: 0.9798，相對亮度比: 0.98，座標: (756, 413)
2026-09-10 13:44:36,417 [INFO] 💀 結算處理：確認處於戰敗畫面 [0.9798]。
2026-09-10 13:44:36,631 [INFO] 成功匹配模板 'defeat_retry.png'！相似度: 0.9105，相對亮度比: 1.00，座標: (668, 651)
2026-09-10 13:44:36,632 [INFO] 👉 偵測到重新開始按鈕 [defeat_retry.png] (信心度: 0.9105)，進行點擊重新開始。
2026-09-10 13:44:36,711 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:36,722 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:36,815 [INFO] 🚀 已點擊重新開始按鈕，累計戰敗次數: 1
2026-09-10 13:44:37,816 [INFO] 🚀 點擊重新開始按鈕，進入過渡載入等待... (累計啟動次數: 87)
2026-09-10 13:44:37,817 [INFO] 🔄 狀態轉移: RESULT -> LOADING
2026-09-10 13:44:39,193 [INFO] ⚔️ 載入完成！偵測到戰鬥特徵 [common/auto.png] (相似度: 0.9535)，轉移至 BATTLE 狀態。
2026-09-10 13:44:39,194 [INFO] 🔄 狀態轉移: LOADING -> BATTLE
2026-09-10 13:44:39,936 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:44:39,938 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:44:40,086 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:44:40,094 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:44:51,303 [INFO] ⚔️ [戰鬥進展] 偵測到血條產生顯著變化 (diff=301, 停滯 6.4s 解除)，戰鬥正常推進中！
2026-09-10 13:44:59,384 [INFO] ⚔️ [戰鬥進展] 偵測到血條產生顯著變化 (diff=307, 停滯 8.1s 解除)，戰鬥正常推進中！
2026-09-10 13:45:11,246 [INFO] 成功匹配模板 'common/continue.png'！相似度: 0.9594，相對亮度比: 0.98，座標: (765, 525)
2026-09-10 13:45:11,501 [INFO] 成功匹配模板 'common/continue_gray.png'！相似度: 0.9678，相對亮度比: 1.01，座標: (761, 511)
2026-09-10 13:45:11,627 [INFO] 🏆 戰鬥結束！偵測到結算按鈕 [common/continue_gray.png] (信心度: 0.9678)，切換至結算狀態。
2026-09-10 13:45:11,628 [INFO] 🔄 狀態轉移: BATTLE -> RESULT
2026-09-10 13:45:12,403 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8681，相對亮度比: 1.02，座標: (766, 523)
2026-09-10 13:45:13,025 [INFO] ⏳ [結算子流程 Step 1] 戰鬥剛結束，執行初次登場沉澱 (休眠 1.5 秒)，等待勝負畫面與第一層彈窗定格...
2026-09-10 13:45:14,626 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:14,821 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:45:14,822 [INFO] 👉 發起點擊 (766, 1628)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:45:14,910 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:14,921 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:15,499 [WARNING] ⚠️ 模板 'common/continue.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-10 13:45:15,503 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.49 秒。
2026-09-10 13:45:16,868 [INFO] 成功匹配模板 'exit_battle.png'！相似度: 0.8681，相對亮度比: 1.02，座標: (766, 523)
2026-09-10 13:45:17,484 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:17,653 [INFO] 👉 [結算 Step 2] 偵測到『繼續』按鈕 (common/continue.png)，發起點擊並 WHILE 輪詢直到消失...
2026-09-10 13:45:17,654 [INFO] 👉 發起點擊 (766, 1628)，啟動「配對確認直到 [common/continue.png] 消失」輪詢閉環...
2026-09-10 13:45:17,742 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:17,752 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:18,313 [INFO] 🟢 [配對確認完成] 模板 [common/continue.png] 已徹底從畫面上消失！費時 0.47 秒。
2026-09-10 13:45:20,078 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:21,188 [INFO] ⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...
2026-09-10 13:45:21,188 [INFO] ⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...
2026-09-10 13:45:22,346 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:23,758 [INFO] ⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...
2026-09-10 13:45:23,758 [INFO] ⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...
2026-09-10 13:45:24,875 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:26,262 [INFO] ⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...
2026-09-10 13:45:26,264 [INFO] ⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...
2026-09-10 13:45:27,371 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:28,720 [INFO] ⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...
2026-09-10 13:45:28,720 [INFO] ⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...
2026-09-10 13:45:29,822 [INFO] 🏰 [Tier 4 插隊] 偵測到週期地下城冷卻結束；本場結算後離場並切回地下城探索。
2026-09-10 13:45:31,151 [INFO] ⌛ [結算 Step 2] continue 按鈕淡出/過場中，等待下一個 continue 或終局按鈕顯現...
2026-09-10 13:45:31,152 [WARNING] ⚠️ 結算畫面連續 5 次未偵測到任何結算按鈕，判定可能已退出或跳轉，重設狀態為 UNKNOWN 進行重新定位。
2026-09-10 13:45:31,152 [INFO] 🔄 狀態轉移: RESULT -> UNKNOWN
2026-09-10 13:45:31,459 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-10 13:45:31,473 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-10 13:45:31,473 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-10 13:45:33,304 [INFO] 成功匹配模板 'dungeons/dungeons_complete.png'！相似度: 0.9307，相對亮度比: 1.00，座標: (766, 722)
2026-09-10 13:45:33,306 [INFO] [State detection] Dungeon anchor [dungeons/dungeons_complete.png] (confidence: 0.9307); entering EXPLORING before battle detection.
2026-09-10 13:45:33,306 [INFO] 🔄 狀態轉移: UNKNOWN -> EXPLORING
2026-09-10 13:45:33,497 [INFO] ⏳ 下樓冷卻結束，已進入地下城新樓層，重設探索記憶。
2026-09-10 13:45:33,869 [INFO] 成功匹配模板 'dungeons/dungeons_complete.png'！相似度: 0.9307，相對亮度比: 1.00，座標: (766, 722)
2026-09-10 13:45:33,870 [INFO] 🎉 偵測到【地下城通關結束】(dungeons/dungeons_complete.png)，信心度: 0.9307，點擊退出。
2026-09-10 13:45:34,005 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:34,018 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:34,112 [INFO] 📊 已完成第 88 次地下城通關！
2026-09-10 13:45:34,113 [INFO] ⏳ 貪婪地下城：設定 [獸人地堡] (#7) 進入 35 分鐘冷卻期。
2026-09-10 13:45:34,113 [INFO] ⏳ [混合模式] 地下城全冷卻！各副本冷卻情形: [冰雪洞窟]: 冷卻中 (18 分 35 秒), [獸人地堡]: 冷卻中 (35 分 0 秒) ➔ 無可用地下城，將退守切換至普通關卡 (Stage)。
2026-09-10 13:45:34,113 [INFO] 🔄 狀態轉移: EXPLORING -> NAVIGATING
2026-09-10 13:45:38,185 [INFO] [IntentRouting] intent=primary_navigation scene=unknown action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:45:39,194 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:45:40,258 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:41,715 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:41,957 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:45:42,844 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:45:43,232 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:45:43,315 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:45:43,779 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9266，相對亮度比: 0.99，座標: (526, 715)
2026-09-10 13:45:43,781 [INFO] 🧭 混合模式：地下城全冷卻 (冷卻情形: [冰雪洞窟]: 冷卻中 (18 分 25 秒), [獸人地堡]: 冷卻中 (34 分 50 秒))，在活動大廳點擊 [common/select_stage.png] (0.9266) 切換至普通關卡頁籤！
2026-09-10 13:45:43,928 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:43,941 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:45,429 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:47,003 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:48,087 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:45:48,473 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:45:48,549 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:45:48,961 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9266，相對亮度比: 0.99，座標: (526, 715)
2026-09-10 13:45:48,964 [INFO] 🧭 混合模式：地下城全冷卻 (冷卻情形: [冰雪洞窟]: 冷卻中 (18 分 20 秒), [獸人地堡]: 冷卻中 (34 分 45 秒))，在活動大廳點擊 [common/select_stage.png] (0.9266) 切換至普通關卡頁籤！
2026-09-10 13:45:49,151 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:49,165 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:49,988 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9927，相對亮度比: 1.01，座標: (1257, 118)
2026-09-10 13:45:50,341 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:45:52,081 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:45:52,263 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:45:52,429 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9927，相對亮度比: 1.01，座標: (1257, 118)
2026-09-10 13:45:53,922 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:45:54,773 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-10 13:45:55,626 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:56,720 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:45:56,885 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:45:57,531 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9047，相對亮度比: 0.92，座標: (531, 712)
2026-09-10 13:45:57,810 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.9444，相對亮度比: 1.00，座標: (648, 713)
2026-09-10 13:45:57,859 [INFO] [IntentRouting] intent=primary_navigation scene=dungeon_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:45:58,166 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9266，相對亮度比: 0.99，座標: (526, 715)
2026-09-10 13:45:58,167 [INFO] 🧭 混合模式：地下城全冷卻 (冷卻情形: [冰雪洞窟]: 冷卻中 (18 分 11 秒), [獸人地堡]: 冷卻中 (34 分 36 秒))，在活動大廳點擊 [common/select_stage.png] (0.9266) 切換至普通關卡頁籤！
2026-09-10 13:45:58,286 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:45:58,297 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:45:59,480 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:00,678 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:00,894 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:01,609 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:01,911 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:01,967 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:02,185 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:46:04,104 [INFO] Resetting shared card list: tab=stage first_card=stages/level1_sky_plains.png attempt=1/7
2026-09-10 13:46:06,096 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:07,169 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:07,338 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:07,972 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:08,245 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:08,295 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:08,510 [INFO] 🧭 [卡片導航] 執行向右滑動拖曳，將清單拉回左側...
2026-09-10 13:46:10,438 [INFO] Resetting shared card list: tab=stage first_card=stages/level1_sky_plains.png attempt=2/7
2026-09-10 13:46:12,426 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:13,598 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:13,769 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:14,408 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:14,719 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:14,769 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:14,969 [INFO] 成功匹配模板 'stages/level1_sky_plains.png'！相似度: 0.9764，相對亮度比: 1.00，座標: (277, 385)
2026-09-10 13:46:14,970 [INFO] Card list aligned: tab=stage first_card=stages/level1_sky_plains.png confidence=0.9764
2026-09-10 13:46:15,307 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:15,666 [INFO] ⌛ 尋路中：目標關卡 [stages/level7_forgotten_wasteland.png] 暫時未出現在畫面上，等待載入與穩定中...
2026-09-10 13:46:16,491 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:17,692 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:17,878 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:18,521 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:18,802 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:18,857 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:19,167 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:19,549 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 1/6 次...
2026-09-10 13:46:23,557 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:24,644 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:24,814 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:25,539 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:25,895 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:25,943 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:26,256 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:26,621 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 2/6 次...
2026-09-10 13:46:30,546 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:31,603 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:31,776 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:32,438 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:32,736 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:32,788 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:33,083 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:33,461 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 3/6 次...
2026-09-10 13:46:37,401 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:38,461 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:38,664 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:39,452 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:39,749 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:39,799 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:40,105 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:40,466 [INFO] 🧭 尋路中：已在關卡選擇介面，但未見目標關卡 [stages/level7_forgotten_wasteland.png]，執行向左滑動清單 (地圖向右移) 第 4/6 次...
2026-09-10 13:46:44,351 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:45,539 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9209，相對亮度比: 0.99，座標: (64, 726)
2026-09-10 13:46:45,743 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9721，相對亮度比: 0.99，座標: (1109, 54)
2026-09-10 13:46:46,461 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-10 13:46:46,759 [INFO] 成功匹配模板 'dungeons/dungeon_after.png'！相似度: 0.8874，相對亮度比: 0.96，座標: (648, 713)
2026-09-10 13:46:46,817 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:47,178 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-10 13:46:47,785 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9665，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:46:48,203 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9665，相對亮度比: 0.99，座標: (1293, 329)
2026-09-10 13:46:48,204 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9665)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:46:48,337 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:46:48,346 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:46:48,809 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9368，相對亮度比: 1.09，座標: (1042, 92)
2026-09-10 13:46:49,078 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:50,105 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:50,453 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9368，相對亮度比: 1.09，座標: (1042, 92)
2026-09-10 13:46:51,669 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9182，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:46:51,718 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:52,344 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9182，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:46:52,764 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9182，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:46:52,766 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9182)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:46:52,856 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:46:52,865 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:46:53,308 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:46:53,562 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:54,612 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:54,824 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:46:55,006 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9834，相對亮度比: 1.01，座標: (1024, 111)
2026-09-10 13:46:56,533 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9166，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:46:56,590 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:46:56,829 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 0.9331，相對亮度比: 1.00，座標: (610, 370)
2026-09-10 13:46:57,000 [INFO] 成功匹配模板 'stages/boss_skull.png'！相似度: 0.9587，相對亮度比: 1.00，座標: (570, 570)
2026-09-10 13:46:57,474 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9786，相對亮度比: 1.00，座標: (604, 269)
2026-09-10 13:46:57,477 [INFO] 🧭 尋路中：在畫面中找到 [stages/boss_skull.png] (信心度: 0.9587)，點擊按鈕中心座標 (571, 1673)。
2026-09-10 13:46:57,579 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:46:57,587 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:46:58,049 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:46:58,341 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:59,511 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:46:59,697 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:46:59,861 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9756，相對亮度比: 0.49，座標: (1024, 111)
2026-09-10 13:47:01,234 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9173，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:47:01,319 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-10 13:47:02,338 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9173，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:47:02,784 [INFO] 成功匹配模板 'stages/level7_forgotten_wasteland.png'！相似度: 0.9173，相對亮度比: 1.07，座標: (1293, 329)
2026-09-10 13:47:02,786 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level7_forgotten_wasteland.png] (信心度: 0.9173)，套用向上偏移 117 像素點擊島嶼本體。
2026-09-10 13:47:02,881 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:47:02,890 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:47:03,353 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:47:03,623 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:47:04,733 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:47:04,909 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:47:05,075 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:47:05,259 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:47:05,311 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:47:05,313 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-10 13:47:05,646 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:47:05,931 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:47:07,396 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:47:07,608 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9605，相對亮度比: 0.39，座標: (1109, 54)
2026-09-10 13:47:07,773 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:47:07,945 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:47:07,948 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-10 13:47:08,161 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9605，相對亮度比: 0.99，座標: (877, 541)
2026-09-10 13:47:08,164 [INFO] Lobby start button [stages/start.png] detected (confidence 0.9605); clicking.
2026-09-10 13:47:08,254 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:47:08,267 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:47:08,686 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9937，相對亮度比: 1.01，座標: (1008, 215)
2026-09-10 13:47:08,942 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9009，相對亮度比: 0.69，座標: (64, 726)
2026-09-10 13:47:10,038 [INFO] 成功匹配模板 'stages/start.png'！相似度: 0.9569，相對亮度比: 1.16，座標: (877, 541)
2026-09-10 13:47:10,040 [INFO] Lobby start button is still visible after 1.9s; retrying click.
2026-09-10 13:47:10,212 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:47:10,223 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:47:11,771 [INFO] Battle feature [common/auto.png] detected (confidence 0.9949); entering BATTLE.
2026-09-10 13:47:11,771 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
2026-09-10 13:47:12,394 [INFO] 成功匹配模板 'common/auto.png'！相似度: 0.9949，相對亮度比: 0.98，座標: (1200, 55)
2026-09-10 13:47:12,395 [INFO] 👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！
2026-09-10 13:47:12,558 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-10 13:47:12,568 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-10 13:47:12,762 [INFO] ⚔️ 戰鬥進行中... 已持續 0 秒


```

</details>
