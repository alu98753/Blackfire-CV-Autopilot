import os
import cv2
import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class BuildingCheckResult:
    """
    城鎮建築與驚嘆號紅點檢測結果 (不可變快照資料類別)。
    :param found_building: 是否在畫面上辨識到該建築
    :param has_red_dot: 建築物正下方是否帶有未完成驚嘆號紅點
    :param building_pos: 建築物於全螢幕之中心座標 (x, y)
    :param red_dot_pos: 紅點於全螢幕之中心座標 (x, y)
    :param confidence_building: 建築物比對信心度
    :param confidence_red_dot: 紅點比對信心度
    """
    found_building: bool
    has_red_dot: bool
    building_pos: Optional[Tuple[int, int]] = None
    red_dot_pos: Optional[Tuple[int, int]] = None
    confidence_building: float = 0.0
    confidence_red_dot: float = 0.0


def _resolve_debug_tag(debug_tag: Optional[str], template_path: str) -> str:
    """依據傳入標籤或模板路徑推斷任務除錯名稱。"""
    if debug_tag:
        return debug_tag
    if "mysterious_treasure" in template_path:
        return "chest"
    if "Tavern" in template_path:
        return "hero_draw"
    if "Blood_Altar" in template_path:
        return "blood_altar"
    if "bulletin_board" in template_path:
        return "bulletin_board"
    return "building"


def _compute_scoped_roi(
    screen_w: int, screen_h: int, bx: int, by: int, bw: int, bh: int, scale: float
) -> Tuple[int, int, int, int]:
    """計算建築物正下方感興趣區域 (Scoped ROI)。"""
    actual_bw = int(round(bw * scale))
    actual_bh = int(round(bh * scale))
    margin_x = int(max(40, actual_bw * 0.35))
    x1 = max(0, int(bx - actual_bw // 2 - margin_x))
    x2 = min(screen_w, int(bx + actual_bw // 2 + margin_x))
    y1 = max(0, int(by - actual_bh // 4))
    margin_y = int(max(120, round(150 * scale)))
    y2 = min(screen_h, int(by + actual_bh // 2 + margin_y))
    return x1, y1, x2, y2


def _find_peak_in_crop(matcher, crop_roi: np.ndarray, template_path: str, scale: float) -> Optional[Tuple[int, int]]:
    """在 crop_roi 中尋找模板之最高相關性位置 (Peak Location)。"""
    if not isinstance(crop_roi, np.ndarray) or crop_roi.size == 0:
        return None
    try:
        load_fn = getattr(matcher, "_load_template", None)
        t_dot = load_fn(template_path, scale=scale) if load_fn else None
        if t_dot is None:
            return None
        th, tw = t_dot.shape[:2]
        ch, cw = crop_roi.shape[:2]
        if th > ch or tw > cw:
            return None
        res_m = cv2.matchTemplate(crop_roi, t_dot, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res_m)
        return (max_loc[0] + tw // 2, max_loc[1] + th // 2)
    except Exception:
        return None


def _save_red_dot_diagnostics(
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
) -> None:
    """繪製並保存全螢幕與局部放大之診斷圖片。"""
    if not isinstance(screen_img, np.ndarray) or screen_img.size == 0:
        return
    # 純黑全零虛擬畫面 (例如單元測試傳入之 np.zeros 假畫面) 絕不落檔，防止測試執行時覆寫真實遊戲截圖
    if int(np.max(screen_img)) == 0:
        return
    try:
        from states.debug.visualizer import DebugVisualizer
        from utils.debug_artifacts import write_debug_image

        bx, by = pos_building
        actual_bw, actual_bh = int(round(bw * scale)), int(round(bh * scale))
        matched_bbox = (int(bx - actual_bw // 2), int(by - actual_bh // 2), actual_bw, actual_bh)
        x1, y1, x2, y2 = roi_coords
        roi_box = (x1, y1, x2 - x1, y2 - y1)
        bname = os.path.basename(building_template)
        debug_full_name = f"debug_red_dot_{debug_tag}.png"
        debug_crop_name = f"debug_red_dot_crop_{debug_tag}.png"

        target_crop_pt = best_pos_dot or peak_crop_pos
        global_target_pt = (x1 + target_crop_pt[0], y1 + target_crop_pt[1]) if target_crop_pt else None

        labels = {"match": f"{bname}"}
        if has_red_dot:
            labels["roi"] = f"Search ROI [{debug_tag}]"
            labels["click"] = f"RedDot ({best_conf:.2f} >= {threshold:.2f})"
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
            filename=debug_full_name,
        )

        if isinstance(crop_roi, np.ndarray) and crop_roi.size > 0:
            crop_canvas = crop_roi.copy()
            if target_crop_pt:
                cv2.circle(crop_canvas, target_crop_pt, 10, (0, 0, 255), 2)
                tag_label = f"Conf:{best_conf:.2f}"
                cv2.putText(
                    crop_canvas,
                    tag_label,
                    (max(5, target_crop_pt[0] - 25), max(15, target_crop_pt[1] - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 0, 255),
                    1,
                    cv2.LINE_AA,
                )
            write_debug_image(debug_crop_name, crop_canvas)
    except Exception as e:
        logging.debug(f"除錯圖片寫入失敗: {e}")


def detect_building_with_red_dot(
    screen_img,
    building_template: str,
    matcher,
    red_dot_template: str = "town_building/red_dot.png",
    building_threshold: float = 0.65,
    red_dot_threshold: float = 0.60,
    debug_tag: Optional[str] = None,
    **match_kwargs,
) -> BuildingCheckResult:
    """城鎮建築與正下方驚嘆號紅點檢測器 (純感知觀察函式)。"""
    if screen_img is None or matcher is None:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    pos_building, conf_building = matcher.match(
        screen_img, building_template, threshold=building_threshold, **match_kwargs
    )
    if not pos_building:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    screen_h, screen_w = (600, 800)
    if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2:
        try:
            screen_h, screen_w = screen_img.shape[:2]
        except Exception:
            pass

    tag = _resolve_debug_tag(debug_tag, building_template)
    templates_dir = getattr(matcher, "templates_dir", "templates")
    if not isinstance(templates_dir, str):
        templates_dir = "templates"
    bw, bh = 180, 160
    if isinstance(building_template, str):
        t_path = os.path.join(templates_dir, building_template)
        if os.path.exists(t_path):
            t_img = cv2.imread(t_path)
            if t_img is not None:
                bh, bw = t_img.shape[:2]

    raw_scale = getattr(matcher, "_compute_auto_scale", lambda w: 1.0)(screen_w)
    if isinstance(raw_scale, (int, float)) and raw_scale > 0:
        screen_scale = float(raw_scale)
    else:
        screen_scale = 1.0

    bx, by = pos_building
    x1, y1, x2, y2 = _compute_scoped_roi(screen_w, screen_h, bx, by, bw, bh, screen_scale)
    if x2 <= x1 or y2 <= y1:
        return BuildingCheckResult(
            found_building=True, has_red_dot=False, building_pos=pos_building, confidence_building=conf_building
        )

    try:
        crop_roi = screen_img[y1:y2, x1:x2]
    except Exception:
        crop_roi = screen_img

    if isinstance(crop_roi, np.ndarray) and (crop_roi.size == 0 or crop_roi.shape[0] < 20 or crop_roi.shape[1] < 20):
        return BuildingCheckResult(
            found_building=True, has_red_dot=False, building_pos=pos_building, confidence_building=conf_building
        )

    # 多尺度候選比對驚嘆號紅點
    candidate_scales = [round(screen_scale, 3)]
    for s in (1.0, round(screen_scale * 0.9, 3), round(screen_scale * 1.1, 3)):
        if not any(abs(s - cs) < 0.03 for cs in candidate_scales):
            candidate_scales.append(s)

    best_pos_dot, best_conf_dot, best_scale_dot = None, 0.0, screen_scale
    for s in candidate_scales:
        pos_d, conf_d = matcher.match(crop_roi, red_dot_template, threshold=red_dot_threshold, scale=s)
        if conf_d > best_conf_dot:
            best_conf_dot = conf_d
            best_scale_dot = s
            if pos_d is not None:
                best_pos_dot = pos_d

    has_red_dot = best_pos_dot is not None
    peak_crop_pos = None if has_red_dot else _find_peak_in_crop(matcher, crop_roi, red_dot_template, best_scale_dot)
    global_dot_pos = (x1 + best_pos_dot[0], y1 + best_pos_dot[1]) if has_red_dot else None

    _save_red_dot_diagnostics(
        screen_img=screen_img,
        crop_roi=crop_roi,
        building_template=building_template,
        pos_building=pos_building,
        bw=bw,
        bh=bh,
        scale=screen_scale,
        roi_coords=(x1, y1, x2, y2),
        has_red_dot=has_red_dot,
        best_conf=best_conf_dot,
        threshold=red_dot_threshold,
        best_pos_dot=best_pos_dot,
        peak_crop_pos=peak_crop_pos,
        debug_tag=tag,
    )

    if has_red_dot:
        logging.info(
            f"🔍 [RedDotDebug] [{tag}] 建築下方成功檢測到紅點！相似度: {best_conf_dot:.4f} "
            f"(門檻: {red_dot_threshold:.2f}, scale: {best_scale_dot:.3f})，座標: {global_dot_pos}"
        )
        return BuildingCheckResult(
            found_building=True,
            has_red_dot=True,
            building_pos=pos_building,
            red_dot_pos=global_dot_pos,
            confidence_building=conf_building,
            confidence_red_dot=best_conf_dot,
        )

    logging.info(
        f"🔍 [RedDotDebug] [{tag}] 建築下方未檢出紅點 (最高相似度: {best_conf_dot:.4f} < "
        f"門檻: {red_dot_threshold:.2f}, scale: {best_scale_dot:.3f})，已產出除錯診斷圖: debug_red_dot_{tag}.png"
    )
    return BuildingCheckResult(
        found_building=True,
        has_red_dot=False,
        building_pos=pos_building,
        confidence_building=conf_building,
        confidence_red_dot=best_conf_dot,
    )
