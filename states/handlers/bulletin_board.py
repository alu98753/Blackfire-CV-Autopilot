import time
import os
import logging
from states.handlers.base import BaseStateHandler

class BulletinBoardHandler(BaseStateHandler):
    """
    每日懸賞告示牌 (Bulletin Board / Bounty) 處理器 - 第一階段：
    1. 確認於城鎮 (INIT)：
       - 先以 _ensure_in_town 確保在城鎮介面。
       - 專精限制於螢幕左上 1/4 區域 (screen_img[0:h//2, 0:w//2]) 匹配並點擊告示牌 (bulletin_board.png)。
    2. 點擊重置按鈕 (ENTERED_BUILDING)：
       - 進入告示牌後，匹配並點擊重置按鈕 (reset.png)。
    3. 第一階段完成 (ALL_DONE_EXITING)：
       - 於 DailyManager 記錄 bulletin_board 完成，重置 Handler 狀態並呼叫 pop_and_next_town_subflow()。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, ENTERED_BUILDING, ALL_DONE_EXITING
        self.last_action_time = 0.0

    def reset_state(self):
        self.step_phase = "INIT"
        self.last_action_time = 0.0

    def _ensure_in_town(self, screen_img, rect=None):
        """
        獨立導航輔助函式：若目前位於大廳 (看得到 goback_town.png)，點擊返回城鎮。
        :return: True 代表目前已在城鎮/建築內；False 代表正在點擊退回城鎮中。
        """
        pos_goback, _ = self.matcher.match(screen_img, "goback_town.png", threshold=0.8)
        if pos_goback:
            logging.info("📋 [懸賞告示牌] 偵測到目前處於大廳畫面，點擊 [goback_town.png] 返回城鎮...")
            left = rect["left"] if rect else 0
            top = rect["top"] if rect else 0
            self.mouse.click(left + pos_goback[0], top + pos_goback[1])
            self.last_action_time = time.time()
            return False
        return True

    def _record_completion(self):
        """記錄 DailyManager 完成狀態並自動切換至下一個城鎮任務"""
        self.reset_state()
        if hasattr(self.machine, "need_bulletin_board"):
            self.machine.need_bulletin_board = False
        dm = getattr(self.machine, "daily_manager", None)
        if dm and hasattr(dm, "record_subflow_completed"):
            dm.record_subflow_completed("bulletin_board")
        logging.info("📋 [懸賞告示牌] 第一階段重置流程完成，消費城鎮佇列中的下一個任務...")
        self.machine.pop_and_next_town_subflow()

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
        building_btn = cfg.get("building_btn", "town_building/bulletin_board/bulletin_board.png")
        reset_btn = cfg.get("reset_btn", "town_building/bulletin_board/reset.png")

        # =========================================================================
        # 1. 退出與紀錄階段 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            self._record_completion()
            self.last_action_time = now
            return

        # =========================================================================
        # 2. 告示牌介面內點擊重置按鈕 (ENTERED_BUILDING)
        # =========================================================================
        if self.step_phase == "ENTERED_BUILDING":
            pos_reset, _ = self.matcher.match(screen_img, reset_btn, threshold=0.75)
            if pos_reset:
                logging.info(f"📋 [懸賞告示牌] 發現重置按鈕 [{reset_btn}]，點擊執行重置！")
                self.mouse.click(left + pos_reset[0], top + pos_reset[1])
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return
            
            # 若已經找不到 reset 按鈕，可能重置已點擊，直接進入完成階段
            self.step_phase = "ALL_DONE_EXITING"
            return

        # =========================================================================
        # 3. 城鎮點擊告示牌建築 (INIT / 左上 1/4 區域精確比對)
        # =========================================================================
        pos_reset_check, _ = self.matcher.match(screen_img, reset_btn, threshold=0.75)
        if pos_reset_check:
            logging.info(f"📋 [懸賞告示牌] 辨識到目前已在告示牌介面，點擊重置按鈕 [{reset_btn}]...")
            self.mouse.click(left + pos_reset_check[0], top + pos_reset_check[1])
            self.step_phase = "ALL_DONE_EXITING"
            self.last_action_time = now
            return

        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        if pos_door:
            # 專精優化：螢幕左上 1/4 區域 (screen_img[0:h//2, 0:w//2]) Scoped Crop 局部比對
            import numpy as np
            h = rect["height"] if rect else (screen_img.shape[0] if isinstance(screen_img, np.ndarray) else 600)
            w = rect["width"] if rect else (screen_img.shape[1] if isinstance(screen_img, np.ndarray) else 800)
            top_left_crop = screen_img[0:h // 2, 0:w // 2] if isinstance(screen_img, np.ndarray) else screen_img
            pos_bb, conf_bb = self.matcher.match(top_left_crop, building_btn, threshold=0.75)
            
            if pos_bb:
                logging.info(f"📋 [懸賞告示牌] 於左上 1/4 區域精確發現告示牌建築 [{building_btn}] (信心度: {conf_bb:.4f})，點擊進入...")
                self.mouse.click(left + pos_bb[0], top + pos_bb[1])
                self.step_phase = "ENTERED_BUILDING"
                self.last_action_time = now
                return

