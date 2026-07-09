"""
DPI 點擊診斷工具 (DPI Click Diagnostic Tool) - 整合版
此工具整合了我們在除錯期間確定的正確多顯示器 DPI 座標模型：
1. 進程設為 Per-Monitor DPI Aware (2) 確保所有 Windows API 回傳物理像素。
2. 後台 PostMessage：傳遞「物理 Client 相對座標」，讓 Windows 自動完成 DPI 虛擬化縮放。
3. 前台滑鼠移動：直接使用 ctypes SetCursorPos 移動至「物理螢幕絕對座標」。
"""
import ctypes
import ctypes.wintypes
try:
    # 宣告進程為 Per-Monitor DPI Aware 確保取得物理坐標
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("[+] 成功宣告 Per-Monitor DPI Aware (2)")
except Exception as e:
    print(f"[-] 宣告 Per-Monitor DPI Aware 失敗: {e}")

import cv2
import numpy as np
import win32gui
import win32api
import win32con
import os
import time
import mss

TITLE = "Blackfire Crusade"

def get_dpi_factor(hwnd):
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        return dpi / 96.0
    except Exception:
        return 1.0

def get_mouse_pos():
    cursor = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor))
    return cursor.x, cursor.y

def match_template(screen_img, template_name):
    possible_paths = [
        os.path.join("templates", template_name),
        os.path.join("..", "templates", template_name)
    ]
    template_path = None
    for p in possible_paths:
        if os.path.exists(p):
            template_path = p
            break
            
    if not template_path:
        return None
        
    tpl = cv2.imread(template_path)
    if tpl is None:
        return None
        
    res = cv2.matchTemplate(screen_img, tpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= 0.7:
        h, w = tpl.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        return (cx, cy), max_val
    return None

def diagnose_dpi():
    hwnd = win32gui.FindWindow(None, TITLE)
    if not hwnd:
        print(f"[-] 找不到遊戲視窗 '{TITLE}'，請先開啟遊戲！")
        return

    # 1. 獲取物理尺寸
    phys_rect = win32gui.GetWindowRect(hwnd)
    pw = phys_rect[2] - phys_rect[0]
    ph = phys_rect[3] - phys_rect[1]
    
    client_rect = win32gui.GetClientRect(hwnd)
    cw = client_rect[2]
    ch = client_rect[3]
    
    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
    border_left = client_origin[0] - phys_rect[0]
    border_top = client_origin[1] - phys_rect[1]
    dpi_factor = get_dpi_factor(hwnd)

    print("\n================== DPI 座標系診斷數據 (DPI Aware) ==================")
    print(f"[*] 視窗所在螢幕 DPI 縮放: {dpi_factor:.2f} ({int(dpi_factor * 100)}%)")
    print(f"[*] 視窗物理外框 Rect: left={phys_rect[0]}, top={phys_rect[1]}, size={pw}x{ph}")
    print(f"[*] 物理 Client 區 Rect: size={cw}x{ch}")
    print(f"[*] 物理邊框偏移: left={border_left}px, top={border_top}px")
    print("==================================================================\n")

    # 2. 擷取畫面
    print("[*] 正在進行畫面擷取...")
    try:
        with mss.MSS() as sct:
            monitor = {"left": phys_rect[0], "top": phys_rect[1], "width": pw, "height": ph}
            screenshot = sct.grab(monitor)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
        print(f"[+] 擷取成功，物理尺寸: {img.shape[1]}x{img.shape[0]}")
    except Exception as e:
        print(f"[-] 畫面擷取失敗: {e}")
        return

    # 3. 匹配可用的圖示
    targets = [
        ("鑽石 (diamond.png)", "diamond.png", 0),
        ("背包文字 (bag_text.png)", "common/bag_text.png", -35), # 調整點擊偏移至背包圖標中心
        ("背包圖示 (bag.png)", "common/bag.png", 0),
        ("傳送門 (door.png)", "common/door.png", 0),
        ("大量分解按鈕 (bag_clean.png)", "common/bag_clean.png", 0)
    ]
    
    match_result = None
    for display_name, file_name, offset_y in targets:
        res = match_template(img, file_name)
        if res:
            match_result = (display_name, res[0], res[1], offset_y)
            break
            
    if not match_result:
        print("[-] 未能在當前畫面上匹配到任何已知圖標（請確保遊戲畫面處於大廳或有匹配圖標的介面）。")
        return
        
    display_name, (mx_win, my_win), conf, offset_y = match_result
    phys_rel_win_x = mx_win
    phys_rel_win_y = my_win + offset_y
    
    # 計算正確的物理 Client 座標 (PostMessage 使用)
    phys_client_x = phys_rel_win_x - border_left
    phys_client_y = phys_rel_win_y - border_top
    
    # 計算物理螢幕絕對座標 (SetCursorPos 使用)
    abs_phys_x = phys_rect[0] + phys_rel_win_x
    abs_phys_y = phys_rect[1] + phys_rel_win_y
    
    print(f"[🎉 匹配成功] 發現目標: {display_name}")
    print(f"    - 信心度: {conf:.4f}")
    print(f"    - 物理相對視窗座標: ({phys_rel_win_x}, {phys_rel_win_y})")
    print(f"    - 物理相對 Client 座標: ({phys_client_x}, {phys_client_y})")
    print(f"    - 物理螢幕絕對座標: ({abs_phys_x}, {abs_phys_y})")

    # 存檔標記圖
    marked = img.copy()
    cv2.circle(marked, (phys_rel_win_x, phys_rel_win_y), 15, (0, 0, 255), 2)
    cv2.drawMarker(marked, (phys_rel_win_x, phys_rel_win_y), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
    cv2.imwrite("debug_dpi_visual.png", marked)
    print("[+] 標記截圖已儲存為 debug_dpi_visual.png，請檢查紅十字標記是否精準對齊目標中心。")

    # 4. 點擊測試方案
    print("\n====================== 點擊診斷測試 ======================")
    print(" 📢 請將遊戲置於可見狀態。")
    print(" 1) [測試 1] 後台 PostMessage (物理 Client 座標) - 【推薦/目前使用方案】")
    print(" 2) [測試 2] 前台 SetCursorPos 實體移動點擊 (無 SW_RESTORE)")
    print(" 3) 退出測試")
    print("==========================================================")
    
    choice = input("請輸入測試項目 (1-3): ").strip()
    if choice == '1':
        print(f"\n📢 3秒後對 HWND {hwnd} 發送 PostMessage 點擊...")
        print(f"   lParam = ({phys_client_x}, {phys_client_y})")
        time.sleep(3)
        
        lp = win32api.MAKELONG(phys_client_x, phys_client_y)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
        
        ans = input("   👉 點擊成功了嗎？ (y/n): ").strip().lower()
        if ans == 'y':
            print("🎉 [測試 1] 後台 PostMessage 成功！驗證此處 DPI 座標映射正確。")
        else:
            print("[-] [測試 1] 失敗。")
            
    elif choice == '2':
        print(f"\n📢 3秒後移動滑鼠並執行點擊...")
        print(f"   螢幕絕對座標: ({abs_phys_x}, {abs_phys_y})")
        time.sleep(3)
        
        old_x, old_y = get_mouse_pos()
        
        # 僅激活，不還原大小 (避免最大化視窗發生還原移動)
        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
        except:
            pass
            
        # 移動並執行物理點擊
        ctypes.windll.user32.SetCursorPos(abs_phys_x, abs_phys_y)
        time.sleep(0.1)
        
        # 執行雙擊
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.1)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        
        time.sleep(0.5)
        ctypes.windll.user32.SetCursorPos(old_x, old_y)
        
        ans = input("   👉 點擊成功了嗎？ (y/n): ").strip().lower()
        if ans == 'y':
            print("🎉 [測試 2] 前台 SetCursorPos 實體移動點擊成功！")
        else:
            print("[-] [測試 2] 失敗。")
            
    else:
        print("[*] 退出診斷。")

if __name__ == "__main__":
    diagnose_dpi()
