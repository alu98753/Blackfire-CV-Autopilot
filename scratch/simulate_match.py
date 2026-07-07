import cv2
import numpy as np

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
screen_img = cv2.imread(screenshot_path)
if screen_img is None:
    print("Cannot read screenshot.")
    exit(1)

# Force resize to exactly 1920x1080
h, w = screen_img.shape[:2]
target_w = 1920
target_h = 1080
print(f"Resized screenshot from {w}x{h} to {target_w}x{target_h}")
resized_screen = cv2.resize(screen_img, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

template_path = "templates/common/bag.png"
template_img = cv2.imread(template_path)
if template_img is None:
    print("Cannot read template.")
    exit(1)

res = cv2.matchTemplate(resized_screen, template_img, cv2.TM_CCOEFF_NORMED)

# Let's print all match confidences >= 0.5 near x = 1402 and x = 1550
loc = np.where(res >= 0.5)
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
        if abs(ux - x) < 30 and abs(uy - y) < 30:
            too_close = True
            break
    if not too_close:
        unique_matches.append(m)

print("Matches on upscaled screen:")
for i, um in enumerate(unique_matches):
    x, y, conf = um
    cx = x + template_img.shape[1] // 2
    cy = y + template_img.shape[0] // 2
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}")
