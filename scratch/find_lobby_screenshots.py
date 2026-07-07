import cv2
import os

path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9"
png_files = []
for root, dirs, files in os.walk(path):
    for f in files:
        if f.endswith(".png") and not f.startswith("l_") and not f.startswith("r_"):
            png_files.append(os.path.join(root, f))

print(f"Found {len(png_files)} PNG files.")
for pf in png_files:
    img = cv2.imread(pf)
    if img is not None:
        print(f" - {os.path.basename(pf)}: shape={img.shape}")
