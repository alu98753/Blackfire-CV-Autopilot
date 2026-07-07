import cv2
import numpy as np

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
screen_img = cv2.imread(screenshot_path)
if screen_img is None:
    print("Cannot read screenshot.")
    exit(1)

template_path = "templates/common/bag.png"
template_img = cv2.imread(template_path)
if template_img is None:
    print("Cannot read template.")
    exit(1)

# Resize template to match the downscaled screenshot scale (900/1920)
scale = 900.0 / 1920.0
temp_w = int(template_img.shape[1] * scale)
temp_h = int(template_img.shape[0] * scale)
template_resized = cv2.resize(template_img, (temp_w, temp_h), interpolation=cv2.INTER_CUBIC)
print(f"Resized template from {template_img.shape[1]}x{template_img.shape[0]} to {temp_w}x{temp_h}")

res = cv2.matchTemplate(screen_img, template_resized, cv2.TM_CCOEFF_NORMED)

loc = np.where(res >= 0.4)
matches = []
for pt in zip(*loc[::-1]):
    conf = res[pt[1], pt[0]]
    matches.append((pt[0], pt[1], conf))

matches = sorted(matches, key=lambda x: x[2], reverse=True)
unique_matches = []
for m in matches:
    x, y, conf = m
    too_close = False
    for um in unique_matches:
        ux, uy, uconf = um
        if abs(ux - x) < 15 and abs(uy - y) < 15:
            too_close = True
            break
    if not too_close:
        unique_matches.append(m)

print("Matches of resized template on downscaled screenshot:")
for i, um in enumerate(unique_matches[:5]):
    x, y, conf = um
    cx = x + temp_w // 2
    cy = y + temp_h // 2
    # Convert center coordinates back to 1920x1080 scale to see where it would click
    cx_1920 = int(cx / scale)
    cy_1920 = int(cy / scale)
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}, center_in_1920=({cx_1920}, {cy_1920})")
