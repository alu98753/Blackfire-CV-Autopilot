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

            # 偵測退出按鈕是否還在
            pos_quit = None
            conf_quit = 0.0
            for quit_btn in ["common/quit.png"]:
                if os.path.exists(os.path.join("templates", quit_btn)):
                    pos, conf = self.matcher.match(screen_img, quit_btn, threshold=0.8)
                    if pos:
                        pos_quit = pos
                        conf_quit = conf
                        break

            # 判斷是否需要退出 (已領取確認，或者判定為冷卻/已領完)
            if not self.machine.bread_collected_this_run and not getattr(self.machine, "bread_cooldown_detected", False):
                # 檢查是否有收集按鈕
                pos_coll = None
                for template_name in ["common/collect.png", "common/bread_collection.png"]:
                    if os.path.exists(os.path.join("templates", template_name)):
                        pos, conf = self.matcher.match(screen_img, template_name, threshold=0.70)
                        if pos:
                            pos_coll = pos
                            break
                # 如果沒有收集按鈕且我們已經嘗試過點擊，判定為冷卻/已領取，此時需要退出
                if not pos_coll and getattr(self.machine, "bread_click_attempted", False) and pos_quit:
                    logging.info("🍞 領體力：無收集按鈕且已嘗試領取，標記冷卻並準備退出。")
                    self.machine.bread_cooldown_detected = True

            if self.machine.bread_collected_this_run or getattr(self.machine, "bread_cooldown_detected", False):
                if pos_quit:
                    # 限制點擊退出按鈕的頻率
                    now = time.time()
                    last_click = getattr(self.machine, "last_bread_quit_click_time", 0.0)
                    if now - last_click > 1.0:
                        logging.info(f"🍞 領體力：偵測到退出體力按鈕 [common/quit.png] ({conf_quit:.4f})，嘗試點擊關閉視窗。")
                        self.mouse.click(rect["left"] + pos_quit[0], rect["top"] + pos_quit[1])
                        self.machine.last_bread_quit_click_time = now
                    else:
                        logging.info("🍞 領體力：已點擊退出，正在等待視窗完全關閉...")
                    time.sleep(0.1)
                    return
                else:
                    # 退出按鈕已經不在畫面上，說明視窗成功關閉！
                    logging.info("🍞 領體力：退出按鈕已消失，確認視窗已關閉。領取體力流程結束。")
                    self.machine.need_bread_collection = False
                    self.machine.bread_collected_this_run = False
                    self.machine.bread_cooldown_detected = False
                    self.machine.bread_window_opened = False
                    self.machine.bread_click_attempted = False
                    self.machine.last_bread_collection_time = time.time()
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                    return

            # 情況二：尚未領取且未冷卻，嘗試領取
            # 3. 領體力按鈕 (不依賴 pos_quit 即可執行比對)
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

            # 防禦性相對座標點擊 (依賴 pos_quit 存在)
            if pos_quit and not getattr(self.machine, "bread_click_attempted", False):
                click_x = rect["left"] + pos_quit[0] - 208
                click_y = rect["top"] + pos_quit[1] + 612
                logging.warning(f"⚠️ 領體力：未匹配到領體力按鈕，執行相對座標防禦性點擊 (收集食物): ({click_x}, {click_y})")
                self.mouse.click(click_x, click_y)
                self.machine.bread_click_attempted = True
                time.sleep(0.1)
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
