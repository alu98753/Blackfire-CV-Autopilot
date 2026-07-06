import time
import logging
from states.handlers.base import BaseStateHandler

class ResultHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        [關卡專屬] 處理關卡多段結算點擊。
        """
        # A. 檢查「再戰」
        pos_retry, conf_retry = self.matcher.match(screen_img, "stages/retry.png", threshold=0.8)
        if pos_retry:
            logging.info("👉 點擊「再戰」！")
            self.mouse.click(rect["left"] + pos_retry[0], rect["top"] + pos_retry[1])
            self.machine.transition_to(self.machine.STATE_LOBBY)
            time.sleep(1.0)
            return

        # B. 比對並點選相似度最高的「繼續」按鈕
        best_match_pos = None
        best_match_conf = 0.8
        best_match_temp = None

        # 這裡會檢查所有的 continue 圖片 (包括 continue3.png)
        for c_temp in self.machine.continue_templates:
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
        lobby_btn = self.machine.config["lobby_start_btn"]
        pos_start, conf_start = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos_start:
            logging.info(f"👉 偵測到已回到大廳 ({lobby_btn})，將狀態轉回 LOBBY。")
            self.machine.transition_to(self.machine.STATE_LOBBY)
            return
            
        logging.info("⌛ 結算畫面的按鈕尚未出現或正在過場，維持結算狀態等待中...")
        time.sleep(0.3)
