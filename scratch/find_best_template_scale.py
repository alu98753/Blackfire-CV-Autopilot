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

best_conf = 0
best_scale = 0
best_pos = (0, 0)

# Let's search over template scale factors from 0.1 to 1.5
for s in np.linspace(0.1, 1.5, 140):
    w = int(template_img.shape[1] * s)
    h = int(template_img.shape[0] * s)
    if w <= 0 or h <= 0 or w > screen_img.shape[1] or h > screen_img.shape[0]:
        continue
    temp_res = cv2.resize(template_img, (w, h), interpolation=cv2.INTER_CUBIC)
    res = cv2.matchTemplate(screen_img, temp_res, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val > best_conf:
        best_conf = max_val
        best_scale = s
        best_pos = max_loc

print(f"Best Match: scale={best_scale:.4f}, confidence={best_conf:.4f}, pos={best_pos}")

# Print matches at the best scale
w = int(template_img.shape[1] * best_scale)
h = int(template_img.shape[0] * best_scale)
temp_res = cv2.resize(template_img, (w, h), interpolation=cv2.INTER_CUBIC)
res = cv2.matchTemplate(screen_img, temp_res, cv2.TM_CCOEFF_NORMED)
loc = np.where(res >= 0.6)
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

print(f"Top 5 matches at scale {best_scale:.4f}:")
for i, um in enumerate(unique_matches[:5]):
    x, y, conf = um
    cx = x + w // 2
    cy = y + h // 2
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}")
