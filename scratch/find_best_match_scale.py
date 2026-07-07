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

h_orig, w_orig = screen_img.shape[:2]

best_conf = 0
best_scale = 0
best_pos = (0, 0)
best_resized_screen = None

# Let's search over a range of widths (maintaining aspect ratio)
for w in range(800, 2000, 20):
    h = int(h_orig * (w / w_orig))
    resized = cv2.resize(screen_img, (w, h), interpolation=cv2.INTER_CUBIC)
    
    if template_img.shape[0] > h or template_img.shape[1] > w:
        continue
        
    res = cv2.matchTemplate(resized, template_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val > best_conf:
        best_conf = max_val
        best_scale = w
        best_pos = max_loc
        best_resized_screen = resized

print(f"Best match: scale width={best_scale}, pos={best_pos}, confidence={best_conf:.4f}")

# At the best scale, let's find all local maxima to see "戰團" vs "物品欄" matches!
h_best = int(h_orig * (best_scale / w_orig))
res = cv2.matchTemplate(best_resized_screen, template_img, cv2.TM_CCOEFF_NORMED)
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
        if abs(ux - x) < 30 and abs(uy - y) < 30:
            too_close = True
            break
    if not too_close:
        unique_matches.append(m)

print(f"Matches at best scale width={best_scale}:")
for i, um in enumerate(unique_matches[:5]):
    x, y, conf = um
    cx = x + template_img.shape[1] // 2
    cy = y + template_img.shape[0] // 2
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}")
