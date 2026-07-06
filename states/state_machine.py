import time
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class GameStateMachine:
    # 定義遊戲狀態
    STATE_UNKNOWN = "UNKNOWN"
    STATE_LOBBY = "LOBBY"          # 準備大廳/副本準備頁面，尋找「開始」按鈕
    STATE_BATTLE = "BATTLE"        # 戰鬥進行中，監控結算畫面，可自動點擊「自動戰鬥」
    STATE_RESULT = "RESULT"        # 戰鬥結束結算，尋找「繼續」或「再戰」按鈕
    
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
        
        # 動態尋找與快取所有的 continue*.png 模板
        self.continue_templates = self._discover_continue_templates()

    def _discover_continue_templates(self):
        """
        掃描 templates 目錄，尋找符合 continue*.png 的所有模板檔名。
        """
        templates = []
        templates_dir = "templates"
        if os.path.exists(templates_dir):
            for f in os.listdir(templates_dir):
                if f.startswith("continue") and f.endswith(".png"):
                    templates.append(f)
        # 照檔名排序以確保匹配順序一致 (例如 continue1.png -> continue2.png)
        templates.sort()
        logging.info(f"🔍 偵測到之「繼續」按鈕模板清單: {templates}")
        return templates

    def transition_to(self, new_state):
        if self.current_state != new_state:
            logging.info(f"🔄 狀態轉移: {self.current_state} -> {new_state}")
            self.current_state = new_state
            self.last_state_change = time.time()
            if new_state == self.STATE_BATTLE:
                # 進入戰鬥狀態時，重設上次點選自動戰鬥的時間
                self.last_auto_click_time = 0

    def step(self):
        """
        執行單步狀態檢索與決策。
        """
        # 1. 取得遊戲視窗邊界與擷取畫面
        rect = self.capturer.get_window_rect()
        if rect is None:
            logging.warning("⚠️ 找不到遊戲視窗，請確認遊戲未縮小且視窗名稱為 'Blackfire Crusade'")
            time.sleep(2)
            return
            
        screen_img = self.capturer.capture(rect)
        if screen_img is None:
            logging.warning("⚠️ 無法擷取畫面")
            time.sleep(1)
            return

        # 2. 依據目前狀態執行決策
        if self.current_state == self.STATE_UNKNOWN:
            # 初始未知狀態下，掃描所有可能的模板來定位當前位置
            self.detect_current_state(screen_img, rect)
            
        elif self.current_state == self.STATE_LOBBY:
            # 大廳狀態下：尋找「開始」按鈕 (start.png)
            pos, conf = self.matcher.match(screen_img, "start.png", threshold=0.8)
            if pos:
                logging.info(f"👉 偵測到「開始」按鈕，信心度: {conf:.4f}。進行點擊。")
                # 點擊按鈕
                self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
                self.run_count += 1
                logging.info(f"🚀 開始第 {self.run_count} 次戰鬥！")
                self.battle_start_time = time.time()
                
                # 進入新的一場戰鬥，重設自動戰鬥狀態時間
                self.last_auto_click_time = 0
                
                # 轉移到戰鬥狀態，並等待進入動畫 (例如等待 2 秒)
                self.transition_to(self.STATE_BATTLE)
                time.sleep(2.0)
            else:
                # 也可能是已經直接在戰鬥中或結算畫面
                self.detect_current_state(screen_img, rect)

        elif self.current_state == self.STATE_BATTLE:
            # 戰鬥狀態下：
            # A. 檢查是否需要啟動自動戰鬥 (auto.png)
            # 使用 3.0 秒的冷卻時間防止重複快速點擊（避免動畫延遲導致點完又關閉），若點擊失敗會自動重試
            if os.path.exists(os.path.join("templates", "auto.png")) and (time.time() - self.last_auto_click_time > 3.0):
                pos_auto, conf_auto = self.matcher.match(screen_img, "auto.png", threshold=0.7)
                logging.info(f"🔍 檢查自動戰鬥按鈕... 最大相似度: {conf_auto:.4f} (閥值: 0.7)")
                if pos_auto:
                    logging.info(f"👉 偵測到「自動戰鬥」按鈕（目前為未啟用狀態），進行點擊啟用！")
                    self.mouse.click(rect["left"] + pos_auto[0], rect["top"] + pos_auto[1])
                    self.last_auto_click_time = time.time()
                    time.sleep(0.5)

            # B. 持續監控是否出現結算按鈕 (retry.png 或任何 continue*.png)
            found_result_trigger = False
            
            # 檢查「再戰/再次挑戰」
            pos_retry, _ = self.matcher.match(screen_img, "retry.png", threshold=0.8)
            if pos_retry:
                logging.info(f"🏆 偵測到「再戰」按鈕，戰鬥結束！")
                found_result_trigger = True
                
            # 檢查所有的「繼續」按鈕
            if not found_result_trigger:
                for c_temp in self.continue_templates:
                    pos_c, _ = self.matcher.match(screen_img, c_temp, threshold=0.8)
                    if pos_c:
                        logging.info(f"🏆 偵測到『繼續』按鈕 ({c_temp})，戰鬥結束！")
                        found_result_trigger = True
                        break
            
            if found_result_trigger:
                self.transition_to(self.STATE_RESULT)
            else:
                # 計算戰鬥持續時間
                if self.battle_start_time:
                    duration = time.time() - self.battle_start_time
                    logging.info(f"⚔️ 戰鬥進行中... 已持續 {int(duration)} 秒")
                else:
                    logging.info(f"⚔️ 戰鬥進行中...")
                time.sleep(2)

        elif self.current_state == self.STATE_RESULT:
            # 結算狀態下：
            # A. 先找「再戰」 (retry.png) 如果有就直接重開一場
            pos_retry, conf_retry = self.matcher.match(screen_img, "retry.png", threshold=0.8)
            if pos_retry:
                logging.info("👉 點擊「再戰」！")
                self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
                # 回到大廳狀態，準備下一場
                self.transition_to(self.STATE_LOBBY)
                time.sleep(1.0)
                return

            # B. 依序檢查所有發現的「繼續」按鈕 (continue1.png, continue2.png, 等)
            # 尋找「相似度最高」的按鈕，以避免點擊到背景中變暗的舊按鈕 (如 continue1.png)
            best_match_pos = None
            best_match_conf = 0.8  # 最低門檻
            best_match_temp = None

            for c_temp in self.continue_templates:
                pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=best_match_conf)
                if pos_c and conf_c > best_match_conf:
                    best_match_conf = conf_c
                    best_match_pos = pos_c
                    best_match_temp = c_temp

            if best_match_pos:
                logging.info(f"👉 點擊相似度最高的「繼續」按鈕 ({best_match_temp})，信心度: {best_match_conf:.4f}，座標: {best_match_pos}")
                self.mouse.click(rect["left"] + best_match_pos[0], rect["top"] + best_match_pos[1])
                time.sleep(0.8)  # 等待過場動畫
                return

            # C. 檢查是否已經默默回到準備大廳 (看到 start.png)
            pos_start, conf_start = self.matcher.match(screen_img, "start.png", threshold=0.8)
            if pos_start:
                logging.info("👉 偵測到已回到大廳 (start.png)，將狀態轉回 LOBBY。")
                self.transition_to(self.STATE_LOBBY)
                return
                
            # D. 若都沒找到，說明可能還在過場動畫中，維持 RESULT 狀態並等待
            logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")
            time.sleep(0.3)

    def detect_current_state(self, screen_img, rect):
        """
        全域掃描，用以確定或重置當前狀態。
        """
        logging.info("🔍 正在掃描畫面以辨識遊戲狀態...")
        
        # 1. 是否在 Lobby (有開始按鈕)
        pos, conf = self.matcher.match(screen_img, "start.png", threshold=0.8)
        if pos:
            self.transition_to(self.STATE_LOBBY)
            return
            
        # 2. 是否在結算頁面 (有再戰)
        pos_retry, _ = self.matcher.match(screen_img, "retry.png", threshold=0.8)
        if pos_retry:
            self.transition_to(self.STATE_RESULT)
            return
            
        # 3. 是否有任何一個繼續按鈕
        for c_temp in self.continue_templates:
            pos_c, _ = self.matcher.match(screen_img, c_temp, threshold=0.8)
            if pos_c:
                self.transition_to(self.STATE_RESULT)
                return
            
        # 4. 如果都不是，假設在戰鬥中
        logging.info("❓ 未能辨識出特定狀態按鈕，暫定為 BATTLE 狀態。")
        self.transition_to(self.STATE_BATTLE)
