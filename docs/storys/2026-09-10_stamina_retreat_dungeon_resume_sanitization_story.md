# 開發故事：體力退避地下城喚醒路由純潔化與關卡打怪洩漏治理 🛡️

> 日期：2026-09-10  
> 分支：`fix/stamina-retreat-dungeon-resume`  
> 成果契約：[Stamina Retreat Feature Contract](../features/stamina_retreat_feature.md)  
> 關鍵模組：[states/state_machine.py](../../states/state_machine.py), [states/handlers/navigation.py](../../states/handlers/navigation.py), [states/handlers/explore.py](../../states/handlers/explore.py), [states/handlers/collect_only.py](../../states/handlers/collect_only.py)  

---

## 1. Purpose (目的)

在系統進入長達數小時的體力退避狀態 (`COLLECT_ONLY`，例如體力耗盡等待 7 小時恢復) 期間，定時地下城冷卻結束喚醒打完通關後，系統出現非預期的行為失控：
1. **路由基因污染 (Route Contamination)**：
   - 待機甦醒時呼叫 `build_dungeon_resume_route()`，該方法錯誤注入了 Tier 4 關卡路徑（第 7 關遺忘荒野魔王關模板），且未顯式宣告 `enable_stage_farming = False`。
2. **調度閉環死巷 (Scheduler Dead-End)**：
   - 地下城通關後進入全冷卻，`evaluate_next_activity()` 檢查到處於體力退避中但無可用地下城時，直接 `return False`，既未切換回 `COLLECT_ONLY` 亦未點擊回城，使狀態機淪為停留在大廳的「導航孤兒」。
3. **導航盲目退守關卡 (Blind Stage Fallback)**：
   - `NavigationHandler` 在大廳看到混合模式且地下城全冷卻，因未檢查體力退避狀態，直接點擊 `common/select_stage.png` 切換普通關卡頁籤並依據殘留路徑直奔第 7 關發起戰鬥，嚴重破壞體力退避節奏。

---

## 2. Action (行動)

1. **重構 `build_dungeon_resume_route()` 建立純潔路由 (規格 1)**：
   - 於 [states/state_machine.py](../../states/state_machine.py) 重構該方法，加入清晰的長效架構語意 Docstring。
   - 明確宣告 `route["enable_stage_farming"] = False`、`route["tier4_mode"] = TIER4_MODE_NONE` 與 `route["is_dungeon_temporary_resume"] = True`。
   - 徹底移除 `self._apply_tier4_stage_selection(route)`，主動清除 `stage_entry` 與 `stage_navigation_path`，僅保留地下城尋路相關模板。
2. **修復 `evaluate_next_activity()` 復歸閉環 (規格 2)**：
   - 於 [states/state_machine.py](../../states/state_machine.py) 的 `stamina_retreat_start_time` 檢查區塊中，當地下城全冷卻或未啟用時，主動檢查當前狀態。
   - 若狀態非 `STATE_COLLECT_ONLY`（如剛通關進入 `STATE_NAVIGATING`），記錄關鍵決策日誌、切換配置為 `collect_only`，並發起 `transition_to(self.STATE_COLLECT_ONLY)` 確保狀態閉環。
3. **強化 `NavigationHandler` 關卡打怪禁絕防護網 (規格 3)**：
   - 於 [states/handlers/navigation.py](../../states/handlers/navigation.py) 依據 DRY 原則提煉具名輔助函式 `_is_stage_farming_allowed()`。
   - 在 `_switch_to_stage_or_back()` 與 `handle()` 的地下城全冷卻退守邏輯中，嚴格禁絕體力退避與臨時地下城喚醒期間的 Stage 打怪，統一呼叫 `_enter_collect_only_after_dungeon_cooldown()` 點擊 `goback_town.png` 返回城鎮並進入 `STATE_COLLECT_ONLY`。
4. **優化 `ExploreHandler` 通關後的語意日誌 (規格 4)**：
   - 於 [states/handlers/explore.py](../../states/handlers/explore.py) 通關結算處，依據體力退避與臨時喚醒旗標動態輸出準確日誌，消除誤導性的「將退守切換至普通關卡 (Stage)」。
5. **強化 `CollectOnlyHandler` 喚醒防護 (規格 5)**：
   - 於 [states/handlers/collect_only.py](../../states/handlers/collect_only.py) 確保處於體力退避時，地下城就緒時一律使用純淨的 `build_dungeon_resume_route()`，杜絕被中斷前的舊關卡配置遮蔽。
6. **契約升格與行為單元測試補強**：
   - 升格 [docs/features/stamina_retreat_feature.md](../features/stamina_retreat_feature.md) Section 5.6 為「體力退避期間常規關卡禁絕律與地下城喚醒契約 (Stamina Retreat Supremacy Invariant)」。
   - 於 [tests/test_behavior_stamina_retreat.py](../../tests/test_behavior_stamina_retreat.py) 新增 `test_3_3` (全冷卻點擊回城) 與 `test_3_4` (退避期間關卡嚴禁啟用) 行為測試。
   - 於 [tests/test_daily_pipeline_stamina_retreat.py](../../tests/test_daily_pipeline_stamina_retreat.py) 新增 `test_evaluate_next_activity_returns_to_collect_only_when_all_dungeons_cooldown_in_retreat` 與 `test_build_dungeon_resume_route_sanitization` 驗證。

---

## 3. Result (結果)

- **徹底消除關卡打怪洩漏**：
  - 臨時喚醒路由 100% 剝除任何普通關卡尋路資產與打怪權限。
  - 地下城通關或全冷卻時，無論是排程器層 (`evaluate_next_activity`) 還是導航層 (`NavigationHandler`)，皆 100% 導向城鎮回退與 `COLLECT_ONLY` 待機。
- **高可觀測性與端正日誌**：
  - 終端清楚顯示 `⏳ [Activity Scheduler] 體力退避期間地下城已全冷卻 ➔ 恢復城鎮待機與 COLLECT_ONLY 狀態`，除錯軌跡一目了然。
- **聚焦領域單元測試 100% 全數綠燈**：
  - [tests/test_behavior_stamina_retreat.py](../../tests/test_behavior_stamina_retreat.py)：4 個測試全數 PASS（耗時 1.56s）。
  - [tests/test_daily_pipeline_stamina_retreat.py](../../tests/test_daily_pipeline_stamina_retreat.py)：8 個測試全數 PASS（耗時 16.28s）。

---

## 4. So What (架構意義)

本修復貫徹了 Greenfield-lite 架構的「狀態驅動，拒絕補釘」與「不變量優於局部判定」原則：
- 確立了**「體力退避最高優先與常規關卡禁絕律 (Stamina Retreat Supremacy Invariant)」**：只要處於退避倒數，系統在任何層級均無權發起常規關卡戰鬥。
- 確立了**「臨時喚醒路由職責有界律 (Bounded Scope for Temporary Resume Routes)」**：臨時路由僅持有單一活動能力，生命週期極簡，打完即焚，不具備向其他活動退守之權力。

---

## 5. Influence (後續影響)

- 體力退避期間的 24/7 自動掛機具備絕對穩定性，使用者可完全放手掛機數小時，無須擔心偷刷關卡導致體力耗損或因體力不足卡死在大廳。
- 臨時路由純潔性標準為後續其他週期性活動（如 Demon Lords、Lord Boss）的臨時喚醒提供了穩固範例。
