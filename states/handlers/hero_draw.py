import os
import time
import logging
from states.handlers.base import BaseStateHandler
from states.handler_mislocation_guard import MislocationGuard, MislocationDecision
from utils.town_building_detector import detect_building_with_red_dot

class HeroDrawHandler(BaseStateHandler):
    """
    酒館免費招募英雄 (Hero Draw Subflow) 處理器：
    1. 在城鎮畫面尋找酒館建築 (Tavern.png)，前置檢查下方是否有紅點。
    2. 若位於大廳 (看得到 goback_town.png)，自動點擊返回城鎮。
    3. 點擊進入酒館，比對免費招募按鈕 (free_recruitment.png)。
    4. 點擊免費招募後，點擊專用招募按鈕 (RECRUITED.png)。
    5. 若抽到重複英雄出現「分解英雄」(deassemble_hero.png) 彈窗，點擊分解領取資源。
    6. 點擊離開/關閉按鈕 (common/quit.png / exitfromhouse_and_to_town.png) 退出酒館。
    7. 在城鎮再次核驗酒館紅點已消失，標記 completed_today 並推進佇列。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_TAVERN, CLICKED_FREE_RECRUITMENT, WAITING_CONFIRM, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.not_found_count = 0
        self.mislocation_guard = MislocationGuard(threshold=2)

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.not_found_count = 0
        self.mislocation_guard.reset()

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

        # Queue-driven runs reached this Handler only after REACH_TOWN.  Keep
        # this legacy route solely for a direct/standalone Handler invocation.
        if getattr(self.machine, "current_town_subflow", None) != "hero_draw":
            pos_goback, _ = self.matcher.match(
                screen_img, "goback_town.png", threshold=0.80
            )
            if pos_goback:
                logging.info("🍺 [抽英雄] 獨立模式偵測到大廳，點擊 [goback_town.png] 返回城鎮...")
                self.mouse.click(left + pos_goback[0], top + pos_goback[1])
                self.last_action_time = now
                return True

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/Tavern/Tavern.png")
        recruitment_btn = cfg.get("recruitment_btn", "town_building/Tavern/free_recruitment.png")

        # 2. INIT 階段：在城鎮尋找並進入酒館 (Tavern.png)
        if self.step_phase == "INIT":
            # 2.1 自身專屬特徵檢查 (own-specific evidence)
            pos_free_check, _ = self.matcher.match(screen_img, recruitment_btn, threshold=0.75, brightness_threshold=0.70)
            pos_rec_check, _ = self.matcher.match(screen_img, "town_building/Tavern/RECRUITED.png", threshold=0.85)
            own_inside_evidence = bool(pos_free_check or pos_rec_check)

            # 2.2 通用建築內部特徵檢查 (generic building-internal evidence)
            pos_exit_check, _ = self.matcher.match(screen_img, "town_building/exitfromhouse_and_to_town.png", threshold=0.80)
            pos_goback_check, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.80)
            generic_building_evidence = bool(pos_exit_check or pos_goback_check)

            decision = self.mislocation_guard.evaluate(own_inside_evidence, generic_building_evidence)
            if decision == MislocationDecision.RETAIN:
                logging.info("🍺 [抽英雄] 辨識到酒館專屬內部特徵，切換至酒館招募階段...")
                self.step_phase = "ENTERED_TAVERN"
                self.not_found_count = 0
                return True
            elif decision == MislocationDecision.RELINQUISH:
                logging.warning(
                    "⚠️ [HeroDraw Mislocation] 觀察到通用建築內部特徵但無酒館專屬特徵，連續確認錯位成立，讓渡實體所有權給 REACH_TOWN..."
                )
                self.reset_state()
                if hasattr(self.machine, "relinquish_subflow_to_navigation"):
                    self.machine.relinquish_subflow_to_navigation("mislocated_in_foreign_building")
                else:
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                return True
            elif generic_building_evidence:
                logging.info("⚠️ [HeroDraw] 觀察到通用建築內部特徵但無酒館特徵 (suspected mislocation 觀測中)...")
                return True

            # 2.3 在城鎮尋找並點擊酒館建築 (Tavern.png，前置紅點預檢)
            if os.path.exists(os.path.join("templates", building_btn)):
                check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="hero_draw")
                if check.found_building:
                    if not check.has_red_dot:
                        logging.info("🍺 [抽英雄 INIT] 酒館下方無驚嘆號紅點，判定今日招募已完成！標記完成並彈出下一任務...")
                        dm = getattr(self.machine, "daily_manager", None)
                        if dm and hasattr(dm, "record_subflow_completed"):
                            dm.record_subflow_completed("hero_draw")
                        self.machine.pop_and_next_town_subflow()
                        return True
                    else:
                        pos_tavern = check.building_pos
                        conf_tavern = check.confidence_building
                        logging.info(f"🍺 [抽英雄] 於城鎮發現酒館建築且帶有紅點 [{building_btn}] [{conf_tavern:.4f}]，點擊進入...")
                        self.mouse.click(left + pos_tavern[0], top + pos_tavern[1])
                        self.last_action_time = now
                        self.step_phase = "ENTERED_TAVERN"
                        self.not_found_count = 0
                        return True

            self.not_found_count += 1
            if self.not_found_count >= 3:
                logging.warning("⚠️ [抽英雄] 城鎮入口證據消失，暫緩而非靜默跳過任務。")
                if getattr(self.machine, "current_town_subflow", None) == "hero_draw":
                    self.machine.defer_current_town_subflow(180)
                else:
                    self.machine.pop_and_next_town_subflow()
                return True

        # 3. ENTERED_TAVERN 階段：精確比對免費招募按鈕 (free_recruitment.png)
        elif self.step_phase == "ENTERED_TAVERN":
            pos_free = None
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
                    self.mislocation_guard.reset()
                    return True

            # 檢查是否因點偏而處於 foreign building
            pos_exit_check, _ = self.matcher.match(screen_img, "town_building/exitfromhouse_and_to_town.png", threshold=0.80)
            pos_rec_check, _ = self.matcher.match(screen_img, "town_building/Tavern/RECRUITED.png", threshold=0.85)
            own_inside = bool(pos_free or pos_rec_check)
            generic_exit = bool(pos_exit_check)
            decision = self.mislocation_guard.evaluate(own_inside, generic_exit)
            if decision == MislocationDecision.RELINQUISH:
                logging.warning(
                    "⚠️ [HeroDraw Mislocation] ENTERED_TAVERN 階段未見酒館招募特徵但見通用建築內部特徵，連續確認成立，讓渡實體所有權給 REACH_TOWN..."
                )
                self.reset_state()
                if hasattr(self.machine, "relinquish_subflow_to_navigation"):
                    self.machine.relinquish_subflow_to_navigation("mislocated_in_foreign_building")
                else:
                    self.machine.transition_to(self.machine.STATE_NAVIGATING)
                return True
            elif generic_exit:
                logging.info("⚠️ [HeroDraw] ENTERED_TAVERN 觀察到通用建築內部特徵但無招募按鈕 (suspected mislocation 觀測中)...")
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

            logging.info("🍺 [抽英雄] 退出酒館按鈕已觸發，轉入 VERIFY_EXIT 階段進行城鎮紅點驗證...")
            self.step_phase = "VERIFY_EXIT"
            self.not_found_count = 0
            self.last_action_time = now
            return True

        # 7. VERIFY_EXIT 階段：退出後在城鎮再次檢查酒館下方紅點 (有檢查到紅點 vs 沒檢查到紅點)
        elif self.step_phase == "VERIFY_EXIT":
            check = detect_building_with_red_dot(screen_img, building_btn, self.matcher, debug_tag="hero_draw")
            if check.found_building:
                if check.has_red_dot:
                    logging.warning("⚠️ [抽英雄 VERIFY_EXIT] 退出後檢查：酒館下方仍有驚嘆號紅點！判定招募未成功，不標記 completed_today，進入 180 秒冷卻退避。")
                    dm = getattr(self.machine, "daily_manager", None)
                    if dm and hasattr(dm, "defer_subflow"):
                        dm.defer_subflow("hero_draw", 180)
                    self.machine.pop_and_next_town_subflow()
                    return True
                else:
                    logging.info("🎉 [抽英雄 VERIFY_EXIT] 退出後檢查：酒館下方已無紅點！確認招募成功，標記 completed_today = True。")
                    dm = getattr(self.machine, "daily_manager", None)
                    if dm and hasattr(dm, "record_subflow_completed"):
                        dm.record_subflow_completed("hero_draw")
                    self.machine.pop_and_next_town_subflow()
                    return True
            else:
                self.not_found_count += 1
                if self.not_found_count >= 3:
                    logging.warning("⚠️ [抽英雄 VERIFY_EXIT] 無法驗證紅點 outcome，暫緩而非標記完成。")
                    if getattr(self.machine, "current_town_subflow", None) == "hero_draw":
                        self.machine.defer_current_town_subflow(180)
                    else:
                        self.machine.pop_and_next_town_subflow()
                    return True

        return False
