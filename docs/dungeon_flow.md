# 地下城與體力領取決策流程圖 (Decision Tree / Flowchart) 📊

本文件詳細記錄了 `dungeon_slime`（史萊姆地下城）模式下，體力自動領取與探險隨機事件的決策樹結構。這有助於理解程式運作時的優先判定邏輯。

---

## 1. 🍞 自動領體力決策樹 (Stamina Collection Flow)

自動領體力功能在啟動時或每 30 分鐘計時器觸發時執行。程式會在尋路頁面進行攔截，並依照以下決策樹進行比對與點擊：

```mermaid
graph TD
    Start([領體力觸發]) --> Check1{畫面上是否有<br>cannor_get_more_bread_confirm.png?}
    
    Check1 -- Yes --> ClickCannot[點擊確認體力已滿] --> Sleep1[等待 1.0 秒] --> EndStep[結束本步]
    Check1 -- No --> Check2{畫面上是否有<br>bread_confirm.png?}
    
    Check2 -- Yes --> ClickConfirm[點擊獲得體力確認] --> Sleep2[等待 1.0 秒] --> EndStep
    Check2 -- No --> Check3{畫面上是否有<br>bread_collection.png?}
    
    Check3 -- Yes --> ClickCollect[點擊領取體力] --> Sleep3[等待 1.0 秒] --> EndStep
    Check3 -- No --> Check4{畫面上是否有<br>quit_bread.png?}
    
    Check4 -- Yes --> ClickQuit[點擊關閉體力視窗] --> ResetTimer[標記領取結束<br>重設 30 分鐘計時器] --> Sleep4[等待 1.5 秒] --> Done([回到大廳, 開始副本尋路])
    Check4 -- No --> Check5{畫面上是否有<br>bread.png?}
    
    Check5 -- Yes --> ClickBread[點擊打開體力視窗] --> Sleep5[等待 1.5 秒] --> EndStep
    Check5 -- No --> Check6{畫面上是否有<br>door.png?}
    
    Check6 -- Yes --> ClickDoor[點擊進入大廳] --> Sleep6[等待 1.5 秒] --> EndStep
    Check6 -- No --> Wait[等待體力按鈕或畫面載入] --> Sleep7[等待 0.5 秒] --> EndStep
```

---

## 2. 🏰 地下城探索決策樹 (Dungeon Exploring Flow)

進入地下城內部後，程式處於 `STATE_DUNGEON_EXPLORING` 狀態。每 0.5 秒截圖一次，並以下方的**優先級（由高到低）**掃描畫面。一旦匹配到對應按鈕，就執行操作並**結束本步**，以防止點擊背景物件：

```mermaid
graph TD
    StartExplore([探索檢索開始]) --> CheckBattle{畫面上是否有 auto.png?}
    
    CheckBattle -- Yes (戰鬥已開始) --> TransBattle[狀態轉移至 STATE_BATTLE] --> RunBattle([自動戰鬥監控])
    
    CheckBattle -- No --> ScanPriorities[按優先級順序比對 explore_priorities]
    
    ScanPriorities --> P1{1. dungeons_complete.png<br>通關結束?}
    P1 -- Yes --> ClickP1[點擊退出地下城] --> TransNav[轉移至 STATE_NAVIGATING<br>重啟下一輪]
    
    P1 -- No --> P2{2. common/confirm.png<br>通用確認彈窗?}
    P2 -- Yes --> ClickP2[點擊確認] --> EndStep([結束本步])
    
    P2 -- No --> P3{3. common/ok.png<br>通用 OK 按鈕?}
    P3 -- Yes --> ClickP3[點擊 OK] --> EndStep
    
    P3 -- No --> P4{4. dungeons/Get_tresure.png<br>點擊獲得寶物?}
    P4 -- Yes --> ClickP4[點擊獲得寶物] --> EndStep
    
    P4 -- No --> P5{5. dungeons/choice_bless.png<br>選擇祝福選項?}
    P5 -- Yes --> ClickP5[點擊選取祝福] --> EndStep
    
    P5 -- No --> P6{6. dungeons/choose.png<br>選擇按鈕?}
    P6 -- Yes --> ClickP6[點擊選擇] --> EndStep
    
    P6 -- No --> P7{7. dungeons/skill_event.png<br>技能事件?}
    P7 -- Yes --> ClickP7[點擊技能卡片/選項] --> EndStep
    
    P7 -- No --> P8{8. dungeons/dungeon_fight.png<br>戰鬥房入口?}
    P8 -- Yes --> ClickP8[點擊進入戰鬥準備] --> EndStep
    
    P8 -- No --> P9{9. dungeons/quit.png<br>關閉彈窗?}
    P9 -- Yes --> ClickP9[點擊退出彈窗] --> EndStep
    
    P9 -- No --> P10{10. dungeons/gungeon_godown.png<br>前進下一層按鈕?}
    P10 -- Yes --> ClickP10[點擊下樓] --> EndStep
    
    P10 -- No --> P11{11. dungeons/Treasure.png<br>寶箱房箱子?}
    P11 -- Yes --> ClickP11[點擊開箱] --> EndStep
    
    P11 -- No --> P12{12. dungeons/dungeon_bless.png<br>接受祝福按鈕?}
    P12 -- Yes --> ClickP12[點擊接受祝福] --> EndStep
    
    P12 -- No --> WaitLoad[等待下一層載入或事件出現] --> Sleep[等待 0.5 秒] --> EndStep
```

---

## 3. 🎒 自動清理背包決策樹 (Backpack Cleaning Flow)

當戰鬥結算偵測到 `common/bagfull_quit.png`（背包已滿）時，程式會點選退出結算並設定清理標記。一旦程式回到準備大廳（普通關卡）或地圖探索畫面（地下城），會**優先攔截並進入 `STATE_BAG_CLEANING` 狀態**，依以下流程進行全自動大量分解與整理：

```mermaid
graph TD
    StartClean([進入背包清理狀態]) --> CheckDialog{畫面上是否有 confirm.png<br>或 ok.png 彈窗?}
    
    CheckDialog -- Yes --> ClickDialog[點擊確認/OK] --> Sleep1[等待 1.2 秒] --> EndStep[結束本步]
    CheckDialog -- No --> CheckTidied{狀態是否已標記為 bag_tidied?}
    
    CheckTidied -- Yes --> FindQuit{尋找 quit.png<br>或 quit_bread.png?}
    FindQuit -- Yes --> ClickQuit[點擊關閉背包] --> ResetFlags[重設清理標記與 bag_tidied] --> TransBack[轉移回 LOBBY<br>或 EXPLORING] --> Done([清理結束])
    FindQuit -- No --> WaitQuit[等待退出按鈕出現] --> SleepQuit[等待 0.5 秒] --> EndStep
    
    CheckTidied -- No --> CheckTidy{畫面上是否有 tidy.png?}
    CheckTidy -- Yes --> ClickTidy[點擊整理按鈕] --> MarkTidied[設定標記 bag_tidied = True] --> SleepTidy[等待 1.2 秒] --> EndStep
    CheckTidy -- No --> CheckDis{畫面上是否有 Disassembly.png?}
    
    CheckDis -- Yes --> ClickDis[點擊分解按鈕] --> SleepDis[等待 1.2 秒] --> EndStep
    CheckDis -- No --> CheckSelect{畫面上是否有 select_all.png?}
    
    CheckSelect -- Yes --> ClickSelect[點擊全選按鈕] --> SleepSelect[等待 1.2 秒] --> EndStep
    CheckSelect -- No --> CheckMass{畫面上是否有 Backpack_Disassembly.png?}
    
    CheckMass -- Yes --> ClickMass[點擊大量分解按鈕] --> SleepMass[等待 1.2 秒] --> EndStep
    CheckMass -- No --> CheckBag{畫面上是否有 bag.png?}
    
    CheckBag -- Yes --> ClickBag[點擊打開背包] --> SleepBag[等待 1.5 秒] --> EndStep
    CheckBag -- No --> WaitBag[等待背包載入或按鈕出現] --> SleepWait[等待 0.5 秒] --> EndStep
```

