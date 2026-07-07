import cv2
import numpy as np

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783383012082.jpg"
img = cv2.imread(screenshot_path)
if img is None:
    print("Cannot read screenshot.")
    exit(1)

# In the 1024x547 user screenshot:
# True backpack button is at center=(823, 500)
# Wrong warband button is at center=(744, 516)

# Let's crop a 40x40 region around both centers
backpack_crop = img[500-20:500+20, 823-20:823+20]
warband_crop = img[516-20:516+20, 744-20:744+20]

# Calculate average color in BGR
bp_mean = np.mean(backpack_crop, axis=(0,1))
wb_mean = np.mean(warband_crop, axis=(0,1))

print(f"Backpack (物品欄) average BGR: {bp_mean}")
print(f"Warband (戰團) average BGR: {wb_mean}")

# Let's convert to HSV to check saturation and hue
bp_hsv = cv2.cvtColor(backpack_crop, cv2.COLOR_BGR2HSV)
wb_hsv = cv2.cvtColor(warband_crop, cv2.COLOR_BGR2HSV)

bp_hsv_mean = np.mean(bp_hsv, axis=(0,1))
wb_hsv_mean = np.mean(wb_hsv, axis=(0,1))

print(f"Backpack (物品欄) average HSV: {bp_hsv_mean}")
print(f"Warband (戰團) average HSV: {wb_hsv_mean}")
