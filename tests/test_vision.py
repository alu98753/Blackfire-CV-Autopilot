import os
import sys
import numpy as np
import cv2

# 將專案根目錄加入 Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.matcher import TemplateMatcher

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    print("=" * 60)
    print(" 🔍 單體測試: 模板匹配（Template Matching）測試 🔍")
    print("=" * 60)
    
    # 建立一個測試用的虛擬畫面 (600x800, 3通道)
    # 背景為深藍色
    test_screen = np.zeros((600, 800, 3), dtype=np.uint8)
    test_screen[:] = (50, 20, 20)  # BGR
    
    # 在 (400, 300) 的位置繪製一個橘黃色按鈕
    btn_color = (0, 165, 255) # Orange in BGR
    # 按鈕左上角 (350, 280)，右下角 (450, 320)，中心點應為 (400, 300)
    cv2.rectangle(test_screen, (350, 280), (450, 320), btn_color, -1)
    # 在按鈕內寫入文字 'START'
    cv2.putText(test_screen, "START", (370, 305), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    # 建立一個與該按鈕相同的模板
    test_template = np.zeros((40, 100, 3), dtype=np.uint8)
    test_template[:] = btn_color
    cv2.putText(test_template, "START", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    # 將測試模板存至專案目錄
    os.makedirs("templates", exist_ok=True)
    temp_path = "templates/test_start_btn_mock.png"
    cv2.imwrite(temp_path, test_template)
    print(f"[+] 建立了模擬的模板檔案: {temp_path}")
    
    # 執行匹配
    matcher = TemplateMatcher()
    
    print("[*] 正在進行模板匹配測試...")
    pos, conf = matcher.match(test_screen, "test_start_btn_mock.png", threshold=0.8)
    
    # 清理模擬檔案
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    print("=" * 60)
    if pos:
        print(f"[🎉] 匹配測試成功！")
        print(f"     找到目標中心座標: {pos} (預期應為 (400, 300) 左右)")
        print(f"     信心度 (Confidence Score): {conf:.4f}")
        
        # 驗證座標是否正確
        err_x = abs(pos[0] - 400)
        err_y = abs(pos[1] - 300)
        if err_x <= 5 and err_y <= 5:
            print("[+] 精度檢查通過！座標誤差在容許範圍內。")
        else:
            print(f"[!] 警告: 座標誤差較大 (X誤差={err_x}, Y誤差={err_y})。")
    else:
        print(f"[-] 匹配測試失敗。未能在畫面中辨識出目標。最高信心度僅為: {conf:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
