# 測試執行效率 Profiling 與 Hotspots 優化規格 (v3) 🧪

---

## 1. 背景與現有成果

在 Phase A (`NavigationHandler` clock seam 解耦 26 處) 與 Phase B (`ResultHandler` tick-driven 子流程重構) 完成後，完整測試套件已達成穩定里程碑：

- **原始 Baseline**：380s+ (約 6.3 分鐘，1087 tests)
- **Phase A/B 成果**：**243.013s** (約 4.0 分鐘，1092 tests，0 Failure，14 Skipped)
- **整體改善**：縮短約 137 秒 (-36%)，測試套件 100% 綠燈。

前序重構歷程請參閱 [test_redundent_spec_v2.md](test_redundent_spec_v2.md)。

---

## 2. 實測 Wall-Clock Gap 分析 (Profiling Evidence)

依據 2026-09-13 於全套測試記錄檔 (`test_run.log`) 提取之真實時間間隙 (單次間隔 >= 1.0s)，累計耗時 **159.11 秒** (共 123 處)。其中高頻聚集之主要 Hotspots 如下：

### Hotspot 1: 地下城寶箱關閉逾時等待 (~12.6s)
- **現象**：`test_run.log` 出現單次高達 10.42 秒與 2.21 秒的阻塞間隙。
  ```text
  L984: [INFO] 關閉寶箱：偵測到退出按鈕 'common/quit.png' (信心度: 0.9000)，點擊關閉...
  L985: [WARNING] [Treasure subflow] Close was clicked, but exit condition timed out (10.0s).
  ```
- **根因**：測試案例驗證寶箱開啟或關閉時，Mock 未及時提供關閉後的畫面特徵，導致子流程陷入 10.0 秒逾時等待。
- **優化方向**：
  1. 檢視 `states/handlers/dungeon_treasure.py` 與相關測試（如 `tests/test_behavior_dungeon_scenarios.py`）。
  2. 確保測試端 Mock 適配後置條件，或將寶箱流程時間推進對齊 ClockPort。

### Hotspot 2: 血祭壇捐獻與 Confirm 輪詢等待 (~16.0s)
- **現象**：`[Phase 4: 捐獻確認]` 連續 8 處出現 2.00s 固定間隔 (累計約 16 秒)。
  ```text
  L2270: [INFO] 👉 [Phase 4: 捐獻確認] 偵測到確認彈窗 [common/confirm.png]...
  L2271: [INFO] 👉 [Phase 4: 捐獻確認] 點擊確認並等待彈窗消失...
  L2272: [INFO] 👉 [血祭壇] 成功完成所有 Phase 捐獻流程。
  ```
- **根因**：血祭壇子流程 (`BloodAltarSubflow`) 或其確認輪詢使用了真實 `time.sleep(2.0)` 或未解耦的等待迴圈。
- **優化方向**：
  1. 引入 `ClockPort` 或 `_sleep` / tick 驅動機制。
  2. 測試端注入 `FakeClock`，消除真實 2.0s 睡眠。

### Hotspot 3: 進程重啟等待 (~6.0s)
- **現象**：`[GameProcess]` 與 `[GameRelaunchSubflow]` 出現 3 處 2.00s 等待 (累計 6 秒)。
  ```text
  L1868: [INFO] [GameProcess] No game window found for ...
  L1869: [INFO] 👉 [GameRelaunchSubflow] 啟動 SteamGameLauncher 重啟程序...
  ```
- **優化方向**：在非整合型單元測試中，對進程重啟與視窗等待注入虛擬時間，避免實體輪詢。

### Hotspot 4: 地下城選卡滑動與動畫等待 (~4.0s)
- **現象**：`Card list aligned` 與選關卡片左右拖曳時存在約 2.06s 的滑動等待。
- **優化方向**：在測試中對拖曳動畫與冷卻檢測導入 FakeClock 推進。

### Hotspot 5: EasyOCR Preload 模型預熱 (~3.0s)
- **現象**：`[OCR Preload] 正在預載 EasyOCR 模型` 耗時約 2.99 秒。
- **優方向**：維持單元測試環境下 OCR 模組的 Lazy Load 或 Test Double 替代。

---

## 3. 實作規劃與分期

1. **Phase 1 (Quick Wins - High ROI)**：
   - 解決 Hotspot 1 (Treasure subflow 逾時 ~12.6s) 與 Hotspot 2 (血祭壇 Confirm 輪詢 ~16.0s)。
   - 預期可縮減測試時間約 25~28 秒。
2. **Phase 2 (Process & Navigation Animations)**：
   - 處理 Hotspot 3 (進程重啟等待 ~6.0s) 與 Hotspot 4 (選卡滑動 ~4.0s)。
   - 預期縮減約 10 秒。
3. **Phase 3 (Re-profiling)**：
   - 驗證全套測試是否降至 200s ~ 210s 區間。
