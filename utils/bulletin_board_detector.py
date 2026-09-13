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


from dataclasses import dataclass, field


@dataclass
class FeatureEvidence:
    name: str
    template: str
    threshold: float
    roi: Tuple[int, int, int, int]
    roi_score: float = 0.0
    roi_position: Optional[Tuple[int, int]] = None
    roi_best_scale: Optional[float] = None
    global_score: float = 0.0
    global_position: Optional[Tuple[int, int]] = None
    global_best_scale: Optional[float] = None
    passed: bool = False
    primary_reason: str = "NO_MEANINGFUL_MATCH"
    diagnostic_flags: List[str] = field(default_factory=list)


def match_roi_only(
    screen_img: np.ndarray,
    matcher,
    template_name: str,
    roi: Tuple[int, int, int, int],
    threshold: float = 0.80,
    scales: Optional[List[float]] = None
) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    僅在 Scoped ROI 區域內執行模板比對，回傳全圖絕對中心座標與信心度。
    [核心決策契約]：絕不進行全圖 fallback，確保 Scoped ROI 決策邊界不被破壞。
    :return: (pos_global, confidence)
    """
    if screen_img is None or not isinstance(screen_img, np.ndarray) or getattr(screen_img, "size", 0) == 0:
        return None, 0.0

    h, w = screen_img.shape[:2]
    rx, ry, rw, rh = roi
    rx = max(0, min(rx, w - 1))
    ry = max(0, min(ry, h - 1))
    rw = max(1, min(rw, w - rx))
    rh = max(1, min(rh, h - ry))

    roi_img = screen_img[ry:ry+rh, rx:rx+rw]
    pos_local, conf = matcher.match(roi_img, template_name, threshold=threshold, quiet=True, scales=scales)

    if pos_local is not None and conf >= threshold:
        gx = rx + pos_local[0]
        gy = ry + pos_local[1]
        return (gx, gy), conf

    return None, conf


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
    evidence_map: Dict[str, FeatureEvidence] = field(default_factory=dict)
    diagnostic_report: str = ""
    candidate_scales: List[float] = field(default_factory=list)


def _enrich_feature_diagnostics(
    screen_img: np.ndarray,
    matcher,
    ev: FeatureEvidence,
    scales: Optional[List[float]] = None
):
    """
    僅在 failure milestone (如 UNKNOWN_OVERLAY 確認或逾時) 昂貴執行的全圖診斷分析。
    比對全圖以判斷是否存在 STRONG_MATCH_OUTSIDE_EXPECTED_ROI，並填寫語意原因。
    """
    pos_global, conf_global = matcher.match(screen_img, ev.template, threshold=0.10, quiet=True, scales=scales)
    ev.global_score = conf_global
    ev.global_position = pos_global
    # Matcher API 目前不暴露 winning scale，明確標示為 None (unavailable)，絕不偽造
    ev.roi_best_scale = None
    ev.global_best_scale = None

    rx, ry, rw, rh = ev.roi
    is_inside_roi = False
    if pos_global is not None:
        is_inside_roi = (rx <= pos_global[0] <= rx + rw) and (ry <= pos_global[1] <= ry + rh)

    if not ev.passed:
        if conf_global >= ev.threshold and not is_inside_roi:
            ev.primary_reason = "STRONG_MATCH_OUTSIDE_EXPECTED_ROI"
            ev.diagnostic_flags.append("STRONG_MATCH_OUTSIDE_EXPECTED_ROI")
        elif (ev.threshold - ev.roi_score) <= 0.05:
            ev.primary_reason = "NEAR_THRESHOLD"
            if conf_global >= ev.threshold and not is_inside_roi:
                ev.diagnostic_flags.append("STRONG_MATCH_OUTSIDE_EXPECTED_ROI")
        elif ev.roi_score < 0.20 and conf_global < 0.20:
            ev.primary_reason = "NO_MEANINGFUL_MATCH"
        else:
            ev.primary_reason = "SCORE_BELOW_THRESHOLD"


def format_diagnostic_report(obs: BulletinBoardObservation) -> str:
    """產生結構化語意診斷報告"""
    lines = [f"[BulletinBoardDetector] classification={obs.classification}\n"]

    # 1. Gate
    ev_quit = obs.evidence_map.get("quit")
    if ev_quit:
        status = "PASS" if ev_quit.passed else "FAIL"
        margin = ev_quit.roi_score - ev_quit.threshold
        sign = "+" if margin >= 0 else ""
        lines.append("Gate:")
        lines.append(f"  quit: {status}")
        lines.append(f"    score={ev_quit.roi_score:.3f} threshold={ev_quit.threshold:.3f} margin={sign}{margin:.3f}")
        lines.append(f"    roi={ev_quit.roi} position={ev_quit.roi_position}")
        lines.append("")

    # 2. Positive evidence
    lines.append("Positive evidence:")
    strongest_name, strongest_score, strongest_gap = None, -1.0, 1.0
    likely_diagnoses = []

    for name in ("reset", "task", "task_after"):
        ev = obs.evidence_map.get(name)
        if not ev:
            continue
        status = "PASS" if ev.passed else ("NEAR_MISS" if ev.primary_reason == "NEAR_THRESHOLD" else "FAIL")
        margin = ev.roi_score - ev.threshold
        sign = "+" if margin >= 0 else ""
        lines.append(f"  {name}: {status}")
        lines.append(f"    score={ev.roi_score:.3f} threshold={ev.threshold:.3f} margin={sign}{margin:.3f}")
        lines.append(f"    roi={ev.roi} reason={ev.primary_reason}")
        if ev.global_position:
            lines.append(f"    global_best={ev.global_score:.3f} at {ev.global_position}")
        if ev.diagnostic_flags:
            lines.append(f"    flags={ev.diagnostic_flags}")

        gap = ev.threshold - ev.roi_score
        if ev.roi_score > strongest_score:
            strongest_score = ev.roi_score
            strongest_name = name
            strongest_gap = gap

        if "STRONG_MATCH_OUTSIDE_EXPECTED_ROI" in ev.diagnostic_flags or ev.primary_reason == "STRONG_MATCH_OUTSIDE_EXPECTED_ROI":
            likely_diagnoses.append(f"{name} template has a strong match outside expected ROI. Possible ROI mismatch or UI layout change.")
        elif ev.primary_reason == "NEAR_THRESHOLD":
            likely_diagnoses.append(f"{name} is near threshold (short by {gap:.3f}). Possible slight scale or lighting variation.")

    lines.append("")

    # 3. Negative evidence
    lines.append("Negative evidence:")
    tidy_status = "DETECTED" if obs.conf_bag_tidy >= 0.80 else "ABSENT"
    disasm_status = "DETECTED" if obs.conf_bag_disasm >= 0.80 else "ABSENT"
    lines.append(f"  bag_tidy: {tidy_status} (score={obs.conf_bag_tidy:.2f})")
    lines.append(f"  bag_disassembly: {disasm_status} (score={obs.conf_bag_disasm:.2f})")
    lines.append("")

    # 4. Strongest positive evidence
    if strongest_name and not any(ev.passed for ev in obs.evidence_map.values() if ev.name in ("reset", "task", "task_after")):
        lines.append(f"Strongest positive evidence: {strongest_name}={strongest_score:.3f}, short by {strongest_gap:.3f}\n")

    # 5. Likely diagnosis
    lines.append("Likely diagnosis:")
    if likely_diagnoses:
        for d in likely_diagnoses:
            lines.append(f"  - {d}")
    elif obs.classification == "UNKNOWN_OVERLAY":
        lines.append("  - All positive features failed to match inside ROI. Possible UI appearance change or completely different window.")
    elif obs.classification == "KNOWN_INTERFERENCE":
        lines.append("  - Explicit backpack features detected. Confirm this overlay is not bulletin board.")
    else:
        lines.append("  - None")
    lines.append("")

    # 6. Candidate scales
    lines.append(f"Candidate scales: {obs.candidate_scales}")
    lines.append("Best scale: unavailable (matcher does not expose winning scale index)\n")
    lines.append("Debug artifact: debug_bulletin_board_verify.png")

    return "\n".join(lines)


def observe_bulletin_board(
    screen_img: np.ndarray,
    matcher,
    cfg: Optional[Dict[str, Any]] = None,
    run_full_diagnostics: bool = False
) -> BulletinBoardObservation:
    """
    觀察並結構化解析目前畫面相對於告示牌介面的所有特徵。
    [計算成本分離]：
    - 快速路徑：每幀僅執行 Scoped ROI 比對與背包檢測，開銷最小。
    - 診斷路徑：僅在非 BOARD_CONFIRMED 且需要詳細報告時（或 run_full_diagnostics=True），
      補齊全圖比對並生成語意診斷報告。
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
    obs.candidate_scales = list(board_scales) if board_scales else []

    positive_threshold = 0.65

    # 1. 基礎門禁：quit 按鈕 (僅限 quit_roi)
    pos_quit, conf_quit = match_roi_only(screen_img, matcher, quit_btn, quit_roi, threshold=0.80, scales=board_scales)
    ev_quit = FeatureEvidence(
        name="quit", template=quit_btn, threshold=0.80, roi=quit_roi,
        roi_score=conf_quit, roi_position=pos_quit, passed=(pos_quit is not None),
        primary_reason="PASS" if pos_quit else "SCORE_BELOW_THRESHOLD"
    )
    obs.evidence_map["quit"] = ev_quit
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

    # 3. 正向三通道獨立檢查 (僅限各自 Scoped ROI)
    pos_reset, conf_reset = match_roi_only(screen_img, matcher, reset_btn, reset_roi, threshold=positive_threshold, scales=board_scales)
    ev_reset = FeatureEvidence(
        name="reset", template=reset_btn, threshold=positive_threshold, roi=reset_roi,
        roi_score=conf_reset, roi_position=pos_reset, passed=(pos_reset is not None),
        primary_reason="PASS" if pos_reset else ("NEAR_THRESHOLD" if (positive_threshold - conf_reset) <= 0.05 else "SCORE_BELOW_THRESHOLD")
    )
    obs.evidence_map["reset"] = ev_reset
    obs.pos_reset = pos_reset
    obs.conf_reset = conf_reset

    pos_task, conf_task = match_roi_only(screen_img, matcher, task_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    ev_task = FeatureEvidence(
        name="task", template=task_tpl, threshold=positive_threshold, roi=task_roi,
        roi_score=conf_task, roi_position=pos_task, passed=(pos_task is not None),
        primary_reason="PASS" if pos_task else ("NEAR_THRESHOLD" if (positive_threshold - conf_task) <= 0.05 else "SCORE_BELOW_THRESHOLD")
    )
    obs.evidence_map["task"] = ev_task
    obs.pos_task = pos_task
    obs.conf_task = conf_task

    pos_after, conf_after = match_roi_only(screen_img, matcher, task_after_tpl, task_roi, threshold=positive_threshold, scales=board_scales)
    ev_after = FeatureEvidence(
        name="task_after", template=task_after_tpl, threshold=positive_threshold, roi=task_roi,
        roi_score=conf_after, roi_position=pos_after, passed=(pos_after is not None),
        primary_reason="PASS" if pos_after else ("NEAR_THRESHOLD" if (positive_threshold - conf_after) <= 0.05 else "SCORE_BELOW_THRESHOLD")
    )
    obs.evidence_map["task_after"] = ev_after
    obs.pos_task_after = pos_after
    obs.conf_task_after = conf_after

    # 4. 決策分類 (嚴格只依據 ROI match 結果，任何 global match 均不影響決策)
    if obs.has_bag:
        obs.classification = "KNOWN_INTERFERENCE"
    elif ev_reset.passed or ev_task.passed or ev_after.passed:
        obs.classification = "BOARD_CONFIRMED"
        hit_name = "Reset" if ev_reset.passed else ("Before" if ev_task.passed else "After")
        hit_conf = conf_reset if ev_reset.passed else (conf_task if ev_task.passed else conf_after)
        logging.info("📋 [懸賞告示牌 介面驗證] 驗證成功 (通道: %s(%.2f))", hit_name, hit_conf)
        return obs
    else:
        obs.classification = "UNKNOWN_OVERLAY"

    # 5. 診斷路徑 (僅在 failure 或顯式診斷要求時補齊昂貴全圖分析)
    if obs.classification != "BOARD_CONFIRMED":
        for ev in (ev_reset, ev_task, ev_after):
            _enrich_feature_diagnostics(screen_img, matcher, ev, scales=board_scales)

        obs.diagnostic_report = format_diagnostic_report(obs)
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

