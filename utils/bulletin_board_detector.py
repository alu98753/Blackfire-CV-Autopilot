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


from dataclasses import dataclass


@dataclass
class BulletinBoardObservation:
    pos_quit: Optional[Tuple[int, int]] = None
    conf_quit: float = 0.0
    pos_reset: Optional[Tuple[int, int]] = None
    conf_reset: float = 0.0
    pos_task: Optional[Tuple[int, int]] = None
    conf_task: float = 0.0
    pos_task_after: Optional[Tuple[int, int]] = None
    conf_task_after: float = 0.0
    has_bag: bool = False
    conf_bag_tidy: float = 0.0
    conf_bag_disasm: float = 0.0
    classification: str = "NO_OVERLAY"


def observe_bulletin_board(
    screen_img: np.ndarray,
    matcher,
    cfg: Optional[Dict[str, Any]] = None
) -> BulletinBoardObservation:
    """
    觀察並結構化解析目前畫面相對於告示牌介面的所有特徵。
    分類結果可能為：
    - BOARD_CONFIRMED: quit 可見、無背包特徵、且至少一項告示牌正向特徵 (reset / task / task_after) 命中。
    - KNOWN_INTERFERENCE: quit 可見，且偵測到明確的負向干擾特徵 (如背包 tidy / Disassembly)。
    - UNKNOWN_OVERLAY: quit 可見，但既無正向告示牌特徵、亦無已知干擾特徵 (未知覆蓋層)。
    - NO_OVERLAY: 未偵測到 quit 視窗按鈕。
    """
    obs = BulletinBoardObservation()
    if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
        return obs

    h, w = screen_img.shape[:2]
    cfg = cfg or {}
    quit_btn = cfg.get("quit_btn", "common/quit.png")
    task_tpl = cfg.get("task_btn", "town_building/bulletin_board/task.png")
    task_after_tpl = cfg.get("task_after_btn", "town_building/bulletin_board/task_after.png")
    reset_btn = cfg.get("reset_btn", "town_building/bulletin_board/reset.png")

    quit_roi = (int(w * 0.5), 0, w - int(w * 0.5), int(h * 0.45))
    task_roi = (0, 0, min(w, int(w * 0.60)), h)
    reset_roi = (0, int(h * 0.60), min(w, int(w * 0.60)), h - int(h * 0.60))

    board_scales = None
    if matcher is not None and hasattr(matcher, "compute_candidate_scales"):
        board_scales = matcher.compute_candidate_scales(w)

    positive_threshold = 0.65

    # 1. 基礎門禁：quit 按鈕
    pos_quit, _, conf_quit = match_in_roi(screen_img, matcher, quit_btn, quit_roi, threshold=0.80, scales=board_scales)
    obs.pos_quit = pos_quit
    obs.conf_quit = conf_quit
    if pos_quit is None:
        obs.classification = "NO_OVERLAY"
        return obs

    # 2. 背包排他特徵檢查 (負向特徵)
    pos_tidy, conf_tidy = matcher.match(screen_img, "common/tidy.png", threshold=0.80, quiet=True)
    pos_disasm, conf_disasm = matcher.match(screen_img, "common/Disassembly.png", threshold=0.80, quiet=True)
    obs.conf_bag_tidy = conf_tidy
    obs.conf_bag_disasm = conf_disasm
    obs.has_bag = (pos_tidy is not None) or (pos_disasm is not None)

    # 3. 正向三通道獨立檢查
    pos_reset, _, conf_reset = match_in_roi(screen_img, matcher, reset_btn, reset_roi, threshold=positive_threshold, scales=board_scales)
    obs.pos_reset = pos_reset
    obs.conf_reset = conf_reset

    pos_task, _, conf_task = match_in_roi(screen_img, matcher, task_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    obs.pos_task = pos_task
    obs.conf_task = conf_task

    pos_after, _, conf_after = match_in_roi(screen_img, matcher, task_after_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    obs.pos_task_after = pos_after
    obs.conf_task_after = conf_after

    # 4. 決策分類
    if obs.has_bag:
        obs.classification = "KNOWN_INTERFERENCE"
    elif (pos_reset is not None) or (pos_task is not None) or (pos_after is not None):
        obs.classification = "BOARD_CONFIRMED"
        hit_channel = "Reset" if pos_reset else ("Before" if pos_task else "After")
        hit_conf = conf_reset if pos_reset else (conf_task if pos_task else conf_after)
        logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: %s(%.2f))", hit_channel, hit_conf)
    else:
        obs.classification = "UNKNOWN_OVERLAY"

    if obs.classification != "BOARD_CONFIRMED":
        logging.warning(
            "[BulletinBoardDetector] Classification=%s | quit=%.2f, reset=%.2f, task=%.2f, task_after=%.2f, bag_tidy=%.2f, bag_disasm=%.2f",
            obs.classification, obs.conf_quit, obs.conf_reset, obs.conf_task, obs.conf_task_after, obs.conf_bag_tidy, obs.conf_bag_disasm
        )
        if obs.classification == "UNKNOWN_OVERLAY":
            write_debug_image("debug_bulletin_board_verify.png", screen_img)

    return obs


def is_inside_bulletin_board(
    screen_img: np.ndarray,
    matcher,
    cfg: Optional[Dict[str, Any]] = None
) -> bool:
    """
    排他性驗證是否身處告示牌介面 (向後相容包裝)。
    """
    obs = observe_bulletin_board(screen_img, matcher, cfg)
    return obs.classification == "BOARD_CONFIRMED"


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

