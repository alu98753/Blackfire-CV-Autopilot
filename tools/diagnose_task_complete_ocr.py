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
from utils.quest_scheduler import QuestScheduler
from utils.quest_mapper import TaskNode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_task_complete_ocr():
    print("=" * 60)
    print(" 🛠️ 任務完成彈窗 (task_complete.png) 局部 OCR 與邏輯診斷工具 🛠️")
    print("=" * 60)

    matcher = TemplateMatcher(templates_dir="templates")
    
    # 測試素材來源：1) task_complete.png 模板本身 2) Daily_task 目錄下的真實截圖
    test_files = [
        "templates/task_complete.png",
     ]

    # 模擬建立 QuestScheduler 與任務佇列
    scheduler = QuestScheduler()
    scheduler.add_task(TaskNode("史萊姆王的毀滅", "dungeon", target_count=1, dungeon_index=0))
    scheduler.add_task(TaskNode("清除骷髏", "stage", target_count=10, stage_level=1, sub_stage="first"))
    scheduler.add_task(TaskNode("清除野豬", "stage", target_count=10, stage_level=1, sub_stage="final"))
    scheduler.add_task(TaskNode("擊敗冰元素", "stage", target_count=10, stage_level=6, sub_stage="first"))
    scheduler.add_task(TaskNode("敵人剿滅", "generic_boss", target_count=10, raw_desc="保護這片土地 盡可能剿滅更多的敵人"))


    extractor = QuestOCRExtractor(matcher=matcher)

    for file_path in test_files:
        if not os.path.exists(file_path):
            continue

        img = cv2.imread(file_path)
        if img is None:
            continue

        h_img, w_img = img.shape[:2]
        print(f"\n📸 [測試圖片] {file_path} ({w_img}x{h_img})")

        pos_task, conf = matcher.match(img, "task_complete.png", threshold=0.60, quiet=True)
        if pos_task:
            cx, cy = pos_task
            print(f"  👉 成功定位 task_complete.png 中心座標: ({cx}, {cy}) (信心度: {conf:.4f})")
        else:
            # 若直接對模板圖檔進行測試，以圖檔中心作為 (cx, cy)
            cx, cy = w_img // 2, h_img // 2
            print(f"  ℹ️ 未匹配到 task_complete.png 錨點，使用圖片中心點: ({cx}, {cy})")

        # 執行 Scoped Crop 裁切
        y1 = max(0, cy - 140)
        y2 = min(h_img, cy + 60)
        x1 = max(0, cx - 250)
        x2 = min(w_img, cx + 250)

        crop_roi = img[y1:y2, x1:x2]

        # 繪製可視化 Debug 圖標標出辨識區域
        debug_img = img.copy()
        cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.circle(debug_img, (cx, cy), 8, (0, 0, 255), -1)
        
        save_name = f"debug_ocr_{os.path.basename(file_path)}"
        cv2.imwrite(save_name, debug_img)
        cv2.imwrite(f"crop_roi_{os.path.basename(file_path)}", crop_roi)

        print(f"  📌 裁切 ROI 範圍: X=[{x1}:{x2}], Y=[{y1}:{y2}] (尺寸: {crop_roi.shape[1]}x{crop_roi.shape[0]})")
        print(f"  📸 可視化 Debug 裁切圖已寫入: {save_name} 與 crop_roi_{os.path.basename(file_path)}")

        # 進行 OCR 辨識
        ocr_text = extractor._ocr_crop(crop_roi)
        print(f"  🔤 EasyOCR 辨識出的文字: '{ocr_text}'")

        # 驗證 record_task_complete() 邏輯
        if ocr_text:
            matched = scheduler.record_task_complete(ocr_text)
            print(f"  🎯 record_task_complete('{ocr_text}') 匹配結果: {'✅ 成功匹配標記完成' if matched else '⚠️ 無匹配任務'}")
        else:
            print("  ⚠️ EasyOCR 未識別出有效標題字串。")

    print("\n" + "=" * 60)
    scheduler.print_task_summary()

if __name__ == "__main__":
    test_task_complete_ocr()
