import os
import time
import logging
from states.handlers.base import BaseStateHandler

class ChestHandler(BaseStateHandler):
    """
    神秘寶箱 (Chest Subflow / 開寶箱) 處理器：
    1. 於城鎮畫面掃描並點擊神秘寶箱建築/按鈕 (mysterious_treasure.png)。
    2. 若位於大廳 (看得到 goback_town.png)，自動點擊返回城鎮。
    3. 點擊領取寶箱後，記錄 DailyManager 狀態 (completed_today = True)，並自動呼叫 pop_and_next_town_subflow() 續行下一個城鎮任務。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, WAITING_CONFIRM
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

        # 1. 優先檢查是否在關卡大廳/選關畫面 (有 goback_town.png)，點擊返回城鎮
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.80)
        if pos_goback:
            logging.info("🎁 [神秘寶箱] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = now
            return True

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/mysterious_treasure/mysterious_treasure.png")

        # 2. INIT 階段：比對神秘寶箱 (mysterious_treasure.png)
        if self.step_phase == "INIT":
            if os.path.exists(os.path.join("templates", building_btn)):
                pos_chest, conf_chest = self.matcher.match(screen_img, building_btn, threshold=0.75)
                if pos_chest:
                    logging.info(f"🎁 [神秘寶箱] 於城鎮發現神秘寶箱 [{building_btn}] [{conf_chest:.4f}]，點擊領取！")
                    self.mouse.click(left + pos_chest[0], top + pos_chest[1])
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"

                    dm = getattr(self.machine, "daily_manager", None)
                    if dm and hasattr(dm, "record_subflow_completed"):
                        dm.record_subflow_completed("chest")

                    time.sleep(0.3)
                    return True

            # 畫面上未發現寶箱
            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🎁 [神秘寶箱] 畫面上未發現神秘寶箱（可能今日已領取或不在城鎮視野內），標記完成並彈出下一個任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("chest")
                self.machine.pop_and_next_town_subflow()
                return True

        # 3. WAITING_CONFIRM 階段：檢查可能彈出的確定/關閉按鈕
        elif self.step_phase == "WAITING_CONFIRM":
            for confirm_template in ["common/confirm.png", "common/ok.png", "common/quit.png"]:
                if os.path.exists(os.path.join("templates", confirm_template)):
                    pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                    if pos_c:
                        logging.info(f"🎁 [神秘寶箱] 發現領取確認按鈕 [{confirm_template}] [{conf_c:.4f}]，進行點擊...")
                        self.mouse.click(left + pos_c[0], top + pos_c[1])
                        time.sleep(0.2)
                        break

            logging.info("🎁 [神秘寶箱] 寶箱領取流程完成，彈出下一個城鎮任務...")
            self.machine.pop_and_next_town_subflow()
            return True

        return False
