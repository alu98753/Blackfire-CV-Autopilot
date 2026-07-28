
# 待辦事項與未來優化規劃 (Future Work & Edge Cases)

## 🛡️ 邊界防守與長掛機防護 (Edge Cases & AFK Stability)

### 🌴 出國五天長掛機注意事項與維護指南

#### 💡 1. 五天長掛機 3 大架構支柱
1. **狀態持久化 ([DailyManager](file:///e:/Side_Project/BlackfireCrusade_tool/utils/daily_manager.py))**：所有完成子流程與 08:05 重置週期自動記錄於 [daily_status.json](file:///e:/Side_Project/BlackfireCrusade_tool/user_data/daily_status.json)，確保斷線重啟能無縫接續進度。
2. **全局看門狗與自癒修復 ([Watchdog](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/watchdog.py) & [UnexpectedPopupRecoveryHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/handler.py))**：超過 N 分鐘未推進時自動觸發全圖意外彈窗清理 (參見 [exception_subsystem_architecture.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/exception_subsystem_architecture.md))。
3. **點擊消失驗證閉環 (`click_and_wait_until_gone`)**：關鍵按鈕點擊後持續輪詢確認消失，防止點擊未生效導致狀態過早推進。

#### 🎯 2. 優化優先級矩陣 (Priority Hierarchy)
- **P0 級 (最高優先 / 系統卡死與阻斷)**：畫面動畫過渡未完成即切換階段、按鈕點擊未驗證消失、全螢幕意外彈窗。**必須 100% 優先修復！**
- **P1 級 (中高優先 / 長期穩定與資源防護)**：
  - **CPU 功耗控管**：主迴圈保持 `0.05s` 適當睡眠，Python 佔用率維持在 $< 2\%$，防熱防死鎖 (參見 [cpu_optimization.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/cpu_optimization.md))。
  - **記憶體洩漏 (RAM Footprint)**：驗證長途運算無 Memory Leak，保持記憶體平穩。
  - **每日 08:05 重置**：確保跨日自動觸發重置與狀態更新。
- **P2 級 (最低優先 / 微幅速度與延遲)**：單次辨識或動作慢 0.2~0.5 秒完全不影響 5 天掛機穩定度，有空再優化。

#### 📋 3. 5 天長掛機已完成項目索引 (Ref Only)
- [已完成] **背包滿自動連動血之祭壇** [REF: [Blood_Altar.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/town_building/Blood_Altar.md)]
- [已完成] **灰色/指定品質商品白名單出售** [REF: [Jewelry_workshop.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/town_building/Jewelry_workshop.md)]
- [已完成] **每日討伐首領領主 (每次討伐需 5 點體力/麵包)** [REF: [lord_boss_story.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/lord_boss/lord_boss_story.md)]
- [已完成] **每日任務與免費抽獎** [REF: [daily8.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/daily_task/daily8.md)]
- [已完成] **CPU 低功耗睡眠控管** [REF: [cpu_optimization.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/cpu_optimization.md)]
- [已驗證] **長時間運轉資源與記憶體無洩漏** (1,000 次循環僅增 1.09MB)

#### 📌 4. 長掛機剩餘待補強項目
- [ ] **Steam/網路嚴重斷線重連防護**：網路崩潰或遊戲關閉時，嘗試自動重新連接或從 Steam 重新拉起遊戲。

---

### 🧪 邊界模擬測試套件 (Edge Case Test Suite)
在 [test_behavioral_scenarios.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_behavioral_scenarios.py) 中，為上述 Edge Cases 寫入自動化模擬測試，確保任何異常彈窗跳出時，狀態機都能 100% 依預期防禦。


- **[已擱置] 稀有戰利品自動背包鎖定**：於戰鬥結束畫面同時偵測到「獲得戰利品」與「繼續」時，先前往背包進行特定裝備的鎖定防護（此功能目前已由貴重裝備色彩分類保留機制完整覆蓋，暫予擱置）。

- **[已擱置] 為了讓稀有戰利品不被誤分解(即使現在可以判斷顏色了)
```
我希望在戰鬥結束畫面(也就是continue處) 判斷到"獲得戰利品"這五個字  跟continue同時存在(可能在不同位置 圖片供你參考)時 去紀錄有哪些要鎖定 如果有 就接著去背包鎖定(如果已經鎖定(只有解鎖的字樣沒有鎖定的字樣) 就退出 (不要再繼續按了)) 如果沒有就再戰鬥 retry

這個在一般關卡 跟地下城 探索但背包滿了 或是 bag_clean 時候 是都要 觸發的 通用的邏  先思考你需要什麼圖片資源 與計畫
```

## 高優先度
怎麼變現? 我想說可能可以做成exe or app?但這是non functional的事情 或許目前功能夠了?

## 低優先度

- **[已擱置] iPad 遠端操控 PC 腳本**：
```
如何用windows 電腦操控ipad 上面的遊戲 做一樣的事情
```
低優先 目前沒遇過

- **[已擱置]** 點錯東西時候的城鎮重來機制

- **[已擱置] 地下城防呆容錯機制**：當手動按錯或誤入非目標地下城地圖時，偵測並點擊退出按鈕安全返回大廳重開，避免因地圖模板不符而卡死。

- **[已擱置] 在不同模式的時候都會遇到一個問題 就是挑選地下城的時候 按錯了 假設我要刷的是第二個 但卻按到第三個的地圖 會導致 因為我們要刷第二個 那匹配的圖就會都是第二個 因此如果按到第三個 那就會卡死 , 我在想該怎麼辦
   可能寫個發現的方式 發現時 可以按下quit, 再重開 或許用其他方式

## 已經解決(觀察中)


- **[已經解決]** 現在在點鑽石的流程中 quit的點擊並不穩定 有時有點到 有時沒有 我要確認 為何會這樣, 並且假設沒成功quit 那狀態不應該從DIAMOND_COLLECTION -> NAVIGATING 要直到quit成功 為止。
  - **原因**：後台模擬點擊需要先發送懸停（Hover）訊號才穩定；且狀態機先前發送點擊後未檢驗視窗是否真的關閉就逕行跳轉。
  - **解法**：在 `actions/mouse.py` 後台 click 加點 `WM_MOUSEMOVE` 穩定焦點；並且令 Handler 持續確認 `common/quit.png` 自畫面上消失，才真正重置變數並回歸 NAVIGATING。

- **[已經解決]** 我現在可以選 stage 我要打第幾關，但是她可能會點錯導致卡死，具體而言我選第四關他可能點到第二關。
  - **原因**：當 `brightness_threshold` 啟用時，舊的 `TemplateMatcher.match` 邏輯在篩選出符合亮度比例的候選點後，以「亮度比例（`ratio`）」進行最優點選擇，而不是「模板相似度（`confidence`）」。這導致程式忽略了信心度高（`0.9363`）的正確第 4 關，卻選中亮度比例相近但信心度極低（`0.6063`，實為第 2 關周邊背景）的雜訊，套用向上偏移 160 像素後點選了第 2 關。
  - **解法**：修改 `vision/matcher.py`，改為先用 `brightness_threshold` 進行亮度合格過濾，隨後從合格候選點中，以**「相似度/信心度（`c[2]`）」**挑選出最優點。同時，新增 `tests/test_vision_matcher.py` 進行單元測試防禦。
  - **精簡日誌**：
    ```log
    2026-07-10 21:24:21,192 [INFO] 成功匹配模板 'stages/level4_desert_ruins.png'！相似度: 0.9363，相對亮度比: 1.01，座標: (1157, 552)
    2026-07-10 21:24:21,805 [INFO] 成功匹配模板 'stages/level4_desert_ruins.png'！相似度: 0.6063，相對亮度比: 1.01，座標: (328, 552)
    2026-07-10 21:24:21,806 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level4_desert_ruins.png] (信心度: 0.6063)，套用向上偏移 160 像素點擊島嶼本體。
    ```

- **[已經解決]** 全域「任務完成」彈窗（`task_complete.png`）領取按鈕按不到但能辨識到。
  - **原因**：全域任務領取按鈕的 `+281` 像素相對偏移量是以標準 1080p 解析度硬編碼設計的。若遊戲視窗高度縮小（例如為 1280x720 或者是因為 DPI 縮放變更），該硬編碼偏移量會超出按鈕物理邊界，導致點擊無效。
  - **解法**：在 `states/state_machine.py` 及關卡選擇島嶼點擊（`states/handlers/navigation.py` 的 `-160` 像素偏移）中，改採依當前視窗高度與 `1080p` 比例進行動態縮放適配（`scale_y = rect_height / 1080.0`），使點擊不論何種解析度均能精確點中。

- **[已經解決]** 地下城全在冷卻中時無關卡可刷導致原地無限等待與卡死。
  - **原因**：舊版地下城模式當所有副本進入冷卻時，會在地下城選關介面重複滑動並原地死守。
  - **解法**：實作 `mix` 混合模式與動態瀑布流退守機制；當所有地下城均進入冷卻時，自動切換至 Stage 普通關卡刷關，並於地下城 CD 結束時即時切換回地下城。

- **[已經解決]** 體力耗盡時彈出 `no_bread.png` 導致腳本停擺卡死。
  - **原因**：體力用盡跳出彈窗後缺少自動退避與模式切換。
  - **解法**：實作全域體力不足攔截 `handle_insufficient_stamina`，自動點擊取消關閉彈窗，退回城鎮備份配置並切換至 `collect_only` 掛機 4.0 小時，冷卻結束後自動恢復原模式。

- **[已經解決]** 程式碼內硬編碼預設清單（`dungeon_names`, `greedy_allowed_indices`, `entry_templates`）導致邊界隱患。
  - **原因**：Handler 與狀態機中分散著 fallback 硬編碼預設值。
  - **解法**：貫徹 Single Source of Truth 與 Fail-Fast 原則，所有參數一律由 `config` 驅動，配置缺失時立即拋出 `ValueError` 防禦性中斷。