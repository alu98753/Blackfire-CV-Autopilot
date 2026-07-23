# 地下城、混合模式與體力退避決策流程圖 (Decision Tree / Flowchart) 📊

本文件記錄了地下城模式、混合模式 (`mix`)、體力/鑽石自動領取、體力退避自適應、探險隨機事件、以及背包已滿自適應分選的決策樹結構。

---

## 1. 領取體力與鑽石決策流程 (Stamina & Diamond Claim Flow)

領取鑽石（每 2 小時）與領體力（每 30 分鐘）由 `NavigationHandler` 在大廳/尋路頁面進行攔截，領取鑽石的優先級高於領體力。

```mermaid
graph TD
    Start([導航領取觸發]) --> CheckDiamond{需要領鑽石?}
    
    CheckDiamond -- Yes --> CheckInDia{在領鑽石視窗內?<br>有 quit_bread/quit 按鈕且無大廳 diamond 入口}
    CheckInDia -- Yes --> CheckFreeDia{偵測到 diamond_free.png<br>閥值 0.90?}
    CheckFreeDia -- Yes --> ClickFreeDia[點擊免費領取] --> WaitDiaConf{出現 confirm.png 或 ok.png?}
    WaitDiaConf -- Yes --> ClickDiaConf[點擊確認/OK] --> MarkDiaCollected[標記本次已領] --> CloseDia[點擊 quit_bread/quit 關閉] --> EndStep[結束本步]
    CheckFreeDia -- No (冷卻中) --> CloseDiaCold[點擊 quit_bread/quit 關閉] --> ClearDiaFlag[標記領取結束<br>重設 2 小時定時器] --> EndStep
    
    CheckInDia -- No --> CheckDiaLobby{大廳 diamond 入口可見?}
    CheckDiaLobby -- Yes --> ClickDiaEntry[點擊 diamond 入口] --> EndStep
    CheckDiaLobby -- No --> CheckGoTown{goback_town.png 可見?}
    CheckGoTown -- Yes --> ClickGoTown[點擊返回城鎮] --> EndStep
    CheckGoTown -- No --> WaitDiaLoad[等待按鈕加載] --> EndStep
    
    CheckDiamond -- No --> CheckBread{需要領體力?}
    CheckBread -- Yes --> CheckInBread{在領體力視窗內?}
    CheckInBread -- Yes --> CheckBreadFull{出現體力已滿提示?}
    CheckBreadFull -- Yes --> ClickBreadFullConf[點擊確認關閉] --> EndStep
    CheckBreadFull -- No --> CheckBreadCollect{出現 bread_collection.png?}
    CheckBreadCollect -- Yes --> ClickBreadCollect[點擊領取體力] --> EndStep
    CheckBreadCollect -- No --> CheckBreadQuit{出現 quit_bread.png?}
    CheckBreadQuit -- Yes --> ClickBreadQuit[點擊關閉體力視窗] --> ClearBreadFlag[標記領取結束<br>重設 30 分鐘定時器] --> EndStep
    CheckInBread -- No --> CheckBreadEntry{大廳 bread 入口可見?}
    CheckBreadEntry -- Yes --> ClickBreadEntry[點擊體力入口] --> EndStep
    CheckBreadEntry -- No --> CheckDoor{door.png 大廳入口可見?}
    CheckDoor -- Yes --> ClickDoor[點擊進入大廳] --> EndStep
    CheckDoor -- No --> WaitBreadLoad[等待體力畫面載入] --> EndStep
    
    CheckBread -- No --> Done([進入正常尋路流程])
```

---

## 2. 地下城探索決策流程 (Dungeon Exploring Flow)

進入地下城內部後，程式處於 `STATE_EXPLORING` 狀態。每 0.5 秒擷取一次畫面，並依以下優先級順序（由高至低）比對畫面：

```mermaid
graph TD
    StartExplore([探索檢索開始]) --> CheckBagCleaning{need_bag_cleaning == True?}
    CheckBagCleaning -- Yes --> TransBagCleaning[狀態轉移至 STATE_BAG_CLEANING] --> DoneClean([進入背包分解流程])
    
    CheckBagCleaning -- No --> CheckBattle{自動戰鬥 auto.png 可見?}
    CheckBattle -- Yes --> TransBattle[狀態轉移至 STATE_BATTLE] --> RunBattle([自動戰鬥監控])
    
    CheckBattle -- No --> ScanPriorities[依優先級比對 explore_priorities]
    
    ScanPriorities --> P1{1. dungeons_complete.png<br>通關結束?}
    P1 -- Yes --> ClickP1[點擊退出地下城] --> TransNav[轉移至 STATE_NAVIGATING]
    
    P1 -- No --> P2{2. common/confirm.png<br>通用確認彈窗?}
    P2 -- Yes --> ClickP2[點擊確認]
    
    P2 -- No --> P3{3. dungeons/gungeon_godown_confirm.png<br>下樓確認彈窗?}
    P3 -- Yes --> ClickP3[點擊確認下樓]
    
    P3 -- No --> P4{4. dungeons/Get_tresure_comfirm.png<br>獲得寶物確認?}
    P4 -- Yes --> ClickP4[點擊確認收下]
    
    P4 -- No --> P5{5. common/ok.png<br>通用 OK 按鈕?}
    P5 -- Yes --> ClickP5[點擊 OK]
    
    P5 -- No --> P6{6. dungeons/Get_tresure.png<br>點擊獲得寶物?}
    P6 -- Yes --> ClickP6[點擊獲得寶物]
    
    P6 -- No --> P7{7. dungeons/choice_bless.png<br>選擇祝福選項?}
    P7 -- Yes --> ClickP7[點擊選取祝福]
    
    P7 -- No --> P8{8. dungeons/choose.png<br>選擇按鈕?}
    P8 -- Yes --> ClickP8[點擊選擇]
    
    P8 -- No --> P9{9. dungeons/dungeon_fight.png<br>戰鬥房入口?}
    P9 -- Yes --> ClickP9[點擊進入戰鬥準備]
    
    P9 -- No --> P10{10. dungeons/quit.png<br>關閉彈窗?}
    P10 -- Yes --> ClickP10[點擊退出彈窗]
    
    P10 -- No --> P11{11. dungeons/Treasure.png<br>寶箱房箱子?}
    P11 -- Yes --> ClickP11[點擊開箱]
    
    P11 -- No --> P12{12. dungeons/skill_event.png<br>技能事件?}
    P12 -- Yes --> ClickP12[點擊技能卡片]
    
    P12 -- No --> P13{13. dungeons/dungeon_bless.png<br>接受祝福按鈕?}
    P13 -- Yes --> ClickP13[點擊接受祝福]
    
    P13 -- No --> P14{14. dungeons/gungeon_godown.png<br>前進下一層按鈕?}
    P14 -- Yes --> ClickP14[點擊下樓]
    
    P14 -- No --> WaitLoad[等待下一層載入或事件出現]
```

---

## 3. 背包滿自適應分選決策流程 (Backpack Full Sorting Flow)

當畫面上彈出「無法容納的物品 (背包已滿)」彈窗 (`backpack_full.png`)，狀態機轉移至 `STATE_BACKPACK_FULL_SORTING`，並設定 `need_bag_cleaning = True`。

```mermaid
graph TD
    StartSort([進入背包分選狀態]) --> ScanLeft{掃描左側溢出格 4x4<br>條件: std > 40.0 且 HSV 判定為藍/紫/黃/橘/紅?}
    
    ScanLeft -- 有貴重物品 --> ScanRight{掃描右側背包格 4x4<br>條件: std > 20.0 且 HSV 判定為綠/灰?}
    ScanRight -- 有低稀有度物品 --> ClickRight[點擊該右側物品] --> ClickDestroy[點擊 destroy.png] --> ClickConfirm[點擊 confirm.png 銷毀] --> ScrollTop[滾動回背包頂端] --> ClickLeft[點擊左側貴重物品] --> ClickCollect[點擊 collect.png 領取] --> Loop[重啟下一輪分選]
    
    ScanRight -- 無低稀有度物品 --> ScrollDown{向下滾動背包<br>最多3次?}
    ScrollDown -- Yes --> ScanRight
    ScrollDown -- No --> CloseWin[點擊右上角關閉 X 按鈕] --> WaitConf{出現 confirm.png 二次確認彈窗?}
    WaitConf -- Yes --> ClickExitConf[點擊確認關閉] --> TransUnknown[轉移至 STATE_UNKNOWN]
    WaitConf -- No --> TransUnknown
    
    ScanLeft -- 無貴重物品 --> CloseWin
```

---

## 4. 背包分解整理決策流程 (Backpack Cleaning Flow)

當狀態機退出 `STATE_BACKPACK_FULL_SORTING` 後，或戰鬥結算後回到大廳且 `need_bag_cleaning == True` 時，狀態機會自動轉移至 `STATE_BAG_CLEANING` 並執行大量分解：

```mermaid
graph TD
    StartClean([進入背包清理狀態]) --> CheckDialog{畫面上是否有 confirm.png<br>或 ok.png 彈窗?}
    
    CheckDialog -- Yes --> ClickDialog[點擊確認/OK]
    CheckDialog -- No --> CheckTidied{狀態是否已標記為 bag_tidied?}
    
    CheckTidied -- Yes --> FindQuit{尋找 quit.png<br>或 quit_bread.png?}
    FindQuit -- Yes --> ClickQuit[點擊關閉背包] --> ResetFlags[重設清理標記與 bag_tidied] --> TransBack[轉移回 LOBBY<br>或 EXPLORING]
    FindQuit -- No --> WaitQuit[等待退出按鈕出現]
    
    CheckTidied -- No --> CheckTidy{畫面上是否有 tidy.png?}
    CheckTidy -- Yes --> ClickTidy[點擊整理按鈕] --> MarkTidied[設定標記 bag_tidied = True]
    CheckTidy -- No --> CheckDis{畫面上是否有 Disassembly.png?}
    
    CheckDis -- Yes --> ClickDis[點擊分解按鈕]
    CheckDis -- No --> CheckSelect{畫面上是否有 select_all.png?}
    
    CheckSelect -- Yes --> ClickSelect[點擊全選按鈕]
    CheckSelect -- No --> CheckMass{畫面上是否有 Backpack_Disassembly.png?}
    
    CheckMass -- Yes --> ClickMass[點擊大量分解按鈕]
    CheckMass -- No --> CheckBag{畫面上是否有 bag.png?}
    
    CheckBag -- Yes --> ClickBag[點擊打開背包]
    CheckBag -- No --> WaitBag[等待背包載入或按鈕出現]
```

---

## 5. 混合模式 (`mix`) 雙向動態切換決策流程 (Hybrid Mix Mode Flow)

在 `mix` 模式下，導航引擎會動態評估地下城 CD 狀態並在大廳進行切換：

```mermaid
graph TD
    StartMix([NAVIGATING 導航觸發]) --> CheckAvail{has_available_dungeon()<br>有可用地下城?}
    
    CheckAvail -- Yes --> CheckDunTab{目前在地下城頁籤?<br>dungeon_select_open == True}
    CheckDunTab -- Yes --> SelectDungeon[對齊與點擊地下城入口] --> EnterDungeon([進入地下城探索])
    CheckDunTab -- No --> ClickDunTab[點擊 dungeons/dungeon.png 切換至地下城頁籤] --> SelectDungeon
    
    CheckAvail -- No (全冷卻) --> CheckStageTab{目前在普通關卡頁籤?<br>select_stage_after == True}
    CheckStageTab -- Yes --> SelectStage[地圖滑動與點擊 stage_target 小關卡/魔王關] --> EnterStage([進入普通關卡準備/戰鬥])
    CheckStageTab -- No --> ClickStageTab[點擊 common/select_stage.png 切換至普通關卡頁籤] --> SelectStage
```

---

## 6. 全域體力不足 (`no_bread`) 退避與恢復流程 (Stamina Retreat Flow)

```mermaid
graph TD
    StartStep([step 幀監控]) --> DetectNoBread{畫面出現 no_bread.png?}
    
    DetectNoBread -- Yes --> ClickCancel[點擊 no_bread/cancel.png 關閉彈窗]
    ClickCancel --> ClearWins[清空 quit.png / exit_battle.png]
    ClearWins --> ClickGoTown[點擊 goback_town.png 返回城鎮]
    ClickGoTown --> BackupConfig[備份 original_config = config<br>記錄 stamina_retreat_start_time]
    BackupConfig --> SwitchCollect[載入 collect_only 配置<br>切換至 STATE_COLLECT_ONLY]
    
    SwitchCollect --> LoopCollect[在城鎮待機 / 定時領鑽石與體力 / 心跳防斷線]
    LoopCollect --> CheckTime{累積退避時間 >= 4.0 小時?}
    CheckTime -- No --> LoopCollect
    CheckTime -- Yes --> RestoreConfig[還原 config = original_config<br>重置 original_config = None]
    RestoreConfig --> TransUnknown[轉移至 STATE_UNKNOWN 全域重新定位]
    
    DetectNoBread -- No --> NormalStep([繼續正常狀態 Handler 處理])
```
