import cv2
import os
import numpy as np

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

# Green and blue combined mask
mask_green = cv2.inRange(hsv, (35, 100, 100), (85, 255, 255))
mask_blue = cv2.inRange(hsv, (90, 100, 100), (130, 255, 255))
mask_combined = cv2.bitwise_or(mask_green, mask_blue)

# Scan along x values for different columns
for col_idx, x_test in enumerate([100, 230, 360, 500]):
    col_pixels = mask_combined[:, x_test]
    print(f"\n--- Column {col_idx} (x={x_test}) ---")
    for y in range(len(col_pixels)):
        if col_pixels[y] > 0:
            print(f"y={y}: {col_pixels[y]}")
