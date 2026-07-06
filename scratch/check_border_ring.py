import cv2
import os
import numpy as np

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
pos_all = (121, 628)

# Crop Slot 0, 1 (green shield)
cx = pos_all[0] - 23 + 1 * 135
cy = pos_all[1] - 425 + 0 * 135
crop = screen[cy-60:cy+60, cx-60:cx+60]
hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

print("Coordinates of green pixels in the 120x120 crop:")
# Green: H in [35, 85], S > 75, V > 75
green_pts = np.argwhere((hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 75) & (hsv[:, :, 2] > 75))
print(f"Total green pixels: {len(green_pts)}")

# Print y, x of first 20 green pixels
for y, x in green_pts[:20]:
    h, s, v = hsv[y, x]
    print(f"y={y}, x={x}, HSV=({h}, {s}, {v})")

print("\nCoordinates of orange/yellow pixels in the crop:")
# Orange/Yellow: H in [10, 34], S > 75, V > 75
orange_pts = np.argwhere((hsv[:, :, 0] >= 10) & (hsv[:, :, 0] <= 34) & (hsv[:, :, 1] > 75) & (hsv[:, :, 2] > 75))
print(f"Total orange/yellow pixels: {len(orange_pts)}")
for y, x in orange_pts[:20]:
    h, s, v = hsv[y, x]
    print(f"y={y}, x={x}, HSV=({h}, {s}, {v})")
