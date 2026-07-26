import os
import cv2
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

        # Step 2: CLICK_FREE_CHEST 階段（先匹配免費寶匣大彈窗 free_treasure.png，再定位內部免費按鈕）
        elif self.step_phase == "CLICK_FREE_CHEST":
            dialog_template = "town_building/mysterious_treasure/free_treasure.png"
            if os.path.exists(os.path.join("templates", dialog_template)):
                pos_ft, conf_ft = self.matcher.match(screen_img, dialog_template, threshold=0.75)
                if pos_ft:
                    t_img = cv2.imread(os.path.join("templates", dialog_template))
                    t_h, t_w = t_img.shape[:2] if t_img is not None else (350, 400)
                    h = rect["height"] if rect else (screen_img.shape[0] if isinstance(screen_img, np.ndarray) else 600)
                    w = rect["width"] if rect else (screen_img.shape[1] if isinstance(screen_img, np.ndarray) else 800)

                    cx, cy = pos_ft
                    x1 = max(0, cx - t_w // 2)
                    x2 = min(w, cx + t_w // 2)
                    y1 = max(0, cy - t_h // 2)
                    y2 = min(h, cy + t_h // 2)
                    dialog_crop = screen_img[y1:y2, x1:x2]

                    click_x = left + cx
                    click_y = top + cy + (t_h // 2) - 35

                    if os.path.exists(os.path.join("templates", "free.png")):
                        pos_sub_free, conf_sub_free = self.matcher.match(dialog_crop, "free.png", threshold=0.70)
                        if pos_sub_free:
                            click_x = left + x1 + pos_sub_free[0]
                            click_y = top + y1 + pos_sub_free[1]
                            logging.info(f"🎁 [神秘寶箱 Step 2] 於免費寶匣彈窗內精確比對到 [free.png] [{conf_sub_free:.4f}]，點擊座標 ({click_x}, {click_y})！")

                    target_template = "free.png" if os.path.exists(os.path.join("templates", "free.png")) and self.matcher.match(dialog_crop, "free.png", threshold=0.70)[0] else dialog_template
                    logging.info(f"🎁 [神秘寶箱 Step 2] 成功鎖定免費寶匣彈窗 [{conf_ft:.4f}]，點擊免費按鈕位置 ({click_x}, {click_y}) 兼 WHILE 輪詢直到消失...")
                    self.machine.click_and_wait_until_gone(
                        target_template, click_x, click_y, rect,
                        timeout=5.0, threshold=0.70, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"
                    self.not_found_count = 0
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 5:
                logging.info("🎁 [神秘寶箱 Step 2] 未發現免費寶匣彈窗（可能今日已完成免費領取），標記完成並彈出下一任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("chest")
                self.machine.pop_and_next_town_subflow()
                return True

        # Step 3: WAITING_CONFIRM 階段（檢查彈出的獎勵確認按鈕 confirm.png / ok.png）
        elif self.step_phase == "WAITING_CONFIRM":
            confirm_list = ["common/confirm.png", "common/ok.png"]
            for confirm_template in confirm_list:
                if os.path.exists(os.path.join("templates", confirm_template)):
                    pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                    if pos_c:
                        logging.info(f"🎁 [神秘寶箱 Step 3] 發現領取確認按鈕 [{confirm_template}] [{conf_c:.4f}]，發起確信點擊與消失輪詢！")
                        self.machine.click_and_wait_until_gone(
                            confirm_template, left + pos_c[0], top + pos_c[1], rect,
                            timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                        )
                        self.last_action_time = now
                        self.step_phase = "WAITING_QUIT"
                        self.not_found_count = 0
                        return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🎁 [神秘寶箱 Step 3] 未跳出額外確認按鈕，轉入 Step 4 檢查退出建築...")
                self.step_phase = "WAITING_QUIT"
                self.not_found_count = 0
                return True

        # Step 4: WAITING_QUIT 階段（點擊 quit.png / exitfromhouse 退出建築返回城鎮）
        elif self.step_phase == "WAITING_QUIT":
            quit_list = [
                "common/quit.png", 
                "town_building/exitfromhouse_and_to_town.png",
                "goback_town.png"
            ]
            quit_clicked = False
            for quit_template in quit_list:
                if os.path.exists(os.path.join("templates", quit_template)):
                    pos_q, conf_q = self.matcher.match(screen_img, quit_template, threshold=0.75)
                    if pos_q:
                        logging.info(f"🎁 [神秘寶箱 Step 4] 發現退出建築按鈕 [{quit_template}] [{conf_q:.4f}]，發起點擊並 WHILE 輪詢直到消失...")
                        self.machine.click_and_wait_until_gone(
                            quit_template, left + pos_q[0], top + pos_q[1], rect,
                            timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.8
                        )
                        quit_clicked = True
                        break

            if quit_clicked or self.not_found_count >= 3:
                logging.info("🎉 [神秘寶箱 Step 4] 寶箱領取與退出流程完成！記錄 DailyManager 並彈出下一個城鎮任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("chest")
                self.machine.pop_and_next_town_subflow()
                return True
            else:
                self.not_found_count += 1

        return False
