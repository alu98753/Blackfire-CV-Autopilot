import cv2
import os

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
mask_blue = cv2.inRange(hsv, (90, 100, 100), (130, 255, 255))

x, y, w, h = cv2.boundingRect(mask_blue)
print(f"Blue mask bounding box: x={x}, y={y}, w={w}, h={h}")
