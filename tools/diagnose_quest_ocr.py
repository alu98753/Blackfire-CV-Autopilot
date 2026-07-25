import os
import sys
import glob
import cv2
import logging
import numpy as np

# 確保專案根目錄納入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.matcher import TemplateMatcher
from utils.quest_ocr_extractor import QuestOCRExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def diagnose_quest_ocr():
    """
    懸賞告示牌 OCR 視覺化診斷小程式：
    1. 讀取 templates/town_building/bulletin_board/Daily_task/ 所有人真實截圖。
    2. 使用 TemplateMatcher 比對 task.png 圖示錨點。
    3. 對右側標題區域畫出綠色框框 (ROI)，對 task.png 錨點畫出紅色框框。
    4. 調用 EasyOCR 進行中文標題辨識，並將辨識結果文字標示在圖片上。
    5. 儲存為 debug_quest_ocr_<檔名>.png 可視化圖片。
    """
    matcher = TemplateMatcher()
    sample_dir = os.path.join("templates", "town_building", "bulletin_board", "Daily_task")
    sample_files = glob.glob(os.path.join(sample_dir, "*.png"))

    if not sample_files:
        print(f"[!] 找不到樣品圖片: {sample_dir}")
        return

    print("============================================================")
    print("  懸賞告示牌 OCR 辨識與視覺化框框診斷小程式 ")
    print("============================================================")

    # 初始化 EasyOCR
    reader = None
    try:
        import easyocr
        print("[*] 正在載入 EasyOCR模型 (繁體中文 + 英文)...")
        reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
        print("[+] EasyOCR 載入成功！\n")
    except Exception as e:
        print(f"[!] EasyOCR 載入失敗/未安裝: {e}，將僅進行區域框框標記。")

    for sample_path in sample_files:
        base_name = os.path.basename(sample_path)
        img = cv2.imread(sample_path)
        if img is None:
            continue

        debug_img = img.copy()
        h_img, w_img = img.shape[:2]

        # 1. 尋找 task.png 錨點 (限定左半邊 cx < w_img // 2，避開右半邊描述區域)
        anchors = matcher.match_all(img, "town_building/bulletin_board/task.png", threshold=0.70, quiet=True)
        anchors = [a for a in anchors if a[0] < w_img // 2]
        
        if not anchors:
            print(f"[*] 圖片 {base_name}: 未發現未接受任務 (task.png)")
            continue

        # 核心邏輯：永遠鎖定最上方 (Y 座標最小) 的未接受任務 top_anchor
        top_anchor = sorted(anchors, key=lambda a: a[1])[0]

        # 取得模板實際大小 (考慮 match_all 多尺度)
        temp_img = matcher._load_template("town_building/bulletin_board/task.png")
        temp_h, temp_w = temp_img.shape[:2] if temp_img is not None else (40, 40)
        scale = 0.863
        icon_w = int(temp_w * scale)
        icon_h = int(temp_h * scale)

        print(f"------------------------------------------------------------")
        print(f"[*] 診斷圖片: {base_name} ({w_img}x{h_img}) | 發現 {len(anchors)} 個未接受 task.png 錨點")
        print(f"[★ 最上方鎖定標的 (top_anchor)] X={top_anchor[0]}, Y={top_anchor[1]}")
        print(f"------------------------------------------------------------")

        recognized_titles = []

        for idx, (cx, cy, conf) in enumerate(sorted(anchors, key=lambda a: a[1])):
            is_top_target = (cx == top_anchor[0] and cy == top_anchor[1])
            x0 = cx - icon_w // 2
            y0 = cy - icon_h // 2

            # 若為最上方鎖定標的，畫厚黃框 (255, 255, 0)；其餘畫紅框
            box_color = (255, 255, 0) if is_top_target else (0, 0, 255)
            thickness = 4 if is_top_target else 2
            cv2.rectangle(debug_img, (x0, y0), (x0 + icon_w, y0 + icon_h), box_color, thickness)

            # 計算右側文字 ROI
            crop_x = x0 + icon_w + 5
            crop_y = max(0, y0 - 5)
            crop_w = min(360, w_img - crop_x)
            crop_h = min(icon_h + 10, h_img - crop_y)

            if crop_w <= 0 or crop_h <= 0:
                continue

            # 畫出文字辨識 ROI 範圍 (最上方目標以厚青框標示，其餘綠框)
            roi_color = (255, 255, 0) if is_top_target else (0, 255, 0)
            cv2.rectangle(debug_img, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), roi_color, thickness)

            # 裁切並執行 OCR
            text_roi = img[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            ocr_text = ""
            ocr_conf = 0.0

            if reader is not None:
                try:
                    res = reader.readtext(text_roi)
                    if res:
                        texts = [r[1].strip() for r in res if r[1].strip()]
                        ocr_text = "".join(texts)
                        ocr_conf = res[0][2] if len(res[0]) > 2 else 1.0
                except Exception as ex:
                    ocr_text = f"Err: {ex}"

            prefix = "[★ 1st 鎖定標的]" if is_top_target else f"   [列 #{idx+1}]"
            if ocr_text:
                recognized_titles.append(ocr_text)
                print(f"{prefix} 座標 (X={cx}, Y={cy}) | 錨點信心度: {conf:.4f} -> 辨識字串: '{ocr_text}' (OCR信心度: {ocr_conf:.2f})")
            else:
                print(f"{prefix} 座標 (X={cx}, Y={cy}) | 錨點信心度: {conf:.4f} -> 未辨識出文字")

        # 保存診斷調試圖片
        out_filename = f"debug_quest_ocr_{os.path.splitext(base_name)[0]}.png"
        cv2.imwrite(out_filename, debug_img)
        print(f"[+] 可視化標籤框框圖已儲存至: {out_filename}")
        print(f"    串接結果字串: \"{', '.join(recognized_titles)}\"\n")

if __name__ == "__main__":
    diagnose_quest_ocr()
