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


def detect_building_with_red_dot(
    screen_img,
    building_template: str,
    matcher,
    red_dot_template: str = "town_building/red_dot.png",
    building_threshold: float = 0.65,
    red_dot_threshold: float = 0.65,
    **match_kwargs,
) -> BuildingCheckResult:
    """
    城鎮建築與正下方驚嘆號紅點檢測器 (純感知觀察函式)。
    
    遵守 AGENTS.md 與 Greenfield-lite v1 架構規範：
    1. Scoped Crop Only：紅點檢測嚴格侷限於「建築物正下方」局部 ROI，禁止全螢幕盲掃。
    2. 感知與決策分離：僅產出 BuildingCheckResult，絕不進行點擊或修改狀態。

    :param screen_img: 城鎮畫面 (numpy.ndarray)
    :param building_template: 建築物模板相對路徑 (例如 town_building/mysterious_treasure/mysterious_treasure.png)
    :param matcher: TemplateMatcher 實例
    :param red_dot_template: 驚嘆號紅點模板路徑 (預設 town_building/red_dot.png)
    :param building_threshold: 建築比對信心度門檻 (預設 0.65)
    :param red_dot_threshold: 紅點比對信心度門檻 (預設 0.75)
    :return: BuildingCheckResult
    """
    if screen_img is None or matcher is None:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    pos_building, conf_building = matcher.match(
        screen_img, building_template, threshold=building_threshold, **match_kwargs
    )
    if not pos_building:
        return BuildingCheckResult(found_building=False, has_red_dot=False)

    bx, by = pos_building
    screen_h, screen_w = (600, 800)
    if hasattr(screen_img, "shape") and len(screen_img.shape) >= 2:
        try:
            screen_h, screen_w = screen_img.shape[:2]
        except Exception:
            pass

    # 取得建築模板尺寸以計算正下方局部感興趣區域 (Scoped ROI)
    templates_dir = getattr(matcher, "templates_dir", "templates")
    if not isinstance(templates_dir, str):
        templates_dir = "templates"
    bw, bh = 180, 160  # 預設保底尺寸
    if isinstance(building_template, str):
        t_path = os.path.join(templates_dir, building_template)
        if os.path.exists(t_path):
            t_img = cv2.imread(t_path)
            if t_img is not None:
                bh, bw = t_img.shape[:2]

    # 💡 依據使用者指引與遊戲實測：紅點常駐於建築物「正下方」
    # 水平方向：涵蓋建築物寬度並向左右微幅擴展 30px
    # 垂直方向：自建築物下半部 (by) 延伸至建築底部外側 120px
    x1 = max(0, int(bx - bw // 2 - 30))
    x2 = min(screen_w, int(bx + bw // 2 + 30))
    y1 = max(0, int(by))
    y2 = min(screen_h, int(by + bh // 2 + 120))

    if x2 <= x1 or y2 <= y1:
        return BuildingCheckResult(
            found_building=True,
            has_red_dot=False,
            building_pos=pos_building,
            confidence_building=conf_building,
        )

    try:
        crop_roi = screen_img[y1:y2, x1:x2]
    except Exception:
        crop_roi = screen_img

    if isinstance(crop_roi, np.ndarray) and (crop_roi.size == 0 or crop_roi.shape[0] < 20 or crop_roi.shape[1] < 20):
        return BuildingCheckResult(
            found_building=True,
            has_red_dot=False,
            building_pos=pos_building,
            confidence_building=conf_building,
        )

    # 局部比對驚嘆號紅點 (繼承全螢幕之縮放比例，避免局部裁切導致 auto_scale 回退)
    screen_scale = getattr(matcher, "_compute_auto_scale", lambda w: None)(screen_w)
    pos_dot, conf_dot = matcher.match(
        crop_roi,
        red_dot_template,
        threshold=red_dot_threshold,
        scale=screen_scale,
    )
    if pos_dot:
        global_dot_pos = (x1 + pos_dot[0], y1 + pos_dot[1])
        return BuildingCheckResult(
            found_building=True,
            has_red_dot=True,
            building_pos=pos_building,
            red_dot_pos=global_dot_pos,
            confidence_building=conf_building,
            confidence_red_dot=conf_dot,
        )

    # 比對未通過時，輸出診斷截圖供現場除錯 (符合 debug-artifact-management 規範)
    if isinstance(crop_roi, np.ndarray):
        try:
            from utils.debug_artifacts import write_debug_image
            write_debug_image("debug_red_dot_crop.png", crop_roi)
            logging.debug(
                f"🔍 [RedDotDebug] 建築下方未檢出紅點 (最大信心度: {conf_dot:.4f}, 門檻: {red_dot_threshold}, scale: {screen_scale})，已寫入 debug_red_dot_crop.png"
            )
        except Exception:
            pass

    return BuildingCheckResult(
        found_building=True,
        has_red_dot=False,
        building_pos=pos_building,
        confidence_building=conf_building,
        confidence_red_dot=conf_dot,
    )
