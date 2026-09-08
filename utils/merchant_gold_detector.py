"""
商人金幣感知模組 (Merchant Gold Perception Detector)

依據 Greenfield-lite v1 與 AGENTS.md 規範：
- 「感知」與「決策」分離：本模組僅負責對畫面進行 Scoped ROI 裁切、OCR 文字識別與數字清洗，不發起任何點擊或狀態轉移。
- 零容忍 Magic Number：ROI 邊界常數由 config.py 注入或由類別常數語意化管理。
- 除錯視覺化：透過 write_debug_image 輸出 debug_merchant_gold_ocr.png。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

import cv2
import numpy as np

from utils.debug_artifacts import write_debug_image

try:
    from config import MERCHANT_GOLD_OCR_ROI
except (ImportError, KeyError):
    MERCHANT_GOLD_OCR_ROI = {
        "relative_x_min": 0.35,
        "relative_x_max": 0.90,
        "relative_y_min": 0.25,
        "relative_y_max": 0.65,
    }


def parse_gold_from_text(raw_text: str) -> int | None:
    """
    從 OCR 識別字串中解析出商人持有的金幣數量。
    支援範例:
      - '金幣: 21413' -> 21413
      - '金常: 21413' -> 21413 (EasyOCR 繁體常/幣字形微差容錯)
      - '金币: 21413' -> 21413
      - '金: 21413' -> 21413
      - '金幣 : 5,000' -> 5000
      - '水晶尤妮 金幣:12345' -> 12345
      - '金幣21413' -> 21413
    """
    if not raw_text:
        return None

    cleaned = raw_text.replace("\n", " ").strip()
    # 支援繁體「金幣」、簡體「金币」、OCR字形微差「金常」或「金:」
    match = re.search(r"(?:金[幣币常]?|[金全][幣币常]?)\s*[:：]?\s*([0-9,]+)", cleaned)
    if match:
        num_str = match.group(1).replace(",", "").strip()
        if num_str.isdigit():
            return int(num_str)

    # 兜底：若前綴模糊但包含冒號且後方為數字 (商人看板第二行典型特徵)
    fallback_match = re.search(r"[:：]\s*([0-9,]{3,})", cleaned)
    if fallback_match:
        num_str = fallback_match.group(1).replace(",", "").strip()
        if num_str.isdigit():
            return int(num_str)

    return None


class MerchantGoldDetector:
    """城鎮商店內部商人金幣識別器。"""

    # 預設 Scoped ROI 相對比例 (當畫面解析度不同時自適應)
    DEFAULT_ROI_X_MIN = 0.35
    DEFAULT_ROI_X_MAX = 0.90
    DEFAULT_ROI_Y_MIN = 0.25
    DEFAULT_ROI_Y_MAX = 0.65

    # 放大縮放比例以增強 EasyOCR 中文字元與數字邊緣辨識率
    RESIZE_SCALE = 2.0

    def __init__(self, ocr_reader: Any | Callable[[], Any] | None = None) -> None:
        self.ocr_reader = ocr_reader

    def _resolve_reader(self, dynamic_reader: Any | Callable[[], Any] | None = None) -> Any:
        reader = dynamic_reader or self.ocr_reader
        if callable(reader) and not hasattr(reader, "readtext"):
            try:
                reader = reader()
            except Exception as e:
                logging.error("調用 OCR Reader Factory 失敗: %s", e)
                reader = None

        if reader is None:
            try:
                import easyocr
                reader = easyocr.Reader(["ch_tra", "en"], gpu=False)
                self.ocr_reader = reader
            except Exception as e:
                logging.error("無法載入 EasyOCR: %s", e)
                return None
        return reader

    def _calculate_roi_rect(self, height: int, width: int) -> tuple[int, int, int, int]:
        cfg = MERCHANT_GOLD_OCR_ROI
        x_min_ratio = cfg.get("relative_x_min", self.DEFAULT_ROI_X_MIN)
        x_max_ratio = cfg.get("relative_x_max", self.DEFAULT_ROI_X_MAX)
        y_min_ratio = cfg.get("relative_y_min", self.DEFAULT_ROI_Y_MIN)
        y_max_ratio = cfg.get("relative_y_max", self.DEFAULT_ROI_Y_MAX)

        crop_x = int(width * x_min_ratio)
        crop_y = int(height * y_min_ratio)
        crop_w = int(width * (x_max_ratio - x_min_ratio))
        crop_h = int(height * (y_max_ratio - y_min_ratio))
        return crop_x, crop_y, crop_w, crop_h

    def _save_debug_image(
        self,
        screen_img: np.ndarray,
        roi_img: np.ndarray,
        roi_rect: tuple[int, int, int, int],
        detected_gold: int | None,
        detected_text: str,
        ocr_results: list[Any] | None = None,
        debug_tag: str | None = None
    ) -> None:
        if not isinstance(screen_img, np.ndarray):
            return
        try:
            crop_x, crop_y, crop_w, crop_h = roi_rect
            debug_canvas = screen_img.copy()

            # 1. 🟩 綠框: 送交 OCR 檢測之商人 Scoped ROI 區域
            cv2.rectangle(debug_canvas, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (0, 255, 0), 2)
            cv2.putText(
                debug_canvas, "Scoped Search ROI", (crop_x + 5, crop_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
            )

            # 2. 逐一繪製各 OCR 辨識字串的精確 Bounding Box
            if ocr_results:
                for item in ocr_results:
                    if len(item) < 2:
                        continue
                    raw_bbox = item[0]
                    txt = str(item[1]).strip()
                    conf = float(item[2]) if len(item) >= 3 else 0.0

                    # 座標逆縮放 (RESIZE_SCALE) 並平移回全螢幕座標系
                    pts = []
                    for pt in raw_bbox:
                        px = crop_x + int(pt[0] / self.RESIZE_SCALE)
                        py = crop_y + int(pt[1] / self.RESIZE_SCALE)
                        pts.append([px, py])
                    pts_np = np.array(pts, dtype=np.int32)

                    gold_val = parse_gold_from_text(txt)
                    if gold_val is not None:
                        # 命中之金幣文字塊：高亮金色粗框 (0, 215, 255)
                        cv2.polylines(debug_canvas, [pts_np], isClosed=True, color=(0, 215, 255), thickness=3)
                        label = f"[GOLD: {gold_val}] ({conf:.2f})"
                        cv2.putText(
                            debug_canvas, label, (pts[0][0], max(20, pts[0][1] - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 215, 255), 2
                        )
                    else:
                        # 一般候選文字塊 (如商人名)：青色細框 (255, 255, 0)
                        cv2.polylines(debug_canvas, [pts_np], isClosed=True, color=(255, 255, 0), thickness=1)
                        ascii_txt = "".join(c for c in txt if ord(c) < 128).strip()
                        label = f"[TEXT: {ascii_txt}] ({conf:.2f})" if ascii_txt else f"[TEXT] ({conf:.2f})"
                        cv2.putText(
                            debug_canvas, label, (pts[0][0], max(15, pts[0][1] - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1
                        )

            # 3. 頂部狀態提示
            top_label = (
                f"Merchant Gold: {detected_gold}"
                if detected_gold is not None
                else f"Failed: {detected_text}"
            )
            top_color = (0, 255, 0) if detected_gold is not None else (0, 0, 255)
            cv2.putText(
                debug_canvas, top_label, (crop_x, max(30, crop_y - 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, top_color, 2
            )

            # 4. 存檔 (支援語意化 tag 與預設覆蓋)
            if debug_tag:
                write_debug_image(f"debug_merchant_gold_ocr_{debug_tag}.png", debug_canvas)
                if isinstance(roi_img, np.ndarray):
                    write_debug_image(f"debug_merchant_gold_roi_{debug_tag}.png", roi_img)

            write_debug_image("debug_merchant_gold_ocr.png", debug_canvas)
            if isinstance(roi_img, np.ndarray):
                write_debug_image("debug_merchant_gold_roi.png", roi_img)
        except Exception as ex:
            logging.warning("⚠️ [MerchantGoldDetector] 保存偵錯圖異常: %s", ex)

    def detect_merchant_gold(
        self,
        screen_img: np.ndarray,
        ocr_reader: Any | Callable[[], Any] | None = None,
        debug_tag: str | None = None
    ) -> int | None:
        """
        對商店內部畫面進行 Scoped ROI 裁切並執行 OCR，解析商人金幣數量。
        :param screen_img: 商店畫面 (BGR ndarray)
        :param ocr_reader: 可選傳入 OCR Reader 實體或工廠函式
        :param debug_tag: 可選傳入語意化偵錯標籤 (如 'jewelry_workshop_init')
        :return: 商人當前金幣整數，若無法識別則回傳 None
        """
        if screen_img is None or not isinstance(screen_img, np.ndarray) or screen_img.ndim < 2:
            return None

        reader = self._resolve_reader(ocr_reader)
        if reader is None:
            return None

        height, width = screen_img.shape[:2]
        crop_x, crop_y, crop_w, crop_h = self._calculate_roi_rect(height, width)
        if crop_w <= 0 or crop_h <= 0:
            return None

        roi_img = screen_img[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]

        try:
            scaled_roi = cv2.resize(
                roi_img, (0, 0),
                fx=self.RESIZE_SCALE, fy=self.RESIZE_SCALE,
                interpolation=cv2.INTER_CUBIC
            )
            results = reader.readtext(scaled_roi)
        except Exception as ex:
            logging.error("⚠️ [MerchantGoldDetector] OCR 執行失敗: %s", ex)
            return None

        detected_gold = None
        all_texts = []
        if results:
            for item in results:
                txt = item[1].strip()
                if txt:
                    all_texts.append(txt)
                    gold = parse_gold_from_text(txt)
                    if gold is not None:
                        detected_gold = gold
                        break

            # 若單個文字塊未匹配成功，合併所有文字再嘗試匹配一次
            if detected_gold is None and all_texts:
                combined = " ".join(all_texts)
                detected_gold = parse_gold_from_text(combined)

        summary_text = " ".join(all_texts)
        self._save_debug_image(
            screen_img, roi_img, (crop_x, crop_y, crop_w, crop_h),
            detected_gold, summary_text, ocr_results=results, debug_tag=debug_tag
        )

        if detected_gold is not None:
            logging.info("💰 [MerchantGoldDetector] 成功識別商人金幣: %d (原始文字: '%s')", detected_gold, summary_text)
        else:
            logging.debug("🔍 [MerchantGoldDetector] 未在商人看板識別到金幣數值 (OCR文字: '%s')", summary_text)

        return detected_gold
