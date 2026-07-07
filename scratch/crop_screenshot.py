import cv2

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
img = cv2.imread(screenshot_path)
if img is None:
    print("Cannot read screenshot.")
    exit(1)

# Let's save a copy to scratch so we can verify it
cv2.imwrite("scratch/original_user_screenshot.png", img)
print(f"Saved original user screenshot of size {img.shape}")
