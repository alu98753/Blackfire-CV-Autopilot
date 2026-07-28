import os
import time
import logging
from typing import Tuple, Optional
from states.exceptions.subflows.base import BaseExceptionSubflow, safe_match


class WheelOfFortuneSubflow(BaseExceptionSubflow):
    """
    幸運輪盤對話框 (Wheel_of_Fortune.png) Subflow (Pure Execution)。
    
    處置流程：
    1. 全圖配對 exceptions/Wheel_of_Fortune.png 取得座標 ROI。
    2. 配對並點擊 Wheel_of_Fortune 內的 quit 按鈕 (common/quit.png 或 quit.png)。
    3. 點擊後進行城鎮檢測 (common/door.png) 並印出 Log 確認是否回到城鎮。
    """
    name: str = "wheel_of_fortune_subflow"

    def __init__(self):
        self.box_templates = ["exceptions/Wheel_of_Fortune.png"]
        self.quit_candidates = ["common/quit.png"]

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
        crop_top = max(0, box_y)
        crop_left = max(0, box_x)

        # 1. 於 Wheel_of_Fortune ROI 內部尋找 quit 按鈕
        wheel_crop = screen_img
        if screen_img is not None and hasattr(screen_img, "shape") and len(screen_img.shape) >= 2:
            h, w = screen_img.shape[:2]
            wheel_crop = screen_img[crop_top:min(h, box_y + 700), crop_left:min(w, box_x + 900)]

        pos_quit, conf_quit, matched_tpl = None, 0.0, ""
        for quit_tpl in self.quit_candidates:
            if os.path.exists(os.path.join("templates", quit_tpl)):
                pos_quit, conf_quit = safe_match(matcher, wheel_crop, quit_tpl, threshold=0.65)
                if pos_quit:
                    matched_tpl = quit_tpl
                    break

        if pos_quit:
            abs_x = rect["left"] + crop_left + pos_quit[0]
            abs_y = rect["top"] + crop_top + pos_quit[1]
            logging.info(f"🛡️ [{self.name}] 成功在 Wheel_of_Fortune ROI 內部匹配 [{matched_tpl}] (信心度: {conf_quit:.4f})，點擊退出: ({abs_x}, {abs_y})")
            if mouse:
                mouse.click(abs_x, abs_y)
        else:
            # 全圖備援匹配
            for quit_tpl in self.quit_candidates:
                if os.path.exists(os.path.join("templates", quit_tpl)):
                    pos_quit, conf_quit = safe_match(matcher, screen_img, quit_tpl, threshold=0.70)
                    if pos_quit:
                        abs_x = rect["left"] + pos_quit[0]
                        abs_y = rect["top"] + pos_quit[1]
                        logging.info(f"🛡️ [{self.name}] 全圖備援成功匹配退出按鈕 [{quit_tpl}] (信心度: {conf_quit:.4f})，點擊: ({abs_x}, {abs_y})")
                        if mouse:
                            mouse.click(abs_x, abs_y)
                        break
            if not pos_quit:
                # 右上角相對點擊備援
                cx = rect["left"] + box_x + 500
                cy = rect["top"] + box_y + 40
                logging.info(f"🛡️ [{self.name}] 未精確匹配到 quit 按鈕，點擊 Wheel_of_Fortune 右上角預設退出座標: ({cx}, {cy})")
                if mouse:
                    mouse.click(cx, cy)

        time.sleep(0.5)

        # 2. 檢測是否回到城鎮 (common/door.png)
        door_tpl = "common/door.png"
        is_back_in_town = False
        if os.path.exists(os.path.join("templates", door_tpl)):
            pos_door, conf_door = safe_match(matcher, screen_img, door_tpl, threshold=0.75)
            if pos_door:
                is_back_in_town = True

        if is_back_in_town:
            logging.info(f"🏰 [{self.name}] ✅ 已成功處置 Wheel_of_Fortune 並檢測確認回到城鎮 (door.png 可見)！")
        else:
            logging.info(f"🏰 [{self.name}] 處置完成，發起狀態恢復...")

        return True
