import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def __init__(self, machine):
        super().__init__(machine)
        self.no_match_count = 0

    def handle(self, screen_img, rect):
        matched = self._handle_impl(screen_img, rect)
        if matched:
            self.no_match_count = 0
            return
            
        # 如果走到了這裡，說明本輪沒有匹配到任何東西
        self.no_match_count += 1
        if self.no_match_count >= 5:
            logging.warning("⚠️ 結算畫面連續 5 次未偵測到任何結算按鈕，判定可能已退出或跳轉，重設狀態為 UNKNOWN 進行重新定位。")
            self.no_match_count = 0
            self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")
        time.sleep(0.05)

    def _handle_impl(self, screen_img, rect):
        """
        處理結算點擊。若成功點擊任何按鈕，回傳 True；否則回傳 False。
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
                            return True

        # A2. 檢查離開戰鬥/結算退出按鈕 (在背包滿需要清理，或領取時間到了需要去領體力/鑽石時，退出戰鬥回大廳)
        should_exit_battle = (
            self.machine.need_bag_cleaning or 
            self.machine.need_diamond_collection or 
            (self.machine.enable_bread and self.machine.need_bread_collection)
        )
        if should_exit_battle:
            if os.path.exists(os.path.join("templates", "exit_battle.png")):
                pos_exit, conf_exit = self.matcher.match(screen_img, "exit_battle.png", threshold=0.8)
                if pos_exit:
                    logging.info(f"👉 偵測到離開戰鬥按鈕 [{conf_exit:.4f}]，點擊退出結算以返回大廳執行清理/領取任務。")
                    self.mouse.click(rect["left"] + pos_exit[0], rect["top"] + pos_exit[1])
                    time.sleep(0.1)
                    return True

        # A2. 檢查結算通用確認彈窗 (例如關卡結算確認)
        pos_conf, conf_conf = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_conf:
            logging.info(f"👉 偵測到結算通用確認按鈕，進行點擊。信心度: {conf_conf:.4f}")
            self.mouse.click(rect["left"] + pos_conf[0], rect["top"] + pos_conf[1])
            time.sleep(0.1)
            return True

        # A3. 檢查「再戰」
        pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.machine.run_count += 1
            logging.info(f"🚀 開始第 {self.machine.run_count} 次關卡戰鬥！(透過再戰)")
            self.machine.transition_to(self.machine.STATE_BATTLE)
            time.sleep(0.1)
            return True

        # B. 檢查「繼續」按鈕
        c_temp = self.machine.continue_template
        if os.path.exists(os.path.join("templates", c_temp)):
            pos_c, conf_c = self.matcher.match(screen_img, c_temp, threshold=0.8)
            if pos_c:
                logging.info(f"👉 偵測到「繼續」按鈕 ({c_temp}) (信心度: {conf_c:.4f})，進行點擊。")
                self.mouse.click(rect["left"] + pos_c[0], rect["top"] + pos_c[1])
                time.sleep(0.1)
                return True

        # C. 檢查是否已經默默回到準備大廳
        lobby_btn = self.machine.config["lobby_start_btn"]
        pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos_start:
            logging.info(f"👉 偵測到已回到大廳 ({lobby_btn})，將狀態轉回 LOBBY。")
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return True
            
        return False
