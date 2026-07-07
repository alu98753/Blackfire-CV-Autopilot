import sys
import os
import cv2
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from capture.screen import ScreenCapturer
from vision.matcher import TemplateMatcher

capturer = ScreenCapturer(window_title="Blackfire Crusade")
matcher = TemplateMatcher(templates_dir="templates")

rect = capturer.get_window_rect()
if rect is None:
    print("Cannot find game window.")
    exit(1)

screen = capturer.capture(rect)
if screen is None:
    print("Cannot capture screen.")
    exit(1)

cv2.imwrite("scratch/current_lobby_screen.png", screen)
print(f"Captured screen of size: {screen.shape}")

templates_to_test = [
    "common/bag.png",
    "common/Backpack_Disassembly.png",
    "common/select_all.png",
    "common/Disassembly.png",
    "common/confirm.png",
    "common/ok.png",
    "common/tidy.png",
    "common/quit.png"
]

for t in templates_to_test:
    if os.path.exists(os.path.join("templates", t)):
        pos, conf = matcher.match(screen, t, threshold=0.5)
        if pos:
            print(f"Template {t}: matched at {pos} with conf={conf:.4f}, center=({pos[0]+rect['left']}, {pos[1]+rect['top']})")
        else:
            print(f"Template {t}: not matched (conf < 0.5)")
    else:
        print(f"Template {t}: file does not exist")
