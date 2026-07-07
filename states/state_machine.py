import time
import os
import logging
from states.handlers import (
    NavigationHandler,
    LobbyHandler,
    BattleHandler,
    ResultHandler,
    ExploreHandler,
    BagCleaningHandler,
    BackpackFullSortingHandler
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class GameStateMachine:
    # 定義遊戲狀態
    STATE_UNKNOWN = "UNKNOWN"
    STATE_NAVIGATING = "NAVIGATING"          # 尋路/導航中，依序點擊路徑按鈕進入副本
    STATE_LOBBY = "LOBBY"                    # [關卡專屬] 準備大廳，尋找並點擊開始按鈕
    STATE_BATTLE = "BATTLE"                  # 戰鬥進行中，點選自動戰鬥並監控結算
    STATE_RESULT = "RESULT"                  # [關卡專屬] 戰鬥結束結算，點擊繼續/再戰
    STATE_DUNGEON_EXPLORING = "EXPLORING"    # [地下城專屬] 地下城探索中，處理隨機事件與前進下一層
    STATE_BAG_CLEANING = "BAG_CLEANING"      # 背包滿了時，自動打開背包進行分解與整理
    STATE_BACKPACK_FULL_SORTING = "BACKPACK_FULL_SORTING" # 背包滿時自適應裝備分選與銷毀
    
    def __init__(self, capturer, matcher, mouse):
        self.capturer = capturer
        self.matcher = matcher
        self.mouse = mouse
        
        self.current_state = self.STATE_UNKNOWN
        self.last_state_change = time.time()
        self.battle_start_time = None
        self.run_count = 0
        
        # 紀錄上次點選自動戰鬥的時間，用以判斷 CD
        self.last_auto_click_time = 0
        
        # 當前模式配置，由外部 main.py 初始化設定
        self.config = None
        
        # 領體力相關屬性 (由外部 main.py 初始化與設定)
        self.enable_bread = False
        self.need_bread_collection = True  # 啟動時預設需要領一次體力
        self.last_bread_collection_time = time.time()
        self.bread_collected_this_run = False
        
        # 領鑽石相關屬性
        self.need_diamond_collection = True  # 啟動時預設領一次鑽石
        self.last_diamond_collection_time = 0.0
        self.diamond_collected_this_run = False
        
        # 背包清理相關屬性
        self.need_bag_cleaning = False
        self.bag_tidied = False
        self.bag_disassembled = False
        self.bag_select_all_clicked = False
        self.bag_deselected = False
        
        # 地下城本層探索記憶 (防止已完成的事件重複點選)
        self.chest_opened_this_floor = False
        self.skill_selected_this_floor = False
        self.bless_received_this_floor = False
        self.last_godown_click_time = None
        
        # 使用者手動介入偵測相關屬性
        self.user_operating = False
        self.last_user_operation_time = 0.0
        self.prev_mouse_pos = None
        
        # 動態尋找所有 continue*.png 模板
        self.continue_templates = self._discover_continue_templates()
        
        # 初始化註冊所有狀態處理器
        self.handlers = {
            self.STATE_NAVIGATING: NavigationHandler(self),
            self.STATE_LOBBY: LobbyHandler(self),
            self.STATE_BATTLE: BattleHandler(self),
            self.STATE_RESULT: ResultHandler(self),
            self.STATE_DUNGEON_EXPLORING: ExploreHandler(self),
            self.STATE_BAG_CLEANING: BagCleaningHandler(self),
            self.STATE_BACKPACK_FULL_SORTING: BackpackFullSortingHandler(self),
        }

    def _discover_continue_templates(self):
        templates = []
        templates_dir = "templates"
        if os.path.exists(templates_dir):
            for root, dirs, files in os.walk(templates_dir):
                for f in files:
                    if f.startswith("continue") and f.endswith(".png"):
                        # 計算相對於 templates_dir 的相對路徑，並將 Windows 斜線替換為正斜線
                        rel_path = os.path.relpath(os.path.join(root, f), templates_dir)
                        templates.append(rel_path.replace("\\", "/"))
        templates.sort()
        logging.info(f"🔍 偵測到之「繼續」按鈕模板清單: {templates}")
        return templates

    def transition_to(self, new_state):
        if self.current_state != new_state:
            logging.info(f"🔄 狀態轉移: {self.current_state} -> {new_state}")
            self.current_state = new_state
            self.last_state_change = time.time()
            if new_state == self.STATE_BATTLE:
                self.last_auto_click_time = 0
            elif new_state == self.STATE_BACKPACK_FULL_SORTING:
                self.need_bag_cleaning = True

    def step(self):
        """
        執行單步狀態檢索與決策（主調度器）。
        """
        if self.config is None:
            logging.warning("⚠️ 尚未載入模式設定 config，請確認 main.py 初始化正確。")
            time.sleep(1)
            return

        # 1. 檢查領體力與領鑽石定時器 (背包整理模式除外)
        if self.config["type"] != "bag_clean":
            # 1.1 鑽石定時器 (2小時 = 7200秒)
            if time.time() - self.last_diamond_collection_time > 7200.0:
                if not self.need_diamond_collection:
                    logging.info("⏰ 距離上次領鑽石已滿 2 小時，排程在下一輪準備階段執行自動領鑽石。")
                    self.need_diamond_collection = True

            # 1.2 體力定時器 (30分鐘 = 1800秒)
            if self.enable_bread and (time.time() - self.last_bread_collection_time > 1800.0):
                if not self.need_bread_collection:
                    logging.info("⏰ 距離上次領體力已滿 30 分鐘，排程在下一輪準備階段執行自動領體力。")
                    self.need_bread_collection = True

        # 2. 取得遊戲視窗邊界與擷取畫面
        rect = self.capturer.get_window_rect()
        if rect is None:
            logging.warning("⚠️ 找不到遊戲視窗，請確認遊戲未縮小且視窗名稱符合設定。")
            time.sleep(0.5)
            return
            
        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            logging.warning("⚠️ 無法擷取畫面")
            time.sleep(0.2)
            return

        # 3. 全域彈窗與任務完成處理
        # 3.1 檢查「任務完成」彈窗 (task_complete.png)
        if os.path.exists(os.path.join("templates", "task_complete.png")):
            pos, conf = self.matcher.match(screen_img, "task_complete.png", threshold=0.8)
            if pos:
                # 計算「領取獎勵」按鈕的相對位置並點擊
                btn_x = rect["left"] + pos[0]
                btn_y = rect["top"] + pos[1] + 281
                logging.info(f"🎉 偵測到【任務完成】彈窗 (信心度: {conf:.4f})，點擊「領取獎勵」按鈕座標: ({btn_x}, {btn_y})。")
                self.mouse.click(btn_x, btn_y)
                time.sleep(0.1)
                return

        # 3.2 檢查「無法容納的物品 (背包滿)」彈窗 (backpack_full.png)
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            # 調低門檻至 0.7 以應對可能的光影或微幅變動，確保 100% 偵測成功
            pos, conf = self.matcher.match(screen_img, "backpack_full.png", threshold=0.7)
            if pos:
                if self.current_state != self.STATE_BACKPACK_FULL_SORTING and self.current_state not in [self.STATE_BATTLE, self.STATE_RESULT]:
                    logging.warning(f"🎒 全域偵測到【無法容納的物品 (背包已滿)】畫面 (信心度: {conf:.4f})，切換至 BACKPACK_FULL_SORTING 狀態進行自適應分選。")
                    self.transition_to(self.STATE_BACKPACK_FULL_SORTING)
                    return

        # 3.3 在大廳或需要清理背包狀態下，若看見通用確認按鈕，點擊以關閉彈窗 (如領取獎勵/關閉背包滿後續確認，排除背包清理狀態自身處理)
        if (self.current_state == self.STATE_LOBBY or self.need_bag_cleaning) and self.current_state not in [self.STATE_BAG_CLEANING, self.STATE_BACKPACK_FULL_SORTING]:
            for conf_btn in ["common/confirm.png", "common/ok.png"]:
                if os.path.exists(os.path.join("templates", conf_btn)):
                    pos, conf = self.matcher.match(screen_img, conf_btn, threshold=0.8)
                    if pos:
                        logging.info(f"👉 偵測到通用確認按鈕 [{conf_btn}] (信心度: {conf:.4f})，點擊關閉。")
                        self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                        time.sleep(0.08)
                        return

        # 4. 分發處理至當前狀態的 Handler
        handler = self.handlers.get(self.current_state)
        if handler:
            handler.handle(screen_img, rect)
        else:
            # 預設未知狀態下，進行全域掃描定位當前狀態
            self.detect_current_state(screen_img, rect)

    def detect_current_state(self, screen_img, rect):
        """
        全域掃描定位當前狀態。
        """
        logging.info("🔍 正在進行全域掃描以辨識遊戲狀態...")
        
        # 0.0 如果看見「無法容納的物品 (背包滿)」彈窗，進入分選狀態
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            pos, _ = self.matcher.match(screen_img, "backpack_full.png", threshold=0.7)
            if pos:
                self.transition_to(self.STATE_BACKPACK_FULL_SORTING)
                return

        # 0.1 如果需要領鑽石或體力，且畫面上看見入口或功能按鈕，進入導航/領取狀態
        if self.need_diamond_collection or (self.enable_bread and self.need_bread_collection):
            nav_buttons = [
                "common/door.png", "goback_town.png", "diamond.png", "diamond_free.png",
                "common/bread.png", "common/bread_collection.png", "common/quit.png"
            ]
            for bf in nav_buttons:
                if os.path.exists(os.path.join("templates", bf)):
                    pos, _ = self.matcher.match(screen_img, bf, threshold=0.8)
                    if pos:
                        self.transition_to(self.STATE_NAVIGATING)
                        return

        # 1. 檢查是否在戰鬥中 (看到 common/auto.png 必定在戰鬥)
        if os.path.exists(os.path.join("templates", "common/auto.png")):
            pos, _ = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
            if pos:
                self.transition_to(self.STATE_BATTLE)
                return

        # 2. 檢查是否在普通關卡大廳
        if self.config["type"] == "stage":
            lobby_btn = self.config["lobby_start_btn"]
            pos, _ = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
            if pos:
                self.transition_to(self.STATE_LOBBY)
                return
                
        # 3. 檢查是否在大廳的尋路路徑上
        for btn in self.config.get("navigation_path", []):
            pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
            if pos:
                self.transition_to(self.STATE_NAVIGATING)
                return
                
        # 4. 檢查是否在地下城探險中
        if self.config["type"] == "dungeon":
            for btn_name in self.config["explore_priorities"]:
                # 如果看見任何探索或通關完成按鈕，說明處於探索狀態
                if btn_name in ["dungeons/dungeons_complete.png", "dungeons/gungeon_godown.png", "dungeons/Treasure.png", "dungeons/dungeon_bless.png"]:
                    pos, _ = self.matcher.match(screen_img, btn_name, threshold=0.8)
                    if pos:
                        self.transition_to(self.STATE_DUNGEON_EXPLORING)
                        return
                        
        # 5. 如果是背包整理模式，強制跳轉至 BAG_CLEANING
        if self.config["type"] == "bag_clean":
            self.transition_to(self.STATE_BAG_CLEANING)
            return

        # 6. 如果以上皆非，依模式給予最安全的預設落點
        if self.config["type"] == "dungeon":
            # 地下城模式下，大部份時間都在走格探索，預設回到 EXPLORING 狀態最為安全
            logging.info("❓ 未能辨識出特定探索按鈕，預設進入 EXPLORING 狀態。")
            self.transition_to(self.STATE_DUNGEON_EXPLORING)
        else:
            logging.info("❓ 未能辨識出大廳按鈕，預設進入 BATTLE 狀態。")
            self.transition_to(self.STATE_BATTLE)
