import os
import time
import logging
from typing import Tuple, Optional
from states.exceptions.subflows.base import BaseExceptionSubflow, safe_match


class RaidBoxSubflow(BaseExceptionSubflow):
    """
    懸賞/掃蕩對話框 (Raid_Box.png) Subflow (Pure Execution)。
    處置流程：
    1. 全圖配對 Raid_Box.png 取得座標 ROI
    2. 切割 Raid_Box 區域，僅於 ROI 內部配對 cancel.png 並發起點擊
    """
    name: str = "raid_box_subflow"

    def __init__(self):
        self.box_templates = ["exceptions/Raid_Box.png", "Raid_Box.png"]
        self.cancel_templates = ["exceptions/cancel.png", "cancel.png"]

    def _find_box(self, screen_img, matcher) -> Tuple[Optional[Tuple[int, int]], str]:
        for tpl in self.box_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.75)
                if pos:
                    return pos, tpl
        return None, ""

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        pos, _ = self._find_box(screen_img, matcher)
        return pos is not None

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        pos_box, tpl_box = self._find_box(screen_img, matcher)
        if not pos_box:
            return True

        box_x, box_y = pos_box

        # 若帶有圖片物件，切割 Raid_Box 區域進行 Scoped Match
        raid_crop = screen_img
        if screen_img is not None and hasattr(screen_img, "shape") and len(screen_img.shape) >= 2:
            h, w = screen_img.shape[:2]
            raid_crop = screen_img[max(0, box_y):min(h, box_y + 600), max(0, box_x):min(w, box_x + 800)]

        pos_cancel, conf_cancel = None, 0.0
        for cancel_tpl in self.cancel_templates:
            if os.path.exists(os.path.join("templates", cancel_tpl)):
                pos_cancel, conf_cancel = safe_match(matcher, raid_crop, cancel_tpl, threshold=0.75)
                if pos_cancel:
                    break

        if pos_cancel:
            abs_x = rect["left"] + box_x + pos_cancel[0]
            abs_y = rect["top"] + box_y + pos_cancel[1]
            logging.info(f"🛡️ [{self.name}] 成功在 Raid_Box ROI 內部匹配 cancel.png (相對: {pos_cancel})，發起絕對點擊: ({abs_x}, {abs_y})")
            if mouse:
                mouse.click(abs_x, abs_y)
            time.sleep(0.5)
            return True
        else:
            # 備援：若未精確比對到 cancel，點擊 box 中央或相對預設點
            cx = rect["left"] + box_x + 100
            cy = rect["top"] + box_y + 300
            logging.info(f"🛡️ [{self.name}] 未在 Raid_Box ROI 內匹配到 cancel，點擊備援相對點: ({cx}, {cy})")
            if mouse:
                mouse.click(cx, cy)
            time.sleep(0.5)
            return True
