import cv2
import os

images = [
    r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\.tempmediaStorage\media_65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9_1783383173427.png",
    r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\.tempmediaStorage\media_65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9_1783383042996.png"
]

for img_path in images:
    if os.path.exists(img_path):
        img = cv2.imread(img_path)
        if img is not None:
            print(f"File: {os.path.basename(img_path)}, shape={img.shape}")
            # Save a crop of bottom right area
            h, w = img.shape[:2]
            crop = img[int(h*0.6):, int(w*0.5):]
            crop_name = f"scratch/crop_{os.path.basename(img_path)}"
            cv2.imwrite(crop_name, crop)
            print(f" Saved crop to {crop_name}, shape={crop.shape}")
