import ctypes
import ctypes.wintypes

def get_active_windows():
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    
    windows = []
    
    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                # 取得視窗大小與位置
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                windows.append((hwnd, title, width, height))
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return windows

if __name__ == "__main__":
    import sys
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
            
    print("=" * 60)
    print(" 正在搜尋所有活動中的 Windows 視窗標題...")
    print("=" * 60)
    
    all_windows = get_active_windows()
    # 依標題字母排序
    all_windows.sort(key=lambda x: x[1].lower())
    
    found_target = False
    for hwnd, title, w, h in all_windows:
        # 特別標出使用者感興趣的遊戲標題
        is_target = "blackfire" in title.lower()
        marker = " 🎯 [TARGET] " if is_target else "  "
        print(f"{marker}HWND: {hwnd:<10} | Size: {w}x{h:<6} | Title: {title}")
        if is_target:
            found_target = True
            
    print("=" * 60)
    if found_target:
        print(" 找到符合 'Blackfire' 的視窗！")
    else:
        print(" 提示：未在目前的活動視窗中偵測到 'Blackfire'。請確認遊戲已啟動並非最小化狀態。")
    print("=" * 60)
