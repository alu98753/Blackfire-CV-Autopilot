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

# Save screen for inspection
cv2.imwrite("scratch/lobby_test.png", screen)

# Let's read the template common/bag.png
template_path = "templates/common/bag.png"
template_img = cv2.imread(template_path)
if template_img is None:
    print(f"Cannot read template: {template_path}")
    exit(1)

# Run match
res = cv2.matchTemplate(screen, template_img, cv2.TM_CCOEFF_NORMED)
# Find top matches
threshold = 0.5
loc = np.where(res >= threshold)
matches = []
for pt in zip(*loc[::-1]):
    conf = res[pt[1], pt[0]]
    matches.append((pt[0], pt[1], conf))

# Sort by confidence descending
matches = sorted(matches, key=lambda x: x[2], reverse=True)

# Group nearby matches to avoid duplicates
unique_matches = []
for m in matches:
    x, y, conf = m
    # Check if nearby exists
    too_close = False
    for um in unique_matches:
        ux, uy, uconf = um
        if abs(ux - x) < 30 and abs(uy - y) < 30:
            too_close = True
            break
    if not too_close:
        unique_matches.append(m)

print(f"Top matches for common/bag.png (threshold={threshold}):")
for i, um in enumerate(unique_matches[:5]):
    x, y, conf = um
    cx = x + template_img.shape[1] // 2
    cy = y + template_img.shape[0] // 2
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}")
