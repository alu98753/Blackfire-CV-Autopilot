import time
import os
import logging
from states.handlers.base import BaseStateHandler


class BloodAltarHandler(BaseStateHandler):
    """
    血之祭壇 (Blood Altar) 狀態處理器 (單向 State Machine Pipeline)：
    1. INIT: 於城鎮點擊血之祭壇建築 (Blood_Altar.png) 進入建築。
    2. ENTERED_BUILDING: 判斷今日是否已領血，未領血 ➔ receive_entry.png，已領血 ➔ SACRIFICE_MENU_OPEN。
    3. RECEIVE_TAB_OPEN: 於領血介面掃描 receive_daily.png (帶入 brightness=0.50，3 幀重試門禁)。
    4. HANDLING_RECEIVE_POPUPS: 專注驗證與清理領水彈窗 (confirm.png / ok.png / quit.png)。全清後 ➔ SACRIFICE_MENU_OPEN。
    5. SACRIFICE_MENU_OPEN: 專職負責點擊 Sacrifice.png 頁籤進入獻祭介面，並執行品質比對 ➔ MAX ➔ alter.png ➔ confirm.png。
    6. ALL_DONE_EXITING: 點擊離開建築 (exitfromhouse_and_to_town.png) 返回城鎮並記錄完成。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, RECEIVE_TAB_OPEN, HANDLING_RECEIVE_POPUPS, SACRIFICE_MENU_OPEN, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0
        self.receive_scan_count = 0
        self.popup_clear_count = 0
        self.has_claimed_daily = False

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0
        self.receive_scan_count = 0
        self.popup_clear_count = 0
        self.has_claimed_daily = False

    def _ensure_in_town(self, screen_img, rect=None):
        """若處於大廳選單，點擊 goback_town 返回城鎮 (配對確認直到消失)"""
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("🩸 [血之祭壇] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.click_and_wait_until_gone("goback_town.png", left + pos_goback[0], top + pos_goback[1], rect)
            self.last_action_time = time.time()
            return False
        return True

    def _record_completion(self):
        """記錄 DailyManager 完成狀態並自動切換至下一個城鎮任務"""
        self.reset_state()
        self.machine.need_blood_altar = False
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "record_subflow_completed"):
            dm.record_subflow_completed("blood_altar")
        logging.info("🩸 [血之祭壇] 領血與獻祭流程完成，消費城鎮佇列中的下一個任務...")
        self.machine.pop_and_next_town_subflow()

    def _is_blood_altar_claimed_today(self):
        """檢查 DailyManager 中 blood_altar 是否今日已領取過免費血水"""
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "is_subflow_completed"):
            return dm.is_subflow_completed("blood_altar") is True
        return False

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return False

        # 防死鎖門禁：若獨立模式或城鎮流水線已不需要血之祭壇獻祭 且處於 INIT 階段，直接 return！
        cfg_type = self.machine.config.get("type") if getattr(self.machine, "config", None) else None
        is_needed = getattr(self.machine, "need_blood_altar", False) or cfg_type == "blood_altar"
        if not is_needed and self.step_phase == "INIT":
            return False

        now = time.time()
        if now - self.last_action_time < 0.5:
            return False

        # 優先導航防護：若處於大廳選單，先退回城鎮
        if not self._ensure_in_town(screen_img, rect):
            return True

        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        cfg = self.machine.config or {}
        building_btn = cfg.get("building_btn", "town_building/Blood_Altar/Blood_Altar.png")
        receive_entry_btn = cfg.get("receive_entry_btn", "town_building/Blood_Altar/receive_entry.png")
        receive_daily_btn = cfg.get("receive_daily_btn", "town_building/Blood_Altar/receive_daily.png")
        sacrifice_btn = cfg.get("sacrifice_btn", "town_building/Blood_Altar/Sacrifice.png")
        alter_btn = cfg.get("alter_btn", "town_building/Blood_Altar/alter.png")
        exit_building_btn = cfg.get("exit_building_btn", "town_building/exitfromhouse_and_to_town.png")
        sacrifice_settings = cfg.get("sacrifice_settings")
        if sacrifice_settings is None:
            from config import GAME_CONFIGS
            sacrifice_settings = GAME_CONFIGS.get("blood_altar", {}).get("sacrifice_settings", {})
        blood_templates = cfg.get("blood_templates", {
            "gray": "town_building/Blood_Altar/gray_blood.png",
            "green": "town_building/Blood_Altar/green_blood.png",
            "blue": "town_building/Blood_Altar/blue_blood.png",
            "purple": "town_building/Blood_Altar/purple_blood.png",
        })

        is_claimed_today = self.has_claimed_daily or self._is_blood_altar_claimed_today()

        # =========================================================================
        # 1. INIT 階段：在城鎮點擊血之祭壇建築 (Blood_Altar.png) 並等待畫面渲染穩定
        # =========================================================================
        if self.step_phase == "INIT":
            # 1.1 UI穩定驗證：必須辨識到建築內部元素（如 exitfromhouse_and_to_town.png 或頁籤）才切換至 ENTERED_BUILDING
            pos_sac_check, _ = self.matcher.match(screen_img, sacrifice_btn, threshold=0.75)
            pos_rec_entry_check, _ = self.matcher.match(screen_img, receive_entry_btn, threshold=0.75)
            pos_exit_check, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)

            if pos_exit_check or pos_sac_check or pos_rec_entry_check:
                logging.info(f"🩸 [血之祭壇] 辨識到已在血之祭壇內部 (離開建築按鈕已解析: {pos_exit_check is not None})，畫面渲染穩定，切換至 ENTERED_BUILDING 階段...")
                self.step_phase = "ENTERED_BUILDING"
                self.last_action_time = now
                return True

            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, conf_building = self.matcher.match(screen_img, building_btn, threshold=0.65, quiet=True)
            if pos_building and pos_door:
                logging.info(f"🩸 [血之祭壇] 於城鎮發現血之祭壇建築 [{building_btn}] (信心度: {conf_building:.4f})，點擊進入 (保持在 INIT 階段等待 UI 渲染完成)...")
                self.mouse.click(left + pos_building[0], top + pos_building[1])
                self.last_action_time = now
                return True

        # =========================================================================
        # 2. ENTERED_BUILDING 階段：進屋後判斷切換至領血頁籤或獻祭頁籤
        # =========================================================================
        elif self.step_phase == "ENTERED_BUILDING":
            pos_rec_entry, conf_rec_entry = self.matcher.match(screen_img, receive_entry_btn, threshold=0.75)
            if not is_claimed_today and pos_rec_entry:
                logging.info(f"🩸 [血之祭壇] 辨識到領血頁籤 [{receive_entry_btn}] [{conf_rec_entry:.4f}]，點擊切換至領血介面...")
                self.mouse.click(left + pos_rec_entry[0], top + pos_rec_entry[1])
                self.step_phase = "RECEIVE_TAB_OPEN"
                self.receive_scan_count = 0
                self.last_action_time = now
                return True

            # 若今日已領取過免費血水或無領血頁籤，直接轉移至 SACRIFICE_MENU_OPEN
            logging.info("🩸 [血之祭壇] 今日免費血水已領取或無須領血，轉移至 SACRIFICE_MENU_OPEN 階段...")
            self.step_phase = "SACRIFICE_MENU_OPEN"
            self.empty_blood_scan_count = 0
            self.last_action_time = now
            return True

        # =========================================================================
        # 3. RECEIVE_TAB_OPEN 階段：領血頁籤介面比對 receive_daily.png (帶配對確認直到消失閉環)
        # =========================================================================
        elif self.step_phase == "RECEIVE_TAB_OPEN":
            pos_rec_daily, conf_rec_daily = self.matcher.match(
                screen_img,
                receive_daily_btn,
                threshold=0.70,
                brightness_threshold=0.50
            )
            if pos_rec_daily:
                logging.info(f"🩸 [血之祭壇] 發現每日領血按鈕 [{receive_daily_btn}] [{conf_rec_daily:.4f}]，點擊並啟動配對確認直到消失閉環...")
                self.click_and_wait_until_gone(
                    receive_daily_btn,
                    left + pos_rec_daily[0],
                    top + pos_rec_daily[1],
                    rect,
                    timeout=5.0,
                    threshold=0.70,
                    brightness_threshold=0.50,
                    retry_interval=1.0,
                    post_delay=0.3
                )
                self.has_claimed_daily = True
                self.step_phase = "HANDLING_RECEIVE_POPUPS"
                self.popup_clear_count = 0
                self.last_action_time = now
                return True

            self.receive_scan_count += 1
            logging.info(f"🩸 [血之祭壇] 掃描每日領血按鈕中... (第 {self.receive_scan_count}/3 幀確認)")
            if self.receive_scan_count >= 3:
                logging.info("🩸 [血之祭壇] 連續 3 幀未偵測到每日領血按鈕 (今日已領完)，轉移至 SACRIFICE_MENU_OPEN 階段...")
                self.step_phase = "SACRIFICE_MENU_OPEN"
                self.empty_blood_scan_count = 0
                self.last_action_time = now
                return True

        # =========================================================================
        # 4. HANDLING_RECEIVE_POPUPS 階段：僅專注驗證與清理領水彈窗 (confirm/ok/quit)
        # =========================================================================
        elif self.step_phase == "HANDLING_RECEIVE_POPUPS":
            pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
            pos_ok, _ = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)

            if pos_confirm:
                logging.info("🩸 [血之祭壇] 點擊領取確認按鈕 [common/confirm.png]...")
                self.click_and_wait_until_gone("common/confirm.png", left + pos_confirm[0], top + pos_confirm[1], rect, threshold=0.8)
                self.popup_clear_count = 0
                self.last_action_time = now
                return True
            elif pos_ok:
                logging.info("🩸 [血之祭壇] 點擊領取 OK 按鈕 [common/ok.png]...")
                self.click_and_wait_until_gone("common/ok.png", left + pos_ok[0], top + pos_ok[1], rect, threshold=0.8)
                self.popup_clear_count = 0
                self.last_action_time = now
                return True
            elif pos_quit:
                logging.info("🩸 [血之祭壇] 點擊領取關閉按鈕 [common/quit.png]...")
                self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, threshold=0.8)
                self.popup_clear_count = 0
                self.last_action_time = now
                return True

            self.popup_clear_count += 1
            if self.popup_clear_count >= 3:
                logging.info("🩸 [血之祭壇] 連續 3 幀無領血彈窗，確信彈窗已全數點完！轉移至 SACRIFICE_MENU_OPEN 階段...")
                self.step_phase = "SACRIFICE_MENU_OPEN"
                self.empty_blood_scan_count = 0
                self.last_action_time = now
                return True

        # =========================================================================
        # 5. SACRIFICE_MENU_OPEN 階段：負責「點擊 Sacrifice.png 頁籤」與後續「獻祭流程」
        # =========================================================================
        elif self.step_phase == "SACRIFICE_MENU_OPEN":
            # 5.1 優先處理獻祭完畢的確認彈窗
            pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
            if pos_confirm:
                logging.info("🩸 [血之祭壇] 點擊獻祭確認按鈕 [common/confirm.png]...")
                self.mouse.click(left + pos_confirm[0], top + pos_confirm[1])
                self.last_action_time = now
                return True

            # 5.2 若當前仍在領血介面 (看得到 Sacrifice.png 頁籤)，點擊切換至獻祭頁面
            pos_sac, conf_sac = self.matcher.match(screen_img, sacrifice_btn, threshold=0.75)
            max_btn = cfg.get("max_btn", "town_building/sell_max.png")
            pos_alter, _ = self.matcher.match(screen_img, alter_btn, threshold=0.75)

            # 若尚未看見 alter 按鈕或 MAX 按鈕，且看得見 Sacrifice 頁籤 ➔ 點擊頁籤進獻祭介面
            if pos_sac and not pos_alter:
                logging.info(f"🩸 [血之祭壇] 辨識到獻祭功能選單 [{sacrifice_btn}] [{conf_sac:.4f}]，點擊切換至獻祭介面...")
                self.mouse.click(left + pos_sac[0], top + pos_sac[1])
                self.last_action_time = now
                return True

            # 5.3 獻祭比對與執行閉環
            pos_max, _ = self.matcher.match(screen_img, max_btn, threshold=0.75)
            matched_blood = None
            for quality, enabled in sacrifice_settings.items():
                if not enabled:
                    continue
                temp_path = blood_templates.get(quality)
                if temp_path and os.path.exists(os.path.join("templates", temp_path)):
                    pos_blood, conf = self.matcher.match(screen_img, temp_path, threshold=0.75)
                    if pos_blood:
                        matched_blood = (quality, temp_path, pos_blood)
                        break

            if matched_blood:
                q_name, q_path, q_pos = matched_blood
                logging.info(f"🩸 [血之祭壇] 找到可獻祭血水 [{q_name}] ({q_path})，點擊選擇...")
                self.mouse.click(left + q_pos[0], top + q_pos[1])
                time.sleep(0.2)

                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else None
                if latest_img is not None:
                    pos_max_now, _ = self.matcher.match(latest_img, max_btn, threshold=0.75)
                    if pos_max_now:
                        pos_max = pos_max_now

                if pos_max:
                    logging.info(f"🩸 [血之祭壇] 點擊 MAX 數量按鈕 [{max_btn}]...")
                    self.mouse.click(left + pos_max[0], top + pos_max[1])
                    time.sleep(0.15)

                if latest_img is not None:
                    pos_alter_now, _ = self.matcher.match(latest_img, alter_btn, threshold=0.75)
                    if pos_alter_now:
                        pos_alter = pos_alter_now

                if pos_alter:
                    logging.info(f"🩸 [血之祭壇] 點擊獻祭執行按鈕 [{alter_btn}]...")
                    self.mouse.click(left + pos_alter[0], top + pos_alter[1])

                self.empty_blood_scan_count = 0
                self.last_action_time = now
                return True

            self.empty_blood_scan_count += 1
            logging.info(f"🩸 [血之祭壇] 畫面暫無可獻祭血水 (連續第 {self.empty_blood_scan_count}/3 幀確認)...")

            if self.empty_blood_scan_count >= 3:
                logging.info("🩸 [血之祭壇] 連續 3 幀無可獻祭血水，判定全數獻祭完成！進入 ALL_DONE_EXITING 階段...")
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return True

        # =========================================================================
        # 6. ALL_DONE_EXITING 階段：離開建築返回城鎮
        # =========================================================================
        elif self.step_phase == "ALL_DONE_EXITING":
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, _ = self.matcher.match(screen_img, building_btn, threshold=0.75)
            if pos_door or pos_building:
                logging.info("✅ [血之祭壇] 偵測到已處於城鎮畫面，完成領血與獻祭流程！")
                self._record_completion()
                self.last_action_time = now
                return True

            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            if pos_quit:
                logging.info("🩸 [血之祭壇] 點擊關閉視窗 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                return True

            pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            if pos_exit:
                logging.info(f"🩸 [血之祭壇] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
                self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                self._record_completion()
                self.last_action_time = now
                return True

        return False
