import time
import os
import logging
import numpy as np
from states.handlers.base import BaseStateHandler

class BulletinBoardHandler(BaseStateHandler):
    """
    每日懸賞告示牌 (Bulletin Board) 處理器 - 第一階段：
    1. 確認與進入城鎮 (INIT)：
       - 以 _ensure_in_town 確保在城鎮介面。
       - 專精限制於螢幕左上 1/4 區域 (screen_img[0:h//2, 0:w//2]) 匹配並點擊告示牌 (bulletin_board.png)。
    2. 等待開窗確認 (WAIT_BOARD_OPEN)：
       - 必須先等待並確認 common/quit.png 出現，作為 100% 成功進入告示牌的憑據。
    3. 條件式重置檢查 (CHECK_RESET)：
       - 若看得到 reset.png 則點擊重置；若未看到則記錄日誌並跳過該步驟。
    4. 最終退出步驟 (EXIT_BOARD)：
       - 點擊 common/quit.png 退出告示牌視窗。
    5. 階段完成與佇列連動 (ALL_DONE_EXITING)：
       - 於 DailyManager 記錄 bulletin_board 完成，重置狀態並呼叫 pop_and_next_town_subflow()。
    """
    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, WAIT_BOARD_OPEN, CHECK_RESET, EXIT_BOARD, ALL_DONE_EXITING
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
        logging.info("📋 [懸賞告示牌] 第一階段重置與退出流程完成，消費城鎮佇列中的下一個任務...")
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
        quit_btn = cfg.get("quit_btn", "common/quit.png")

        # =========================================================================
        # 1. 紀錄與階段完成 (ALL_DONE_EXITING)
        # =========================================================================
        if self.step_phase == "ALL_DONE_EXITING":
            self._record_completion()
            self.last_action_time = now
            return

        # =========================================================================
        # 2. 最終退出步驟：點擊 quit.png (EXIT_BOARD)
        # =========================================================================
        if self.step_phase == "EXIT_BOARD":
            pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.75)
            if pos_quit:
                logging.info(f"📋 [懸賞告示牌] 點擊關閉視窗按鈕 [{quit_btn}] 退出告示牌介面...")
                self.mouse.click(left + pos_quit[0], top + pos_quit[1])
                self.step_phase = "ALL_DONE_EXITING"
                self.last_action_time = now
                return
            
            # 若已看不到 quit.png，說明已離開告示牌介面
            logging.info("📋 [懸賞告示牌] 已無視窗退出按鈕 (回到城鎮)，完成離場步驟。")
            self.step_phase = "ALL_DONE_EXITING"
            self.last_action_time = now
            return

        # =========================================================================
        # 3. 條件式重置檢查：若無 reset.png 則自動跳過 (CHECK_RESET)
        # =========================================================================
        if self.step_phase == "CHECK_RESET":
            pos_reset, _ = self.matcher.match(screen_img, reset_btn, threshold=0.75)
            if pos_reset:
                logging.info(f"📋 [懸賞告示牌] 發現重置按鈕 [{reset_btn}]，點擊執行重置！")
                self.mouse.click(left + pos_reset[0], top + pos_reset[1])
                self.step_phase = "EXIT_BOARD"
                self.last_action_time = now
                return
            else:
                logging.info(f"📋 [懸賞告示牌] 未發現重置按鈕 [{reset_btn}] (無需重新整理或已重置)，跳過該步驟！")
                self.step_phase = "EXIT_BOARD"
                self.last_action_time = now
                return

        # =========================================================================
        # 4. 等待開窗：先確認 quit.png 出現才算真正進入告示牌 (WAIT_BOARD_OPEN)
        # =========================================================================
        pos_quit, _ = self.matcher.match(screen_img, quit_btn, threshold=0.75)
        if self.step_phase == "WAIT_BOARD_OPEN":
            if pos_quit:
                logging.info(f"📋 [懸賞告示牌] 偵測到 [{quit_btn}]，確認已成功進入告示牌介面！進行重置判斷...")
                self.step_phase = "CHECK_RESET"
                self.last_action_time = now
                return
            return

        # =========================================================================
        # 5. 城鎮點擊告示牌建築 (INIT / 左上 1/4 區域 Scoped Crop 精確比對)
        # =========================================================================
        if pos_quit:
            logging.info(f"📋 [懸賞告示牌] 辨識到目前已在告示牌介面 (發現 {quit_btn})，準備進行重置判斷...")
            self.step_phase = "CHECK_RESET"
            self.last_action_time = now
            return

        pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75)
        if pos_door:
            h = rect["height"] if rect else (screen_img.shape[0] if isinstance(screen_img, np.ndarray) else 600)
            w = rect["width"] if rect else (screen_img.shape[1] if isinstance(screen_img, np.ndarray) else 800)
            top_left_crop = screen_img[0:h // 2, 0:w // 2] if isinstance(screen_img, np.ndarray) else screen_img
            pos_bb, conf_bb = self.matcher.match(top_left_crop, building_btn, threshold=0.75)
            
            if pos_bb:
                logging.info(f"📋 [懸賞告示牌] 於左上 1/4 區域精確發現告示牌建築 [{building_btn}] (信心度: {conf_bb:.4f})，點擊進入...")
                self.mouse.click(left + pos_bb[0], top + pos_bb[1])
                self.step_phase = "WAIT_BOARD_OPEN"
                self.last_action_time = now
                return
