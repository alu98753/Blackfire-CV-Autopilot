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
            # 情況一：如果已經點過免費鑽石並確認了，我們尋找退出按鈕關閉彈窗
            if self.machine.diamond_collected_this_run:
                for quit_btn in ["common/quit.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            logging.info(f"💎 領鑽石：偵測到退出按鈕 [{quit_btn}] ({conf_quit:.4f})，點擊關閉，領鑽石流程結束。")
                            self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                            self.machine.need_diamond_collection = False
                            self.machine.diamond_collected_this_run = False
                            self.machine.diamond_window_opened = False  # 重置視窗開啟狀態
                            self.machine.last_diamond_collection_time = time.time()
                            time.sleep(1.0)  # 增加延遲，確保視窗完全關閉
                            self.machine.transition_to(self.machine.STATE_NAVIGATING)
                            return
            else:
                # 情況二：尚未領取或確認，進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得鑽石確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"💎 領鑽石：偵測到確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return
                
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"💎 領鑽石：偵測到 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.diamond_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 檢查是否在領鑽石彈窗內 (尋找退出/關閉按鈕)
                in_diamond_window = False
                active_quit_btn = None
                quit_pos = None
                for quit_btn in ["common/quit.png"]:
                    if os.path.exists(os.path.join("templates", quit_btn)):
                        pos_quit, conf_quit = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                        if pos_quit:
                            in_diamond_window = True
                            active_quit_btn = quit_btn
                            quit_pos = pos_quit
                            break

                if in_diamond_window and quit_pos:
                    # 2. 如果在彈窗內，只嘗試領取免費鑽石 (diamond_free.png)
                    # 使用較高閥值 (0.90) 以避免誤判到付費的 $4.99 按鈕
                    if os.path.exists(os.path.join("templates", "free.png")):
                        pos_free, conf_free = self.matcher.match(screen_img, "free.png", threshold=0.90)
                        if pos_free:
                            logging.info(f"💎 領鑽石：在視窗內偵測到免費鑽石按鈕 [{conf_free:.4f}]，點擊領取。")
                            self.mouse.click(rect["left"] + pos_free[0], rect["top"] + pos_free[1])
                            time.sleep(0.03)
                            return

                    # 3. 如果在彈窗內但沒有免費鑽石按鈕，說明鑽石正處於冷卻，點點退出按鈕關閉
                    logging.info(f"💎 領鑽石：鑽石視窗已開啟但無免費按鈕 (處於冷卻)，點擊退出按鈕 [{active_quit_btn}] 退出。")
                    self.mouse.click(rect["left"] + quit_pos[0], rect["top"] + quit_pos[1])
                    self.machine.need_diamond_collection = False
                    self.machine.diamond_collected_this_run = False
                    self.machine.diamond_window_opened = False
                    self.machine.last_diamond_collection_time = time.time()
                    time.sleep(1.0)  # 增加延遲，確保視窗完全關閉
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return
        else:
            # B. 情況三：尚未開啟鑽石彈窗，尋找並點選城鎮中的鑽石入口
            if os.path.exists(os.path.join("templates", "diamond.png")):
                pos_dia, conf_dia = self.matcher.match(screen_img, "diamond.png", threshold=0.50)
                if pos_dia and conf_dia >= 0.65:
                    logging.info(f"💎 領鑽石：在畫面偵測到鑽石按鈕 [{conf_dia:.4f}]，點擊打開領取畫面。")
                    self.mouse.click(rect["left"] + pos_dia[0], rect["top"] + pos_dia[1])
                    self.machine.diamond_window_opened = True
                    time.sleep(0.03)
                    return

            logging.info("⌛ 領鑽石狀態中，正在等待鑽石畫面或入口載入...")
            time.sleep(0.01)
