import os
import time
import logging
from states.handlers.base import BaseStateHandler

class HeroDrawHandler(BaseStateHandler):
    """
    抽英雄 (Hero Draw / 酒館免費招募 Subflow) 處理器：
    1. 於城鎮畫面點擊進入酒館 (town_building/Tavern/Tavern.png)。
    2. 若位於大廳 (看得到 goback_town.png)，自動點擊返回城鎮。
    3. 進入酒館後，點擊免費招募 (town_building/Tavern/free_recruitment.png)。
    4. 於彈窗中點擊專用「招募」按鈕 (town_building/Tavern/RECRUITED.png)。
    5. 點擊獲得英雄領取確認 (common/confirm.png / common/ok.png)。
    6. 點擊離開/關閉按鈕 (common/quit.png / exitfromhouse_and_to_town.png) 退出酒館。
    7. 記錄 DailyManager 狀態 (completed_today = True)，並自動呼叫 pop_and_next_town_subflow() 續行佇列。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_TAVERN, CLICKED_FREE_RECRUITMENT, WAITING_CONFIRM, ALL_DONE_EXITING
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
            logging.info("🍺 [抽英雄] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = now
            return True

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/Tavern/Tavern.png")
        recruitment_btn = cfg.get("recruitment_btn", "town_building/Tavern/free_recruitment.png")

        # 2. INIT 階段：在城鎮尋找並進入酒館 (Tavern.png)
        if self.step_phase == "INIT":
            if os.path.exists(os.path.join("templates", building_btn)):
                pos_tavern, conf_tavern = self.matcher.match(screen_img, building_btn, threshold=0.75)
                if pos_tavern:
                    logging.info(f"🍺 [抽英雄] 於城鎮發現酒館建築 [{building_btn}] [{conf_tavern:.4f}]，點擊進入...")
                    self.mouse.click(left + pos_tavern[0], top + pos_tavern[1])
                    self.last_action_time = now
                    self.step_phase = "ENTERED_TAVERN"
                    self.not_found_count = 0
                    time.sleep(0.3)
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🍺 [抽英雄] 畫面上未發現酒館建築，標記完成並彈出下一個城鎮任務...")
                dm = getattr(self.machine, "daily_manager", None)
                if dm and hasattr(dm, "record_subflow_completed"):
                    dm.record_subflow_completed("hero_draw")
                self.machine.pop_and_next_town_subflow()
                return True

        # 3. ENTERED_TAVERN 階段：精確比對免費招募按鈕 (free_recruitment.png)
        elif self.step_phase == "ENTERED_TAVERN":
            if os.path.exists(os.path.join("templates", recruitment_btn)):
                # 配合包含「❶免費招募」紅色驚嘆號的獨特模板，門檻設定為 0.75 即可 100% 辨識
                pos_free, conf_free = self.matcher.match(
                    screen_img, 
                    recruitment_btn, 
                    threshold=0.75, 
                    brightness_threshold=0.70
                )
                if pos_free:
                    logging.info(f"🍺 [抽英雄] 於酒館精確匹配到免費招募按鈕 [{recruitment_btn}] [{conf_free:.4f}]，進行點擊！")
                    self.mouse.click(left + pos_free[0], top + pos_free[1])
                    self.last_action_time = now
                    self.step_phase = "CLICKED_FREE_RECRUITMENT"
                    self.not_found_count = 0
                    time.sleep(0.3)
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🍺 [抽英雄] 未發現免費招募按鈕（可能今日已完成招募），準備退出酒館...")
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return True

        # 4. CLICKED_FREE_RECRUITMENT 階段：僅配對專用「招募」按鈕 (RECRUITED.png)
        elif self.step_phase == "CLICKED_FREE_RECRUITMENT":
            recruited_template = "town_building/Tavern/RECRUITED.png"
            if os.path.exists(os.path.join("templates", recruited_template)):
                pos_r, conf_r = self.matcher.match(screen_img, recruited_template, threshold=0.75)
                if pos_r:
                    logging.info(f"🍺 [抽英雄] 於彈窗中發現專用「招募」按鈕 [{recruited_template}] [{conf_r:.4f}]，進行點擊！")
                    self.mouse.click(left + pos_r[0], top + pos_r[1])
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"
                    self.not_found_count = 0
                    time.sleep(0.3)
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🍺 [抽英雄] 未發現專用招募按鈕，直接進入確認檢查階段...")
                self.step_phase = "WAITING_CONFIRM"
                self.last_action_time = now
                return True

        # 5. WAITING_CONFIRM 階段：點擊獲得英雄確認/確定按鈕 (confirm.png / ok.png)
        elif self.step_phase == "WAITING_CONFIRM":
            for confirm_template in ["common/confirm.png", "common/ok.png"]:
                if os.path.exists(os.path.join("templates", confirm_template)):
                    pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                    if pos_c:
                        logging.info(f"🍺 [抽英雄] 發現獲得英雄確認按鈕 [{confirm_template}] [{conf_c:.4f}]，進行點擊...")
                        self.mouse.click(left + pos_c[0], top + pos_c[1])
                        self.last_action_time = now
                        time.sleep(0.3)
                        break

            self.step_phase = "ALL_DONE_EXITING"
            return True

        # 6. ALL_DONE_EXITING 階段：點擊退出按鈕，寫入 DailyManager 並彈出下一任務
        elif self.step_phase == "ALL_DONE_EXITING":
            for exit_template in ["common/quit.png", "town_building/exitfromhouse_and_to_town.png"]:
                if os.path.exists(os.path.join("templates", exit_template)):
                    pos_exit, conf_exit = self.matcher.match(screen_img, exit_template, threshold=0.75)
                    if pos_exit:
                        logging.info(f"🍺 [抽英雄] 點擊退出酒館按鈕 [{exit_template}] [{conf_exit:.4f}] 返回城鎮...")
                        self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                        time.sleep(0.3)
                        break

            dm = getattr(self.machine, "daily_manager", None)
            if dm and hasattr(dm, "record_subflow_completed"):
                dm.record_subflow_completed("hero_draw")

            logging.info("🍺 [抽英雄] 招募流程完成，彈出下一個城鎮任務...")
            self.machine.pop_and_next_town_subflow()
            return True

        return False
