import os
import sys
import cv2
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from vision.matcher import TemplateMatcher
from utils.quest_ocr_extractor import QuestOCRExtractor
from config import BULLETIN_BOARD_OCR_OFFSET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def diagnose_bulletin_board():
    print("=" * 60)
    print(" 🛠️ 懸賞告示牌清單 (bulletin_board) 局部 OCR 與方框調校工具 🛠️")
    print("=" * 60)

    matcher = TemplateMatcher(templates_dir="templates")
    extractor = QuestOCRExtractor(matcher=matcher)

    sample_dir = "templates/town_building/bulletin_board/Daily_task"
    if not os.path.exists(sample_dir):
        print(f"⚠️ 找不到測試資料夾: {sample_dir}")
        return

    sample_files = [os.path.join(sample_dir, f) for f in os.listdir(sample_dir) if f.endswith(".png")]

    print(f"⚙️ [當前 config.py 裁切參數] offset_x={BULLETIN_BOARD_OCR_OFFSET.get('offset_x', 5)}, offset_y={BULLETIN_BOARD_OCR_OFFSET.get('offset_y', -5)}, width={BULLETIN_BOARD_OCR_OFFSET.get('box_width', 360)}, height={BULLETIN_BOARD_OCR_OFFSET.get('box_height', 40)}")

    for sample_file in sample_files:
        img = cv2.imread(sample_file)
        if img is None:
            continue

        h_img, w_img = img.shape[:2]
        base_name = os.path.basename(sample_file)
        print(f"\n📸 [測試圖檔] {base_name} ({w_img}x{h_img})")

        # 匹配 task.png 錨點
        anchors = matcher.match_all(img, "town_building/bulletin_board/task.png", threshold=0.60, quiet=True)
        if not anchors:
            print("  ⚠️ 未辨識到任何 task.png 錨點。")
            continue

        # 專精優化：過濾只保留螢幕左半邊 (cx < w_img // 2) 的 task.png 錨點
        anchors = [a for a in anchors if a[0] < w_img // 2]
        if not anchors:
            print("  ⚠️ 左半邊未辨識到任何 task.png 錨點。")
            continue

        # 按 Y 座標排序
        anchors = sorted(anchors, key=lambda a: a[1])

        debug_img = img.copy()

        temp_img = matcher._load_template("town_building/bulletin_board/task.png")
        temp_h, temp_w = (temp_img.shape[0], temp_img.shape[1]) if temp_img is not None else (40, 40)
        scale = w_img / 1940.0 if w_img < 1500 else 1.0
        icon_w = max(20, int(temp_w * scale))
        icon_h = max(20, int(temp_h * scale))

        off_x = BULLETIN_BOARD_OCR_OFFSET.get("offset_x", 5)
        off_y = BULLETIN_BOARD_OCR_OFFSET.get("offset_y", -5)
        box_w = BULLETIN_BOARD_OCR_OFFSET.get("box_width", 360)
        box_h = BULLETIN_BOARD_OCR_OFFSET.get("box_height", 40)

        for idx, (cx, cy, conf) in enumerate(anchors, 1):
            x0 = cx - icon_w // 2
            y0 = cy - icon_h // 2

            crop_x = max(0, x0 + icon_w + int(off_x * scale))
            crop_y = max(0, y0 + int(off_y * scale))
            crop_w = min(max(20, int(box_w * scale)), w_img - crop_x)
            crop_h = min(max(10, int(box_h * scale)), h_img - crop_y)

            cv2.rectangle(debug_img, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (0, 255, 0), 2)
            cv2.circle(debug_img, (cx, cy), 5, (0, 0, 255), -1)

            text_roi = img[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            title = extractor._ocr_crop(text_roi, crop_top_half=True)
            print(f"  📌 任務列 #{idx} (X={crop_x}, Y={crop_y}, W={crop_w}, H={crop_h}) ➔ OCR 辨識結果: '{title}'")

        save_path = f"debug_bulletin_{base_name}"
        cv2.imwrite(save_path, debug_img)
        print(f"  📸 可視化 Debug 方框圖已寫入: {save_path}")

    print("\n" + "=" * 60)
    print("💡 提示：若發現框框偏高或偏低，請直接打開 config.py 調整 BULLETIN_BOARD_OCR_OFFSET 參數，再重新執行本腳本確認！")
    print("=" * 60)

if __name__ == "__main__":
    diagnose_bulletin_board()
