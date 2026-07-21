import ctypes
try:
    # 宣告進程為 Per-Monitor DPI Aware 確保取得物理坐標，避免 OpenCV 視窗在高 DPI 縮放下無法拖曳且卡死
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import cv2
import os
import sys
import time
from capture.screen import ScreenCapturer

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    print("=" * 60)
    print(" 🎮 Blackfire Crusade 模板裁剪工具 🎮")
    print("=" * 60)
    
    # 預期 templates 資料夾存在
    os.makedirs("templates", exist_ok=True)
    
    # 初始化畫面擷取器
    target_title = "Blackfire Crusade"
    capturer = ScreenCapturer(window_title=target_title)
    
    print(f"[*] 正在尋找視窗: '{target_title}'...")
    rect = capturer.get_window_rect()
    
    if rect is None:
        print(f"[!] 找不到 '{target_title}' 視窗！")
        print("請確認遊戲已啟動，且視窗名稱無誤。您可以執行 list_windows.py 來列出所有視窗標題。")
        sys.exit(1)
        
    print(f"[+] 成功定位視窗: '{rect['title']}'")
    print(f"    位置: ({rect['left']}, {rect['top']}) | 大小: {rect['width']}x{rect['height']}")
    
    print("\n[*] 提示：請切換到遊戲視窗，並把畫面停留在包含您要裁剪按鈕的畫面。")
    print("    系統將在 5 秒後自動截圖...")
    for i in range(5, 0, -1):
        print(f"⏳ {i} 秒...")
        time.sleep(1)
    
    print("[*] 正在擷取畫面...")
    img = capturer.capture(rect)
    
    if img is None:
        print("[!] 擷取畫面失敗！")
        sys.exit(1)
        
    print("\n[+] 擷取成功！即將打開裁切視窗。")
    print("=" * 60)
    print(" 💡 裁切操作說明：")
    print(" 1. 用滑鼠左鍵「拖曳」拉出一個矩形，選取想要辨識的按鈕（如：開始戰鬥、再次挑戰）。")
    print("    建議裁剪範圍只包含『按鈕文字』及少許邊界，避免包含過多動態發光或背景。")
    print(" 2. 選好後按 [Enter] 或 [空白鍵] 確認選取。")
    print(" 3. 如果想重新選取，直接重新拖曳即可。")
    print(" 4. 按 [ESC] 鍵可取消並退出。")
    print("=" * 60)
    
    # 建立視窗並設定為普通大小
    window_name = "Crop Tool - Drag to Select ROI, Press Enter/Space to confirm, ESC to cancel"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # 使用 OpenCV 的 ROI 選擇器
    r = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
    
    # 關閉所有視窗並清空事件佇列，防範視窗殘留卡死
    cv2.destroyAllWindows()
    for _ in range(5):
        cv2.waitKey(1)
    
    x, y, w, h = r
    if w > 0 and h > 0:
        cropped_img = img[int(y):int(y+h), int(x):int(x+w)]
        
        print(f"\n[+] 選取區域座標: X={x}, Y={y}, Width={w}, Height={h}")
        filename = input("請輸入欲儲存的模板檔名 (例如: start.png 或 retry.png): ").strip()
        if not filename:
            filename = "temp_cropped.png"
        elif not filename.endswith(".png"):
            filename += ".png"
            
        save_path = os.path.join("templates", filename)
        cv2.imwrite(save_path, cropped_img)
        print(f"[🎉] 模板已成功儲存至: {save_path}")
        print("您可以在接下來的腳本中直接使用此檔案。")
    else:
        print("\n[-] 您取消了選取。")

if __name__ == "__main__":
    main()
