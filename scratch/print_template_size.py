import cv2
import os

for f in os.listdir("templates/common"):
    if f.endswith(".png"):
        img = cv2.imread(os.path.join("templates/common", f))
        if img is not None:
            print(f"Template {f}: shape={img.shape}")
