import os
import time
import logging
from states.handlers.base import BaseStateHandler

class BreadCollectionHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        自動領體力狀態處理器。
        """
        # A. 如果體力視窗已開啟 (看到 quit.png 或 bread_window_opened)
        if self.machine.bread_window_opened:
            # 情況一：如果已經確認領過體力（或體力已滿確認了），我們只專心尋找退出按鈕，不要重複按領取或體力按鈕
            if self.machine.bread_collected_this_run:
                # 關閉體力視窗按鈕 (quit bread)
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
                if pos_quit:
                    logging.info(f"🍞 領體力：偵測到退出體力按鈕 [{conf_quit:.4f}]，點擊關閉，領取體力流程結束。")
                    self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                    self.machine.need_bread_collection = False
                    self.machine.bread_collected_this_run = False  # 重設狀態
                    self.machine.bread_window_opened = False       # 重設視窗開啟狀態
                    self.machine.bread_click_attempted = False      # 重設狀態
                    self.machine.last_bread_collection_time = time.time()
                    time.sleep(0.03)
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return
            else:
                # 情況二：尚未領取或尚未點擊確認，正常進行領取步驟
                # 1. 彈窗內的確認按鈕 (獲得體力確認或體力已滿提示確認)
                pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
                if pos_conf:
                    logging.info(f"🍞 領體力：偵測到體力確認按鈕 [{conf_conf:.4f}]，點擊確認。")
                    self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 2. 彈窗內的 OK 按鈕 (同樣代表確認)
                pos_ok, conf_ok = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
                if pos_ok:
                    logging.info(f"🍞 領體力：偵測到體力 OK 按鈕 [{conf_ok:.4f}]，點擊 OK。")
                    self.mouse.click(rect["left"] + pos_ok[0], rect["top"] + pos_ok[1])
                    self.machine.bread_collected_this_run = True  # 標記本次已確認領取
                    time.sleep(0.03)
                    return

                # 3. 領體力按鈕 (嘗試匹配通用 collect.png 或專屬 bread_collection.png，使用 0.70 的容錯閥值)
                pos_coll = None
                conf_coll = 0.0
                matched_template = None
                
                for template_name in ["common/collect.png", "common/bread_collection.png"]:
                    if os.path.exists(os.path.join("templates", template_name)):
                        pos, conf = self.matcher.match(screen_img, template_name, threshold=0.70)
                        if pos:
                            pos_coll = pos
                            conf_coll = conf
                            matched_template = template_name
                            break
                            
                if pos_coll:
                    logging.info(f"🍞 領體力：偵測到領體力按鈕 [{matched_template}] (信心度: {conf_coll:.4f})，進行點擊領取。")
                    self.mouse.click(rect["left"] + pos_coll[0], rect["top"] + pos_coll[1])
                    self.machine.bread_click_attempted = True
                    time.sleep(0.03)
                    return

                # 防禦性相對座標點擊：
                # 如果體力視窗已開啟 (看到 quit.png)，但沒偵測到「收集」按鈕，
                # 且我們在本次流程中「尚未點擊過領取」，則使用相對 quit.png 的座標執行一次點擊 (收集食物)。
                pos_quit, conf_quit = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
                if pos_quit:
                    if not getattr(self.machine, "bread_click_attempted", False):
                        # 關閉按鈕匹配中心為 (X, Y)，「收集食物」按鈕相對於 X 的偏移為 dx=-208, dy=612
                        click_x = rect["left"] + pos_quit[0] - 208
                        click_y = rect["top"] + pos_quit[1] + 612
                        logging.warning(f"⚠️ 領體力：未匹配到領體力按鈕，執行相對座標防禦性點擊 (收集食物): ({click_x}, {click_y})")
                        self.mouse.click(click_x, click_y)
                        self.machine.bread_click_attempted = True
                        time.sleep(0.1)
                        return
                    else:
                        # 如果已經嘗試點擊過領取 (不論是匹配還是相對點擊)，但畫面上依然沒有確認彈窗，說明確實處於冷卻或已領完，此時點點退出關閉視窗
                        logging.info(f"🍞 領體力：已嘗試過點擊領取但無效，判定為冷卻或已領完，點擊退出體力按鈕 [{conf_quit:.4f}] 退出。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.need_bread_collection = False
                        self.machine.bread_collected_this_run = False
                        self.machine.bread_click_attempted = False  # 重置標記
                        self.machine.bread_window_opened = False    # 重置視窗開啟狀態
                        self.machine.last_bread_collection_time = time.time()
                        time.sleep(0.03)
                        self.machine.transition_to(self.machine.STATE_NAVIGATING)
                        return
        else:
            # B. 情況三：尚未開啟體力彈窗，尋找並點選大廳中的入口按鈕打開它
            # 5. 打開體力視窗按鈕 (bread)
            pos_bread, conf_bread = self.matcher.match(screen_img, "common/bread.png", threshold=0.8)
            if pos_bread:
                logging.info(f"🍞 領體力：在大廳偵測到體力按鈕 [{conf_bread:.4f}]，點擊打開體力視窗。")
                self.mouse.click(rect["left"] + pos_bread[0], rect["top"] + pos_bread[1])
                self.machine.bread_window_opened = True  # 標記體力視窗已開啟
                time.sleep(0.03)
                return

            logging.info("⌛ 領體力狀態中，正在等待體力畫面或入口載入...")
            time.sleep(0.01)
