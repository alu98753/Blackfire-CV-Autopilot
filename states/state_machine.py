import time
import os
import cv2
import logging
from states.handlers import (
    NavigationHandler,
    LobbyHandler,
    BattleHandler,
    ResultHandler,
    ExploreHandler,
    BagCleaningHandler,
    BackpackFullSortingHandler,
    BreadCollectionHandler,
    DiamondCollectionHandler,
    CollectOnlyHandler,
    LoadingHandler,
    BloodAltarHandler
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
    STATE_BREAD_COLLECTION = "BREAD_COLLECTION"          # 自動領體力流程
    STATE_DIAMOND_COLLECTION = "DIAMOND_COLLECTION"      # 自動領鑽石流程
    STATE_COLLECT_ONLY = "COLLECT_ONLY"                  # 定時領取麵包與鑽石待機流程
    STATE_LOADING = "LOADING"                            # 畫面過渡載入流程
    STATE_BLOOD_ALTAR = "BLOOD_ALTAR"                    # 血之祭壇獻祭流程
    
    def __init__(self, capturer, matcher, mouse):
        self.capturer = capturer
        self.matcher = matcher
        self.mouse = mouse
        
        self.current_state = self.STATE_UNKNOWN
        self.last_state = None
        self.last_state_change = time.time()
        self.battle_start_time = None
        self.run_count = 0
        
        # 紀錄上次點選自動戰鬥的時間，用以判斷 CD
        self.last_auto_click_time = 0
        
        # 當前模式配置，由外部 main.py 初始化設定
        self.config = None
        
        # 領體力相關屬性 (由外部 main.py 初始化與設定)
        self.enable_bread = False
        self.need_bread_collection = False  # 啟動時預設不設定領取，需大門觸發
        self.last_bread_collection_time = 0.0
        self.bread_collected_this_run = False
        self.bread_click_attempted = False
        self.bread_window_opened = False
        
        # 領鑽石相關屬性
        self.need_diamond_collection = False  # 啟動時預設不設定領取，需大門觸發
        self.last_diamond_collection_time = 0.0
        self.diamond_collected_this_run = False
        self.diamond_window_opened = False
        self.diamond_ocr_success = False
        
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
        self.dungeon_floor_transitioning = False
        self.consecutive_stuck_count = 0
        
        # 地下城與關卡戰敗計數與退避相關屬性
        self.dungeon_cooldowns = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.current_dungeon_index = 0
        self.defeat_count = 0
        self.fallback_swipe_count = 0
        
        # 使用者手動介入偵測相關屬性
        self.user_operating = False
        self.last_user_operation_time = 0.0
        self.prev_mouse_pos = None
        
        # 體力不足退避與還原相關屬性
        self.original_config = None
        self.stamina_retreat_start_time = None
        self.last_lobby_start_click_time = 0.0
        self.last_result_retry_click_time = 0.0
        self.loading_start_time = 0.0
        
        # 定義單一繼續模板路徑
        self.continue_template = "common/continue.png"
        self._ocr_reader = None
        
        # 初始化註冊所有狀態處理器
        self.handlers = {
            self.STATE_NAVIGATING: NavigationHandler(self),
            self.STATE_LOBBY: LobbyHandler(self),
            self.STATE_BATTLE: BattleHandler(self),
            self.STATE_RESULT: ResultHandler(self),
            self.STATE_DUNGEON_EXPLORING: ExploreHandler(self),
            self.STATE_BAG_CLEANING: BagCleaningHandler(self),
            self.STATE_BACKPACK_FULL_SORTING: BackpackFullSortingHandler(self),
            self.STATE_BREAD_COLLECTION: BreadCollectionHandler(self),
            self.STATE_DIAMOND_COLLECTION: DiamondCollectionHandler(self),
            self.STATE_COLLECT_ONLY: CollectOnlyHandler(self),
            self.STATE_LOADING: LoadingHandler(self),
            self.STATE_BLOOD_ALTAR: BloodAltarHandler(self),
        }

    @property
    def dungeon_defeat_count(self):
        return self.defeat_count

    @dungeon_defeat_count.setter
    def dungeon_defeat_count(self, value):
        self.defeat_count = value

    def get_ocr_reader(self):
        """
        延遲載入並取得 EasyOCR 讀取器實例，避免啟動延遲。
        """
        if self._ocr_reader is None:
            import easyocr
            logging.info("⚙️ 正在首次載入 EasyOCR 辨識模型 (使用 CPU)...")
            self._ocr_reader = easyocr.Reader(['en'], gpu=False)
        return self._ocr_reader



    def transition_to(self, new_state):
        if self.config is not None and self.config.get("type") == "collect_only":
            if new_state in [self.STATE_NAVIGATING, self.STATE_LOBBY]:
                new_state = self.STATE_COLLECT_ONLY

        if self.current_state != new_state:
            logging.info(f"🔄 狀態轉移: {self.current_state} -> {new_state}")
            self.last_state = self.current_state
            self.current_state = new_state
            self.last_state_change = time.time()
            self.consecutive_stuck_count = 0
            if new_state == self.STATE_BATTLE:
                self.last_auto_click_time = 0
            elif new_state == self.STATE_LOADING:
                self.loading_start_time = time.time()
            elif new_state == self.STATE_BACKPACK_FULL_SORTING:
                self.need_bag_cleaning = True
                self.handlers[new_state].screenshot_counter = 1

    def step(self):
        """
        執行單步狀態檢索與決策（主調度器）。
        """
        if self.config is None:
            logging.warning("⚠️ 尚未載入模式設定 config，請確認 main.py 初始化正確。")
            time.sleep(1)
            return

        pass

        # 2. 取得遊戲視窗邊界與擷取畫面
        rect = self.capturer.get_window_rect()
        self.last_rect = rect # 快取當前幀最穩定的物理邊界
        
        if rect is None:
            logging.warning("⚠️ 找不到遊戲視窗，請確認遊戲未縮小且視窗名稱符合設定。")
            time.sleep(0.5)
            return
            
        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            logging.warning("⚠️ 無法擷取畫面")
            time.sleep(0.2)
            return



        # B. 全域自動重登處理 (低頻率檢測)
        import sys
        is_testing = "unittest" in sys.modules
        now_time = time.time()
        last_low_freq = getattr(self, "_last_low_freq_check_time", 0.0)
        last_state = getattr(self, "_last_low_freq_state", None)
        state_changed = (self.current_state != last_state)
        should_check_low_freq = is_testing or state_changed or (now_time - last_low_freq >= 1.5) or (self.current_state in [self.STATE_UNKNOWN, self.STATE_LOADING])

        if should_check_low_freq:
            self._last_low_freq_check_time = now_time
            self._last_low_freq_state = self.current_state
            from states.login_flow import handle_global_login
            if handle_global_login(self, screen_img, rect):
                return

            # C. 體力不足（食物不足）退避處理
            if self.current_state in [self.STATE_NAVIGATING, self.STATE_LOBBY, self.STATE_RESULT, self.STATE_LOADING]:
                from states.stamina_flow import handle_insufficient_stamina
                if handle_insufficient_stamina(self, screen_img, rect):
                    return

        # 3. 僅有在大門 common/door.png 可見時，才觸發自動領鑽石/領麵包定時檢查
        self.check_collection_trigger(screen_img)

        # A. 卡死監控 (stuck monitoring)
        # 只有在非戰鬥、非探索、非未知的過渡狀態下，如果同一個狀態持續了太多幀，說明流程可能卡住了
        if self.current_state not in [self.STATE_BATTLE, self.STATE_DUNGEON_EXPLORING, self.STATE_UNKNOWN, self.STATE_COLLECT_ONLY, self.STATE_LOADING]:
            self.consecutive_stuck_count += 1
            
            if self.consecutive_stuck_count >= 15:
                logging.warning(f"⚠️ [防卡死] 狀態 [{self.current_state}] 連續 {self.consecutive_stuck_count} 幀未轉移，判定為流程卡住。嘗試點擊全域 confirm/continue 按鈕...")
                
                # 嘗試尋找全域確認或繼續/退出按鈕
                stuck_dismissed = False
                for btn in ["common/confirm.png", "common/ok.png", "common/continue.png", "common/quit.png"]:
                    if os.path.exists(os.path.join("templates", btn)):
                        pos, conf = self.matcher.match(screen_img, btn, threshold=0.8)
                        if pos:
                            logging.info(f"👉 [防卡死] 偵測到通用確認/繼續/退出按鈕 [{btn}] (信心度: {conf:.4f})，進行點擊以清除阻礙。")
                            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                            self.consecutive_stuck_count = 0  # 重置計數
                            stuck_dismissed = True
                            time.sleep(0.15)
                            break
                            
                if not stuck_dismissed:
                    logging.warning(f"⚠️ [防卡死] 未能在畫面上找到任何全域確認/繼續/退出按鈕，將狀態重設為 UNKNOWN 以進行重新定位。")
                    self.transition_to(self.STATE_UNKNOWN)
                    return
        else:
            self.consecutive_stuck_count = 0

        # 3. 全域彈窗與任務完成處理 (低頻率檢測)
        if should_check_low_freq:
            # 3.1 檢查「任務完成」彈窗 (task_complete.png)
            if os.path.exists(os.path.join("templates", "task_complete.png")):
                pos, conf = self.matcher.match(screen_img, "task_complete.png", threshold=0.8)
                if pos:
                    # 計算「領取獎勵」按鈕的相對位置（依據當前畫面高度動態縮放偏移量，以 1080p 為基準）
                    height_to_use = rect.get("height") or screen_img.shape[0] or 1080
                    scale_y = height_to_use / 1080.0
                    btn_x = rect["left"] + pos[0]
                    btn_y = rect["top"] + pos[1] + int(281 * scale_y)
                    logging.info(f"🎉 偵測到【任務完成】彈窗 (信心度: {conf:.4f})，啟動「領取任務獎勵」子流程，點擊座標 ({btn_x}, {btn_y})。")
                    self.mouse.click(btn_x, btn_y)
                    time.sleep(0.5)  # 等待動畫
                    self._run_task_complete_subflow(rect)
                    return

            # 3.2 檢查「無法容納的物品 (背包滿)」彈窗 (backpack_full.png)
            if os.path.exists(os.path.join("templates", "backpack_full.png")):
                # 調高門檻至 0.80 以避免大廳背景等介面產生虛假誤判，真實彈窗特徵明顯，信心度極高
                pos, conf = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
                if pos:
                    if self.current_state != self.STATE_BACKPACK_FULL_SORTING:
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
        # 每秒最多存檔一次除錯畫面，避免過度佔用硬碟 I/O
        import numpy as np
        now = time.time()
        if now - getattr(self, "last_detect_save_time", 0.0) > 1.0:
            self.last_detect_save_time = now
            if isinstance(screen_img, np.ndarray):
                cv2.imwrite("debug_detect.png", screen_img)
                logging.info("📸 [除錯] 已儲存當前全域辨識畫面至專案根目錄下的 debug_detect.png")

        logging.info("🔍 正在進行全域掃描以辨識遊戲狀態...")
        
        # 0.0 如果看見「無法容納的物品 (背包滿)」彈窗，進入分選狀態
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            pos, _ = self.matcher.match(screen_img, "backpack_full.png", threshold=0.80)
            if pos:
                self.transition_to(self.STATE_BACKPACK_FULL_SORTING)
                return

        # 0.02 如果看見「戰敗畫面」 (defeat.png)，進入結算狀態
        if os.path.exists(os.path.join("templates", "defeat.png")):
            pos, _ = self.matcher.match(screen_img, "defeat.png", threshold=0.75)
            if pos:
                self.transition_to(self.STATE_RESULT)
                return

        # 0.05 如果需要清理背包 (need_bag_cleaning == True) 且已回到了大廳/城鎮畫面 (看到 common/door.png 或 goback_town.png)
        if self.need_bag_cleaning:
            for town_btn in ["common/door.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", town_btn)):
                    pos_t, _ = self.matcher.match(screen_img, town_btn, threshold=0.8)
                    if pos_t:
                        self.transition_to(self.STATE_BAG_CLEANING)
                        return

        # 0.1 如果需要領鑽石或體力，且畫面上看見入口或功能按鈕，進入導航/領取狀態
        # logging.info(f"🔍 [除錯] 領取旗標狀態：need_diamond={self.need_diamond_collection}, enable_bread={self.enable_bread}, need_bread={self.need_bread_collection}")
        if self.need_diamond_collection or (self.enable_bread and self.need_bread_collection):
            nav_buttons = [
                "common/door.png", "goback_town.png", "diamond.png", "free.png",
                "common/bread.png", "common/collect.png", "common/bread_collection.png", "common/quit.png"
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

        # 2. 檢查是否在普通關卡大廳 (判斷 common/select_stage.png 與 goback_town.png 至少存在一個)
        if self.config["type"] == "stage":
            in_lobby = False
            for btn in ["common/select_stage.png", "goback_town.png"]:
                if os.path.exists(os.path.join("templates", btn)):
                    pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
                    if pos:
                        in_lobby = True
                        break
            if in_lobby:
                self.transition_to(self.STATE_LOBBY)
                return
                
        # 3. 檢查是否在大廳的尋路路徑上
        for btn in self.config.get("navigation_path", []):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.8)
            logging.info(f"🔍 [除錯] 比對尋路按鈕 '{btn}'，最高相似度: {conf:.4f}，座標: {pos}")
            if pos and conf >= 0.8:
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

        # 6. 如果以上皆非，嘗試檢查是否有退出或確認按鈕可以點擊（代表可能卡在某個手動操作的子視窗/子介面，需關閉以返回大廳）
        for quit_btn in ["common/quit.png", "common/confirm.png", "common/ok.png"]:
            if os.path.exists(os.path.join("templates", quit_btn)):
                pos, conf = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                if pos:
                    logging.info(f"🧭 全域定位：未能辨識主要狀態，但偵測到退出/確認按鈕 [{quit_btn}] (信心度: {conf:.4f})，嘗試點擊以返回大廳。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    # 點擊後不轉移狀態，等待下一幀的 UNKNOWN 重新進行定位與尋路
                    time.sleep(0.3)
                    return

        # 7. 如果真的是完全沒有任何可交互按鈕，才依模式給予最安全的預設落點
        if self.config["type"] == "dungeon":
            # 地下城模式下，大部份時間都在走格探索，預設回到 EXPLORING 狀態最為安全
            logging.info("❓ 未能辨識出特定探索按鈕，預設進入 EXPLORING 狀態。")
            self.transition_to(self.STATE_DUNGEON_EXPLORING)
        else:
            # 普通關卡模式下，如果能匹配到自動戰鬥特徵，預設為 BATTLE；否則預設為 NAVIGATING 以重啟大廳尋路
            has_auto = False
            if os.path.exists(os.path.join("templates", "common/auto.png")):
                pos_auto, _ = self.matcher.match(screen_img, "common/auto.png", threshold=0.7)
                if pos_auto:
                    has_auto = True
            
            if has_auto:
                logging.info("❓ 未能辨識出關卡大廳特徵，但偵測到自動戰鬥特徵，預設進入 BATTLE 狀態。")
                self.transition_to(self.STATE_BATTLE)
            else:
                logging.info("❓ 未能辨識出關卡大廳特徵，且無自動戰鬥特徵，預設進入 NAVIGATING 狀態重啟尋路.")
                self.transition_to(self.STATE_NAVIGATING)

    def has_available_dungeon(self):
        """檢查記憶體中是否有冷卻已結束且允許打的地下城"""
        if not self.config:
            return False

        # 如果先前已確認所有地下城皆在冷卻中，且尚未超過暫存冷卻時間，直接傳回 False
        all_cd_until = getattr(self, "all_dungeons_on_cooldown_until", 0.0)
        if time.time() < all_cd_until:
            return False

        allowed_indices = self.config.get("greedy_allowed_indices")
        if allowed_indices is None:
            raise ValueError("配置錯誤：config 未設定 'greedy_allowed_indices'，請在 config.py 或啟動設定中指定允許的地下城索引清單 (例如: [0, 1, 2, 3, 4])。")

        now = time.time()
        is_greedy = self.config.get("greedy_dungeon", False)
        
        if is_greedy:
            for idx in allowed_indices:
                if now >= self.dungeon_cooldowns.get(idx, 0.0):
                    return True
            return False
        else:
            # 非貪婪模式 (指定特定副本)：只檢查 navigation_path 中指定的副本索引
            entry_templates = self.config.get("dungeon_entries")
            if entry_templates is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_entries'，請在 config.py 或啟動設定中指定地下城入口模板清單。")
            nav_path = self.config.get("navigation_path")
            if nav_path is None:
                raise ValueError("配置錯誤：config 未設定 'navigation_path'。")

            target_idx = None
            for idx, temp_name in enumerate(entry_templates):
                if temp_name in nav_path:
                    target_idx = idx
                    break
            
            if target_idx is not None:
                return now >= self.dungeon_cooldowns.get(target_idx, 0.0)
            
            return False

    def get_dungeon_cooldown_status(self):
        """
        列出當前所有允許地下城的冷卻情形，以及判定可挑戰的地下城列表。
        :return: (status_summary_str, available_dungeon_names_list)
        """
        if not self.config:
            raise ValueError("配置錯誤：GameStateMachine 尚未設定 config。")

        dungeon_names = self.config.get("dungeon_names")
        if dungeon_names is None:
            raise ValueError("配置錯誤：config 未設定 'dungeon_names'，請在 config.py 或啟動設定中指定地下城名稱清單。")

        allowed_indices = self.config.get("greedy_allowed_indices")
        if allowed_indices is None:
            raise ValueError("配置錯誤：config 未設定 'greedy_allowed_indices'，請在 config.py 或啟動設定中指定允許的地下城索引清單。")

        from utils.time_parser import format_seconds_to_readable
        now = time.time()

        is_greedy = self.config.get("greedy_dungeon", False)
        if is_greedy:
            target_indices = allowed_indices
        else:
            entry_templates = self.config.get("dungeon_entries")
            if entry_templates is None:
                raise ValueError("配置錯誤：config 未設定 'dungeon_entries'，請在 config.py 或啟動設定中指定地下城入口模板清單。")
            nav_path = self.config.get("navigation_path")
            if nav_path is None:
                raise ValueError("配置錯誤：config 未設定 'navigation_path'。")

            target_idx = None
            for idx, temp_name in enumerate(entry_templates):
                if temp_name in nav_path:
                    target_idx = idx
                    break
            target_indices = [target_idx] if target_idx is not None else []

        cd_details = []
        available_names = []

        for idx in allowed_indices:
            if idx >= len(dungeon_names):
                raise ValueError(f"配置錯誤：greedy_allowed_indices 中的索引 {idx} 超出 dungeon_names 長度 ({len(dungeon_names)})。")
            name = dungeon_names[idx]
            cd_until = self.dungeon_cooldowns.get(idx, 0.0)
            rem = cd_until - now
            if rem > 0:
                if cd_until == float('inf'):
                    cd_details.append(f"[{name}]: 永久不可打")
                else:
                    cd_str = format_seconds_to_readable(rem)
                    cd_details.append(f"[{name}]: 冷卻中 ({cd_str})")
            else:
                if idx in target_indices:
                    cd_details.append(f"[{name}]: 就緒 (可打)")
                    available_names.append(name)
                else:
                    cd_details.append(f"[{name}]: 就緒 (未啟用)")

        return ", ".join(cd_details), available_names

    def check_collection_trigger(self, screen_img):
        """
        依據冷卻時間觸發鑽石與麵包的領取（全域時間檢測，不限於大門畫面）。
        """
        if self.config is not None and self.config["type"] == "bag_clean":
            return  # 背包整理模式不參與領取

        from config import GLOBAL_SETTINGS

        # 1. 檢查鑽石 CD
        default_diamond_cd = GLOBAL_SETTINGS.get("default_diamond_cd", 7200.0)
        diamond_cd = self.config.get("diamond_cd", default_diamond_cd) if self.config else default_diamond_cd
        if time.time() - self.last_diamond_collection_time > diamond_cd:
            if not self.need_diamond_collection:
                logging.info(f"⏰ 距離上次領鑽石已滿 {int(diamond_cd // 60)} 分鐘，觸發自動領鑽石。")
                self.need_diamond_collection = True
                self.diamond_collected_this_run = False

        # 2. 檢查體力 CD
        default_bread_cd = 7200.0 if (self.config and self.config.get("type") == "collect_only") else GLOBAL_SETTINGS.get("default_bread_cd", 1800.0)
        bread_cd = self.config.get("bread_cd", default_bread_cd) if self.config else default_bread_cd
        if self.enable_bread and (time.time() - self.last_bread_collection_time > bread_cd):
            if not self.need_bread_collection:
                logging.info(f"⏰ 距離上次領體力已滿 {int(bread_cd // 60)} 分鐘，觸發自動領體力。")
                self.need_bread_collection = True
                self.bread_collected_this_run = False
                self.bread_click_attempted = False

    def _run_task_complete_subflow(self, rect):
        logging.info("🎉 [子流程] 開始執行「領取任務獎勵」確認子流程...")
        start_time = time.time()
        timeout = 5.0  # 最多執行 5 秒
        
        subflow_templates = [
            ("common/confirm.png", 0.80),
            ("common/ok.png", 0.80)
        ]
        
        while time.time() - start_time < timeout:
            screen_img = self.capturer.capture(rect)
            if screen_img is None:
                time.sleep(0.2)
                continue
                
            matched_any = False
            for template_name, thresh in subflow_templates:
                if not os.path.exists(os.path.join("templates", template_name)):
                    continue
                pos, conf = self.matcher.match(screen_img, template_name, threshold=thresh)
                if pos:
                    logging.info(f"🎉 [子流程] 偵測到確認按鈕 '{template_name}'，相似度: {conf:.4f}，進行點擊...")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    matched_any = True
                    time.sleep(0.5) # 等待彈窗關閉動畫
                    break # 重新擷取畫面以確認是否消失
                    
            if not matched_any:
                # 2. 如果無任何確認按鈕，檢查任務完成主彈窗是否消失
                pos_task, conf_task = self.matcher.match(screen_img, "task_complete.png", threshold=0.8)
                if not pos_task:
                    logging.info("🟢 [子流程] 任務完成彈窗已確認關閉，成功領取獎勵！")
                    return
                else:
                    # 3. 若任務彈窗仍存在且無確認按鈕，說明第一步點選「領取獎勵」失效，進行重新點擊！
                    height_to_use = rect.get("height") or screen_img.shape[0] or 1080
                    scale_y = height_to_use / 1080.0
                    btn_x = rect["left"] + pos_task[0]
                    btn_y = rect["top"] + pos_task[1] + int(281 * scale_y)
                    logging.info(f"🔄 [子流程] 偵測到任務完成彈窗仍存在，但無確認按鈕，重新點擊領取獎勵座標 ({btn_x}, {btn_y})。")
                    self.mouse.click(btn_x, btn_y)
                    time.sleep(0.5)

