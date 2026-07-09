"""
🎒 背包已滿分選 - 網格座標微調與校準工具
--------------------------------------------------
使用說明：
1. 您可以直接修改下方【微調參數區】的數值。
2. 在終端機執行：
   .\.venv\Scripts\python tools\calibrate_grid.py
3. 打開 e:\\Side_Project\\BlackfireCrusade_tool\\scratch\\grid_calibration_result.png
   觀察綠框（左側）、藍框（右側）以及紅點是否完美對齊您的格子。
4. 反覆調整數值直到滿意，再把這組數字填回 logic 代碼即可！
"""

# ==================================================
# 🎯 【微調參數區】您可以在這裡自由修改數值並執行測試！
# ==================================================
# 1. 左側溢出區的網格起點 (相對於標題中心點的設計偏移)
LEFT_DX = -589
LEFT_DY = 105

# 2. 右側背包區的網格起點 (相對於標題中心點的設計偏移)
RIGHT_DX = 34
RIGHT_DY = LEFT_DY

# 3. 格子大小 (寬度/高度) 與行/列間距
CELL_W = 134
CELL_H = 139.5
STEP_X = CELL_W
STEP_Y = CELL_H

# 4. 指定用於校準的輸入截圖檔名
INPUT_IMAGE = "feature_destroyandget_3.png"
# ==================================================

import os
import sys
# 自動將專案根目錄加入路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from vision.matcher import TemplateMatcher

def main():
    img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), INPUT_IMAGE)
    if not os.path.exists(img_path):
        print(f"❌ 錯誤：找不到輸入圖像 '{img_path}'，請確認該檔案存在於專案根目錄！")
        return
        
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    print(f"🖼️ 讀取圖像成功！解析度：{w}x{h}")
    
    # 尋找彈窗標題中心點
    matcher = TemplateMatcher(templates_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"))
    pos_full, conf = matcher.match(img, "backpack_full.png", threshold=0.5)
    
    if not pos_full:
        print("❌ 錯誤：無法在截圖中識別出 'backpack_full.png' 標題，請確認截圖是否正確！")
        return
        
    print(f"🎯 偵測到標題中心：{pos_full} (匹配信心度: {conf:.4f})")
    
    scale_x = w / 1920.0
    scale_y = h / 1080.0
    print(f"📊 縮放比例計算：scale_x={scale_x:.4f}, scale_y={scale_y:.4f}")
    
    # 繪製輸出影像
    out_img = img.copy()
    cw = int(CELL_W * scale_x)
    ch = int(CELL_H * scale_y)
    
    # 1. 繪製左側 4x4 網格 (綠框)
    for r in range(4):
        for c in range(4):
            lcx = int(pos_full[0] + (LEFT_DX + c * STEP_X) * scale_x)
            lcy = int(pos_full[1] + (LEFT_DY + r * STEP_Y) * scale_y)
            cv2.rectangle(out_img, (lcx, lcy), (lcx+cw, lcy+ch), (0, 0, 255), 2)
            # 在中心畫一個小黃點表示點擊中心
            ccx = lcx + cw // 2
            ccy = lcy + ch // 2
            cv2.circle(out_img, (ccx, ccy), 4, (0, 255, 255), -1)
            
    # 2. 繪製右側 4x4 網格 (藍框)
    for r in range(4):
        for c in range(4):
            rcx = int(pos_full[0] + (RIGHT_DX + c * STEP_X) * scale_x)
            rcy = int(pos_full[1] + (RIGHT_DY + r * STEP_Y) * scale_y)
            cv2.rectangle(out_img, (rcx, rcy), (rcx+cw, rcy+ch), (0, 0, 255), 2)
            # 在中心畫一個小黃點表示點擊中心
            ccx = rcx + cw // 2
            ccy = rcy + ch // 2
            cv2.circle(out_img, (ccx, ccy), 4, (0, 255, 255), -1)
            
    # 3. 繪製右上角防禦性關閉按鈕中心 (紅點)
    close_x = int(pos_full[0] + 598 * scale_x)
    close_y = int(pos_full[1] - 41 * scale_y)
    cv2.circle(out_img, (close_x, close_y), 8, (0, 0, 255), -1)
    cv2.putText(out_img, "Close Button", (close_x - 100, close_y - 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # 確保 scratch 目錄存在
    scratch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
    os.makedirs(scratch_dir, exist_ok=True)
    
    out_path = os.path.join(scratch_dir, "grid_calibration_result.png")
    cv2.imwrite(out_path, out_img)
    
    print("\n==================================================")
    print(f"🎉 繪製完成！請查看校準輸出影像：")
    print(f"👉 {out_path}")
    print("==================================================")

if __name__ == "__main__":
    main()
