import cv2

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
img = cv2.imread(screenshot_path)
if img is None:
    print("Cannot read screenshot.")
    exit(1)

h, w = img.shape[:2]
# Crop bottom-right region where the icons should be (e.g. bottom 25% of height, right 50% of width)
crop = img[int(h*0.75):, int(w*0.5):]
cv2.imwrite("scratch/user_icons_crop.png", crop)
print(f"Cropped bottom-right of user screenshot to scratch/user_icons_crop.png, shape={crop.shape}")
