import cv2
import numpy as np

screenshot_path = "scratch/original_user_screenshot.png"
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

# Let's search over scale factors of the template
best_matches_all_scales = []

for s in np.linspace(0.2, 1.2, 101):
    w = int(template_img.shape[1] * s)
    h = int(template_img.shape[0] * s)
    if w <= 0 or h <= 0 or w > w_orig or h > h_orig:
        continue
    temp_res = cv2.resize(template_img, (w, h), interpolation=cv2.INTER_CUBIC)
    res = cv2.matchTemplate(screen_img, temp_res, cv2.TM_CCOEFF_NORMED)
    
    # Get all matches >= 0.4
    loc = np.where(res >= 0.4)
    for pt in zip(*loc[::-1]):
        conf = res[pt[1], pt[0]]
        matches_all_scales = (pt[0], pt[1], w, h, s, conf)
        best_matches_all_scales.append(matches_all_scales)

# Sort by confidence descending
best_matches_all_scales = sorted(best_matches_all_scales, key=lambda x: x[5], reverse=True)

# Deduplicate matches
unique = []
for m in best_matches_all_scales:
    x, y, w, h, s, conf = m
    cx = x + w // 2
    cy = y + h // 2
    # Check if a nearby center is already in unique
    too_close = False
    for u in unique:
        ux, uy, uw, uh, us, uconf = u
        ucx = ux + uw // 2
        ucy = uy + uh // 2
        if abs(ucx - cx) < 20 and abs(ucy - cy) < 20:
            too_close = True
            break
    if not too_close:
        unique.append(m)

print("Top 10 scale-space matches on user screenshot:")
for i, m in enumerate(unique[:10]):
    x, y, w, h, s, conf = m
    cx = x + w // 2
    cy = y + h // 2
    print(f" {i+1}: scale={s:.4f}, pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}, size={w}x{h}")
