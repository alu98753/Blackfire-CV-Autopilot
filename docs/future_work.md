
# 待辦事項與未來優化規劃 (Future Work & Edge Cases)

## 🛡️ 邊界防守與長期掛機防護 (Edge Cases & AFK Stability)

🔴 **Edge Case A: 網路連線中斷 / 伺服器斷線彈窗 (Network / Server Disconnect)**
- **可能發生的狀況**：網路波動或伺服器斷線，遊戲跳出「連線逾時」、「重新連接」或「回到標題」彈窗。
- **現有防禦與補強**：雖然目前有 `login_flow.py`，但需確保當斷線彈窗出現時，能自動點擊「重新連線」，或當遊戲崩潰時能嘗試從 Steam 重新開啟遊戲並自動點擊回到遊戲大廳。

🔴 **Edge Case C: 背包清理與彈窗恢復防重入 (Bag Cleaning & Sorting Recovery)**
- **可能發生的狀況**：當戰鬥獎勵導致背包全滿跳出 `backpack_full.png` 彈窗，狀態轉移至 `BACKPACK_FULL_SORTING` / `BAG_CLEANING` 進行裝備清理後，需要 100% 確保能平滑返回原本的 `mix` 導航狀態。

🔴 **Edge Case D: 長時間運轉資源與記憶體管理 (Long-running Resource Cleanup)**
- **可能發生的狀況**：腳本連續運行 12 小時以上（如出國 5 天長掛機），Python/OpenCV 的快取或 Windows API 視窗控制代碼可能累積導致記憶體溢位。
- **補強建議**：
  1. **定時記憶體回收 (Garbage Collection)**：在狀態機中加入定時記憶體回收與快取清理。
  2. **診斷截圖自動清理機制**：只保留近 7 天的 `debug_click.png` / `debug_detect.png`。
  3. **CPU 與效能優化**：參照 [cpu_optimization.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/cpu_optimization.md) 降低輪詢資源佔用。

- **[待辦] 出國五天長掛機注意事項與維護**：
  - 血池可能滿出來要清
   時間點 背包滿了 清背包的時候標記 此時就要回去town 再開始該子流程
  - 特定的灰色物品要賣
      要有true,false 在config中 因為有些有時很費 但是有時會需要,因此有時要賣有時不賣
  - 每天打首領
  - 記憶體溢位防禦與快取釋放
  - 斷線：看能不能從 Steam 重新開啟遊戲
  - [cpu優化](file:///e:/Side_Project/BlackfireCrusade_tool/docs/cpu_optimization.md)

---

### 🧪 邊界模擬測試套件 (Edge Case Test Suite)
在 [test_behavioral_scenarios.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_behavioral_scenarios.py) 中，為上述 Edge Cases 寫入自動化模擬測試，確保任何異常彈窗跳出時，狀態機都能 100% 依預期防禦。


- **[待辦]** 點錯東西時候的城鎮重來機制

- **[待辦] 地下城防呆容錯機制**：當手動按錯或誤入非目標地下城地圖時，偵測並點擊退出按鈕安全返回大廳重開，避免因地圖模板不符而卡死。

- **[待辦] 在不同模式的時候都會遇到一個問題 就是挑選地下城的時候 按錯了 假設我要刷的是第二個 但卻按到第三個的地圖 會導致 因為我們要刷第二個 那匹配的圖就會都是第二個 因此如果按到第三個 那就會卡死 , 我在想該怎麼辦
   可能寫個發現的方式 發現時 可以按下quit, 再重開 或許用其他方式

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