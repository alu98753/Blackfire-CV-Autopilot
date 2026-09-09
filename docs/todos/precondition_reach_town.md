在整個專案架構與掛機生命週期中，除了目前正在處理的 **5 大每日城鎮子流程 (Town Subflows: chest, hero_draw, blood_altar, jewelry_workshop, bulletin_board)** 之外，所有需要**主動返回城鎮 (`REACH_TOWN` / `goback_town`)** 的業務事件、保護性退避與重定位情境彙整如下：

---

### 一、 資源與體力類事件 (Resources & Stamina)

1. **體力耗盡退避 (Stamina Retreat / No Bread)**
   * **觸發點**：戰鬥大廳點擊開始後跳出「麵包不足 (`no_bread`)」彈窗，或確認無體力。
   * **回城行為**：
     - 關閉 `no_bread` 彈窗。
     - 點擊 `goback_town.png` 退出大廳／關卡選單，**退回城鎮進入 `COLLECT_ONLY`（定時待機領取模式）**。
     - 規範要求：必須待在城鎮主畫面等待體力恢復或定時領體力，嚴禁滯留在關卡大廳。

2. **定時領取鑽石 (Diamond Collection)**
   * **觸發點**：每 120 分鐘計時器到期，或啟動時偵測到冷卻結束。
   * **回城行為**：
     - 領鑽石的入口按鈕 `diamond.png` **僅存在於城鎮主畫面右上角**。
     - 若當前角色在大廳、選關或副本外，必須先沿 `goback_town.png` **返回城鎮**，才能看見並點擊 `diamond.png`。

---

### 二、 背包與裝備整理類事件 (Inventory & Equipment)

3. **背包已滿清理退回 (Backpack Full & Cleaning Trigger)**
   * **觸發點**：戰鬥中、結算時或領地探索時彈出 `backpack_full.png`（背包已滿）。
   * **回城行為**：
     - 雖然在大廳也能點右下角物品欄，但若需要執行更深度的裝備銷毀、祭壇獻祭或前往商店販售，系統會導航回大廳或城鎮。
   * **特別注意（剛才碰到的死循環情境）**：
     - 當背包整理完畢關閉後，會觸發「自動前往血之祭壇 + 珠寶店」的城鎮流水線，**此時必須從背包狀態切出並回到城鎮**。

---

### 三、 首領戰與週期活動類事件 (Bosses & Periodic Events)

4. **首領討伐 (Lord Boss) 冷卻完畢或次數可用**
   * **觸發點**：`DailyManager` 偵測到三大首領（蜘蛛、惡靈、雪山食屍王）冷卻結束且今日次數未滿。
   * **回城行為**：
     - 雖然 Lord 入口在選關頁籤的第三個 tab (`lord_after.png`)，但目前很多 Handler（如 `LordBossHandler`）在初始與退出時，若迷航或需要重定位，會**優先透過 `common/door.png` 重新錨定回城鎮座標系**。

5. **深淵魔王 (Demon Lords) 挑戰發起**
   * **觸發點**：每日 3 次深淵魔王次數可用。
   * **回城行為**：
     - 購買門票或進入大廳準備時，若當前處於迷航或待機狀態，會從待機模式喚醒並**回到城鎮大門重新發起流程**。

---

### 四、 跨日重置與調度邊界事件 (Daily Reset & Scheduling Boundaries)

6. **每日清晨 08:05 跨日重置 (Daily Scheduled Reset)**
   * **觸發點**：每日伺服器換日點（08:00）過後，本地定時器於 08:05 觸發全域重置。
   * **回城行為**：
     - 刷新所有 Daily 狀態檔與冷卻時間。
     - 系統強制要求**退出當前任何非戰鬥中的深層選單，返回城鎮 (`TOWN`)**，作為新一天所有日常流水線的唯一乾淨起點（Clean Slate）。

7. **懸賞任務清單完成 / 全部無任務可做 (Daily Pipeline Drain & Fallback)**
   * **觸發點**：五大城鎮速領完成、且懸賞任務全部打完（或 0 項任務）。
   * **回城行為**：
     - 卸載懸賞排程器，若使用者設定為「全冷卻時待機」，則點擊 `goback_town` **退回城鎮進入 `STATE_COLLECT_ONLY` 發呆**。

---

### 五、 異常復原與安全看門狗類事件 (Exception Watchdog & Recovery)

8. **地下城探索結束／通關結算 (Dungeon Exit)**
   * **觸發點**：地下城探索達到最大層數、死亡失敗、或點擊離開。
   * **回城行為**：
     - 結算後回到地下城選擇列表，若沒有下一輪地下城計畫，點擊 `goback_town` **返回城鎮**。

9. **領地探索中斷／需要回城 (Domain Explore Exit)**
   * **觸發點**：黃金古國等領地探索步數耗盡、陣亡、或被更高優先級的活動（如 Lord、Daily）插隊。
   * **回城行為**：
     - 點擊 `domains/common/exit_to_lobby.png` 退出領地主畫面回到大廳。
     - 接著點擊 `goback_town.png` **退回城鎮**。

10. **全域卡死自癒／彈窗迷航恢復 (Unexpected Popup Recovery & Watchdog Staircase)**
    * **觸發點**：連續 N 幀無進展、遇到未知全螢幕彈窗、輪盤抽獎 (`wheel_of_fortune`) 等臨時活動彈窗。
    * **回城行為**：
      - 關閉彈窗後，安全階梯的第一原則是：**尋找 `common/quit.png` 或 `goback_town.png` 無腦點擊，直到看見 `common/door.png`（回到城鎮安全區）**，重新進行場景定位（Relocalize）。

11. **遊戲重啟後的冷啟動定位 (Game Relaunch / Cold Boot Relocalization)**
    * **觸發點**：進程重啟（ProcessPort relaunch）或手動啟動腳本。
    * **回城行為**：
      - 登入點擊 `login.png` 後，`login_flow.py` 的唯一成功判定標誌就是：**等到城鎮大門 `common/door.png` 出現**，確認進入城鎮才交出控制權。

---

### 總結架構圖：所有需要 `REACH_TOWN` 的來源

```text
               ┌─ 體力耗盡退避 (No Bread)
               ├─ 領鑽石 (Diamond Collection)
               ├─ 背包清理結束 (Bag Cleaned -> Subflow Chain)
               ├─ 08:05 跨日全域重置 (Daily Reset)
               ├─ 每日任務全數完成進入待機 (Pipeline Drain -> Collect Only)
[ 觸發事件 ] ──┼─ 領地探索結束/插隊 (Domain Explore Exit)
               ├─ 5 大城鎮子流程前置導航 (Town Subflows Precondition)
               ├─ 迷航與彈窗自癒 (Watchdog Recovery)
               └─ 遊戲重新啟動登入 (Game Relaunch Login)
                       │
                       ▼
            【 共用 REACH_TOWN 路由 】
       (關前景彈窗 -> 離開建築 -> 離開領地 -> 退出大廳)
                       │
                       ▼
              抵達目標：【 SceneId.TOWN 】
```

這意味著：**`REACH_TOWN` 確實是整個遊戲自動化系統的「安全樞紐（Home Hub）」**，把它從各 Handler 抽離成共用路由表的決策是 100% 正確的。