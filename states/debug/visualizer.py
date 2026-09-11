import cv2
import numpy as np
import logging
import os
from typing import Tuple, Optional, Dict, Any, List
from utils.debug_artifacts import write_debug_image


class DebugVisualizer:
    """
    除錯繪圖與視覺化診斷工具 (DebugVisualizer)
    
    職責：
    將除錯繪圖邏輯從硬編碼手寫中解耦抽離。
    支援在 debug_click.png 上標註：
    1. 點擊目標標記與座標 (Click Point & Coordinates)
    2. 模板匹配成功的 Bounding Box 矩形框 (Match Bounding Box - 紅色空心框)
    3. 搜尋/裁切的 ROI 範圍框 (ROI Bounding Box - 紅色虛線/空心框)
    """

    @staticmethod
    def draw_detection(
        screen_img: np.ndarray,
        click_pos: Optional[Tuple[int, int]] = None,
        matched_bbox: Optional[Tuple[int, int, int, int]] = None,
        roi_box: Optional[Tuple[int, int, int, int]] = None,
        ocr_box: Optional[Tuple[int, int, int, int]] = None,
        status_text: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        filename: str = "debug_click.png"
    ) -> bool:
        """
        統一在畫面繪製 ROI 框、匹配 Bounding Box、OCR 區域框與點擊座標標記，並保存圖檔。
        - 模板與 ROI 方框採用【紅色空心方框】(BGR: (0, 0, 255), thickness=2)
        - OCR 區域框採用【黃色空心方框】(BGR: (0, 255, 255), thickness=2)
        
        :param screen_img: 原始螢幕或截圖影像 (BGR 格式)
        :param click_pos: 點擊目標相對/絕對座標 (x, y)
        :param matched_bbox: 模板匹配成功的 Bounding Box (x, y, width, height)
        :param roi_box: 搜尋/裁切的 ROI 區域框 (x, y, width, height)
        :param ocr_box: 送入 OCR 辨識的精確區域框 (x, y, width, height)
        :param status_text: 頂部狀態橫幅文字 (可選)
        :param labels: 標籤字典 {"click": "...", "match": "...", "roi": "...", "ocr": "...", "status": "..."}
        :param filename: 存檔檔名 (預設 debug_click.png)
        :return: True 代表寫入成功
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
            return False

        canvas = screen_img.copy()
        labels = labels or {}
        RED_COLOR = (0, 0, 255)      # BGR: 純正紅色
        YELLOW_COLOR = (0, 255, 255) # BGR: 醒目黃色 (專用於 OCR 區域標定)

        # 1. 繪製 ROI 搜尋範圍框 (紅色空心矩形框 / Red Hollow Box)
        if roi_box:
            rx, ry, rw, rh = roi_box
            cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), RED_COLOR, 2)
            roi_label = labels.get("roi", "ROI Search Region")
            cv2.putText(canvas, f"[ROI] {roi_label}", (rx + 5, max(20, ry + 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED_COLOR, 1, cv2.LINE_AA)

        # 2. 繪製模板匹配 Bounding Box (紅色空心矩形框 / Red Hollow Box)
        if matched_bbox:
            mx, my, mw, mh = matched_bbox
            cv2.rectangle(canvas, (mx, my), (mx + mw, my + mh), RED_COLOR, 2)
            match_label = labels.get("match", "Matched BBox")
            cv2.putText(canvas, f"[Match] {match_label}", (mx, max(15, my - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED_COLOR, 1, cv2.LINE_AA)

        # 3. 繪製 OCR 區域框 (黃色空心矩形框 / Yellow Hollow Box，專門標註送入 OCR 辨識的文字區域)
        if ocr_box:
            ox, oy, ow, oh = ocr_box
            cv2.rectangle(canvas, (ox, oy), (ox + ow, oy + oh), YELLOW_COLOR, 2)
            ocr_label = labels.get("ocr", "OCR Target Region")
            cv2.putText(canvas, f"[OCR] {ocr_label}", (ox + 5, max(20, oy - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, YELLOW_COLOR, 1, cv2.LINE_AA)

        # 4. 繪製點擊座標標靶與紅圈 (紅色 / Red Target Circle & Crosshair)
        if click_pos:
            cx, cy = click_pos
            cv2.circle(canvas, (cx, cy), 15, RED_COLOR, 2)
            cv2.circle(canvas, (cx, cy), 3, RED_COLOR, -1)
            cv2.line(canvas, (cx - 20, cy), (cx + 20, cy), RED_COLOR, 1)
            cv2.line(canvas, (cx, cy - 20), (cx, cy + 20), RED_COLOR, 1)
            click_label = labels.get("click", f"Click ({cx}, {cy})")
            cv2.putText(canvas, f"[Click] {click_label}", (cx + 20, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED_COLOR, 1, cv2.LINE_AA)

        # 5. 繪製頂部狀態橫幅 (Status Banner)
        banner_text = status_text or labels.get("status")
        if banner_text:
            h, w = canvas.shape[:2]
            bar_height = 36
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (w, bar_height), (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)
            color = (0, 255, 0) if any(kw in banner_text.upper() for kw in ["SUCCESS", "PASS"]) else (
                (0, 0, 255) if any(kw in banner_text.upper() for kw in ["FAIL", "DEFER", "WARN"]) else (255, 255, 255)
            )
            cv2.putText(canvas, banner_text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

        try:
            saved = write_debug_image(filename, canvas)
            logging.info(f"🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 {filename}")
            return saved
        except Exception as e:
            logging.debug(f"無法寫入 {filename}: {e}")
            return False

    @staticmethod
    def draw_features_diagnostic(
        screen_img: np.ndarray,
        features: List[Dict[str, Any]],
        status_text: Optional[str] = None,
        filename: str = "debug_features_diagnostic.png"
    ) -> bool:
        """
        繪製多特徵診斷視覺化圖檔：
        將所有檢測項目的 ROI 搜尋區域、最佳匹配點 BBox（達標綠框 / 未達標紅框）與信心度/門檻標籤繪製於畫面上，
        並在頂部產生狀態橫幅。

        :param screen_img: 原始截圖 (BGR 格式)
        :param features: 特徵項目清單，每項格式如：
               {
                   "name": "task (Before)",
                   "roi": (rx, ry, rw, rh), # 可選
                   "matched_bbox": (mx, my, mw, mh), # 可選
                   "confidence": 0.65,
                   "threshold": 0.70,
                   "matched": False
               }
        :param status_text: 頂部狀態橫幅文字
        :param filename: 存檔檔名
        :return: bool 寫入是否成功
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
            return False

        canvas = screen_img.copy()
        GREEN_COLOR = (0, 220, 0)      # BGR: 達標綠色
        RED_COLOR = (0, 0, 255)        # BGR: 未達標/失敗紅色
        BLUE_ROI_COLOR = (255, 180, 0) # BGR: 天藍色 (ROI 搜尋邊框)

        # 1. 繪製各項特徵的 ROI 搜尋邊界框
        for feat in features:
            roi = feat.get("roi")
            if roi:
                rx, ry, rw, rh = roi
                cv2.rectangle(canvas, (rx, ry), (rx + rw, ry + rh), BLUE_ROI_COLOR, 1)
                name = feat.get("name", "ROI")
                cv2.putText(canvas, f"[ROI] {name}", (rx + 5, max(15, ry + 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, BLUE_ROI_COLOR, 1, cv2.LINE_AA)

        # 2. 繪製各項特徵的匹配 Bounding Box 與信心度文字
        for feat in features:
            bbox = feat.get("matched_bbox")
            name = feat.get("name", "Feature")
            conf = feat.get("confidence", 0.0)
            th = feat.get("threshold", 0.70)
            matched = feat.get("matched", False)

            color = GREEN_COLOR if matched else RED_COLOR
            tag = "PASS" if matched else "FAIL"

            if bbox:
                bx, by, bw, bh = bbox
                thickness = 2 if matched else 1
                cv2.rectangle(canvas, (bx, by), (bx + bw, by + bh), color, thickness)
                label = f"[{tag}] {name}: {conf:.3f} / th={th:.2f}"
                cv2.putText(canvas, label, (bx, max(15, by - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            else:
                # 若無明確 bbox (例如完全未匹配)，在畫面下方或左側標記未檢測到
                pass

        # 3. 繪製頂部狀態橫幅 (Status Banner)
        if status_text:
            h, w = canvas.shape[:2]
            bar_height = 40
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (w, bar_height), (25, 25, 25), -1)
            cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)

            is_pass = any(kw in status_text.upper() for kw in ["PASS", "SUCCESS"])
            banner_color = GREEN_COLOR if is_pass else RED_COLOR
            cv2.putText(canvas, status_text, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, banner_color, 2, cv2.LINE_AA)

        try:
            saved = write_debug_image(filename, canvas)
            logging.info(f"🎯 [DebugVisualizer] 已成功將多特徵診斷視覺化標記寫入 {filename}")
            return saved
        except Exception as e:
            logging.debug(f"無法寫入 {filename}: {e}")
            return False

