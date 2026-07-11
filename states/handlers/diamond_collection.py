import os
import time
import logging
from states.handlers.base import BaseStateHandler

class DiamondCollectionHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        自動領鑽石狀態處理器。
        """
        # A. 如果鑽石視窗已開啟 (看到 quit.png 或 diamond_window_opened)
        if self.machine.diamond_window_opened:
            # 偵測退出按鈕是否還在
            pos_quit = None
            conf_quit = 0.0
            for quit_btn in ["common/quit.png"]:
                if os.path.exists(os.path.join("templates", quit_btn)):
                    pos, conf = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                    if pos:
                        pos_quit = pos
                        conf_quit = conf
                        self.machine.diamond_window_missing_count = 0  # 成功看到元素，重置缺失計數
                        break

            # 1. 彈窗內的確認按鈕 (獲得鑽石確認) - 僅在已點擊過免費按鈕後才執行
            if getattr(self.machine, "diamond_free_clicked", False):
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"💎 領鑽石：偵測到確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    self.machine.diamond_window_missing_count = 0  # 成功看到元素，重置缺失計數
                    time.sleep(0.03)
                    return
                
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"💎 領鑽石：偵測到 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    self.machine.diamond_window_missing_count = 0  # 成功看到元素，重置缺失計數
                    time.sleep(0.03)
                    return

            # 判斷是否需要退出 (已領取確認，或者無免費按鈕判定為冷卻)
            if not self.machine.diamond_collected_this_run and not getattr(self.machine, "diamond_cooldown_detected", False):
                pos_free = None
                if os.path.exists(os.path.join("templates", "free.png")):
                    pos_free, conf_free = self.matcher.match(screen_img, "free.png", threshold=0.90)
                    if pos_free:
                        self.machine.diamond_window_missing_count = 0  # 成功看到元素，重置缺失計數
                if not pos_free and pos_quit:
                    cooldown_count = getattr(self.machine, "diamond_cooldown_confirm_count", 0) + 1
                    self.machine.diamond_cooldown_confirm_count = cooldown_count
                    logging.info(f"💎 領鑽石：無免費按鈕，累計檢測次數: {cooldown_count}/3...")
                    if cooldown_count >= 3:
                        logging.info("💎 領鑽石：鑽石視窗已開啟且連續 3 幀無免費按鈕 (處於冷卻)，標記冷卻並準備退出。")
                        self.machine.diamond_cooldown_detected = True
                else:
                    self.machine.diamond_cooldown_confirm_count = 0

            if self.machine.diamond_collected_this_run or getattr(self.machine, "diamond_cooldown_detected", False):
                if pos_quit:
                    # 限制點擊退出按鈕的頻率 (1秒一次)，確保穩定性並給予過渡動畫時間
                    now = time.time()
                    last_click = getattr(self.machine, "last_diamond_quit_click_time", 0.0)
                    if now - last_click > 1.0:
                        logging.info(f"💎 領鑽石：偵測到退出按鈕 [common/quit.png] ({conf_quit:.4f})，嘗試點擊關閉視窗。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.last_diamond_quit_click_time = now
                    else:
                        logging.info("💎 領鑽石：已點擊退出，正在等待視窗完全關閉...")
                    time.sleep(0.1)
                    return
                else:
                    # 退出按鈕已經不在畫面上，說明視窗成功關閉！
                    logging.info("💎 領鑽石：退出按鈕已消失，確認視窗已關閉。領鑽石流程結束。")
                    self.machine.need_diamond_collection = False
                    self.machine.diamond_collected_this_run = False
                    self.machine.diamond_cooldown_detected = False
                    self.machine.diamond_window_opened = False
                    self.machine.diamond_free_clicked = False
                    self.machine.diamond_cooldown_confirm_count = 0
                    self.machine.diamond_window_missing_count = 0
                    self.machine.last_diamond_collection_time = time.time()
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return
 
            # 情況二：尚未領取且無冷卻，點擊免費鑽石
            if os.path.exists(os.path.join("templates", "free.png")):
                pos_free, conf_free = self.matcher.match(screen_img, "free.png", threshold=0.90)
                if pos_free:
                    logging.info(f"💎 領鑽石：在視窗內偵測到免費鑽石按鈕 [{conf_free:.4f}]，點擊領取。")
                    self.mouse.click(rect["left"] + pos_free[0], rect["top"] + pos_free[1])
                    self.machine.diamond_free_clicked = True
                    self.machine.diamond_window_missing_count = 0  # 成功看到元素，重置缺失計數
                    time.sleep(0.03)
                    return

            # 自癒防禦：若走到這一步，代表鑽石開啟狀態為 True，但畫面上找不到任何相關彈窗元素 (confirm/ok/quit/free)
            missing_count = getattr(self.machine, "diamond_window_missing_count", 0) + 1
            self.machine.diamond_window_missing_count = missing_count
            logging.info(f"💎 領鑽石：未偵測到任何彈窗內元素，累計未發現次數: {missing_count}/3...")
            if missing_count >= 3:
                logging.warning("⚠️ 領鑽石：連續 3 幀未偵測到任何視窗元素，判定鑽石視窗已關閉或打開失敗。重置開啟狀態...")
                self.machine.diamond_window_opened = False
                self.machine.diamond_window_missing_count = 0
                self.machine.diamond_free_clicked = False
            return
        else:
            # B. 情況三：尚未開啟鑽石彈窗，尋找並點選城鎮中的鑽石入口
            if os.path.exists(os.path.join("templates", "diamond.png")):
                pos_dia, conf_dia = self.matcher.match(screen_img, "diamond.png", threshold=0.50)
                if pos_dia and conf_dia >= 0.65:
                    logging.info(f"💎 領鑽石：在畫面偵測到鑽石按鈕 [{conf_dia:.4f}]，點擊打開領取畫面。")
                    self.mouse.click(rect["left"] + pos_dia[0], rect["top"] + pos_dia[1])
                    self.machine.diamond_window_opened = True
                    time.sleep(1.0)
                    return

            logging.info("⌛ 領鑽石狀態中，正在等待鑽石畫面或入口載入...")
            time.sleep(0.01)
