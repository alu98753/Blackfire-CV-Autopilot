import time
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class GameStateMachine:
    # 定義遊戲狀態
    STATE_UNKNOWN = "UNKNOWN"
    STATE_NAVIGATING = "NAVIGATING"          # 尋路/導航中，依序點擊路徑按鈕進入副本
    STATE_LOBBY = "LOBBY"                    # [關卡專屬] 準備大廳，尋找並點擊開始按鈕
    STATE_BATTLE = "BATTLE"                  # 戰鬥進行中，點選自動戰鬥並監控結算
    STATE_RESULT = "RESULT"                  # [關卡專屬] 戰鬥結束結算，點擊繼續/再戰
    STATE_DUNGEON_EXPLORING = "EXPLORING"    # [地下城專屬] 地下城探索中，處理隨機事件與前進下一層
    
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
        
        # 動態尋找所有 continue*.png 模板
        self.continue_templates = self._discover_continue_templates()

    def _discover_continue_templates(self):
        templates = []
        templates_dir = "templates"
        if os.path.exists(templates_dir):
            for f in os.listdir(templates_dir):
                if f.startswith("continue") and f.endswith(".png"):
                    templates.append(f)
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

    def step(self):
        """
        執行單步狀態檢索與決策。
        """
        if self.config is None:
            logging.warning("⚠️ 尚未載入模式設定 config，請確認 main.py 初始化正確。")
            time.sleep(1)
            return

        # 1. 取得遊戲視窗邊界與擷取畫面
        rect = self.capturer.get_window_rect()
        if rect is None:
            logging.warning("⚠️ 找不到遊戲視窗，請確認遊戲未縮小且視窗名稱符合設定。")
            time.sleep(2)
            return
            
        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            logging.warning("⚠️ 無法擷取畫面")
            time.sleep(1)
            return

        # 2. 依據目前狀態執行決策
        if self.current_state == self.STATE_UNKNOWN:
            # 初始未知狀態下，進行全域掃描定位當前狀態
            self.detect_current_state(screen_img, rect)
            
        elif self.current_state == self.STATE_NAVIGATING:
            # 尋路/跳轉進入副本狀態
            self.handle_navigation(screen_img, rect)
            
        elif self.current_state == self.STATE_LOBBY:
            # [關卡專屬] 大廳狀態下：尋找大廳開始按鈕
            lobby_btn = self.config["lobby_start_btn"]
            pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
            if pos:
                logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊。")
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                self.run_count += 1
                logging.info(f"🚀 開始第 {self.run_count} 次關卡戰鬥！")
                self.battle_start_time = time.time()
                self.transition_to(self.STATE_BATTLE)
                time.sleep(2.0) # 等待戰鬥載入
            else:
                self.detect_current_state(screen_img, rect)

        elif self.current_state == self.STATE_BATTLE:
            # [雙模式通用] 戰鬥狀態下：
            self.handle_battle(screen_img, rect)

        elif self.current_state == self.STATE_RESULT:
            # [關卡專屬] 關卡結算狀態下：
            self.handle_stage_results(screen_img, rect)

        elif self.current_state == self.STATE_DUNGEON_EXPLORING:
            # [地下城專屬] 地下城探索狀態下：
            self.handle_dungeon_exploring(screen_img, rect)

    def handle_navigation(self, screen_img, rect):
        """
        尋路導航處理邏輯。
        """
        nav_path = self.config.get("navigation_path", [])
        if not nav_path:
            # 如果沒有設定尋路路徑 (例如普通關卡)，直接進入大廳狀態
            self.transition_to(self.STATE_LOBBY)
            return

        # 逆序掃描導航路徑中可見的按鈕，點擊最深層的那個
        clicked_any = False
        for btn in reversed(nav_path):
            pos, conf = self.matcher.match(screen_img, btn, threshold=0.8)
            if pos:
                logging.info(f"🧭 尋路中：在畫面中找到 [{btn}] (信心度: {conf:.4f})，點擊跳轉。")
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                clicked_any = True
                time.sleep(1.5) # 等待跳轉動畫
                break

        if not clicked_any:
            # 如果畫面上任何尋路按鈕都找不到了，代表我們已經跳轉進去
            logging.info("🧭 尋路按鈕已不在畫面上，判斷已成功抵達副本內部。")
            if self.config["type"] == "dungeon":
                self.transition_to(self.STATE_DUNGEON_EXPLORING)
            else:
                self.transition_to(self.STATE_LOBBY)

    def handle_battle(self, screen_img, rect):
        """
        戰鬥狀態處理：啟用自動戰鬥與監控戰鬥結算。
        """
        # A. 檢查是否需要啟動自動戰鬥 (auto.png)
        if os.path.exists(os.path.join("templates", "auto.png")) and (time.time() - self.last_auto_click_time > 3.0):
            pos_auto, conf_auto = self.matcher.match(screen_img, "auto.png", threshold=0.7)
            logging.info(f"🔍 檢查自動戰鬥按鈕... 最大相似度: {conf_auto:.4f} (閥值: 0.7)")
            if pos_auto:
                logging.info(f"👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！")
                self.mouse.click(rect["left"] + pos_auto[0], rect["top"] + pos_auto[1])
                self.last_auto_click_time = time.time()
                time.sleep(0.5)

        # B. 監控戰鬥結算
        if self.config["type"] == "stage":
            # 關卡模式：檢查 retry.png 與所有 continue*.png
            found_result_trigger = False
            for btn in self.config["result_buttons"]:
                pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
                if pos:
                    logging.info(f"🏆 偵測到結算按鈕 [{btn}]，戰鬥結束！")
                    found_result_trigger = True
                    break
            if found_result_trigger:
                self.transition_to(self.STATE_RESULT)
            else:
                self.log_battle_duration()
                time.sleep(1.0)
                
        elif self.config["type"] == "dungeon":
            # 地下城模式：檢查 dungeon_battle_results 結算按鈕 (排除 continue3.png)
            best_match_pos = None
            best_match_conf = 0.8
            best_match_temp = None
            
            for btn in self.config["dungeon_battle_results"]:
                pos, conf = self.matcher.match(screen_img, btn, threshold=best_match_conf)
                if pos and conf > best_match_conf:
                    best_match_conf = conf
                    best_match_pos = pos
                    best_match_temp = btn
                    
            if best_match_pos:
                logging.info(f"🏆 戰鬥結束！點擊相似度最高的地下城結算按鈕 [{best_match_temp}]，信心度: {best_match_conf:.4f}")
                self.mouse.click(rect["left"] + best_match_pos[0], rect["top"] + best_match_pos[1])
                # 點擊完結算後，會回到地下城層與層之間，轉移回探索狀態
                self.transition_to(self.STATE_DUNGEON_EXPLORING)
                time.sleep(1.5)
            else:
                self.log_battle_duration()
                time.sleep(1.0)

    def log_battle_duration(self):
        if self.battle_start_time:
            duration = time.time() - self.battle_start_time
            logging.info(f"⚔️ 戰鬥進行中... 已持續 {int(duration)} 秒")
        else:
            logging.info(f"⚔️ 戰鬥進行中...")

    def handle_stage_results(self, screen_img, rect):
        """
        [關卡專屬] 處理關卡多段結算點擊。
        """
        # A. 檢查「再戰」
        pos_retry, conf_retry = self.matcher.match(screen_img, "retry.png", threshold=0.8)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.transition_to(self.STATE_LOBBY)
            time.sleep(1.0)
            return

        # B. 比對並點選相似度最高的「繼續」按鈕
        best_match_pos = None
        best_match_conf = 0.8
        best_match_temp = None

        # 這裡會檢查所有的 continue 圖片 (包括 continue3.png)
        for c_temp in self.continue_templates:
            pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=best_match_conf)
            if pos_c and conf_c > best_match_conf:
                best_match_conf = conf_c
                best_match_pos = pos_c
                best_match_temp = c_temp

        if best_match_pos:
            logging.info(f"👉 點擊相似度最高的關卡「繼續」按鈕 ({best_match_temp})，信心度: {best_match_conf:.4f}")
            self.mouse.click(rect["left"] + best_match_pos[0], rect["top"] + best_match_pos[1])
            time.sleep(0.8)
            return

        # C. 檢查是否已經默默回到準備大廳
        lobby_btn = self.config["lobby_start_btn"]
        pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos_start:
            logging.info(f"👉 偵測到已回到大廳 ({lobby_btn})，將狀態轉回 LOBBY。")
            self.transition_to(self.STATE_LOBBY)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")
        time.sleep(0.3)

    def handle_dungeon_exploring(self, screen_img, rect):
        """
        [地下城專屬] 依照優先級掃描探險事件。
        """
        for btn_name in self.config["explore_priorities"]:
            # 檢查模板檔案是否存在
            if not os.path.exists(os.path.join("templates", btn_name)):
                continue
                
            pos, conf = self.matcher.match(screen_img, btn_name, threshold=0.8)
            if pos:
                if btn_name == "dungeons_complete.png":
                    logging.info(f"🎉 偵測到【地下城通關結束】({btn_name})，信心度: {conf:.4f}，點擊退出。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.run_count += 1
                    logging.info(f"📊 已完成第 {self.run_count} 次地下城通關！")
                    # 通關後回到最外層大廳，轉移至尋路導航狀態重新進副本
                    self.transition_to(self.STATE_NAVIGATING)
                    time.sleep(2.0)
                    
                elif btn_name == "dungeon_fight.png":
                    logging.info(f"⚔️ 偵測到【戰鬥房入口】({btn_name})，信心度: {conf:.4f}，點擊進入戰鬥。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    self.battle_start_time = time.time()
                    self.transition_to(self.STATE_BATTLE)
                    time.sleep(2.0)
                    
                else:
                    logging.info(f"👉 偵測到探險事件 [{btn_name}]，信心度: {conf:.4f}，點擊處理。")
                    self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                    time.sleep(0.8) # 點擊後等待短暫動畫
                    
                return # 成功處理一個優先級最高的事項後即結束該步，等待下一次截圖
                
        logging.info("⌛ 地下城探索中，正在等待下一層載入或新的隨機事件按鈕出現...")
        time.sleep(0.5)

    def detect_current_state(self, screen_img, rect):
        """
        全域掃描定位當前狀態。
        """
        logging.info("🔍 正在進行全域掃描以辨識遊戲狀態...")
        
        # 1. 檢查是否在普通關卡大廳
        if self.config["type"] == "stage":
            lobby_btn = self.config["lobby_start_btn"]
            pos, _ = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
            if pos:
                self.transition_to(self.STATE_LOBBY)
                return
                
        # 2. 檢查是否在大廳的尋路路徑上
        for btn in self.config.get("navigation_path", []):
            pos, _ = self.matcher.match(screen_img, btn, threshold=0.8)
            if pos:
                self.transition_to(self.STATE_NAVIGATING)
                return
                
        # 3. 檢查是否在地下城探險中
        if self.config["type"] == "dungeon":
            for btn_name in self.config["explore_priorities"]:
                # 如果看見任何探索或通關完成按鈕，說明處於探索狀態
                if btn_name in ["dungeons_complete.png", "gungeon_godown.png", "Treasure.png", "dungeon_bless.png"]:
                    pos, _ = self.matcher.match(screen_img, btn_name, threshold=0.8)
                    if pos:
                        self.transition_to(self.STATE_DUNGEON_EXPLORING)
                        return
                        
        # 4. 如果以上皆非，預設轉為戰鬥或尋路狀態
        if self.config["type"] == "dungeon":
            logging.info("❓ 未能辨識出特定探索按鈕，預設為 BATTLE 狀態。")
            self.transition_to(self.STATE_BATTLE)
        else:
            logging.info("❓ 未能辨識出大廳按鈕，預設為 BATTLE 狀態。")
            self.transition_to(self.STATE_BATTLE)
