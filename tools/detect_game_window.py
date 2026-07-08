import sys
import time
import win32gui
import win32api
import win32con

TARGET_TITLE = "Blackfire Crusade"

def get_all_visible_windows():
    """
    獲取系統中所有可見的非空標題視窗列表，便於找不到目標時提供測試參考
    """
    windows = []
    def enum_handler(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                windows.append((hwnd, title))
    win32gui.EnumWindows(enum_handler, None)
    return windows

def monitor_window(target_title):
    print("=" * 60)
    print(f" [DETECT] 跨螢幕動態定位探路工具啟動 (目標視窗: '{target_title}')")
    print("=" * 60)
    print("[*] 請隨意在您的主螢幕與延伸螢幕之間拖曳/移動遊戲視窗...")
    print("[*] 若要結束偵測，請按 Ctrl + C\n")

    last_rect = None
    last_monitor_device = None

    while True:
        hwnd = win32gui.FindWindow(None, target_title)
        
        if not hwnd:
            print(f"[!] 未能找到標題為 '{target_title}' 的視窗。")
            print("[*] 當前系統中可用的活動視窗標題如下（您可以任意選一個進行測試）：")
            visible_windows = get_all_visible_windows()
            # 只顯示前 15 個
            for i, (h, t) in enumerate(visible_windows[:15]):
                try:
                    # 避免標題本身有無法編碼的字元
                    print(f"   {i+1}) [HWND: {h}] {t}")
                except Exception:
                    pass
            print("\n[-] 請開啟遊戲或將 TARGET_TITLE 修改為上方列表中存在的標題，然後重新運行。")
            print("[-] 腳本將在 5 秒後重新嘗試搜尋...")
            time.sleep(5)
            last_rect = None
            last_monitor_device = None
            continue

        try:
            # 1. 獲取視窗在虛擬螢幕中的絕對邊界
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # 2. 獲取視窗所在的 Monitor 顯示器控制代碼
            hmonitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            
            # 3. 獲取該 Monitor 的詳細資訊
            monitor_info = win32api.GetMonitorInfo(hmonitor)
            device_name = monitor_info.get("Device", "未知設備")
            monitor_rect = monitor_info.get("Monitor")
            is_primary = (monitor_info.get("Flags", 0) & win32con.MONITORINFOF_PRIMARY) != 0

            # 4. 如果視窗位置或所在的螢幕發生變更，印出最新狀態
            if rect != last_rect or device_name != last_monitor_device:
                print("-" * 60)
                print(f"[STATUS] 偵測到視窗狀態變更！")
                print(f"   - 視窗絕對座標: Left={rect[0]}, Top={rect[1]}, Right={rect[2]}, Bottom={rect[3]}")
                print(f"   - 視窗尺寸: {width} x {height}")
                print(f"   - 當前座落螢幕: {device_name} ({'主顯示器' if is_primary else '延伸顯示器'})")
                print(f"   - 該顯示器解析度: {monitor_rect[2] - monitor_rect[0]} x {monitor_rect[3] - monitor_rect[1]} (虛擬座標起點: {monitor_rect[0]}, {monitor_rect[1]})")
                
                last_rect = rect
                last_monitor_device = device_name
                
        except Exception as e:
            print(f"[ERROR] 偵測過程中發生錯誤: {e}")
            
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        # 支援從命令列參數傳入自訂視窗標題進行測試
        title = sys.argv[1] if len(sys.argv) > 1 else TARGET_TITLE
        monitor_window(title)
    except KeyboardInterrupt:
        print("\n[*] 探路監測結束。")
        sys.exit(0)
