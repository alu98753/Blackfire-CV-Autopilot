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
        
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.8, quiet=True)
        pos_diamond, _ = self.matcher.match(screen_img, "diamond.png", threshold=0.8, quiet=True)
        if pos_door or pos_diamond:
            is_town = True
            
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8, quiet=True)
        pos_bread_btn, _ = self.matcher.match(screen_img, "common/bread.png", threshold=0.8, quiet=True)
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
        now = time.time()
        last_log = getattr(self, "last_log_time", 0.0)
        
        # 動態決定 log 間隔：最長為 300 秒 (5分鐘)，若 CD 比 5 分鐘短則跟隨較短的 CD，以利測試
        diamond_cd = self.machine.config.get("diamond_cd", 7200.0)
        default_bread_cd = 7200.0 if self.machine.config.get("type") == "collect_only" else 1800.0
        bread_cd = self.machine.config.get("bread_cd", default_bread_cd)
        log_interval = min(300.0, diamond_cd, bread_cd)
        
        should_log = (now - last_log >= log_interval)
        if should_log:
            self.last_log_time = now
            
            # 計算剩餘秒數
            dia_rem = max(0.0, diamond_cd - (now - self.machine.last_diamond_collection_time))
            brd_rem = max(0.0, bread_cd - (now - self.machine.last_bread_collection_time))
            
            # 格式化輸出剩餘時間
            def format_time(seconds):
                if seconds <= 0:
                    return "即將執行"
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                if h > 0:
                    return f"{h}小時{m}分{s}秒"
                elif m > 0:
                    return f"{m}分{s}秒"
                else:
                    return f"{s}秒"
                    
            dia_str = format_time(dia_rem)
            brd_str = format_time(brd_rem) if self.machine.enable_bread else "已停用"
            
            logging.info(f"⌛ [定時領取狀態] 運作中。距離下一次領取 💎 鑽石還剩: {dia_str}，🍞 體力還剩: {brd_str}。")

        if is_lobby:
            if pos_goback:
                logging.info("🧭 定時領取：目前在大廳且無領取任務，點擊 [goback_town.png] 返回城鎮...")
                self.mouse.click(rect["left"] + pos_goback[0], rect["top"] + pos_goback[1])
                time.sleep(1.0)
                return
        elif is_town:
            time.sleep(1.0)
            return
        else:
            if should_log:
                logging.warning("⚠️ 定時領取：未處於大廳或城鎮，嘗試原地等待重新偵測...")
            time.sleep(1.0)
            return
