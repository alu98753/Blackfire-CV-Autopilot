"""
🎒 背包大量分解 - 網格座標微調與校準工具 (134 x 139.5 規格)
--------------------------------------------------
使用說明：
1. 您可以在下方【微調參數區】修改數值 (如 QUIT_DX, QUIT_DY)。
2. 在終端機執行：
   .\.venv\Scripts\python tools\calibrate_bag_cleaning_grid.py
3. 打開 e:\Side_Project\BlackfireCrusade_tool\scratch\bag_cleaning_calibration_result.png
   觀察紅/黃/紫框與黃色打勾區是否完美對齊您的 134 x 139.5 裝備格子。
4. 滿意後，將此組參數同步更新至 states/handlers/bag_cleaning.py 即可！
"""

# ==================================================
# 🎯 【微調參數區】您可以在這裡自由修改數值並執行測試！
# ==================================================
# 1. 以 common/quit.png (右上角紅色 X 按鈕中心: 1391, 213) 為錨點的 Row 0 Col 0 設計偏移
QUIT_DX = -842   # 相對於 quit.png 中心的 X 軸偏移量
QUIT_DY = 76  # 相對於 quit.png 中心的 Y 軸偏移量

# 2. 以 common/select_all.png (全選按鈕中心: 676, 808) 為備用錨點的 Row 0 Col 0 設計偏移
SELECT_ALL_DX = -127
SELECT_ALL_DY = -520

# 3. 格子大小 (寬度/高度) 與行/列間距
CELL_W = 134.0
CELL_H = 139.5
STEP_X = CELL_W
STEP_Y = CELL_H

ROWS = 3
COLS = 6

# 4. 指定用於校準的輸入截圖檔名 (專案根目錄或 templates/debag.png)
INPUT_IMAGE = r"tools/debag.png"
# ==================================================

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from vision.matcher import TemplateMatcher
from states.handlers.bag_cleaning import BagCleaningHandler
from states.state_machine import GameStateMachine
from unittest.mock import MagicMock

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 支援絕對路徑與相對路徑，並防止 Windows \t 反斜線轉義誤判
    clean_input_path = INPUT_IMAGE.replace("\t", "/t")
    if os.path.isabs(clean_input_path):
        img_path = os.path.normpath(clean_input_path)
    else:
        img_path = os.path.normpath(os.path.join(base_dir, clean_input_path))
        
    if not os.path.exists(img_path):
        print(f"[ERROR] Cannot find input image '{img_path}'!")
        return
        
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    print(f"[INFO] Loaded image successfully: {w}x{h}")
    
    matcher = TemplateMatcher(templates_dir=os.path.join(base_dir, "templates"))
    sm = GameStateMachine(MagicMock(), matcher, MagicMock())
    sm.config = {"type": "mix", "disassemble_colors": ["gray_or_empty", "green"]}
    handler = BagCleaningHandler(sm)
    
    # 手動與自動比對定位
    pos_quit, conf_quit = matcher.match(img, "common/quit.png", threshold=0.40)
    pos_all, conf_all = matcher.match(img, "common/select_all.png", threshold=0.40)
    
    start_cx, start_cy = None, None
    anchor_name = ""
    
    if pos_quit:
        anchor_name = f"quit.png {pos_quit} (conf: {conf_quit:.4f})"
        start_cx = pos_quit[0] + QUIT_DX
        start_cy = pos_quit[1] + QUIT_DY
    elif pos_all:
        anchor_name = f"select_all.png {pos_all} (conf: {conf_all:.4f})"
        start_cx = pos_all[0] + SELECT_ALL_DX
        start_cy = pos_all[1] + SELECT_ALL_DY
    else:
        # 使用預設標準坐標 (1121, 105) 防護
        pos_quit = (1121, 105)
        anchor_name = f"quit.png (manual fallback {pos_quit})"
        start_cx = pos_quit[0] + QUIT_DX
        start_cy = pos_quit[1] + QUIT_DY
        
    print(f"[INFO] Anchor used: {anchor_name}")
    print(f"[INFO] Calculated Row 0 Col 0 center: ({start_cx}, {start_cy})")
    
    out_img = img.copy()
    grid_results = []
    
    for r in range(ROWS):
        for c in range(COLS):
            x1 = int(start_cx + c * STEP_X)
            y1 = int(start_cy + r * STEP_Y)
            x2 = int(x1 + CELL_W)
            y2 = int(y1 + CELL_H)
            
            cx = x1 + int(CELL_W / 2)
            cy = y1 + int(CELL_H / 2)
            
            crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            color = handler.classify_slot_color(crop) if crop.size > 0 else "gray_or_empty"
            is_valuable = color not in ["gray_or_empty", "green"]
            
            check_x = cx - 17
            check_y = cy - 25
            check_zone = img[max(0, check_y):min(h, check_y+30), max(0, check_x):min(w, check_x+34)]
            
            has_check = False
            if check_zone.size > 0:
                hsv_check = cv2.cvtColor(check_zone, cv2.COLOR_BGR2HSV)
                mask_green = cv2.inRange(hsv_check, (45, 80, 80), (95, 255, 255))
                has_check = (mask_green > 0).sum() > 10
                
            grid_results.append((r, c, cx, cy, x1, y1, x2, y2, color, is_valuable, has_check))

    color_bgr_map = {
        "purple": (255, 0, 255),
        "blue": (255, 255, 0),
        "green": (0, 255, 0),
        "red": (0, 0, 255),
        "orange_yellow": (0, 165, 255),
        "gray_or_empty": (128, 128, 128)
    }
    
    for r, c, cx, cy, x1, y1, x2, y2, color, is_valuable, has_check in grid_results:
        box_color = color_bgr_map.get(color, (255, 255, 255))
        # 繪製 134 x 139.5 主外框
        cv2.rectangle(out_img, (x1, y1), (x2, y2), box_color, 2)
        # 繪製中心點
        cv2.circle(out_img, (cx, cy), 3, (0, 255, 255), -1)
        
        check_str = "[v]" if has_check else "[X]"
        val_str = "VAL" if is_valuable else "COM"
        label = f"R{r}C{c} {color[:4]} {val_str} {check_str}"
        cv2.putText(out_img, label, (x1 + 4, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
    out_dir = os.path.join(base_dir, "scratch")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "bag_cleaning_calibration_result.png")
    cv2.imwrite(out_path, out_img)
    print(f"[SUCCESS] Calibration image saved: {out_path}")
    print(f"[HINT] Open {out_path} to inspect 134x139.5 grid overlay!")

if __name__ == "__main__":
    main()
