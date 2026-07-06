import cv2
import os
import numpy as np

img_path = r"C:\Users\abc\.gemini\antigravity-ide\brain\65c89eb8-9150-4c5a-9b7f-7a238ebcc3c9\media__1783364529138.png"
if not os.path.exists(img_path):
    print("Uploaded image not found.")
    exit(1)

screen = cv2.imread(img_path)
pos_all = (121, 628) # Simulated matching position of select_all.png

# Color classification from BackpackFullSortingHandler
def classify_slot(crop):
    mask = np.zeros(crop.shape[:2], dtype=np.uint8)
    cv2.rectangle(mask, (0, 0), (120, 120), 255, -1)
    cv2.rectangle(mask, (8, 8), (112, 112), 0, -1)
    
    ring_pixels = crop[mask == 255]
    if len(ring_pixels) == 0:
        return "gray_or_empty"
        
    hsv_pixels = cv2.cvtColor(np.expand_dims(ring_pixels, axis=0), cv2.COLOR_BGR2HSV)[0]
    
    counts = {
        "red": 0,
        "orange_yellow": 0,
        "green": 0,
        "blue": 0,
        "purple": 0
    }
    
    for h, s, v in hsv_pixels:
        if s > 75 and v > 75:
            if h <= 9 or h >= 165:
                counts["red"] += 1
            elif 10 <= h <= 34:
                counts["orange_yellow"] += 1
            elif 35 <= h <= 85:
                counts["green"] += 1
            elif 90 <= h <= 130:
                counts["blue"] += 1
            elif 130 < h < 165:
                counts["purple"] += 1
                
    max_color = "gray_or_empty"
    max_count = 25
    for color, count in counts.items():
        if count > max_count:
            max_count = count
            max_color = color
    return max_color

print("Scanning 6x4 slots in the mass disassemble screen:")
for r in range(4):
    for c in range(6):
        cx = pos_all[0] - 23 + c * 135
        cy = pos_all[1] - 425 + r * 135
        
        crop_x = cx - 60
        crop_y = cy - 60
        
        # Ensure we don't go out of bounds
        crop = screen[crop_y:crop_y+120, crop_x:crop_x+120]
        std_val = np.std(crop)
        color = classify_slot(crop)
        print(f"Slot Row {r}, Col {c}: center=({cx}, {cy}), std={std_val:.2f}, color={color}")
