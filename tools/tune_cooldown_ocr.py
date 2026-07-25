import os
import sys
import argparse
import cv2
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.time_parser import parse_time_to_seconds, format_seconds_to_readable

def main():
    parser = argparse.ArgumentParser(description="冷卻木牌綠框與 EasyOCR 互動微調工具")
    parser.add_argument("--image", type=str, default="debug_cooldown_match.png", help="要除錯微調的原始圖片路徑")
    parser.add_argument("--offset-x", type=int, default=0, help="X 軸中心點額外偏移量 (像素)")
    parser.add_argument("--offset-y", type=int, default=0, help="Y 軸中心點額外偏移量 (像素)")
    parser.add_argument("--crop-w", type=int, default=170, help="裁剪區域寬度 (像素)")
    parser.add_argument("--crop-h", type=int, default=30, help="裁剪區域高度 (像素)")
    parser.add_argument("--threshold", type=float, default=0.70, help="木牌模板匹配門檻 (0.50 ~ 0.95)")
    parser.add_argument("--interactive", action="store_true", help="開啟 OpenCV Trackbar 視窗進行即時視覺拖曳")

    args = parser.parse_args()

    img_path = args.image
    if not os.path.exists(img_path):
        print(f"❌ 找不到目標圖片: {img_path}")
        print("💡 請先執行 python main.py --backend --subflow lord_boss 生成截圖，或使用 --image <圖片路徑>")
        return

    screen_img = cv2.imread(img_path)
    if screen_img is None:
        print(f"❌ 無法讀取圖片: {img_path}")
        return

    print("============================================================")
    print(" 🛠️  Blackfire Crusade 冷卻木牌 OCR 區域手動微調工具 🛠️")
    print("============================================================")
    print(f"[*] 輸入圖片: {img_path} ({screen_img.shape[1]}x{screen_img.shape[0]})")
    print(f"[*] 當前參數: Offset X={args.offset_x}, Offset Y={args.offset_y}, Width={args.crop_w}, Height={args.crop_h}, Threshold={args.threshold:.2f}")
    print("============================================================")

    def process_and_preview(offset_x, offset_y, crop_w, crop_h, threshold_val, run_ocr=True):
        img_copy = screen_img.copy()
        
        # 嘗試在圖中尋找木牌模板
        has_match = False
        matched_temp = None
        best_loc = None
        best_val = 0.0
        template_w, template_h = 0, 0

        for cd_temp in ["dungeons/cooldown_left.png", "dungeons/cooldown_right.png", "load/cooldown_sign.png"]:
            temp_path = os.path.join("templates", cd_temp)
            if os.path.exists(temp_path):
                t_img = cv2.imread(temp_path)
                if t_img is not None:
                    res = cv2.matchTemplate(img_copy, t_img, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, loc = cv2.minMaxLoc(res)
                    if max_val >= threshold_val and max_val > best_val:
                        best_val = max_val
                        best_loc = loc
                        has_match = True
                        matched_temp = cd_temp
                        template_w = t_img.shape[1]
                        template_h = t_img.shape[0]

        # 若未匹配到，預設以圖片中心點為錨點，讓使用者依然能自由移動滑桿
        if has_match:
            cx = best_loc[0] + template_w // 2 + offset_x
            cy = best_loc[1] + template_h // 2 + offset_y
            status_text = f"Matched: {matched_temp} ({best_val:.2f})"
        else:
            cx = img_copy.shape[1] // 2 + offset_x
            cy = img_copy.shape[0] // 2 + offset_y
            status_text = f"Manual Anchor (No Match < {threshold_val:.2f}, max={best_val:.2f})"

        half_w = crop_w // 2
        half_h = crop_h // 2

        tx1 = max(0, cx - half_w)
        tx2 = min(img_copy.shape[1], cx + half_w)
        ty1 = max(0, cy - half_h)
        ty2 = min(img_copy.shape[0], cy + half_h)

        # 繪製除錯圖形：紅點 (中心點), 綠框 (裁切框)
        cv2.circle(img_copy, (cx, cy), 5, (0, 0, 255), -1)
        cv2.rectangle(img_copy, (tx1, ty1), (tx2, ty2), (0, 255, 0), 2)

        cv2.putText(img_copy, status_text, (max(10, tx1), max(20, ty1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imwrite("debug_tune_preview.png", img_copy)
        print(f"📸 預覽圖已寫入 debug_tune_preview.png | {status_text} | 中心: ({cx},{cy}) | 綠框: X[{tx1}:{tx2}], Y[{ty1}:{ty2}]")

        time_crop = screen_img[ty1:ty2, tx1:tx2]
        if time_crop.size > 0:
            time_gray = cv2.cvtColor(time_crop, cv2.COLOR_BGR2GRAY)
            padded = cv2.copyMakeBorder(time_gray, 15, 15, 30, 30, cv2.BORDER_CONSTANT, value=159)
            resized_text = cv2.resize(padded, (0, 0), fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            cv2.imwrite("debug_tune_ocr.png", resized_text)
            print("📸 放大 OCR 切片已寫入 debug_tune_ocr.png")

            if run_ocr:
                try:
                    import easyocr
                    print("⚙️ 正在進行 EasyOCR 識別測試...")
                    reader = easyocr.Reader(['en'], gpu=False)
                    ocr_results = reader.readtext(resized_text, allowlist="0123456789:")
                    print("------------------------------------------------------------")
                    if ocr_results:
                        for idx, item in enumerate(ocr_results):
                            raw_text = item[1]
                            conf = item[2]
                            parsed_secs = parse_time_to_seconds(raw_text)
                            readable = format_seconds_to_readable(parsed_secs) if parsed_secs else "無法解析時間"
                            print(f"  [{idx+1}] OCR 識別結果: \"{raw_text}\" (信心度: {conf:.4f}) ➔ 解析秒數: {parsed_secs} ({readable})")
                    else:
                        print("  ❌ 未辨識出任何符合 [0-9:] 的文字資訊！")
                    print("------------------------------------------------------------")
                except Exception as err:
                    print(f"⚠️ OCR 測試過程發生例外: {err}")

    process_and_preview(args.offset_x, args.offset_y, args.crop_w, args.crop_h, args.threshold)

    if args.interactive:
        print("\n🎛️ 開啟 GUI Trackbar 微調模式 (按 Enter 執行 OCR，按 ESC 退出)...")
        win_name = "Cooldown OCR Tuner"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, 800, 600)

        cv2.createTrackbar("Offset X (+150)", win_name, args.offset_x + 150, 300, lambda x: None)
        cv2.createTrackbar("Offset Y (+100)", win_name, args.offset_y + 100, 200, lambda x: None)
        cv2.createTrackbar("Crop Width", win_name, args.crop_w, 300, lambda x: None)
        cv2.createTrackbar("Crop Height", win_name, args.crop_h, 100, lambda x: None)
        cv2.createTrackbar("Threshold (x100)", win_name, int(args.threshold * 100), 95, lambda x: None)

        while True:
            cur_ox = cv2.getTrackbarPos("Offset X (+150)", win_name) - 150
            cur_oy = cv2.getTrackbarPos("Offset Y (+100)", win_name) - 100
            cur_cw = max(10, cv2.getTrackbarPos("Crop Width", win_name))
            cur_ch = max(10, cv2.getTrackbarPos("Crop Height", win_name))
            cur_th = max(50, cv2.getTrackbarPos("Threshold (x100)", win_name)) / 100.0

            process_and_preview(cur_ox, cur_oy, cur_cw, cur_ch, cur_th, run_ocr=False)

            preview_img = cv2.imread("debug_tune_preview.png")
            if preview_img is not None:
                cv2.imshow(win_name, preview_img)

            key = cv2.waitKey(100) & 0xFF
            if key == 13:  # Enter 鍵執行 OCR
                print("\n⌨️ 觸發 EasyOCR 辨識測試...")
                process_and_preview(cur_ox, cur_oy, cur_cw, cur_ch, cur_th, run_ocr=True)
            elif key == 27:  # ESC 鍵退出
                break

        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
