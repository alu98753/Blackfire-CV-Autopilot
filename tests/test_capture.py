import os
import sys

# 將專案根目錄加入 Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.screen import ScreenCapturer

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    print("=" * 60)
    print(" 🔍 單體測試: 視窗定位與畫面擷取測試 🔍")
    print("=" * 60)
    
    target_title = "Blackfire Crusade"
    capturer = ScreenCapturer(window_title=target_title)
    
    print(f"[*] 正在尋找視窗: '{target_title}'...")
    rect = capturer.get_window_rect()
    
    if rect:
        print(f"[+] 成功定位視窗: '{rect['title']}'")
        print(f"    座標: ({rect['left']}, {rect['top']})")
        print(f"    大小: {rect['width']}x{rect['height']}")
        
        print("[*] 正在嘗試擷取視窗畫面...")
        img = capturer.capture(rect)
        if img is not None:
            print(f"[+] 畫面擷取成功！影像維度: {img.shape}")
            output_file = "test_captured_window.png"
            import cv2
            cv2.imwrite(output_file, img)
            print(f"[🎉] 測試畫面已成功儲存至: {os.path.abspath(output_file)}")
            print("     請打開此圖確認擷取到的畫面是否完整（無黑畫面或裁剪不全）。")
        else:
            print("[!] 畫面擷取失敗（回傳 None）。")
    else:
        print(f"[-] 未偵測到 '{target_title}' 視窗。")
        print("    [備用測試] 擷取主螢幕畫面...")
        img = capturer.capture(rect=None)
        if img is not None:
            print(f"[+] 主螢幕擷取成功！影像維度: {img.shape}")
            output_file = "test_captured_fullscreen.png"
            import cv2
            cv2.imwrite(output_file, img)
            print(f"[🎉] 測試全螢幕已成功儲存至: {os.path.abspath(output_file)}")
        else:
            print("[!] 全螢幕擷取失敗。")
    print("=" * 60)

if __name__ == "__main__":
    main()
