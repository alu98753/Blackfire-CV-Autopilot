"""
🎒 背包大量分解 - 網格座標微調與校準工具 (134 x 139.5 規格)
--------------------------------------------------
使用說明：
1. 您可以在下方【微調參數區】修改數值 (如 QUIT_DX, QUIT_DY)。
2. 在終端機執行：
   .\.venv\Scripts\python scripts\calibrate_bag_cleaning_grid.py
3. 打開 scratch/bag_cleaning_calibration_result.png
   觀察紅/黃/紫框與黃色打勾區是否完美對齊您的 134 x 139.5 裝備格子。
4. 滿意後，將此組參數同步更新至 states/handlers/bag_cleaning.py 即可！
"""

# ==================================================
# 🎯 【微調參數區】您可以在這裡自由修改數值並執行測試！
# ==================================================
# 1. 以 common/quit.png 為錨點的 Row 0 Col 0 設計偏移 (以 1920x1080 基準)
QUIT_DX = -842   # 相對於 quit.png 中心的 X 軸偏移量
QUIT_DY = 87     # 相對於 quit.png 中心的 Y 軸偏移量

# 2. 以 common/select_all.png 為備用錨點的 Row 0 Col 0 設計偏移
SELECT_ALL_DX = -127
SELECT_ALL_DY = -520

# 3. 格子大小 (寬度/高度) 與行/列間距 (基準 1920x1080)
CELL_W = 134.0
CELL_H = 139.5
STEP_X = CELL_W
STEP_Y = CELL_H

# 4. 打勾標記偵測區域 (相對於格子中心 cx, cy)
CHECK_OFFSET_X = -21  # 打勾區相對於中心 cx 的 X 偏移
CHECK_OFFSET_Y = -5   # 打勾區相對於中心 cy 的 Y 偏移 (貼近圖案正中心)
CHECK_W = 34
CHECK_H = 30

ROWS = 3
COLS = 6

# 5. 指定輸入截圖檔名 (若找不到或為 debag.png，將自動載入 scratch/debug/ 下最新的 debug_bag_4_grid_scan_*.png)
INPUT_IMAGE = r"scratch/debug/debug_bag_4_grid_scan_20260903_111801.png"
# ==================================================

import os
import sys
import glob
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from vision.matcher import TemplateMatcher
from states.handlers.bag_cleaning import BagCleaningHandler
from states.state_machine import GameStateMachine
from unittest.mock import MagicMock

def find_target_image(base_dir):
    """依優先序搜尋校準輸入圖像"""
    # 1. 命令列指定路徑
    if len(sys.argv) > 1:
        arg_path = sys.argv[1].replace("\t", "/t")
        if os.path.isabs(arg_path) and os.path.exists(arg_path):
            return os.path.normpath(arg_path)
        rel_path = os.path.normpath(os.path.join(base_dir, arg_path))
        if os.path.exists(rel_path):
            return rel_path

    # 2. INPUT_IMAGE 指定路徑
    clean_input = INPUT_IMAGE.replace("\t", "/t")
    if os.path.isabs(clean_input) and os.path.exists(clean_input):
        return os.path.normpath(clean_input)
    rel_input = os.path.normpath(os.path.join(base_dir, clean_input))
    if os.path.exists(rel_input):
        return rel_input

    # 3. 自動搜尋 scratch/debug/ 內最新的 debug_bag_4_grid_scan_*.png
    debug_files = sorted(glob.glob(os.path.join(base_dir, "scratch", "debug", "debug_bag_4_grid_scan_*.png")))
    if debug_files:
        print(f"[INFO] 未找到指定圖檔，自動載入最新除錯截圖: {os.path.basename(debug_files[-1])}")
        return debug_files[-1]

    return None

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_path = find_target_image(base_dir)

    if not img_path or not os.path.exists(img_path):
        print(f"[ERROR] Cannot find input image '{INPUT_IMAGE}' or any debug screenshots in scratch/debug/!")
        return

    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    scale_x = w / 1920.0
    scale_y = h / 1080.0
    print(f"[INFO] Loaded image successfully: {img_path}")
    print(f"[INFO] Resolution: {w}x{h} (Scale X: {scale_x:.4f}, Y: {scale_y:.4f})")

    matcher = TemplateMatcher(templates_dir=os.path.join(base_dir, "templates"))
    sm = GameStateMachine(MagicMock(), matcher, MagicMock())
    sm.config = {"type": "mix", "disassemble_colors": ["gray_or_empty", "green", "blue"]}
    handler = BagCleaningHandler(sm)

    # 手動與自動比對定位
    pos_quit, conf_quit = matcher.match(img, "common/quit.png", threshold=0.40)
    pos_all, conf_all = matcher.match(img, "common/select_all.png", threshold=0.40)

    start_cx, start_cy = None, None
    anchor_name = ""

    if pos_quit:
        anchor_name = f"quit.png {pos_quit} (conf: {conf_quit:.4f})"
        start_cx = pos_quit[0] + int(QUIT_DX * scale_x)
        start_cy = pos_quit[1] + int(QUIT_DY * scale_y)
    elif pos_all:
        anchor_name = f"select_all.png {pos_all} (conf: {conf_all:.4f})"
        start_cx = pos_all[0] + int(SELECT_ALL_DX * scale_x)
        start_cy = pos_all[1] + int(SELECT_ALL_DY * scale_y)
    else:
        # 使用預設標準坐標 (1121, 105) 防護
        pos_quit = (int(1391 * scale_x), int(185 * scale_y))
        anchor_name = f"quit.png (manual fallback {pos_quit})"
        start_cx = pos_quit[0] + int(QUIT_DX * scale_x)
        start_cy = pos_quit[1] + int(QUIT_DY * scale_y)

    print(f"[INFO] Anchor used: {anchor_name}")
    print(f"[INFO] Calculated Row 0 Col 0 top-left: ({start_cx}, {start_cy})")

    cell_w = CELL_W * scale_x
    cell_h = CELL_H * scale_y
    step_x = STEP_X * scale_x
    step_y = STEP_Y * scale_y

    cz_w = int(CHECK_W * scale_x)
    cz_h = int(CHECK_H * scale_y)

    out_img = img.copy()
    grid_results = []

    # 精準綠色打勾 HSV 閾值 (排除藍綠色/青色背景)
    lower_green = np.array([55, 120, 90])
    upper_green = np.array([85, 255, 255])

    disassemble_colors = sm.config.get("disassemble_colors", ["gray_or_empty", "green", "blue"])

    for r in range(ROWS):
        for c in range(COLS):
            x1 = int(start_cx + c * step_x)
            y1 = int(start_cy + r * step_y)
            x2 = int(x1 + cell_w)
            y2 = int(y1 + cell_h)

            cx = int(x1 + cell_w / 2.0)
            cy = int(y1 + cell_h / 2.0)

            crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            color = handler.classify_slot_color(crop) if crop.size > 0 else "gray_or_empty"
            is_valuable = color not in disassemble_colors

            check_x = int(cx + CHECK_OFFSET_X * scale_x)
            check_y = int(cy + CHECK_OFFSET_Y * scale_y)
            check_zone = img[max(0, check_y):min(h, check_y + cz_h), max(0, check_x):min(w, check_x + cz_w)]

            has_check = False
            green_px = 0
            if check_zone.size > 0:
                hsv_check = cv2.cvtColor(check_zone, cv2.COLOR_BGR2HSV)
                mask_green = cv2.inRange(hsv_check, lower_green, upper_green)
                green_px = int((mask_green > 0).sum())
                has_check = green_px > 15

            grid_results.append((r, c, cx, cy, x1, y1, x2, y2, check_x, check_y, color, is_valuable, has_check, green_px))

    color_bgr_map = {
        "purple": (255, 0, 255),
        "blue": (255, 255, 0),
        "green": (0, 255, 0),
        "red": (0, 0, 255),
        "orange_yellow": (0, 165, 255),
        "gray_or_empty": (128, 128, 128)
    }

    print("\n--- 網格識別結果明細 ---")
    for item in grid_results:
        r, c, cx, cy, x1, y1, x2, y2, chk_x, chk_y, color, is_valuable, has_check, green_px = item
        box_color = color_bgr_map.get(color, (255, 255, 255))

        # 1. 繪製 134 x 139.5 主外框
        cv2.rectangle(out_img, (x1, y1), (x2, y2), box_color, 2)
        # 2. 繪製中心點
        cv2.circle(out_img, (cx, cy), 3, (0, 255, 255), -1)
        # 3. 繪製打勾檢測區 (黃色小方框)
        cv2.rectangle(out_img, (chk_x, chk_y), (chk_x + cz_w, chk_y + cz_h), (0, 255, 255), 1)

        check_str = "[V]" if has_check else "[X]"
        val_str = "VAL" if is_valuable else "COM"
        label = f"R{r}C{c} {color[:4]} {val_str} {check_str}"
        cv2.putText(out_img, label, (x1 + 4, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        target_flag = " <-- [TARGET DESELECT]" if (is_valuable and has_check) else ""
        print(f"R{r}C{c}: {color:13s} | {val_str} | {check_str} (green_px={green_px:3d}){target_flag}")

    out_dir = os.path.join(base_dir, "scratch")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "bag_cleaning_calibration_result.png")
    cv2.imwrite(out_path, out_img)
    print(f"\n[SUCCESS] Calibration image saved: {out_path}")
    print(f"[HINT] Open {out_path} to inspect 134x139.5 grid overlay and yellow check_zone boxes!")

if __name__ == "__main__":
    main()
