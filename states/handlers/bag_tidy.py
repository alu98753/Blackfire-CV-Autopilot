"""
城鎮背包整理獨立子流程處理器 (Bag Tidy Subflow Handler)

負責在城鎮中打開背包、點擊整理按鈕使物品自動排序靠齊、關閉背包，
並嚴格執行 Postcondition Verification（確保背包完全關閉消失且畫面恢復為純淨城鎮基準場景）
後才結案交棒，徹底與珠寶店等業務流程解耦。
"""

import os
import time
import logging
import numpy as np
from states.handlers.base import BaseStateHandler


class BagTidyHandler(BaseStateHandler):
    """
    背包整理獨立子流程處理器。
    非破壞性純排序（Tidy Only），不執行大量分解與裝備銷毀。
    """

    def __init__(self, machine):
        super().__init__(machine)
        self.step_phase = "INIT"  # INIT, WAIT_BAG_OPEN, WAIT_TIDY_SETTLE, CLOSE_AND_VERIFY
        self.last_action_time = 0.0
        self.start_time = 0.0

    def reset_state(self):
        """重置處理器所有階段狀態"""
        self.step_phase = "INIT"
        self.last_action_time = 0.0
        self.start_time = 0.0

    def is_backpack_opened(self, screen_img) -> bool:
        """檢測背包是否已處於開啟狀態 (看得到 tidy 或 Disassembly)"""
        for feature in ["common/tidy.png", "common/Disassembly.png", "common/Backpack_Disassembly.png"]:
            if os.path.exists(os.path.join("templates", feature)):
                pos, _ = self.matcher.match(screen_img, feature, threshold=0.75, quiet=True)
                if pos:
                    return True
        return False

    def open_backpack(self, screen_img, rect) -> bool:
        """偵測並點擊開啟背包 (優先比對「物品欄」文字，備用比對背包圖標)"""
        pos_text, conf_text = self.matcher.match(screen_img, "common/bag_text.png", threshold=0.70, quiet=True)
        if pos_text:
            logging.info("🎒 [城鎮背包整理] 偵測到背包入口文字「物品欄」 (%.4f)，點擊打開背包...", conf_text)
            self.notify_ui_progress()
            self.mouse.click(rect["left"] + pos_text[0], rect["top"] + pos_text[1] - 45)
            return True

        pos_bag, conf_bag = self.matcher.match(screen_img, "common/bag.png", threshold=0.72, quiet=True)
        if pos_bag:
            h_limit, w_limit = screen_img.shape[:2]
            c_x1, c_x2 = max(0, pos_bag[0] - 5), min(w_limit, pos_bag[0] + 5)
            c_y1, c_y2 = max(0, pos_bag[1] - 5), min(h_limit, pos_bag[1] + 5)
            center_crop = screen_img[c_y1:c_y2, c_x1:c_x2]
            is_real = np.max(center_crop) > 0 if center_crop.size > 0 else False
            r_minus_b = (np.mean(center_crop, axis=(0, 1))[2] - np.mean(center_crop, axis=(0, 1))[0]) if is_real else 99.0

            if r_minus_b > 18.0:
                logging.info("🎒 [城鎮背包整理] 偵測到背包圖標入口 (%.4f, R-B: %.1f)，點擊打開背包...", conf_bag, r_minus_b)
                self.notify_ui_progress()
                self.mouse.click(rect["left"] + pos_bag[0], rect["top"] + pos_bag[1])
                return True
        return False

    def handle(self, screen_img=None, rect=None):
        if screen_img is None and self.capturer:
            rect = rect or self.capturer.get_window_rect()
            if rect:
                screen_img = self.capturer.capture(rect)
        if screen_img is None:
            return

        now = time.time()
        if self.start_time == 0.0:
            self.start_time = now

        # 防卡死超時保護 (20 秒上限)
        if now - self.start_time > 20.0:
            logging.warning("⚠️ [城鎮背包整理] 執行超過 20 秒逾時，嘗試關閉背包並退出自癒...")
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.75, quiet=True)
            if pos_quit:
                left = rect["left"] if rect else 0
                top = rect["top"] if rect else 0
                self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, threshold=0.75)
            self.reset_state()
            self.machine.pop_and_next_town_subflow()
            return

        # 動作頻率限制 (至少間隔 0.2 秒)
        if now - self.last_action_time < 0.2:
            return

        left = rect["left"] if rect else 0
        top = rect["top"] if rect else 0

        # =========================================================================
        # 階段 1：INIT (確認環境並發起開包)
        # =========================================================================
        if self.step_phase == "INIT":
            # 若背包已經開啟，直接進入等待整理
            if self.is_backpack_opened(screen_img):
                logging.info("🎒 [城鎮背包整理 INIT] 畫面已見開啟的背包，直接進入整理階段...")
                self.step_phase = "WAIT_BAG_OPEN"
                self.last_action_time = now
                return

            # 若畫面上有非背包的殘留 quit 覆蓋層，優先閉環清理
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.80, quiet=True)
            pos_door, _ = self.matcher.match(screen_img, "common/door.png", threshold=0.75, quiet=True)
            if pos_quit and not pos_door:
                logging.warning("⚠️ [城鎮背包整理 INIT] 偵測到殘留覆蓋層 (quit 可見)，優先閉環關閉...")
                self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, timeout=3.0, threshold=0.80)
                self.last_action_time = time.time()
                return

            # 正常城鎮環境：點擊開包
            if pos_door:
                if self.open_backpack(screen_img, rect):
                    self.step_phase = "WAIT_BAG_OPEN"
                    self.last_action_time = now
                return
            return

        # =========================================================================
        # 階段 2：WAIT_BAG_OPEN (等待背包就緒並點擊整理)
        # =========================================================================
        if self.step_phase == "WAIT_BAG_OPEN":
            pos_tidy, conf_tidy = self.matcher.match(screen_img, "common/tidy.png", threshold=0.80, quiet=True)
            if pos_tidy:
                logging.info("🎒 [城鎮背包整理] 背包已展開，偵測到整理按鈕 (%.4f)，點擊整理...", conf_tidy)
                self.notify_ui_progress()
                self.mouse.click(left + pos_tidy[0], top + pos_tidy[1])
                self.step_phase = "WAIT_TIDY_SETTLE"
                self.last_action_time = now
                return

            # 若超過 2.5 秒未看到 tidy，重試開包
            if now - self.last_action_time > 2.5:
                logging.info("🎒 [城鎮背包整理] 等待開包逾時，重新嘗試點擊開啟背包...")
                self.step_phase = "INIT"
                self.last_action_time = now
            return

        # =========================================================================
        # 階段 3：WAIT_TIDY_SETTLE (等待整理渲染完成)
        # =========================================================================
        if self.step_phase == "WAIT_TIDY_SETTLE":
            # 靜置至少 0.2 秒以等待遊戲內格子排序動畫
            if now - self.last_action_time < 0.2:
                return

            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.80, quiet=True)
            if pos_quit:
                self.step_phase = "CLOSE_AND_VERIFY"
                self.last_action_time = now
            return

        # =========================================================================
        # 階段 4：CLOSE_AND_VERIFY (關閉背包並嚴格驗證 Postcondition)
        # =========================================================================
        if self.step_phase == "CLOSE_AND_VERIFY":
            pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.80, quiet=True)
            if pos_quit:
                logging.info("🎒 [城鎮背包整理] 點擊關閉按鈕，啟動配對確認直到消失閉環...")
                self.click_and_wait_until_gone("common/quit.png", left + pos_quit[0], top + pos_quit[1], rect, timeout=4.0, threshold=0.80)

            # 核心 Postcondition 驗證：
            fresh_img = self.capturer.capture(rect) if self.capturer else screen_img
            chk_quit, _ = self.matcher.match(fresh_img, "common/quit.png", threshold=0.80, quiet=True)
            chk_tidy, _ = self.matcher.match(fresh_img, "common/tidy.png", threshold=0.80, quiet=True)
            chk_door, _ = self.matcher.match(fresh_img, "common/door.png", threshold=0.75, quiet=True)

            if chk_quit is None and chk_tidy is None and chk_door is not None:
                logging.info("✅ [城鎮背包整理] 後置條件驗證通過：背包已徹底關閉且恢復乾淨城鎮，結案交棒！")
                self.reset_state()
                self.machine.pop_and_next_town_subflow()
                return
            else:
                logging.warning("⚠️ [城鎮背包整理] 後置條件尚未完全滿足 (quit=%s, tidy=%s, door=%s)，等待畫面淡出...",
                                bool(chk_quit), bool(chk_tidy), bool(chk_door))
                self.last_action_time = now
                return
