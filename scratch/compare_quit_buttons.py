import cv2
import os
import numpy as np

img1_path = "templates/common/quit_bread.png"
img2_path = "templates/dungeons/quit.png"

if not os.path.exists(img1_path) or not os.path.exists(img2_path):
    print("One of the templates does not exist.")
    exit(1)

img1 = cv2.imread(img1_path)
img2 = cv2.imread(img2_path)

print(f"quit_bread.png shape: {img1.shape}")
print(f"quit.png shape: {img2.shape}")

# Match img2 (quit.png) inside img1 (quit_bread.png)
res = cv2.matchTemplate(img1, img2, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
print(f"Matching quit.png inside quit_bread.png - max confidence: {max_val:.4f}")

# Match img1 (quit_bread.png) inside img2 (quit.png)
# Since img1 is larger, we can't do it unless we resize, but let's see.
