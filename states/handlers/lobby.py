import time
import logging
from states.handlers.base import BaseStateHandler

class LobbyHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        普通關卡大廳狀態下的開始按鈕點擊處理。
        """
        lobby_btn = self.machine.config["lobby_start_btn"]
        pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos:
            logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊。")
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.machine.run_count += 1
            logging.info(f"🚀 開始第 {self.machine.run_count} 次關卡戰鬥！")
            self.machine.battle_start_time = time.time()
            self.machine.transition_to(self.machine.STATE_BATTLE)
            time.sleep(2.0) # 等待戰鬥載入
        else:
            self.machine.detect_current_state(screen_img, rect)
