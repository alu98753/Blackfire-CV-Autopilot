import cv2
import os

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)

mask_blue = cv2.inRange(hsv, (90, 100, 100), (130, 255, 255))
mask_green = cv2.inRange(hsv, (35, 100, 100), (85, 255, 255))

for color_name, mask in [("Blue", mask_blue), ("Green", mask_green)]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"\n=== {color_name} Contours ===")
    for idx, c in enumerate(contours):
        area = cv2.contourArea(c)
        if area > 10:
            x, y, w, h = cv2.boundingRect(c)
            print(f"Contour {idx}: x={x}, y={y}, w={w}, h={h}, area={area}")
