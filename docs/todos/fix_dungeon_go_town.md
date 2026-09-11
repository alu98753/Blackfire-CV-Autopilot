背景描述:

當我在地下城探索中restart的時候 他沒辦法正確接續流程,原因是他無法配對下樓的記號 並按下去 我不知道為何(但他可以匹配到leave.png 這個地下橙特徵)

時間點 發生在sandbox 的log 0912 00:38 左右

```
tifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-12 00:38:05,203 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-12 00:38:10,119 [INFO] [FullRelocalize] reason=legacy_or_unspecified expected_tab=None candidates=[] winner=None is_conflict=False elapsed=1.125s
2026-09-12 00:38:11,680 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9653，相對亮度比: 0.99，座標: (64, 717)
2026-09-12 00:38:11,681 [INFO] 🟢 [登入流程] 登入後畫面載入完成！全域感知識別世界場景 [SceneId.DUNGEON_EXPLORING]，交由主狀態機接管！
2026-09-12 00:38:11,682 [INFO] 🔄 [登入流程] 畫面載入完畢，立即發起全域狀態定位 (detect_current_state)...
2026-09-12 00:38:11,805 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_detect.png
2026-09-12 00:38:11,814 [INFO] 📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png
2026-09-12 00:38:11,815 [INFO] 🔍 正在進行全域掃描以辨識遊戲狀態...
2026-09-12 00:38:13,506 [INFO] 🔍 [除錯] 比對尋路按鈕 'common/door.png'，最高相似度: 0.3956，座標: None
2026-09-12 00:38:13,564 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/Domains_entry.png'，最高相似度: 0.3583，座標: None
2026-09-12 00:38:13,626 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/golden_empire/entry.png'，最高相似度: 0.1201，座標: None
2026-09-12 00:38:13,676 [INFO] 🔍 [除錯] 比對尋路按鈕 'domains/common/start_btn.png'，最高相似度: 0.4921，座標: None
2026-09-12 00:38:14,014 [INFO] 成功匹配模板 'dungeons/leave.png'！相似度: 0.9653，相對亮度比: 0.99，座標: (64, 717)
2026-09-12 00:38:14,015 [INFO] 🏰 全域定位：偵測到地下城內部特徵 [dungeons/leave.png] (信心度: 0.9653)，鎖定地下城探索狀態！
2026-09-12 00:38:14,016 [INFO] 🔄 狀態轉移: UNKNOWN -> EXPLORING
2026-09-12 00:38:14,390 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:14,863 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:15,375 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:16,277 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
2026-09-12 00:38:16,613 [INFO] ⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...
```

---

## 根本原因與問題定位 (Root Cause Analysis)

1. **核心缺陷：`ensure_explore_config()` 的盲目假定**
   - 在每日模式 (`--mode daily`) 啟動時，若今日任務已完成或冷卻，調度器會評估 Tier 4 退守模式。當使用者的 Tier 4 為領地模式（如黃金古國 `golden_empire`）時，`self.config` 被替換為 `golden_empire` 的設定。
   - `golden_empire` 設定具有 `type = "domain"` 與 `explore_priorities = ["domains/golden_empire/explore_btn.png"]`。
   - 角色肉身身處地下城重啟時，`transition_to(STATE_DUNGEON_EXPLORING)` 觸發 `ensure_explore_config()`，該函式僅檢查 `"explore_priorities" in active_config`，誤將領地古國配置當作地下城探索配置，未進行意圖鎖定與離場路由注入。
   - 導致 `ExploreHandler.handle()` 在地下城內部持續比對古國按鈕，無法掃描或點擊地下城下樓圖標 (`dungeons/gungeon_godown.png`)。

2. **處理器領域自治缺失**
   - `ExploreHandler.handle()` 盲目信任外部傳入之 `explore_priorities`，未檢驗其是否包含地下城有效模板，且其內部備援清單將 `dungeons/leave.png` 置於 `dungeons/gungeon_godown.png` 之前。

3. **全域感知被業務 Config 遮蔽**
   - `DUNGEON_RECOVERY_MODE_TYPES` 未包含 `"domain"` 與 `"collect_only"`，導致全域定位第一步略過地下城錨點檢驗。

---

## 解決方案與規範契約 (Resolution & Architecture Contract)

- 正式架構契約：[地下城重啟復原與前置離場路由契約](../features/navigation/dungeon_relaunch_recovery_contract.md)
- 上位準則：[Precondition Contracts](../architecture/precondition_contracts.md)（第 7.1 與 7.2 節）
- 落地修改：
  1. `GameStateMachine.is_dungeon_explore_config`：精準檢驗配置是否具備地下城特徵。
  2. `GameStateMachine.ensure_explore_config`：非地下城目標意圖（如 `golden_empire`）鎖定至 `dungeon_recovery_return_config`，注入標準地下城前置離場配置；離場後於 `_finalize_dungeon_completion` 原樣還原。
  3. `ExploreHandler`：強化領域自治，若優先級清單不含地下城特徵，自主 fallback 至標準離場清單，且修正 `leave.png` 至清單末位。
  4. `config/defaults.toml`：在 `daily.explore_priorities` 末尾補充 `dungeons/leave.png`。
- 單元測試套件：[tests/test_dungeon_relaunch_recovery.py](../../tests/test_dungeon_relaunch_recovery.py)