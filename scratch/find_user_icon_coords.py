import cv2
import numpy as np

screenshot_path = "scratch/original_user_screenshot.png"
screen_img = cv2.imread(screenshot_path)
if screen_img is None:
    print("Cannot read screenshot.")
    exit(1)

# Let's search for templates of other lobby buttons to see where they match, e.g., tidy.png or Disassembly.png
# Wait, let's search for common/bag.png at multiple scales from 0.1 to 1.5, and see all match locations with conf >= 0.5.
# This will show us BOTH the false positive (戰團) and the true positive (物品欄) coordinates!
template_path = "templates/common/bag.png"
template_img = cv2.imread(template_path)
if template_img is None:
    print("Cannot read template.")
    exit(1)

h_orig, w_orig = screen_img.shape[:2]
print(f"User screenshot size: {w_orig}x{h_orig}")

# Let's find matches at various scales
all_matches = []
for s in np.linspace(0.3, 1.2, 91):
    w = int(template_img.shape[1] * s)
    h = int(template_img.shape[0] * s)
    if w <= 0 or h <= 0 or w > w_orig or h > h_orig:
        continue
    temp_res = cv2.resize(template_img, (w, h), interpolation=cv2.INTER_CUBIC)
    res = cv2.matchTemplate(screen_img, temp_res, cv2.TM_CCOEFF_NORMED)
    
    loc = np.where(res >= 0.50)
    for pt in zip(*loc[::-1]):
        conf = res[pt[1], pt[0]]
        all_matches.append((pt[0], pt[1], w, h, s, conf))

# Sort by confidence descending
all_matches = sorted(all_matches, key=lambda x: x[5], reverse=True)

# Deduplicate
unique = []
for m in all_matches:
    x, y, w, h, s, conf = m
    cx = x + w // 2
    cy = y + h // 2
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

print("Top 10 scale-space matches of bag.png on user screenshot:")
for i, m in enumerate(unique[:10]):
    x, y, w, h, s, conf = m
    cx = x + w // 2
    cy = y + h // 2
    rel_x = cx / w_orig
    print(f" {i+1}: scale={s:.4f}, center=({cx}, {cy}), rel_x={rel_x:.4f}, conf={conf:.4f}")
