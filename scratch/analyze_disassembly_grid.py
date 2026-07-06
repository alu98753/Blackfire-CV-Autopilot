import cv2
import os
import numpy as np

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

# Let's find green border pixels or blue border pixels
# Green color in HSV: Hue around 35-85, Saturation > 100, Value > 100
mask_green = cv2.inRange(hsv, (35, 100, 100), (85, 255, 255))
# Blue color in HSV: Hue around 90-130, Saturation > 100, Value > 100
mask_blue = cv2.inRange(hsv, (90, 100, 100), (130, 255, 255))

mask_combined = cv2.bitwise_or(mask_green, mask_blue)

# Find contours of border pixels
contours, _ = cv2.findContours(mask_combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

print(f"Found {len(contours)} border contours.")
for idx, c in enumerate(contours):
    x, y, w, h = cv2.boundingRect(c)
    if w > 30 and h > 30:
        print(f"Contour {idx}: x={x}, y={y}, w={w}, h={h}, center=({x+w//2}, {y+h//2})")

# Let's also print vertical/horizontal lines or grid structure if possible
# Or let's scan across row 0 (around y=200) to see where the cells are
y_test = 200
row_pixels = mask_combined[y_test, :]
print(f"Combined mask values at y={y_test}:")
for x in range(len(row_pixels)):
    if row_pixels[x] > 0:
        print(f"x={x}: {row_pixels[x]}")
