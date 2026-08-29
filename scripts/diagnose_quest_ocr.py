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
    懸賞告示牌 OCR 辨識與方案一 match_mutually_exclusive_tabs 狀態切換對比測試：
    1. 測試圖片包含 Daily_task/ 以及 tools/TASK_AFTER_TEST.png。
    2. 比對畫面左半邊的未接受 task.png 與已接受 task_after.png 錨點。
    3. 對每一列調用 matcher.match_mutually_exclusive_tabs(row_roi, "task.png", "task_after.png") 進行互斥比較。
    4. 輸出 status: [未接受 task.png] vs [已接受 task_after.png] 及信心度。
    5. 保存繪有紅色(未接受)/紫色(已接受)/黃色(最上方標的)框框的可視化 debug 圖片。
    """
    matcher = TemplateMatcher()
    sample_files = []
    
    # 1. 加入 Daily_task 樣品圖片
    sample_dir = os.path.join("templates", "town_building", "bulletin_board", "Daily_task")
    if os.path.exists(sample_dir):
        sample_files.extend(glob.glob(os.path.join(sample_dir, "*.png")))
    
    # 2. 也嘗試在 templates 找自訂樣品
    tpl_test_path = os.path.join("templates", "TASK_AFTER_TEST.png")
    if os.path.exists(tpl_test_path):
        sample_files.append(tpl_test_path)

    if not sample_files:
        print("[!] 找不到樣品圖片: Daily_task 樣品目錄")
        return

    print("============================================================")
    print("  懸賞告示牌方案一 (match_mutually_exclusive_tabs) 互斥對比測試 ")
    print("============================================================")

    # 初始化 EasyOCR
    reader = None
    try:
        import easyocr
        print("[*] 正在載入 EasyOCR模型 (繁體中文 + 英文)...")
        reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
        print("[+] EasyOCR 載入成功！\n")
    except Exception as e:
        print(f"[!] EasyOCR 載入失敗/未安裝: {e}，將僅進行區域框框與狀態標記。")

    for sample_path in sample_files:
        base_name = os.path.basename(sample_path)
        img = cv2.imread(sample_path)
        if img is None:
            continue

        debug_img = img.copy()
        h_img, w_img = img.shape[:2]

        # 1. 尋找畫面左半邊所有未接受 (task.png) 與 已接受 (task_after.png) 錨點
        anchors_unaccepted = matcher.match_all(img, "town_building/bulletin_board/task.png", threshold=0.60, quiet=True)
        anchors_accepted = matcher.match_all(img, "town_building/bulletin_board/task_after.png", threshold=0.60, quiet=True)

        anchors_unaccepted = [a for a in anchors_unaccepted if a[0] < w_img // 2]
        anchors_accepted = [a for a in anchors_accepted if a[0] < w_img // 2]

        # 彙整所有左半邊圖示錨點
        all_anchors = []
        for x, y, c in anchors_unaccepted:
            all_anchors.append((x, y, c, "task.png"))
        for x, y, c in anchors_accepted:
            # 避免與 unaccepted 重疊
            if not any(abs(x - ax) < 30 and abs(y - ay) < 30 for ax, ay, _, _ in all_anchors):
                all_anchors.append((x, y, c, "task_after.png"))

        if not all_anchors:
            print(f"[*] 圖片 {base_name}: 未在左半邊發現任何 task.png / task_after.png 錨點。")
            continue

        # 按 Y 座標排序 (自上而下)
        all_anchors = sorted(all_anchors, key=lambda a: a[1])

        # 找出未接受任務中最上方的一個 (top_anchor)
        unaccepted_only = [a for a in all_anchors if a[3] == "task.png"]
        top_anchor = unaccepted_only[0] if unaccepted_only else None

        # 模板預設尺寸
        temp_img = matcher._load_template("town_building/bulletin_board/task.png")
        temp_h, temp_w = temp_img.shape[:2] if temp_img is not None else (40, 40)
        scale = 0.863 if w_img > 800 else 1.0
        icon_w = int(temp_w * scale)
        icon_h = int(temp_h * scale)

        print(f"------------------------------------------------------------")
        print(f"[*] 診斷圖片: {base_name} ({w_img}x{h_img}) | 總任務列: {len(all_anchors)} 行 (未接受: {len(unaccepted_only)} | 已接受: {len(all_anchors)-len(unaccepted_only)})")
        if top_anchor:
            print(f"[★ 最上方待接受鎖定標的 (top_anchor)] X={top_anchor[0]}, Y={top_anchor[1]}")
        print(f"------------------------------------------------------------")

        recognized_titles = []

        for idx, (cx, cy, conf, initial_type) in enumerate(all_anchors):
            is_top_target = (top_anchor and cx == top_anchor[0] and cy == top_anchor[1])
            x0 = cx - icon_w // 2
            y0 = cy - icon_h // 2

            # 裁切該圖示區域進行【方案一：match_mutually_exclusive_tabs】公用互斥比對
            crop_icon_x0 = max(0, x0 - 5)
            crop_icon_y0 = max(0, y0 - 5)
            crop_icon_w = min(icon_w + 10, w_img - crop_icon_x0)
            crop_icon_h = min(icon_h + 10, h_img - crop_icon_y0)
            icon_roi = img[crop_icon_y0:crop_icon_y0+crop_icon_h, crop_icon_x0:crop_icon_x0+crop_icon_w]

            # 調用公用互斥對比函式 match_mutually_exclusive_tabs
            is_a_unaccepted, is_b_accepted, conf_a, conf_b = matcher.match_mutually_exclusive_tabs(
                icon_roi,
                "town_building/bulletin_board/task.png",
                "town_building/bulletin_board/task_after.png",
                threshold=0.50
            )

            # 確定當前狀態與框框顏色
            if is_top_target:
                status_str = "[★ 未接受 (最優先標的)]"
                box_color = (255, 255, 0)  # 黃色/青色
                thickness = 4
            elif conf_a >= conf_b:
                status_str = "[未接受 task.png]"
                box_color = (0, 0, 255)    # 紅色
                thickness = 2
            else:
                status_str = "[已接受 task_after.png]"
                box_color = (255, 0, 255)  # 紫色/洋紅
                thickness = 2

            # 畫出圖示框框
            cv2.rectangle(debug_img, (x0, y0), (x0 + icon_w, y0 + icon_h), box_color, thickness)

            # 計算右側文字 ROI 範圍並執行 EasyOCR
            crop_x = x0 + icon_w + 5
            crop_y = max(0, y0 - 5)
            crop_w = min(360, w_img - crop_x)
            crop_h = min(icon_h + 10, h_img - crop_y)

            if crop_w > 0 and crop_h > 0:
                cv2.rectangle(debug_img, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), box_color, thickness)
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
                    except Exception:
                        pass

                prefix = f"   [列 #{idx+1}]"
                print(f"{prefix} 座標 (X={cx}, Y={cy}) | 互斥對比: task={conf_a:.2f} vs task_after={conf_b:.2f} -> 判定: {status_str} | 標題: '{ocr_text}'")

        # 儲存診斷圖片
        out_filename = f"debug_quest_ocr_{os.path.splitext(base_name)[0]}.png"
        cv2.imwrite(out_filename, debug_img)
        print(f"[+] 方案一對比視覺化圖檔已儲存至: {out_filename}\n")

if __name__ == "__main__":
    diagnose_quest_ocr()
