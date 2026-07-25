import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ChestHandler(BaseStateHandler):
    """
    神秘寶箱 (Chest Subflow / 開寶箱) 處理器：
    1. Step 1 (INIT): 於城鎮畫面掃描並點擊神秘寶箱建築 (mysterious_treasure.png)。若在選關畫面則點擊 goback_town.png 返回城鎮。
    2. Step 2 (CLICK_FREE_CHEST): 掃描並點擊免費寶箱領取按鈕 (free_treasure.png)。
    3. Step 3 (WAITING_CONFIRM): 檢查領取/確認彈窗 (confirm.png / ok.png)，記錄 DailyManager 完成狀態並切至下一任務。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, CLICK_FREE_CHEST, WAITING_CONFIRM
        self.last_action_time = 0.0
        self.not_found_count = 0

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.not_found_count = 0

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return False

        now = time.time()
        if now - self.last_action_time < 0.5:
            return False

        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        # 0. 優先檢查是否在關卡大廳/選關畫面 (有 goback_town.png)，點擊返回城鎮
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.80)
        if pos_goback:
            logging.info("🎁 [神秘寶箱] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = now
            return True

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/mysterious_treasure/mysterious_treasure.png")
        free_btn = cfg.get("free_btn", "town_building/mysterious_treasure/free_treasure.png")

        # Step 1: INIT 階段（比對並點擊城鎮寶箱建築）
        if self.step_phase == "INIT":
            if os.path.exists(os.path.join("templates", building_btn)):
                pos_chest, conf_chest = self.matcher.match(screen_img, building_btn, threshold=0.75)
                if pos_chest:
                    logging.info(f"🎁 [神秘寶箱 Step 1] 於城鎮發現神秘寶箱建築 [{building_btn}] [{conf_chest:.4f}]，點擊進入！")
                    self.mouse.click(left + pos_chest[0], top + pos_chest[1])
                    self.last_action_time = now
                    self.step_phase = "CLICK_FREE_CHEST"
                    self.not_found_count = 0
                    time.sleep(0.3)
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 5:
                logging.info("🎁 [神秘寶箱] 畫面上未發現神秘寶箱建築（可能不在城鎮視野內），標記完成並彈出下一個任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("chest")
                self.machine.pop_and_next_town_subflow()
                return True

        # Step 2: CLICK_FREE_CHEST 階段（比對並點擊免費寶箱按鈕 free_treasure.png）
        elif self.step_phase == "CLICK_FREE_CHEST":
            if os.path.exists(os.path.join("templates", free_btn)):
                pos_free, conf_free = self.matcher.match(screen_img, free_btn, threshold=0.70)
                if pos_free:
                    logging.info(f"🎁 [神秘寶箱 Step 2] 發現免費寶箱領取按鈕 [{free_btn}] [{conf_free:.4f}]，進行點擊領取！")
                    self.mouse.click(left + pos_free[0], top + pos_free[1])
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"
                    self.not_found_count = 0
                    time.sleep(0.3)
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 5:
                logging.info("🎁 [神秘寶箱 Step 2] 未發現免費寶箱領取按鈕（可能今日已完成免費領取），標記完成並彈出下一任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("chest")
                self.machine.pop_and_next_town_subflow()
                return True

        # Step 3: WAITING_CONFIRM 階段（檢查彈出的獎勵確認 / 關閉按鈕）
        elif self.step_phase == "WAITING_CONFIRM":
            confirm_list = [
                "common/confirm.png", 
                "common/ok.png", 
                "common/quit.png", 
                "town_building/exitfromhouse_and_to_town.png"
            ]
            for confirm_template in confirm_list:
                if os.path.exists(os.path.join("templates", confirm_template)):
                    pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                    if pos_c:
                        logging.info(f"🎁 [神秘寶箱 Step 3] 發現領取確認按鈕 [{confirm_template}] [{conf_c:.4f}]，進行點擊！")
                        self.mouse.click(left + pos_c[0], top + pos_c[1])
                        time.sleep(0.2)
                        break

            logging.info("🎉 [神秘寶箱 Step 3] 寶箱領取流程完成！記錄 DailyManager 並彈出下一個城鎮任務...")
            dm = getattr(self.machine, "daily_manager", None)
            if dm and hasattr(dm, "record_subflow_completed"):
                dm.record_subflow_completed("chest")
            self.machine.pop_and_next_town_subflow()
            return True

        return False
