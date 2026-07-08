import cv2
import numpy as np
import os
import argparse
import sys

def analyze_brightness(screen_path, template_path, output_dir="."):
    """
    分析給定截圖中與模板匹配區域的灰階平均亮度，計算相似度與亮度比例。
    """
    if not os.path.exists(screen_path):
        print(f"錯誤：找不到截圖檔案 '{screen_path}'")
        return False
    if not os.path.exists(template_path):
        print(f"錯誤：找不到模板檔案 '{template_path}'")
        return False

    # 1. 讀取彩色圖片
    screen_img = cv2.imread(screen_path)
    template_img = cv2.imread(template_path)

    if screen_img is None or template_img is None:
        print("錯誤：無法成功解析圖片檔案。")
        return False

    screen_h, screen_w = screen_img.shape[:2]
    temp_h, temp_w = template_img.shape[:2]

    if temp_h > screen_h or temp_w > screen_w:
        print("錯誤：模板尺寸大於截圖尺寸。")
        return False

    # 2. 執行模板匹配
    res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    top_left = max_loc
    center_x = top_left[0] + temp_w // 2
    center_y = top_left[1] + temp_h // 2

    # 3. 截取匹配區域切片
    crop = screen_img[top_left[1]:top_left[1]+temp_h, top_left[0]:top_left[0]+temp_w]

    # 4. 計算灰階平均亮度
    temp_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    mean_temp = np.mean(temp_gray)
    mean_crop = np.mean(crop_gray)
    brightness_ratio = mean_crop / max(1.0, mean_temp)

    print("=" * 60)
    print(f"📊 圖像亮度分析診斷報告 ({os.path.basename(template_path)})")
    print("=" * 60)
    print(f"[*] 匹配相似度 (Confidence): {max_val:.4f}")
    print(f"[*] 匹配中心座標 (Center):   ({center_x}, {center_y})")
    print(f"[*] 原始模板平均亮度:        {mean_temp:.2f}")
    print(f"[*] 匹配切片平均亮度:        {mean_crop:.2f}")
    print(f"[*] 實質亮度比例 (Ratio):    {brightness_ratio:.4f} (匹配區 / 模板)")
    print("-" * 60)
    
    if brightness_ratio < 0.8:
        print("⚠️ 判定結果：亮度比例低於 0.8，屬於「被調暗的背景暗區」！")
    else:
        print("💚 判定結果：亮度比例達標 (>= 0.8)，屬於「前景高亮區域」！")
    print("=" * 60)

    # 5. 繪製紅框定位並保存結果圖片
    marked_screen = screen_img.copy()
    cv2.rectangle(marked_screen, top_left, (top_left[0] + temp_w, top_left[1] + temp_h), (0, 0, 255), 3)
    cv2.putText(marked_screen, f"Conf: {max_val:.2f}, Ratio: {brightness_ratio:.2f}", 
                (top_left[0], max_loc[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    full_out = os.path.join(output_dir, "debug_analyze_full.png")
    crop_out = os.path.join(output_dir, "debug_analyze_crop.png")

    cv2.imwrite(full_out, marked_screen)
    cv2.imwrite(crop_out, crop)

    print(f"[+] 標記定位全螢幕圖已保存至: {full_out}")
    print(f"[+] 匹配區域切片圖已保存至:   {crop_out}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blackfire Crusade 圖像匹配亮度分析診斷工具")
    parser.add_argument("-s", "--screen", type=str, default="debug_click.png",
                        help="輸入的遊戲截圖檔案路徑 (預設為當前根目錄的 debug_click.png)")
    parser.add_argument("-t", "--template", type=str, default="templates/common/continue.png",
                        help="待分析的模板圖片路徑 (預設為 templates/common/continue.png)")
    
    args = parser.parse_args()
    
    # 執行分析
    success = analyze_brightness(args.screen, args.template)
    if not success:
        sys.exit(1)
