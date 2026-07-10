import os
import time
import logging
from states.handlers.base import BaseStateHandler

class CollectOnlyHandler(BaseStateHandler):
    def handle(self, screen_img, rect):
        """
        定時領取模式的狀態處理器：
        - 檢查是否需要領取鑽石或體力。
        - 如果需要領取鑽石，在城鎮則進入領取；在大廳則點擊返回城鎮。
        - 如果需要領取體力，在大廳則進入領取；在城鎮則點擊門進入大廳。
        - 如果目前無領取任務，在大廳則自動返回城鎮，在城鎮則維持原地待機。
        """
        # 1. 取得當前位置狀態
        is_town = False
        is_lobby = False
        
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.8)
        pos_diamond, _ = self.matcher.match(screen_img, "diamond.png", threshold=0.8)
        if pos_door or pos_diamond:
            is_town = True
            
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        pos_bread_btn, _ = self.matcher.match(screen_img, "common/bread.png", threshold=0.8)
        if pos_goback or pos_bread_btn:
            is_lobby = True

        # 2. 領鑽石優先流程
        if self.machine.need_diamond_collection:
            if is_town:
                logging.info("💎 定時領取：在城鎮畫面，跳轉至 DIAMOND_COLLECTION。")
                self.machine.transition_to(self.machine.STATE_DIAMOND_COLLECTION)
                self.machine.handlers[self.machine.STATE_DIAMOND_COLLECTION].handle(screen_img, rect)
                return
            elif is_lobby:
                if pos_goback:
                    logging.info("💎 定時領取：在大廳畫面，點擊返回城鎮按鈕 [goback_town.png] 以便領取鑽石。")
                    self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                    time.sleep(0.5)
                    return
            # 輔助：如果畫面上已經有鑽石圖標，直接跳轉
            if pos_diamond:
                self.machine.transition_to(self.machine.STATE_DIAMOND_COLLECTION)
                self.machine.handlers[self.machine.STATE_DIAMOND_COLLECTION].handle(screen_img, rect)
                return

        # 3. 領體力流程
        elif self.machine.enable_bread and self.machine.need_bread_collection:
            if is_lobby:
                logging.info("🍞 定時領取：在大廳畫面，跳轉至 BREAD_COLLECTION。")
                self.machine.transition_to(self.machine.STATE_BREAD_COLLECTION)
                self.machine.handlers[self.machine.STATE_BREAD_COLLECTION].handle(screen_img, rect)
                return
            elif is_town:
                if pos_door:
                    logging.info("🍞 定時領取：在城鎮畫面，點擊入口 [common/door.png] 進入大廳以領取體力。")
                    self.mouse.click(rect["left"] + pos_door[0], rect["top"] + pos_door[1])
                    time.sleep(0.5)
                    return
            # 輔助：如果畫面上已經有體力圖標，直接跳轉
            if pos_bread_btn:
                self.machine.transition_to(self.machine.STATE_BREAD_COLLECTION)
                self.machine.handlers[self.machine.STATE_BREAD_COLLECTION].handle(screen_img, rect)
                return

        # 4. 如果不需要任何領取，執行待機/返回邏輯
        if is_lobby:
            if pos_goback:
                logging.info("🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...")
                self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                time.sleep(1.0)
                return
        elif is_town:
            logging.info("⌛ 定時領取：已在城鎮主畫面，且無領取任務，原地等待中...")
            time.sleep(1.0)
            return
        else:
            logging.warning("⚠️ 定時領取：未處於大廳或城鎮，嘗試原地等待重新偵測...")
            time.sleep(1.0)
            return
