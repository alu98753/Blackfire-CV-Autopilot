import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        [關卡專屬] 處理關卡多段結算點擊。
        """
        # A1. 檢查是否背包已滿 (需要同時看見 backpack_full.png 且能匹配到關閉按鈕)
        if os.path.exists(os.path.join("templates", "backpack_full.png")):
            pos_full, conf_full = self.matcher.match(screen_img, "backpack_full.png", threshold=0.7)
            if pos_full:
                # 尋找退出按鈕進行點擊
                for q_btn in ["common/quit.png"]:
                    if os.path.exists(os.path.join("templates", q_btn)):
                        pos_bag, conf_bag = self.matcher.match(screen_img, q_btn, threshold=0.8)
                        if pos_bag:
                            logging.warning(f"🧭 偵測到「背包已滿」！出現 'backpack_full.png'，點擊退出按鈕 [{q_btn}]。")
                            self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                            self.machine.need_bag_cleaning = True  # 標記需要清理背包
                            time.sleep(0.1)
                            return

        # A2. 檢查離開戰鬥/結算退出按鈕
        if os.path.exists(os.path.join("templates", "exit_battle.png")):
            pos_exit, conf_exit = self.matcher.match(screen_img, "exit_battle.png", threshold=0.8)
            if pos_exit:
                logging.info(f"👉 偵測到離開戰鬥按鈕 [{conf_exit:.4f}]，點擊退出結算。")
                self.mouse.click(rect["left"] + pos_exit[0], rect["top"] + pos_exit[1])
                time.sleep(0.1)
                return

        # A2. 檢查結算通用確認彈窗 (例如關卡結算確認)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"👉 偵測到結算通用確認按鈕，進行點擊。信心度: {conf_conf:.4f}")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            time.sleep(0.1)
            return

        # A3. 檢查「再戰」
        pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.machine.transition_to(self.machine.STATE_LOBBY)
            time.sleep(0.1)
            return

        # B. 依照優先級由高到低 (continue3 -> continue2 -> continue1) 檢查繼續按鈕
        # 只要高優先級的比對成功 (>= 0.8)，就直接點擊並結束，避免背景低優先級按鈕的干擾
        for c_temp in reversed(self.machine.continue_templates):
            pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.8)
            if pos_c:
                logging.info(f"👉 點擊優先級最高的關卡「繼續」按鈕 ({c_temp})，信心度: {conf_c:.4f}")
                self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                time.sleep(0.1)
                return

        # C. 檢查是否已經默默回到準備大廳
        lobby_btn = self.machine.config["lobby_start_btn"]
        pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos_start:
            logging.info(f"👉 偵測到已回到大廳 ({lobby_btn})，將狀態轉回 LOBBY。")
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")
        time.sleep(0.05)
