import os
import cv2
import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from utils.red_dot_diagnostics import save_red_dot_diagnostics

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


# 色彩門禁常數 (零容忍 Magic Number)
RED_DOT_HUE_MAX_LOWER = 8
RED_DOT_HUE_MIN_UPPER = 172
RED_DOT_MIN_SATURATION = 60
RED_DOT_MIN_VALUE = 50
RED_DOT_MIN_RG_RATIO = 2.2
RED_DOT_MIN_RED_PIXEL_RATIO = 0.50
RED_DOT_MIN_COLORED_PIXELS = 10

# 橘色任務驚嘆號常數 (零容忍 Magic Number)
ORANGE_DOT_HUE_MIN = 9
ORANGE_DOT_HUE_MAX = 25
ORANGE_DOT_MIN_RG_RATIO = 1.10
ORANGE_DOT_MIN_ORANGE_PIXEL_RATIO = 0.50

from config import TOWN_BUILDING_BRIGHTNESS_THRESHOLD


def _analyze_dot_color_patch(
    patch_img: np.ndarray,
    hue_mask_fn,
    min_ratio: float,
    rg_ratio_threshold: float,
) -> Tuple[bool, float]:
    """
    通用彩色驚嘆號/紅點像素區塊色彩比率分析私有工具函式。
    """
    if not isinstance(patch_img, np.ndarray) or patch_img.size == 0 or len(patch_img.shape) < 3:
        return False, 0.0
    h, w = patch_img.shape[:2]
    if h < 3 or w < 3:
        return False, 0.0

    g = patch_img[:, :, 1].astype(np.float32)
    r = patch_img[:, :, 2].astype(np.float32)

    hsv = cv2.cvtColor(patch_img, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # 1. 篩選具色彩飽和度的有效像素 (排除黑邊、深灰背景)
    color_mask = (sat >= RED_DOT_MIN_SATURATION) & (val >= RED_DOT_MIN_VALUE)
    total_colored = int(np.sum(color_mask))
    if total_colored < RED_DOT_MIN_COLORED_PIXELS:
        return False, 0.0

    # 2. 應用特定色彩之色相與 R/G 比值門禁
    hue_mask = hue_mask_fn(hue)
    rg_mask = (r / np.maximum(1.0, g)) >= rg_ratio_threshold
    target_mask = color_mask & hue_mask & rg_mask

    target_pixels = int(np.sum(target_mask))
    ratio = target_pixels / float(total_colored)
    return (ratio >= min_ratio), ratio


def is_true_red_dot(
    patch_img: np.ndarray,
    min_red_ratio: float = RED_DOT_MIN_RED_PIXEL_RATIO,
    rg_ratio_threshold: float = RED_DOT_MIN_RG_RATIO,
) -> Tuple[bool, float]:
    """
    檢驗影像區塊 (Patch) 是否為真實紅色驚嘆號，嚴格排除橘色任務驚嘆號。
    :param patch_img: BGR 格式之候選影像區塊
    :param min_red_ratio: 有效彩色像素中純紅像素之最低佔比
    :param rg_ratio_threshold: R/G 通道比值之最低門檻
    :return: (is_red: bool, red_ratio: float)
    """
    return _analyze_dot_color_patch(
        patch_img,
        lambda hue: (hue <= RED_DOT_HUE_MAX_LOWER) | (hue >= RED_DOT_HUE_MIN_UPPER),
        min_red_ratio,
        rg_ratio_threshold,
    )


def is_true_orange_dot(
    patch_img: np.ndarray,
    min_orange_ratio: float = ORANGE_DOT_MIN_ORANGE_PIXEL_RATIO,
    rg_ratio_threshold: float = ORANGE_DOT_MIN_RG_RATIO,
) -> Tuple[bool, float]:
    """
    檢驗影像區塊 (Patch) 是否為真實橘色任務驚嘆號 (適用於 bulletin_board 等重置後待接任務狀態)。
    :param patch_img: BGR 格式之候選影像區塊
    :param min_orange_ratio: 有效彩色像素中橘色像素之最低佔比
    :param rg_ratio_threshold: R/G 通道比值之最低門檻
    :return: (is_orange: bool, orange_ratio: float)
    """
    return _analyze_dot_color_patch(
        patch_img,
        lambda hue: (hue >= ORANGE_DOT_HUE_MIN) & (hue <= ORANGE_DOT_HUE_MAX),
        min_orange_ratio,
        rg_ratio_threshold,
    )


def _resolve_debug_tag(debug_tag: Optional[str], template_path: str) -> str:
    """依據傳入標籤或模板路徑推斷任務除錯名稱。"""
    if debug_tag:
        return debug_tag
    tag_map = {"mysterious_treasure": "chest", "Tavern": "hero_draw", "Blood_Altar": "blood_altar", "bulletin_board": "bulletin_board"}
    for key, name in tag_map.items():
        if key in template_path:
            return name
    return "building"


def _load_template_dims(templates_dir: str, template_name: str, default_dims: Tuple[int, int]) -> Tuple[int, int]:
    """安全載入模板尺寸 (height, width)。"""
    if isinstance(template_name, str):
        t_path = os.path.join(templates_dir, template_name)
        if os.path.exists(t_path):
            t_img = cv2.imread(t_path)
            if t_img is not None:
                return t_img.shape[:2]
    return default_dims


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


def _verify_red_dot_color(
    crop_roi: np.ndarray,
    candidate_pos: Optional[Tuple[int, int]],
    dot_w: int,
    dot_h: int,
    screen_scale: float,
    tag: str,
    conf: float,
    allow_orange: bool = False,
) -> Tuple[bool, bool, Optional[Tuple[int, int]]]:
    """
    色彩門禁核驗：若候選點存在，切割 Patch 驗證是否為可點擊驚嘆號 (純紅，或特定建築允許之橘色)。
    回傳: (has_red_dot: bool, ignored_orange: bool, final_pos: Optional[Tuple[int, int]])
    """
    if candidate_pos is None or not isinstance(crop_roi, np.ndarray) or crop_roi.size == 0:
        return False, False, None
    if int(np.max(crop_roi)) == 0:
        return True, False, candidate_pos

    cx, cy = candidate_pos
    hw = max(4, int(round((dot_w * screen_scale) / 2)))
    hh = max(4, int(round((dot_h * screen_scale) / 2)))
    py1, py2 = max(0, cy - hh), min(crop_roi.shape[0], cy + hh)
    px1, px2 = max(0, cx - hw), min(crop_roi.shape[1], cx + hw)
    dot_patch = crop_roi[py1:py2, px1:px2]

    is_red, red_ratio = is_true_red_dot(dot_patch)
    if is_red:
        return True, False, candidate_pos

    is_orange, orange_ratio = is_true_orange_dot(dot_patch)
    if allow_orange and is_orange:
        logging.info(
            f"🟠 [RedDotColorGate] [{tag}] 檢測到合法橘色任務驚嘆號 (Conf: {conf:.2f}, OrangeRatio: {orange_ratio:.2f})，予以放行進入！"
        )
        return True, False, candidate_pos

    logging.info(
        f"⚠️ [RedDotColorGate] [{tag}] 檢測到驚嘆號形狀 (Conf: {conf:.2f})，"
        f"但色彩判定為非純紅/橘色 (RedRatio: {red_ratio:.2f} < {RED_DOT_MIN_RED_PIXEL_RATIO})，已自動過濾！"
    )
    return False, True, None


def _locate_building(screen_img, building_template: str, matcher, threshold: float, candidate_scales, match_kwargs: dict):
    """建築物模板比對子步驟 (套用多尺度與亮度設定)。"""
    kwargs = dict(match_kwargs)
    kwargs.setdefault("brightness_threshold", TOWN_BUILDING_BRIGHTNESS_THRESHOLD)
    if candidate_scales is not None and "scales" not in kwargs:
        kwargs["scales"] = candidate_scales
    return matcher.match(screen_img, building_template, threshold=threshold, **kwargs)


def _get_building_crop_roi(screen_img, pos_building: Tuple[int, int], bw: int, bh: int, screen_scale: float):
    """計算並切取建築正下方感興趣區域 (crop_roi)。"""
    screen_h, screen_w = screen_img.shape[:2] if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2 else (600, 800)
    bx, by = pos_building
    x1, y1, x2, y2 = _compute_scoped_roi(screen_w, screen_h, bx, by, bw, bh, screen_scale)
    if x2 <= x1 or y2 <= y1:
        return None, (x1, y1, x2, y2)
    crop_roi = screen_img[y1:y2, x1:x2] if hasattr(screen_img, "__getitem__") else screen_img
    if isinstance(crop_roi, np.ndarray) and (crop_roi.size == 0 or crop_roi.shape[0] < 20 or crop_roi.shape[1] < 20):
        return None, (x1, y1, x2, y2)
    return crop_roi, (x1, y1, x2, y2)


def _collect_red_dot_candidates(
    matcher, crop_roi: np.ndarray, red_dot_template: str, threshold: float, candidate_scales
) -> Tuple[list, float]:
    """獲取驚嘆號紅點候選清單 (優先調用 match_all，降級支援 match)。"""
    candidates = []
    if hasattr(matcher, "match_all") and callable(matcher.match_all):
        try:
            all_matches = matcher.match_all(
                crop_roi, red_dot_template, threshold=threshold, scales=candidate_scales, brightness_threshold=0.0
            )
            if all_matches:
                candidates = [(int(pt[0]), int(pt[1]), float(pt[2])) for pt in all_matches]
        except Exception as e:
            logging.debug(f"matcher.match_all 調用異常，降級為單點比對: {e}")

    if not candidates:
        raw_dot_pos, best_conf_dot = matcher.match(
            crop_roi, red_dot_template, threshold=threshold, scales=candidate_scales, brightness_threshold=0.0
        )
        if raw_dot_pos is not None:
            candidates = [(int(raw_dot_pos[0]), int(raw_dot_pos[1]), float(best_conf_dot))]
        return candidates, float(best_conf_dot)

    return candidates, float(candidates[0][2])


def _detect_and_verify_red_dot(
    crop_roi, matcher, red_dot_template: str, threshold: float, candidate_scales, templates_dir: str, screen_scale: float, tag: str, allow_orange: bool = False
):
    """比對驚嘆號形狀並執行色彩門禁核驗 (支援多候選點遍歷，紅點優先且保障告示牌防回歸)。"""
    candidates, fallback_conf = _collect_red_dot_candidates(
        matcher, crop_roi, red_dot_template, threshold, candidate_scales
    )
    if not candidates:
        return False, False, None, None, fallback_conf

    dot_h, dot_w = _load_template_dims(templates_dir, red_dot_template, (24, 24))
    hw = max(4, int(round((dot_w * screen_scale) / 2)))
    hh = max(4, int(round((dot_h * screen_scale) / 2)))

    valid_red = None
    valid_orange = None
    any_orange_ignored = False

    for cx, cy, conf in candidates:
        cand_pos = (cx, cy)
        is_valid, is_orange_ignored, _ = _verify_red_dot_color(
            crop_roi, cand_pos, dot_w, dot_h, screen_scale, tag, conf, allow_orange=allow_orange
        )
        if is_orange_ignored:
            any_orange_ignored = True

        if is_valid:
            py1, py2 = max(0, cy - hh), min(crop_roi.shape[0], cy + hh)
            px1, px2 = max(0, cx - hw), min(crop_roi.shape[1], cx + hw)
            patch = crop_roi[py1:py2, px1:px2]
            is_red, _ = is_true_red_dot(patch)
            if is_red:
                valid_red = (cand_pos, conf)
                break
            elif allow_orange and valid_orange is None:
                valid_orange = (cand_pos, conf)

    chosen = valid_red or valid_orange
    if chosen is not None:
        best_pos, best_conf = chosen
        return True, False, best_pos, best_pos, best_conf

    first_pos = (candidates[0][0], candidates[0][1])
    first_conf = candidates[0][2]
    return False, any_orange_ignored, None, first_pos, first_conf


def detect_building_with_red_dot(
    screen_img,
    building_template: str,
    matcher,
    red_dot_template: str = "town_building/red_dot.png",
    building_threshold: float = 0.65,
    red_dot_threshold: float = 0.60,
    debug_tag: Optional[str] = None,
    allow_orange: Optional[bool] = None,
    **match_kwargs,
) -> BuildingCheckResult:
    """城鎮建築與正下方驚嘆號紅點檢測器 (純感知觀察函式)。"""
    if screen_img is None or matcher is None:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    screen_h, screen_w = screen_img.shape[:2] if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2 else (600, 800)
    candidate_scales = matcher.compute_candidate_scales(screen_w) if hasattr(matcher, "compute_candidate_scales") else None

    # 1. 建築物比對
    pos_building, conf_building = _locate_building(
        screen_img, building_template, matcher, building_threshold, candidate_scales, match_kwargs
    )
    if not pos_building:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    tag = _resolve_debug_tag(debug_tag, building_template)
    effective_allow_orange = (tag == "bulletin_board") if allow_orange is None else allow_orange

    templates_dir = getattr(matcher, "templates_dir", "templates")
    if not isinstance(templates_dir, str):
        templates_dir = "templates"

    bh, bw = _load_template_dims(templates_dir, building_template, (160, 180))
    raw_scale = getattr(matcher, "_compute_auto_scale", lambda w: 1.0)(screen_w)
    screen_scale = float(raw_scale) if isinstance(raw_scale, (int, float)) and raw_scale > 0 else 1.0

    # 2. 感興趣區域 (ROI) 切割
    crop_roi, roi_coords = _get_building_crop_roi(screen_img, pos_building, bw, bh, screen_scale)
    if crop_roi is None:
        return BuildingCheckResult(found_building=True, has_red_dot=False, building_pos=pos_building, confidence_building=conf_building)

    # 3. 比對與色彩門禁核驗
    has_red_dot, ignored_orange, best_pos_dot, raw_dot_pos, best_conf_dot = _detect_and_verify_red_dot(
        crop_roi, matcher, red_dot_template, red_dot_threshold, candidate_scales, templates_dir, screen_scale, tag, allow_orange=effective_allow_orange
    )

    peak_crop_pos = None if has_red_dot else _find_peak_in_crop(matcher, crop_roi, red_dot_template, screen_scale)
    diagnostic_pos = raw_dot_pos if ignored_orange else best_pos_dot
    x1, y1 = roi_coords[:2]
    global_dot_pos = (x1 + best_pos_dot[0], y1 + best_pos_dot[1]) if (has_red_dot and best_pos_dot) else None

    save_red_dot_diagnostics(
        screen_img=screen_img,
        crop_roi=crop_roi,
        building_template=building_template,
        pos_building=pos_building,
        bw=bw,
        bh=bh,
        scale=screen_scale,
        roi_coords=roi_coords,
        has_red_dot=has_red_dot,
        best_conf=best_conf_dot,
        threshold=red_dot_threshold,
        best_pos_dot=diagnostic_pos,
        peak_crop_pos=peak_crop_pos,
        debug_tag=tag,
        ignored_orange=ignored_orange,
    )

    if has_red_dot:
        logging.info(
            f"🔍 [RedDotDebug] [{tag}] 建築下方成功檢測到紅點！相似度: {best_conf_dot:.4f} "
            f"(門檻: {red_dot_threshold:.2f}, scale: {screen_scale:.3f})，座標: {global_dot_pos}"
        )
        return BuildingCheckResult(
            found_building=True,
            has_red_dot=True,
            building_pos=pos_building,
            red_dot_pos=global_dot_pos,
            confidence_building=conf_building,
            confidence_red_dot=best_conf_dot,
        )

    log_reason = f"橘色任務驚嘆號 (Conf: {best_conf_dot:.2f})" if ignored_orange else f"最高相似度: {best_conf_dot:.4f} < 門檻: {red_dot_threshold:.2f}"
    logging.info(f"🔍 [RedDotDebug] [{tag}] 建築下方無可領取紅點 ({log_reason})，已產出除錯診斷圖: debug_red_dot_{tag}.png")
    return BuildingCheckResult(
        found_building=True,
        has_red_dot=False,
        building_pos=pos_building,
        confidence_building=conf_building,
        confidence_red_dot=best_conf_dot,
    )

