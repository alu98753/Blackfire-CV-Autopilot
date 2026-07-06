import time
import logging
from states.handlers.base import BaseStateHandler

class LobbyHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        普通關卡大廳狀態下的開始按鈕點擊處理。
        """
        # 如果背包滿了，優先轉移至 BAG_CLEANING 狀態進行清理，暫不開啟戰鬥
        if self.machine.need_bag_cleaning:
            logging.info("🎒 大廳：偵測到需要清理背包，優先轉移至 BAG_CLEANING 狀態。")
            self.machine.transition_to(self.machine.STATE_BAG_CLEANING)
            return

        # 如果需要領鑽石或體力，優先轉移至 NAVIGATING 狀態進行領取
        if self.machine.need_diamond_collection or (self.machine.enable_bread and self.machine.need_bread_collection):
            logging.info("💎/🍞 大廳：偵測到需要領取鑽石或體力，優先轉移至 NAVIGATING 狀態。")
            self.machine.transition_to(self.machine.STATE_NAVIGATING)
            return

        lobby_btn = self.machine.config["lobby_start_btn"]
        pos, conf = self.matcher.match(screen_img, lobby_btn, threshold=0.8)
        if pos:
            logging.info(f"👉 偵測到大廳開始按鈕 [{lobby_btn}] (信心度: {conf:.4f})，進行點擊。")
            self.mouse.click(rect["left"] + pos[0], rect["top"] + pos[1])
            self.machine.run_count += 1
            logging.info(f"🚀 開始第 {self.machine.run_count} 次關卡戰鬥！")
            self.machine.battle_start_time = time.time()
            self.machine.transition_to(self.machine.STATE_BATTLE)
            time.sleep(0.3) # 等待戰鬥載入
        else:
            self.machine.detect_current_state(screen_img, rect)
