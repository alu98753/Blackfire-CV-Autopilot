import os
import time
import logging
from states.exceptions.subflows.base import BaseExceptionSubflow, safe_match


class GenericAntiStuckSubflow(BaseExceptionSubflow):
    """
    通用防卡死兜底 Subflow (Generic Anti-Stuck Fallback Subflow)。
    
    職責：
    僅當「沒有任何專屬 Exception Subflow 圖案被匹配到」時，作為優先級 2 備援執行。
    依序嘗試比對與點擊通用全域按鈕：
    common/confirm.png, common/continue.png, common/quit.png, common/ok.png, exceptions/cancel.png
    """
    name: str = "generic_anti_stuck_subflow"

    def __init__(self):
        self.fallback_templates = [
            "common/confirm.png",
            "common/continue.png",
            "common/quit.png",
            "common/ok.png",
            "exceptions/cancel.png",
            "cancel.png"
        ]

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        for tpl in self.fallback_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.80
)
                if pos:
                    return True
        return False

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        for tpl in self.fallback_templates:
            if os.path.exists(os.path.join("templates", tpl)):
                pos, conf = safe_match(matcher, screen_img, tpl, threshold=0.80
)
                if pos:
                    cx = rect["left"] + pos[0]
                    cy = rect["top"] + pos[1]
                    logging.info(f"🛡️ [{self.name}] 偵測到通用防卡死全域按鈕 [{tpl}] (相似度: {conf:.4f})，進行點擊以清除阻礙: ({cx}, {cy})")
                    self.draw_trigger_visualizer(
                        screen_img,
                        trigger_tpl=tpl,
                        matched_center=pos,
                        confidence=conf,
                        click_pos=pos,
                        pause_sec=0.0
                    )
                    if mouse:
                        mouse.click(cx, cy)
                    time.sleep(0.5)
                    return True
        return True
