import os
import time
import logging
from typing import Optional, Tuple
import numpy as np


def safe_match(matcher, screen_img, template_name, threshold=0.75) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    安全包裝 matcher.match()，相容標準 API 與各類測試 Mock 傳回值。
    """
    if matcher is None:
        return None, 0.0
    try:
        res = matcher.match(screen_img, template_name, threshold=threshold)
        if isinstance(res, (tuple, list)) and len(res) >= 2 and res[0]:
            pos = res[0]
            conf = float(res[1]) if res[1] is not None else 0.0
            return pos, conf
    except Exception as e:
        logging.debug(f"safe_match 比對異常: {e}")
    return None, 0.0


class BaseExceptionSubflow:
    """
    純粹化例外處置 Subflow 抽象基類 (Pure Execution Subflow)。
    職責：僅負責該 Exception 視窗/彈窗的圖案比對與滑鼠點擊，絕對不處理狀態暫存 (stash) 與還原 (restore)。
    """
    name: str = "base_exception_subflow"

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        """
        判斷傳入畫面是否符合本 Subflow 的例外視窗特徵。
        """
        raise NotImplementedError

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        """
        執行本 Subflow 的單步點擊/關閉處置邏輯 (純化執行，無狀態操控)。
        """
        raise NotImplementedError

    def draw_trigger_visualizer(
        self,
        screen_img: np.ndarray,
        trigger_tpl: str,
        matched_center: Tuple[int, int],
        confidence: float,
        click_pos: Optional[Tuple[int, int]] = None,
        pause_sec: float = 0.0,
        filename: str = "debug_click.png"
    ) -> bool:
        """
        通用 Subflow trigger_template 紅色空心框視覺化繪圖方法。
        
        :param screen_img: 原始截圖
        :param trigger_tpl: 觸發圖案檔名 (例如 "exceptions/Wheel_of_Fortune.png")
        :param matched_center: 匹配到的中心座標 (x, y)
        :param confidence: 匹配相似度
        :param click_pos: 點擊座標 (x, y)
        :param pause_sec: 開發現場暫停秒數 (預設 0.0 秒；Wheel_of_Fortune 可設為 5.0s)
        :param filename: 存檔檔名 (預設 debug_click.png)
        """
        import cv2
        from states.debug import DebugVisualizer

        bw, bh = 100, 100
        tpl_path = os.path.join("templates", trigger_tpl)
        if os.path.exists(tpl_path):
            img = cv2.imread(tpl_path)
            if img is not None and len(img.shape) >= 2:
                bh, bw = img.shape[:2]

        box_x, box_y = matched_center
        matched_bbox = (max(0, box_x - bw // 2), max(0, box_y - bh // 2), bw, bh)

        res = DebugVisualizer.draw_detection(
            screen_img,
            click_pos=click_pos,
            matched_bbox=matched_bbox,
            labels={"match": f"{self.name} ({confidence:.2f})", "click": f"Click {self.name}"},
            filename=filename
        )

        if pause_sec > 0:
            logging.info(f"⏸️ [Debug Breakpoint] [{self.name}] 已在 [{trigger_tpl}] (位址 {matched_bbox}) 劃出紅色空心框並寫入 {filename}！暫停 {pause_sec:.1f} 秒供開發者對照檢查...")
            time.sleep(pause_sec)

        return res
