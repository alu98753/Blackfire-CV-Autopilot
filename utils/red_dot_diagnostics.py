import os
import cv2
import logging
import numpy as np
from typing import Optional, Tuple
from utils.debug_artifacts import write_debug_image

COLOR_ORANGE_BGR = (0, 140, 255)
COLOR_RED_BGR = (0, 0, 255)
COLOR_GRAY_BGR = (128, 128, 128)
MARKER_RADIUS = 10
FONT_SCALE = 0.4
FONT_THICKNESS = 1


def _draw_crop_canvas(
    crop_roi: np.ndarray,
    target_crop_pt: Optional[Tuple[int, int]],
    has_red_dot: bool,
    ignored_orange: bool,
    best_conf: float,
    debug_tag: str,
) -> None:
    """繪製並保存局部裁切區域 (Crop ROI) 之診斷標記。"""
    if not isinstance(crop_roi, np.ndarray) or crop_roi.size == 0 or target_crop_pt is None:
        return
    crop_canvas = crop_roi.copy()
    color = COLOR_ORANGE_BGR if ignored_orange else (COLOR_RED_BGR if has_red_dot else COLOR_GRAY_BGR)
    cv2.circle(crop_canvas, target_crop_pt, MARKER_RADIUS, color, 2)
    tag_label = f"Orange:{best_conf:.2f}" if ignored_orange else f"Conf:{best_conf:.2f}"
    tx = max(5, target_crop_pt[0] - 25)
    ty = max(15, target_crop_pt[1] - 8)
    cv2.putText(crop_canvas, tag_label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, color, FONT_THICKNESS, cv2.LINE_AA)
    write_debug_image(f"debug_red_dot_crop_{debug_tag}.png", crop_canvas)


def save_red_dot_diagnostics(
    screen_img: np.ndarray,
    crop_roi: np.ndarray,
    building_template: str,
    pos_building: Tuple[int, int],
    bw: int,
    bh: int,
    scale: float,
    roi_coords: Tuple[int, int, int, int],
    has_red_dot: bool,
    best_conf: float,
    threshold: float,
    best_pos_dot: Optional[Tuple[int, int]],
    peak_crop_pos: Optional[Tuple[int, int]],
    debug_tag: str,
    ignored_orange: bool = False,
) -> None:
    """
    繪製並保存全螢幕與局部放大之紅點除錯診斷圖片。
    :param screen_img: 全螢幕原始畫面 (BGR)
    :param crop_roi: 建築正下方裁切區域
    :param building_template: 建築物模板名稱或路徑
    :param pos_building: 建築物中心座標 (x, y)
    :param bw: 建築物寬度
    :param bh: 建築物高度
    :param scale: 畫面縮放比例
    :param roi_coords: 搜尋區塊 (x1, y1, x2, y2)
    :param has_red_dot: 是否確認為真紅點
    :param best_conf: 比對相似度
    :param threshold: 相似度門檻
    :param best_pos_dot: 候選/命中之紅點位置 (在 crop_roi 內)
    :param peak_crop_pos: 未命中時之最高相關性位置
    :param debug_tag: 除錯標籤
    :param ignored_orange: 是否為橘色任務點被過濾
    """
    if not isinstance(screen_img, np.ndarray) or screen_img.size == 0 or int(np.max(screen_img)) == 0:
        return
    try:
        from states.debug.visualizer import DebugVisualizer

        bx, by = pos_building
        actual_bw = int(round(bw * scale))
        actual_bh = int(round(bh * scale))
        matched_bbox = (int(bx - actual_bw // 2), int(by - actual_bh // 2), actual_bw, actual_bh)
        x1, y1, x2, y2 = roi_coords
        roi_box = (x1, y1, x2 - x1, y2 - y1)
        bname = os.path.basename(building_template)
        target_crop_pt = best_pos_dot or peak_crop_pos
        global_target_pt = (x1 + target_crop_pt[0], y1 + target_crop_pt[1]) if target_crop_pt else None

        labels = {"match": f"{bname}"}
        if has_red_dot:
            labels["roi"] = f"Search ROI [{debug_tag}]"
            labels["click"] = f"RedDot ({best_conf:.2f} >= {threshold:.2f})"
        elif ignored_orange:
            labels["roi"] = f"Search ROI [{debug_tag}] Ignored Orange ({best_conf:.2f})"
            if global_target_pt:
                labels["click"] = f"Ignored Orange ({best_conf:.2f})"
        else:
            labels["roi"] = f"Search ROI [{debug_tag}] MaxConf={best_conf:.2f}<{threshold:.2f}"
            if global_target_pt:
                labels["click"] = f"Peak ({best_conf:.2f} < {threshold:.2f})"

        DebugVisualizer.draw_detection(
            screen_img,
            click_pos=global_target_pt,
            matched_bbox=matched_bbox,
            roi_box=roi_box,
            labels=labels,
            filename=f"debug_red_dot_{debug_tag}.png",
        )
        _draw_crop_canvas(crop_roi, target_crop_pt, has_red_dot, ignored_orange, best_conf, debug_tag)
    except Exception as e:
        logging.debug(f"除錯圖片寫入失敗: {e}")
