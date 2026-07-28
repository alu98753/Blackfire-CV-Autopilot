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

        # 1. 嘗試於 Raid_Box ROI 內部進行關閉按鈕匹配 (使用較寬鬆門檻 0.65 以相容背景透明度)
        crop_top = max(0, box_y)
        crop_left = max(0, box_x)
        raid_crop = screen_img
        if screen_img is not None and hasattr(screen_img, "shape") and len(screen_img.shape) >= 2:
            h, w = screen_img.shape[:2]
            raid_crop = screen_img[crop_top:min(h, box_y + 650), crop_left:min(w, box_x + 850)]

        cancel_candidates = [
            "exceptions/cancel.png"
        ]

        pos_cancel, conf_cancel = None, 0.0
        for cancel_tpl in cancel_candidates:
            if os.path.exists(os.path.join("templates", cancel_tpl)):
                pos_cancel, conf_cancel = safe_match(matcher, raid_crop, cancel_tpl, threshold=0.65)
                if pos_cancel:
                    abs_x = rect["left"] + crop_left + pos_cancel[0]
                    abs_y = rect["top"] + crop_top + pos_cancel[1]
                    logging.info(f"🛡️ [{self.name}] 成功在 Raid_Box ROI 內部匹配 [{cancel_tpl}] (相對: {pos_cancel}, 信心度: {conf_cancel:.4f})，點擊: ({abs_x}, {abs_y})")
                    if mouse:
                        mouse.click(abs_x, abs_y)
                    time.sleep(0.5)
                    return True


        # 2. 全圖備援匹配 (若 ROI 切割未能匹配到，於全圖嘗試搜尋關閉/取消按鈕)
        for cancel_tpl in cancel_candidates:
            if os.path.exists(os.path.join("templates", cancel_tpl)):
                pos_cancel, conf_cancel = safe_match(matcher, screen_img, cancel_tpl, threshold=0.70)
                if pos_cancel:
                    abs_x = rect["left"] + pos_cancel[0]
                    abs_y = rect["top"] + pos_cancel[1]
                    logging.info(f"🛡️ [{self.name}] 全圖備援成功匹配關閉按鈕 [{cancel_tpl}] (信心度: {conf_cancel:.4f})，點擊: ({abs_x}, {abs_y})")
                    if mouse:
                        mouse.click(abs_x, abs_y)
                    time.sleep(0.5)
                    return True

        # 3. 終極備援：若無任何關閉圖案比對成功，點擊 Raid_Box 右上角關閉位置 (box_x + 360, box_y + 35) 或取消區
        cx = rect["left"] + box_x + 360
        cy = rect["top"] + box_y + 35
        logging.info(f"🛡️ [{self.name}] 未在畫面中精確匹配到 cancel 按鈕，點擊 Raid_Box 右上角預設關閉座標: ({cx}, {cy})")
        if mouse:
            mouse.click(cx, cy)
        time.sleep(0.5)
        return True

