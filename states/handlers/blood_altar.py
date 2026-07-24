import time
import os
import logging
from states.handlers.base import BaseStateHandler

class BloodAltarHandler(BaseStateHandler):
    """
    血之祭壇獻祭 (Blood Altar) 處理器：
    1. 於城鎮點擊祭壇建築 (Blood_Altar.png) 進入建築 (進入 ENTERED_BUILDING)。
    2. 點擊獻祭功能選單 (Sacrifice.png) 進入 SACRIFICE_MENU_OPEN。
    3. 嚴格獻祭隔離模式 (SACRIFICE_MENU_OPEN)：
       - 封鎖 Blood_Altar.png / quit.png / exitfromhouse_and_to_town.png 比對。
       - 僅允許比對: confirm.png、啟用的血水 (gray/green/blue/purple)、alter.png。
       - 依據配置點擊各品質血水 ➔ 點擊 alter.png ➔ 點擊 confirm.png。
       - 當連續 3 幀無任何可獻祭血水 (empty_blood_scan_count >= 3) 時，判定全數獻祭完成 ➔ 進入 ALL_DONE_EXITING 階段。
    4. 退出階段 (ALL_DONE_EXITING)：
       - 點擊關閉視窗 (quit.png)。
       - 點擊離開建築按鈕 (exitfromhouse_and_to_town.png) 返回城鎮。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, SACRIFICE_MENU_OPEN, ALL_DONE_EXITING
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.empty_blood_scan_count = 0

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
        sacrifice_btn = cfg.get("sacrifice_btn", "town_building/Blood_Altar/Sacrifice.png")
        alter_btn = cfg.get("alter_btn", "town_building/Blood_Altar/alter.png")
        exit_building_btn = cfg.get("exit_building_btn", "town_building/exitfromhouse_and_to_town.png")
        sacrifice_settings = cfg.get("sacrifice_settings", {
            "gray": True,
            "green": True,
            "blue": True,
            "purple": False,
        })
        blood_templates = cfg.get("blood_templates", {
            "gray": "town_building/Blood_Altar/gray_blood.png",
            "green": "town_building/Blood_Altar/green_blood.png",
            "blue": "town_building/Blood_Altar/blue_blood.png",
            "purple": "town_building/Blood_Altar/purple_blood.png",
        })

        # 0. 通用防呆：若出現 common/confirm.png 彈窗，優先點擊確認
        pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_confirm:
            logging.info("🩸 [血之祭壇] 點擊通用確認按鈕 [common/confirm.png]...")
            self.mouse.click(left + pos_confirm[0], top + pos_confirm[1])
            self.last_action_time = now
            return

        # =========================================================================
        # 1. 嚴格獻祭選單開啟狀態 (SACRIFICE_MENU_OPEN) - 嚴格隔離模式
        # =========================================================================
        if self.step_phase == "SACRIFICE_MENU_OPEN":
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

            # 如果單獨看到 alter.png，且剛剛有選擇血水
            if pos_alter:
                logging.info(f"🩸 [血之祭壇] 點擊獻祭執行按鈕 [{alter_btn}]...")
                self.mouse.click(left + pos_alter[0], top + pos_alter[1])
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
        # 2. 退出階段 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
            if pos_quit:
                logging.info("🩸 [血之祭壇] 獻祭全數完成，點擊關閉視窗 [common/quit.png]...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.last_action_time = now
                return

            pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
            if pos_exit:
                logging.info(f"🩸 [血之祭壇] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
                self.mouse.click(left + pos_exit[0], top + pos_exit[1])
                self.reset_state()
                self.last_action_time = now
                
                if cfg.get("type") == "blood_altar":
                    logging.info("✅ [血之祭壇] 獨立單次獻祭流程完成！切換至 UNKNOWN 進行下一輪巡檢...")
                    self.machine.transition_to(self.machine.STATE_UNKNOWN)
                return
            return

        # =========================================================================
        # 3. 城鎮階段 (INIT) ➔ 進入建築 ➔ 點擊 Sacrifice.png
        # =========================================================================
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        pos_building, _ = self.matcher.match(screen_img, building_btn, threshold=0.75)
        if pos_building and (pos_door or self.step_phase == "INIT"):
            logging.info(f"🩸 [血之祭壇] 於城鎮發現血之祭壇建築 [{building_btn}]，點擊進入...")
            self.mouse.click(left + pos_building[0], top + pos_building[1])
            self.step_phase = "ENTERED_BUILDING"
            self.last_action_time = now
            return

        pos_sac, _ = self.matcher.match(screen_img, sacrifice_btn, threshold=0.75)
        if pos_sac:
            logging.info(f"🩸 [血之祭壇] 發現獻祭功能選單 [{sacrifice_btn}]，點擊開啟選單...")
            self.mouse.click(left + pos_sac[0], top + pos_sac[1])
            self.step_phase = "SACRIFICE_MENU_OPEN"
            self.empty_blood_scan_count = 0  # 剛開啟選單，重置掃描計數
            self.last_action_time = now
            return
