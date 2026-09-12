"""
懸賞告示牌介面感知檢測模組 (Bulletin Board Detector)

符合 Greenfield Lite v1 之「感知與決策分離」原則：
- 本模組只負責觀察畫面特徵、Scoped ROI 計算與輸出狀態/診斷，絕不觸發任何滑鼠點擊或狀態機跳轉。
- 集中管理告示牌專屬特徵：quit 門禁、背包排他過濾、三通道 Early Return 與自適應動態尺度。
"""

import logging
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from utils.debug_artifacts import write_debug_image


def match_in_roi(
    screen_img: np.ndarray,
    matcher,
    template_name: str,
    roi: Tuple[int, int, int, int],
    threshold: float = 0.80,
    scales: Optional[List[float]] = None
) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int, int, int]], float]:
    """
    在指定 Scoped ROI 區域內執行模板比對，回傳全圖中心座標、全圖 BBox 與信心度。
    :return: (pos_global, bbox_global, confidence)
    """
    if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
        return None, None, 0.0

    h, w = screen_img.shape[:2]
    rx, ry, rw, rh = roi
    rx = max(0, min(rx, w - 1))
    ry = max(0, min(ry, h - 1))
    rw = max(1, min(rw, w - rx))
    rh = max(1, min(rh, h - ry))

    roi_img = screen_img[ry:ry+rh, rx:rx+rw]
    pos_local, conf = matcher.match(roi_img, template_name, threshold=threshold, quiet=True, scales=scales)

    tmpl = getattr(matcher, "_load_template", lambda _: None)(template_name)
    tw, th = (tmpl.shape[1], tmpl.shape[0]) if isinstance(tmpl, np.ndarray) else (40, 40)

    if pos_local is not None:
        gx = rx + pos_local[0]
        gy = ry + pos_local[1]
        bx = max(0, gx - tw // 2)
        by = max(0, gy - th // 2)
        return (gx, gy), (bx, by, tw, th), conf

    # 若 ROI 內未達標，進行全圖比對以取得全局最高匹配資訊供診斷繪圖
    pos_global, conf_global = matcher.match(screen_img, template_name, threshold=threshold, quiet=True, scales=scales)
    if pos_global is not None:
        bx = max(0, pos_global[0] - tw // 2)
        by = max(0, pos_global[1] - th // 2)
        return pos_global, (bx, by, tw, th), conf_global
    return None, None, max(conf, conf_global)


def has_bag_features(screen_img: np.ndarray, matcher, threshold: float = 0.80) -> bool:
    """
    排他特徵檢查：檢測畫面是否存在背包專屬特徵 (tidy.png / Disassembly.png)。
    若存在，代表此視窗為背包而非告示牌。
    """
    if screen_img is None or matcher is None:
        return False
    pos_tidy, _ = matcher.match(screen_img, "common/tidy.png", threshold=threshold, quiet=True)
    pos_disasm, _ = matcher.match(screen_img, "common/Disassembly.png", threshold=threshold, quiet=True)
    return (pos_tidy is not None) or (pos_disasm is not None)


def is_inside_bulletin_board(
    screen_img: np.ndarray,
    matcher,
    cfg: Optional[Dict[str, Any]] = None
) -> bool:
    """
    排他性驗證是否身處告示牌介面：
    必須滿足：
    1. 基礎門禁：看得到 quit_btn（未出現 quit 立即回傳 False 省去後續比對）；
    2. 負向排他：畫面絕無背包專屬特徵（tidy.png、Disassembly.png）；
    3. 正向三通道 Early Return（自適應動態尺度，門檻 0.65）：
       - 通道 1【Reset 按鈕】：左下角出現 reset.png
       - 通道 2【Before 任務】：左側出現未接取任務捲軸 task.png
       - 通道 3【After 任務】：左側出現已接取任務捲軸 task_after.png
       只要任一通道命中，立即 Early Return True。
    4. 若三者皆未命中，透過 DebugVisualizer 輸出至 debug_bulletin_board_verify.png。
    """
    if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
        return False

    h, w = screen_img.shape[:2]
    cfg = cfg or {}
    quit_btn = cfg.get("quit_btn", "common/quit.png")
    task_tpl = cfg.get("task_btn", "town_building/bulletin_board/task.png")
    task_after_tpl = cfg.get("task_after_btn", "town_building/bulletin_board/task_after.png")
    reset_btn = cfg.get("reset_btn", "town_building/bulletin_board/reset.png")

    # 0. 定義 Scoped ROI 範圍 (依畫面幾何劃分)
    quit_roi = (int(w * 0.5), 0, w - int(w * 0.5), int(h * 0.45))
    task_roi = (0, 0, min(w, int(w * 0.60)), h)
    reset_roi = (0, int(h * 0.60), min(w, int(w * 0.60)), h - int(h * 0.60))

    # 針對解析度微幅縮放差異，採用自適應動態尺度
    board_scales = matcher.compute_candidate_scales(w)
    positive_threshold = 0.65

    # 1. 基礎門禁：quit 按鈕
    pos_quit, bbox_quit, conf_quit = match_in_roi(screen_img, matcher, quit_btn, quit_roi, threshold=0.80, scales=board_scales)
    if pos_quit is None:
        return False

    # 2. 背包排他特徵檢查
    if has_bag_features(screen_img, matcher, threshold=0.80):
        return False

    # 3. 正向三通道獨立檢查（Early Return：其中一張為 True 即確認並立即返回）
    pos_reset, bbox_reset, conf_reset = match_in_roi(screen_img, matcher, reset_btn, reset_roi, threshold=positive_threshold, scales=board_scales)
    if pos_reset is not None:
        logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: Reset(%.2f))", conf_reset)
        return True

    pos_task, bbox_task, conf_task = match_in_roi(screen_img, matcher, task_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    if pos_task is not None:
        logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: Before(%.2f))", conf_task)
        return True

    pos_after, bbox_after, conf_after = match_in_roi(screen_img, matcher, task_after_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    if pos_after is not None:
        logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: After(%.2f))", conf_after)
        return True

    # 4. 若三者皆未命中，輸出除錯影像並返回 False
    write_debug_image("debug_bulletin_board_verify.png", screen_img)
    return False


def scan_and_filter_tasks(
    screen_img: np.ndarray,
    matcher,
    task_tpl: str,
    task_after_tpl: str,
    w_img: int,
    h_img: int
) -> Tuple[List[Any], List[Any]]:
    """
    掃描畫面左半邊所有待接任務錨點，並比對 task_after 過濾已接取項目。
    回傳: (raw_anchors, filtered_anchors)
    """
    raw_anchors = matcher.match_all(screen_img, task_tpl, threshold=0.70, brightness_threshold=0.88, quiet=True)
    raw_anchors = [a for a in raw_anchors if a[0] < w_img // 2]
    logging.info(f"📋 [懸賞告示牌 診斷分析] 在畫面左半邊共掃描到 {len(raw_anchors)} 個未接取任務候選點")

    tmpl = getattr(matcher, "_load_template", lambda _: None)(task_after_tpl)
    mean_after_temp = np.mean(cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)) if isinstance(tmpl, np.ndarray) else 89.3

    anchors = []
    for (cx, cy, conf_before) in raw_anchors:
        x1, x2 = max(0, cx - 60), min(w_img, cx + 60)
        y1, y2 = max(0, cy - 60), min(h_img, cy + 60)
        roi = screen_img[y1:y2, x1:x2]
        pos_after, conf_after = matcher.match(roi, task_after_tpl, threshold=0.75, quiet=True)
        if pos_after:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if isinstance(roi, np.ndarray) else None
            ratio_after = (np.mean(roi_gray) / max(1.0, mean_after_temp)) if roi_gray is not None else 1.0
            if conf_after >= 0.75 and ratio_after <= 0.88:
                continue
        anchors.append((cx, cy, conf_before))
    return raw_anchors, anchors

