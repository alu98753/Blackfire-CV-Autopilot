import time
import os
import logging
from states.handlers.base import BaseStateHandler

class BloodAltarHandler(BaseStateHandler):
    """
    血之祭壇獻祭 (Blood Altar) 處理器：
    1. 於城鎮點擊祭壇建築 (Blood_Altar.png) 進入建築。
    2. 點擊獻祭功能選單 (Sacrifice.png)。
    3. 依據配置 (sacrifice_settings: {"gray": True, "green": True, "blue": True, "purple": False})，
       點擊各品質血水圖案 ➔ 點擊獻祭按鈕 (alter.png) ➔ 點擊確認按鈕 (confirm.png) 進行獻祭，直到無符合的血水。
    4. 點擊關閉按鈕 (quit.png) ➔ 點擊離開建築按鈕 (exitfromhouse_and_to_town.png) 返回城鎮。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, IN_SACRIFICE_MENU, SACRIFICING, EXITING
        self.last_action_time = 0.0

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0

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

        # 0. 防呆：若是看到 common/confirm.png 彈窗，優先點擊確認
        pos_confirm, _ = self.matcher.match(screen_img, "common/confirm.png", threshold=0.8)
        if pos_confirm:
            logging.info("🩸 [血之祭壇] 點擊通用確認按鈕 [common/confirm.png]...")
            self.mouse.click(pos_confirm[0], pos_confirm[1])
            self.last_action_time = now
            return

        # 1. 城鎮階段：尋找並點擊血之祭壇建築物 (Blood_Altar.png)
        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        pos_building, _ = self.matcher.match(screen_img, building_btn, threshold=0.75)
        if pos_building and (pos_door or self.step_phase == "INIT"):
            logging.info(f"🩸 [血之祭壇] 於城鎮發現血之祭壇建築 [{building_btn}]，點擊進入...")
            self.mouse.click(pos_building[0], pos_building[1])
            self.step_phase = "ENTERED_BUILDING"
            self.last_action_time = now
            return

        # 2. 建築內階段：點擊獻祭按鈕 (Sacrifice.png)
        pos_sac, _ = self.matcher.match(screen_img, sacrifice_btn, threshold=0.75)
        if pos_sac:
            logging.info(f"🩸 [血之祭壇] 發現獻祭功能選單 [{sacrifice_btn}]，點擊開啟選單...")
            self.mouse.click(pos_sac[0], pos_sac[1])
            self.step_phase = "IN_SACRIFICE_MENU"
            self.last_action_time = now
            return

        # 3. 獻祭執行階段：比對各品質血水並進行獻祭
        pos_alter, _ = self.matcher.match(screen_img, alter_btn, threshold=0.75)
        
        # 檢查是否有任何啟用的品質血水在畫面上
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
            self.mouse.click(q_pos[0], q_pos[1])
            time.sleep(0.3)
            
            # 若有 alter.png 按鈕，直接點擊獻祭
            if pos_alter:
                logging.info(f"🩸 [血之祭壇] 點擊獻祭執行按鈕 [{alter_btn}]...")
                self.mouse.click(pos_alter[0], pos_alter[1])
            
            self.step_phase = "SACRIFICING"
            self.last_action_time = now
            return

        # 若 alter.png 存在但畫面已無可獻祭的血水 (或已被點選完畢)，點擊 alter
        if pos_alter and self.step_phase == "SACRIFICING":
            logging.info(f"🩸 [血之祭壇] 點擊獻祭執行按鈕 [{alter_btn}]...")
            self.mouse.click(pos_alter[0], pos_alter[1])
            self.last_action_time = now
            return

        # 4. 退出階段：關閉視窗 (quit.png) 與離開建築 (exitfromhouse_and_to_town.png)
        pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.8)
        if pos_quit:
            logging.info("🩸 [血之祭壇] 無更多可獻祭血水，點擊關閉視窗 [common/quit.png]...")
            self.mouse.click(pos_quit[0], pos_quit[1])
            self.step_phase = "EXITING"
            self.last_action_time = now
            return

        pos_exit, _ = self.matcher.match(screen_img, exit_building_btn, threshold=0.75)
        if pos_exit:
            logging.info(f"🩸 [血之祭壇] 點擊離開建築按鈕 [{exit_building_btn}] 返回城鎮...")
            self.mouse.click(pos_exit[0], pos_exit[1])
            self.reset_state()
            self.last_action_time = now
            
            if cfg.get("type") == "blood_altar":
                logging.info("✅ [血之祭壇] 獨立單次獻祭流程完成！切換至 UNKNOWN 進行下一輪巡檢...")
                self.machine.transition_to(self.machine.STATE_UNKNOWN)
            return

        # 5. Fallback 預備
        if self.step_phase == "EXITING" and pos_door:
            logging.info("✅ [血之祭壇] 已成功返回城鎮大門畫面！")
            self.reset_state()
            if cfg.get("type") == "blood_altar":
                self.machine.transition_to(self.machine.STATE_UNKNOWN)
