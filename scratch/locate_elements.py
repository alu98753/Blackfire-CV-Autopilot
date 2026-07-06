import cv2
import os
import numpy as np

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
print(f"Screen shape: {screen.shape}")

# Template matching for select_all.png
sel_template_path = "templates/common/select_all.png"
if os.path.exists(sel_template_path):
    sel_temp = cv2.imread(sel_template_path)
    res = cv2.matchTemplate(screen, sel_temp, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"select_all.png: conf={max_val:.4f}, loc={max_loc}, center=({max_loc[0] + sel_temp.shape[1]//2}, {max_loc[1] + sel_temp.shape[0]//2})")

# Template matching for Disassembly.png
dis_template_path = "templates/common/Disassembly.png"
if os.path.exists(dis_template_path):
    dis_temp = cv2.imread(dis_template_path)
    res = cv2.matchTemplate(screen, dis_temp, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"Disassembly.png: conf={max_val:.4f}, loc={max_loc}, center=({max_loc[0] + dis_temp.shape[1]//2}, {max_loc[1] + dis_temp.shape[0]//2})")

# Template matching for close button common/quit.png
quit_template_path = "templates/common/quit.png"
if os.path.exists(quit_template_path):
    quit_temp = cv2.imread(quit_template_path)
    res = cv2.matchTemplate(screen, quit_temp, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    print(f"quit.png: conf={max_val:.4f}, loc={max_loc}, center=({max_loc[0] + quit_temp.shape[1]//2}, {max_loc[1] + quit_temp.shape[0]//2})")
