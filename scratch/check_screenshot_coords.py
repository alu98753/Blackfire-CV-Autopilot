import cv2

image_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
img = cv2.imread(image_path)
if img is None:
    print("Cannot read uploaded screenshot!")
    exit(1)

print(f"Uploaded screenshot shape: {img.shape}")

# Let's run template matching of templates/common/bag.png on this uploaded screenshot
template_path = "templates/common/bag.png"
template_img = cv2.imread(template_path)
if template_img is None:
    print("Cannot read template!")
    exit(1)

# Run match
res = cv2.matchTemplate(img, template_img, cv2.TM_CCOEFF_NORMED)

# Let's find the top matches
import numpy as np
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

print("Matches on the uploaded screenshot:")
for i, um in enumerate(unique_matches):
    x, y, conf = um
    cx = x + template_img.shape[1] // 2
    cy = y + template_img.shape[0] // 2
    print(f" {i+1}: pos=({x}, {y}), center=({cx}, {cy}), conf={conf:.4f}")
