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
            # 2.1 防呆：若目前已在酒館內部 (看得到免費招募/招募按鈕/房屋退出按鈕)，直接切換至 ENTERED_TAVERN 階段
            pos_free_check, _ = self.matcher.match(screen_img, recruitment_btn, threshold=0.75, brightness_threshold=0.70)
            pos_rec_check, _ = self.matcher.match(screen_img, "town_building/Tavern/RECRUITED.png", threshold=0.85)
            pos_exit_check, _ = self.matcher.match(screen_img, "town_building/exitfromhouse_and_to_town.png", threshold=0.80)

            if pos_free_check or pos_rec_check or pos_exit_check:
                logging.info("🍺 [抽英雄] 辨識到目前已在酒館內部，直接切換至酒館招募階段...")
                self.step_phase = "ENTERED_TAVERN"
                self.not_found_count = 0
                return True

            # 2.2 在城鎮尋找並點擊酒館建築 (Tavern.png)
            if os.path.exists(os.path.join("templates", building_btn)):
                pos_tavern, conf_tavern = self.matcher.match(screen_img, building_btn, threshold=0.75)
                if pos_tavern:
                    logging.info(f"🍺 [抽英雄] 於城鎮發現酒館建築 [{building_btn}] [{conf_tavern:.4f}]，點擊進入...")
                    self.machine.click_and_wait_until_gone(
                        building_btn, left + pos_tavern[0], top + pos_tavern[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "ENTERED_TAVERN"
                    self.not_found_count = 0
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
                pos_free, conf_free = self.matcher.match(
                    screen_img, 
                    recruitment_btn, 
                    threshold=0.75, 
                    brightness_threshold=0.70
                )
                if pos_free:
                    logging.info(f"🍺 [抽英雄] 於酒館精確匹配到免費招募按鈕 [{recruitment_btn}] [{conf_free:.4f}]，點擊並 WHILE 輪詢直到消失...")
                    self.machine.click_and_wait_until_gone(
                        recruitment_btn, left + pos_free[0], top + pos_free[1], rect,
                        timeout=5.0, threshold=0.75, brightness_threshold=0.70, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "CLICKED_FREE_RECRUITMENT"
                    self.not_found_count = 0
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
                    logging.info(f"🍺 [抽英雄] 於彈窗中發現專用「招募」按鈕 [{recruited_template}] [{conf_r:.4f}]，點擊並 WHILE 輪詢直到消失...")
                    self.machine.click_and_wait_until_gone(
                        recruited_template, left + pos_r[0], top + pos_r[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    self.step_phase = "WAITING_CONFIRM"
                    self.not_found_count = 0
                    return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.info("🍺 [抽英雄] 未發現專用招募按鈕，直接進入確認檢查階段...")
                self.step_phase = "WAITING_CONFIRM"
                self.last_action_time = now
                return True

        # 5. WAITING_CONFIRM 階段：點擊獲得英雄 OK 按鈕或「分解英雄」按鈕 (deassemble_hero.png)
        elif self.step_phase == "WAITING_CONFIRM":
            deassemble_list = [
                "town_building/Tavern/deassemble_hero.png",
                "deassemble_hero.png"
            ]
            # 5.1 優先檢查與點擊「分解英雄」按鈕 (抽到重複英雄時分解領取資源，帶入 brightness_threshold=0.85 防止前景彈窗遮罩壓暗背景殘影誤判)
            for deassemble_template in deassemble_list:
                if os.path.exists(os.path.join("templates", deassemble_template)):
                    pos_d, conf_d = self.matcher.match(
                        screen_img, 
                        deassemble_template, 
                        threshold=0.75, 
                        brightness_threshold=0.85
                    )
                    if pos_d:
                        logging.info(f"🍺 [抽英雄] 發現「分解英雄」按鈕 [{deassemble_template}] [{conf_d:.4f}]，點擊分解獲得資源 (配對確認直到消失)...")
                        self.machine.click_and_wait_until_gone(
                            deassemble_template, left + pos_d[0], top + pos_d[1], rect,
                            timeout=5.0, threshold=0.75, brightness_threshold=0.85, check_interval=0.25, post_delay=0.5
                        )
                        self.last_action_time = now
                        self.not_found_count = 0
                        return True

            # 5.2 檢查與點擊 OK / 確認按鈕 / 關閉按鈕 (支援多個連續彈窗，點擊後保持 WAITING_CONFIRM 直到所有彈窗被點完)
            confirm_list = ["common/ok.png", "common/confirm.png", "common/quit.png"]
            for confirm_template in confirm_list:
                if os.path.exists(os.path.join("templates", confirm_template)):
                    pos_c, conf_c = self.matcher.match(screen_img, confirm_template, threshold=0.75)
                    if pos_c:
                        logging.info(f"🍺 [抽英雄] 發現確認/關閉按鈕 [{confirm_template}] [{conf_c:.4f}]，發起確信點擊與消失輪詢...")
                        self.machine.click_and_wait_until_gone(
                            confirm_template, left + pos_c[0], top + pos_c[1], rect,
                            timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                        )
                        self.last_action_time = now
                        self.not_found_count = 0
                        return True

            # 5.3 無彈窗門禁：連續 3 幀確信畫面上無任何分解或 OK/確認/關閉按鈕後，才切換至 ALL_DONE_EXITING
            self.not_found_count += 1
            if self.not_found_count < 3:
                logging.info(f"🍺 [抽英雄] 等待 OK / 分解 / 關閉按鈕彈出中... (第 {self.not_found_count}/3 幀嘗試)")
                self.last_action_time = now
                return True

            logging.info("🍺 [抽英雄] 連續 3 幀未偵測到 OK、分解或 Quit 按鈕，確信所有彈窗已完全清理，準備退出酒館...")
            self.step_phase = "ALL_DONE_EXITING"
            self.not_found_count = 0
            self.last_action_time = now
            return True

        # 6. ALL_DONE_EXITING 階段：點擊房屋退出按鈕 (若殘留 quit 彈窗則先關閉)
        elif self.step_phase == "ALL_DONE_EXITING":
            # 6.1 若畫面上仍殘留關閉按鈕 (如卡片/提示彈窗)，先關閉彈窗
            if os.path.exists(os.path.join("templates", "common/quit.png")):
                pos_q, conf_q = self.matcher.match(screen_img, "common/quit.png", threshold=0.75)
                if pos_q:
                    logging.info(f"🍺 [抽英雄] 退出前發現殘留彈窗關閉按鈕 [common/quit.png] [{conf_q:.4f}]，點擊關閉...")
                    self.machine.click_and_wait_until_gone(
                        "common/quit.png", left + pos_q[0], top + pos_q[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.5
                    )
                    self.last_action_time = now
                    return True

            exit_template = "town_building/exitfromhouse_and_to_town.png"
            exit_clicked = False
            if os.path.exists(os.path.join("templates", exit_template)):
                pos_exit, conf_exit = self.matcher.match(screen_img, exit_template, threshold=0.75)
                if pos_exit:
                    logging.info(f"🍺 [抽英雄] 點擊退出酒館按鈕 [{exit_template}] [{conf_exit:.4f}]，點擊並 WHILE 輪詢直到消失...")
                    self.machine.click_and_wait_until_gone(
                        exit_template, left + pos_exit[0], top + pos_exit[1], rect,
                        timeout=5.0, threshold=0.75, check_interval=0.25, post_delay=0.8
                    )
                    exit_clicked = True

            dm = getattr(self.machine, "daily_manager", None)
            if dm and hasattr(dm, "record_subflow_completed"):
                dm.record_subflow_completed("hero_draw")

            logging.info("🍺 [抽英雄] 招募流程完成，彈出下一個城鎮任務...")
            self.machine.pop_and_next_town_subflow()
            return True

        return False
