import cv2
import numpy as np
import logging
import os
from typing import Tuple, Optional, Dict, Any, List


class DebugVisualizer:
    """
    除錯繪圖與視覺化診斷工具 (DebugVisualizer)
    
    職責：
    將除錯繪圖邏輯從硬編碼手寫中解耦抽離。
    支援在 debug_click.png 上標註：
    1. 點擊目標標記與座標 (Click Point & Coordinates)
    2. 模板匹配成功的 Bounding Box 矩形框 (Match Bounding Box)
    3. 搜尋/裁切的 ROI 範圍框 (ROI Bounding Box)
    """

    @staticmethod
    def draw_detection(
        screen_img: np.ndarray,
        click_pos: Optional[Tuple[int, int]] = None,
        matched_bbox: Optional[Tuple[int, int, int, int]] = None,
        roi_box: Optional[Tuple[int, int, int, int]] = None,
        labels: Optional[Dict[str, str]] = None,
        filename: str = "debug_click.png"
    ) -> bool:
        """
        統一在畫面繪製 ROI 框、匹配 Bounding Box 與點擊座標標記，並保存圖檔。
        
        :param screen_img: 原始螢幕或截圖影像 (BGR 格式)
        :param click_pos: 點擊目標絕對座標 (x, y)
        :param matched_bbox: 模板匹配成功的 Bounding Box (x, y, width, height)
        :param roi_box: 搜尋/裁切的 ROI 區域框 (x, y, width, height)
        :param labels: 標籤字典 {"click": "...", "match": "...", "roi": "..."}
        :param filename: 存檔檔名 (預設 debug_click.png)
        :return: True 代表寫入成功
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
            return False

        canvas = screen_img.copy()
        labels = labels or {}

        # 1. 繪製 ROI 範圍框 (橙色 / Orange)
        if roi_box:
            rx, ry, rw, rh = roi_box
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), (0, 165, 255), 2)
            roi_label = labels.get("roi", "ROI Search Region")
            cv2.putText(canvas, roi_label, (rx, max(15, ry - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1, cv2.LINE_AA)

        # 2. 繪製模板匹配 Bounding Box (綠色 / Green)
        if matched_bbox:
            mx, my, mw, mh = matched_bbox
            cv2.rectangle(canvas, (mx, my), (mx + mw, my + mh), (0, 255, 0), 2)
            match_label = labels.get("match", "Matched BBox")
            cv2.putText(canvas, match_label, (mx, max(15, my - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        # 3. 繪製點擊座標十字與紅圈 (紅色 / Red)
        if click_pos:
            cx, cy = click_pos
            cv2.circle(canvas, (cx, cy), 15, (0, 0, 255), 2)
            cv2.circle(canvas, (cx, cy), 3, (0, 0, 255), -1)
            # 十字線
            cv2.line(canvas, (cx - 20, cy), (cx + 20, cy), (0, 0, 255), 1)
            cv2.line(canvas, (cx, cy - 20), (cx, cy + 20), (0, 0, 255), 1)
            click_label = labels.get("click", f"Click ({cx}, {cy})")
            cv2.putText(canvas, click_label, (cx + 20, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        try:
            cv2.imwrite(filename, canvas)
            logging.info(f"🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/Click) 寫入 {filename}")
            return True
        except Exception as e:
            logging.debug(f"無法寫入 {filename}: {e}")
            return False
