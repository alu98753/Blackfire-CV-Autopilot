import os
import time
import logging
from states.exceptions.subflows.base import BaseExceptionSubflow, safe_match


class GenericCancelSubflow(BaseExceptionSubflow):
    """
    通用取消/關閉按鈕 Subflow (Pure Execution)。
    嘗試比對與點擊 cancel.png, common/close.png, common/x_button.png 等關閉圖示。
    """
    name: str = "generic_cancel_subflow"

    def __init__(self):
        self.cancel_templates = [
            "exceptions/cancel.png",
            "cancel.png",
            "common/close.png",
            "common/x_button.png",
            "common/cancel.png"
        ]

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        for tpl in self.cancel_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.75)
                if pos:
                    return True
        return False

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        for tpl in self.cancel_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.75)
                if pos:
                    cx = rect["left"] + pos[0]
                    cy = rect["top"] + pos[1]
                    logging.info(f"🛡️ [{self.name}] 檢測到通用關閉/取消按鈕 [{tpl}] (相似度: {conf:.4f})，進行點擊: ({cx}, {cy})")
                    if mouse:
                        mouse.click(cx, cy)
                    time.sleep(0.5)
                    return True
        return True
