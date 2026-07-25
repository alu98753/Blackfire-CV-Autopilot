import time
import os
import sys
import logging
import cv2
from states.handlers.base import BaseStateHandler


class BloodAltarHandler(BaseStateHandler):
    """
    血之祭壇 (Blood Altar) 處理器：
    1. 於城鎮點擊祭壇建築 (Blood_Altar.png) 進入建築 (INIT -> ENTERED_BUILDING)。
    2. 領取每日免費血水/體力 (RECEIVE_TAB_OPEN -> HANDLING_RECEIVE_POPUPS)：
       - 點擊領水頁籤 (receive_entry.png)。
       - 點擊每日領取按鈕 (receive_daily.png)。
       - 處理領取確認/關閉彈窗 (confirm.png / ok.png / quit.png)。
    3. (選用) 獻祭功能 (SACRIFICE_MENU_OPEN)：
       - 若畫面有 Sacrifice.png，進行血水點擊 ➔ alter.png 獻祭。
       - 當連續 3 幀無任何可獻祭血水時，轉移至 ALL_DONE_EXITING。
    4. 退出階段 (ALL_DONE_EXITING)：
       - 點擊離開建築按鈕 (exitfromhouse_and_to_town.png) 返回城鎮。
       - 於 DailyManager 記錄 blood_altar 完成，消費佇列中的下一個任務。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, RECEIVE_TAB_OPEN, HANDLING_RECEIVE_POPUPS, SACRIFICE_MENU_OPEN, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0
        self.has_claimed_daily = False

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0
        self.has_claimed_daily = False

    def _ensure_in_town(self, screen_img, rect=None):
        """
        獨立導航輔助函式：若目前位於大廳 (看得到 goback_town.png)，點擊返回城鎮。
        :return: True 代表目前已在城鎮/建築內；False 代表正在點擊退回城鎮中。
        """
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("🩸 [血之祭壇] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
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
            return

        now = time.time()
        if now - self.last_action_time < 0.8:
            return

        # 優先檢查是否需要從小圖示大廳退回城鎮 (Return to Town)
        if not self._ensure_in_town(screen_img, rect):
            return

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

        # 🔍 視覺化除錯：對當前畫面比對所有相關模板，印出最高相似度與座標，並畫圖存為 debug_blood_altar_detect.png
        try:
            debug_img = screen_img.copy()
            debug_templates = [
                ("building", building_btn),
                ("door", "common/door.png"),
                ("sacrifice", sacrifice_btn),
                ("rec_entry", receive_entry_btn),
                ("rec_daily", receive_daily_btn),
                ("exit", exit_building_btn),
            ]
            for label, temp_name in debug_templates:
                pos, conf = self.matcher.match(screen_img, temp_name, threshold=0.1, quiet=True)
                if pos:
                    cx, cy = pos
                    cv2.circle(debug_img, (cx, cy), 6, (0, 255, 0), -1)
                    cv2.putText(debug_img, f"{label}:{conf:.3f}", (cx + 10, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    logging.info(f"🩸 [血之祭壇 Debug 掃描] 模板 [{label} -> {temp_name}] 最高相似度: {conf:.4f} @ 座標 ({cx}, {cy})")
                else:
                    logging.info(f"🩸 [血之祭壇 Debug 掃描] 模板 [{label} -> {temp_name}] 最高相似度: {conf:.4f} (未能匹配)")
            cv2.imwrite("debug_blood_altar_detect.png", debug_img)
        except Exception as debug_err:
            logging.debug(f"無法寫入 debug_blood_altar_detect.png: {debug_err}")

        # =========================================================================
        # 1. 領取每日免費血水階段 (RECEIVE_TAB_OPEN / HANDLING_RECEIVE_POPUPS)
        # =========================================================================

        if self.step_phase == "RECEIVE_TAB_OPEN":
            pos_rec_daily, _ = self.matcher.match(screen_img, receive_daily_btn, threshold=0.75)
            if pos_rec_daily:
                logging.info(f"🩸 [血之祭壇] 發現每日領血按鈕 [{receive_daily_btn}]，點擊領取免費血水！")
                self.mouse.click(left + pos_rec_daily[0], top + pos_rec_daily[1])
                self.has_claimed_daily = True
                self.step_phase = "HANDLING_RECEIVE_POPUPS"
                self.last_action_time = now
                return

            # 若未看到領取按鈕（可能已領取或仍在彈窗中），轉至彈窗處理或結束/獻祭
            self.step_phase = "HANDLING_RECEIVE_POPUPS"

        if self.step_phase == "HANDLING_RECEIVE_POPUPS":
            pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
            pos_ok, _ = self.matcher.match(screen_img, "common/ok.png", threshold=0.8)
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            
            if pos_confirm:
                logging.info("🩸 [血之祭壇] 點擊領取確認按鈕 [common/confirm.png]...")
                self.mouse.click(left + pos_confirm[0], top + pos_confirm[1])
                self.last_action_time = now
                return
            elif pos_ok:
                logging.info("🩸 [血之祭壇] 點擊領取 OK 按鈕 [common/ok.png]...")
                self.mouse.click(left + pos_ok[0], top + pos_ok[1])
                self.last_action_time = now
                return
            elif pos_quit:
                logging.info("🩸 [血之祭壇] 點擊領取關閉按鈕 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                return

            # 彈窗關閉後，若看到離場按鈕或獻祭按鈕，代表領取完畢
            pos_exit_check, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            pos_sac_check, _ = self.matcher.match(screen_img, sacrifice_btn, threshold=0.75)
            if pos_exit_check or pos_sac_check:
                logging.info("🩸 [血之祭壇] 每日領血彈窗已關閉，完成領血步驟！")
                # 若無獻祭需求或已有獻祭按鈕可選，檢查是否轉入 ALL_DONE_EXITING
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return

        # =========================================================================
        # 2. 獻祭選單開啟狀態 (SACRIFICE_MENU_OPEN) - 嚴格隔離模式
        # =========================================================================
        if self.step_phase == "SACRIFICE_MENU_OPEN":
            # 通用防呆：若出現 common/confirm.png 彈窗，優先點擊確認
            pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
            if pos_confirm:
                logging.info("🩸 [血之祭壇] 點擊獻祭確認按鈕 [common/confirm.png]...")
                self.mouse.click(left + pos_confirm[0], top + pos_confirm[1])
                self.last_action_time = now
                return

            max_btn = cfg.get("max_btn", "town_building/sell_max.png")
            pos_alter, _ = self.matcher.match(screen_img, alter_btn, threshold=0.75)
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
                time.sleep(0.3)
                
                latest_img = self.capturer.capture(rect) if (self.capturer and rect) else None
                if latest_img is not None:
                    pos_max_now, _ = self.matcher.match(latest_img, max_btn, threshold=0.75)
                    if pos_max_now:
                        pos_max = pos_max_now

                # 若有 MAX 數量按鈕，點擊拉滿數量
                if pos_max:
                    logging.info(f"🩸 [血之祭壇] 點擊 MAX 數量按鈕 [{max_btn}]...")
                    self.mouse.click(left + pos_max[0], top + pos_max[1])
                    time.sleep(0.2)

                if latest_img is not None:
                    pos_alter_now, _ = self.matcher.match(latest_img, alter_btn, threshold=0.75)
                    if pos_alter_now:
                        pos_alter = pos_alter_now

                # 若有 alter.png 按鈕，直接點擊獻祭
                if pos_alter:
                    logging.info(f"🩸 [血之祭壇] 點擊獻祭執行按鈕 [{alter_btn}]...")
                    self.mouse.click(left + pos_alter[0], top + pos_alter[1])
                
                self.empty_blood_scan_count = 0  # 重置無血水掃描計數
                self.last_action_time = now
                return

            # 若畫面上完全沒有符合品質的血水，增加計數
            self.empty_blood_scan_count += 1
            logging.info(f"🩸 [血之祭壇] 畫面暫無可獻祭血水 (連續第 {self.empty_blood_scan_count}/3 幀確認)...")
            
            # 只有連續 3 幀確認皆無血水，才判定「全數獻祭完成」，轉移至 ALL_DONE_EXITING 退出階段
            if self.empty_blood_scan_count >= 3:
                logging.info("🩸 [血之祭壇] 連續 3 幀確認無任何可獻祭血水，判定全數獻祭完成！進入退出階段...")
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
            return

        # =========================================================================
        # 3. 退出階段 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
            pos_building, _ = self.matcher.match(screen_img, building_btn, threshold=0.75)
            if pos_door or pos_building:
                logging.info("✅ [血之祭壇] 偵測到目前已處於城鎮大門畫面，視為已退回城鎮，完成領血與獻祭流程！")
                self._record_completion()
                self.last_action_time = now
                return

            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            if pos_quit:
                logging.info("🩸 [血之祭壇] 點擊關閉視窗 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                return

            pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            if pos_exit:
                logging.info(f"🩸 [血之祭壇] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
                self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                self._record_completion()
                self.last_action_time = now
                return

        # =========================================================================
        # 4. 城鎮與建築內起點階段 (INIT / ENTERED_BUILDING)
        # =========================================================================
        # 4.1 檢查是否在建築物內部 (若尚未領取且看得到領水頁籤，優先點擊頁籤)
        is_claimed_today = self.has_claimed_daily or self._is_blood_altar_claimed_today()
        pos_rec_entry, _ = self.matcher.match(screen_img, receive_entry_btn, threshold=0.75)

        pos_rec_daily, _ = self.matcher.match(screen_img, receive_daily_btn, threshold=0.75)

        if not is_claimed_today and pos_rec_entry:
            logging.info(f"🩸 [血之祭壇] 辨識到領血頁籤 [{receive_entry_btn}]，點擊切換至領血介面...")
            self.mouse.click(left + pos_rec_entry[0], top + pos_rec_entry[1])
            self.step_phase = "RECEIVE_TAB_OPEN"
            self.last_action_time = now
            return
        elif not is_claimed_today and pos_rec_daily and self.step_phase == "RECEIVE_TAB_OPEN":
            logging.info(f"🩸 [血之祭壇] 已在領血介面，點擊每日領取按鈕 [{receive_daily_btn}]...")
            self.mouse.click(left + pos_rec_daily[0], top + pos_rec_daily[1])
            self.has_claimed_daily = True
            self.step_phase = "HANDLING_RECEIVE_POPUPS"
            self.last_action_time = now
            return

        pos_sac, conf_sac = self.matcher.match(screen_img, sacrifice_btn, threshold=0.85)
        pos_exit_init, conf_exit_init = self.matcher.match(screen_img, exit_building_btn, threshold=0.85)
        if pos_sac and pos_exit_init:
            if not is_claimed_today and pos_rec_entry:
                logging.info(f"🩸 [血之祭壇] 已在建築物內部，優先點擊領水頁籤 [{receive_entry_btn}]...")
                self.mouse.click(left + pos_rec_entry[0], top + pos_rec_entry[1])
                self.step_phase = "RECEIVE_TAB_OPEN"
                self.last_action_time = now
                return

        # 4.2 城鎮點擊祭壇建築 (Blood_Altar.png)
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        pos_building, conf_building = self.matcher.match(screen_img, building_btn, threshold=0.65)
        if pos_building and pos_door:
            logging.info(f"🩸 [血之祭壇] 於城鎮發現血之祭壇建築 [{building_btn}] (信心度: {conf_building:.4f})，點擊進入...")
            self.mouse.click(left + pos_building[0], top + pos_building[1])
            self.step_phase = "ENTERED_BUILDING"
            self.building_search_count = 0
            self.last_action_time = now
            return

        if pos_sac:
            if not is_claimed_today and pos_rec_entry:
                logging.info(f"🩸 [血之祭壇] 點擊領水頁籤 [{receive_entry_btn}]...")
                self.mouse.click(left + pos_rec_entry[0], top + pos_rec_entry[1])


                self.step_phase = "RECEIVE_TAB_OPEN"
            else:
                logging.info(f"🩸 [血之祭壇] 點擊獻祭功能選單 [{sacrifice_btn}]...")
                self.mouse.click(left + pos_sac[0], top + pos_sac[1])
                self.step_phase = "SACRIFICE_MENU_OPEN"
                self.empty_blood_scan_count = 0
            self.last_action_time = now
            return

