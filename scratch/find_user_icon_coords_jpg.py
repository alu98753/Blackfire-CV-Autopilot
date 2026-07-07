import cv2
import numpy as np

screenshot_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783383012082.jpg"
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
print(f"User screenshot size: {w_orig}x{h_orig}")

# Let's search over scale factors s from 0.1 to 1.5
all_matches = []
for s in np.linspace(0.1, 1.5, 141):
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
        if abs(ucx - cx) < 25 and abs(ucy - cy) < 25:
            too_close = True
            break
    if not too_close:
        unique.append(m)

print("Top 10 scale-space matches of bag.png on actual user lobby screenshot:")
for i, m in enumerate(unique[:10]):
    x, y, w, h, s, conf = m
    cx = x + w // 2
    cy = y + h // 2
    rel_x = cx / w_orig
    print(f" {i+1}: scale={s:.4f}, center=({cx}, {cy}), rel_x={rel_x:.4f}, conf={conf:.4f}, size={w}x{h}")
