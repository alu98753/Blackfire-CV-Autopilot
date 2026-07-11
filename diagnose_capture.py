import os
import sys
import time
import logging
import win32gui
import win32api
import win32con
import win32ui
import ctypes
import numpy as np
import cv2
import mss

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_window_info(title):
    hwnd = win32gui.FindWindow(None, title)
    if not hwnd:
        return None
    rect = win32gui.GetWindowRect(hwnd)
    client_rect = win32gui.GetClientRect(hwnd)
    return {
        "hwnd": hwnd,
        "rect": rect,
        "client_rect": client_rect,
        "width": rect[2] - rect[0],
        "height": rect[3] - rect[1]
    }

def capture_method_gdi_bitblt(hwnd, w, h):
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)
        
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        # Clean up
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        return img_bgr
    except Exception as e:
        logging.error(f"GDI BitBlt failed: {e}")
        return None

def capture_method_printwindow(hwnd, w, h, flag):
    try:
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        
        res = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), flag)
        if res:
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr = None
            
        # Clean up
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        return img_bgr
    except Exception as e:
        logging.error(f"PrintWindow (flag={flag}) failed: {e}")
        return None

def capture_method_mss(rect):
    try:
        sct = mss.mss()
        monitor = {
            "left": rect[0],
            "top": rect[1],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1]
        }
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img_bgr
    except Exception as e:
        logging.error(f"MSS Capture failed: {e}")
        return None

def analyze_black_shadow(img):
    if img is None:
        return 1.0, 1.0
    
    # 轉為灰階
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    total_pixels = gray.size
    black_pixels = np.sum(gray == 0)
    total_ratio = black_pixels / total_pixels
    
    # 分析底部 30% 區間的黑色比例
    h, w = gray.shape
    bottom_start_y = int(h * 0.70)
    bottom_part = gray[bottom_start_y:h, :]
    bottom_total = bottom_part.size
    bottom_black = np.sum(bottom_part == 0)
    bottom_ratio = bottom_black / bottom_total
    
    return total_ratio, bottom_ratio

def main():
    target_title = "Blackfire Crusade"
    logging.info(f"開始診斷視窗 '{target_title}' 截圖與黑影問題...")
    
    info = get_window_info(target_title)
    if not info:
        logging.error(f"找不到視窗 '{target_title}'，請確認遊戲已啟動且並未最小化。")
        sys.exit(1)
        
    hwnd = info["hwnd"]
    rect = info["rect"]
    w, h = info["width"], info["height"]
    
    logging.info("=" * 60)
    logging.info(f"視窗控制代碼 (HWND): {hwnd}")
    logging.info(f"視窗座標 (RECT): Left={rect[0]}, Top={rect[1]}, Right={rect[2]}, Bottom={rect[3]}")
    logging.info(f"視窗尺寸: {w}x{h}")
    
    # 取得系統多螢幕資訊
    v_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    v_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    v_w = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    v_h = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    logging.info(f"虛擬桌面總範圍: Left={v_left}, Top={v_top}, Width={v_w}, Height={v_h}")
    logging.info("=" * 60)
    
    # 測試方法 A: GDI BitBlt
    logging.info("📸 嘗試方法 A: GDI BitBlt...")
    img_gdi = capture_method_gdi_bitblt(hwnd, w, h)
    if img_gdi is not None:
        cv2.imwrite("debug_capture_gdi_dc.png", img_gdi)
        tot, bot = analyze_black_shadow(img_gdi)
        logging.info(f"   - [成功] 檔案儲存至 debug_capture_gdi_dc.png")
        logging.info(f"   - 全域黑色比例: {tot*100:.1f}%, 底部30%黑色比例: {bot*100:.1f}%")
    else:
        logging.warning("   - [失敗]")
        
    # 測試方法 B: PrintWindow (一般)
    logging.info("📸 嘗試方法 B: PrintWindow (預設Flag=0)...")
    img_pw = capture_method_printwindow(hwnd, w, h, 0)
    if img_pw is not None:
        cv2.imwrite("debug_capture_printwindow_normal.png", img_pw)
        tot, bot = analyze_black_shadow(img_pw)
        logging.info(f"   - [成功] 檔案儲存至 debug_capture_printwindow_normal.png")
        logging.info(f"   - 全域黑色比例: {tot*100:.1f}%, 底部30%黑色比例: {bot*100:.1f}%")
    else:
        logging.warning("   - [失敗]")
        
    # 測試方法 C: PrintWindow (RENDERFULLCONTENT=2)
    logging.info("📸 嘗試方法 C: PrintWindow (Flag=2 - RENDERFULLCONTENT)...")
    img_pw2 = capture_method_printwindow(hwnd, w, h, 2)
    if img_pw2 is not None:
        cv2.imwrite("debug_capture_printwindow_renderfull.png", img_pw2)
        tot, bot = analyze_black_shadow(img_pw2)
        logging.info(f"   - [成功] 檔案儲存至 debug_capture_printwindow_renderfull.png")
        logging.info(f"   - 全域黑色比例: {tot*100:.1f}%, 底部30%黑色比例: {bot*100:.1f}%")
    else:
        logging.warning("   - [失敗]")
        
    # 測試方法 D: MSS Desktop Capture
    logging.info("📸 嘗試方法 D: MSS 桌面前台裁剪...")
    img_mss = capture_method_mss(rect)
    if img_mss is not None:
        cv2.imwrite("debug_capture_mss.png", img_mss)
        tot, bot = analyze_black_shadow(img_mss)
        logging.info(f"   - [成功] 檔案儲存至 debug_capture_mss.png")
        logging.info(f"   - 全域黑色比例: {tot*100:.1f}%, 底部30%黑色比例: {bot*100:.1f}%")
    else:
        logging.warning("   - [失敗]")
        
    logging.info("=" * 60)
    logging.info("診斷完畢，請打開產出的截圖檔案，檢查是否有哪張截圖中沒有黑影擋住遊戲！")
    logging.info("特別關注『底部 30% 黑色比例』最接近 0% 的截圖！")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
