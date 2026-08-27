"""Windows 視窗控制代碼的共用存取介面。"""

import win32gui


class WindowHandle:
    """依視窗標題取得並快取有效的 Windows HWND。"""

    def __init__(self, window_title: str):
        self.window_title = window_title
        self._hwnd = None

    def get(self):
        """回傳有效 HWND；快取失效時依標題重新查找。"""
        if not self._hwnd or not win32gui.IsWindow(self._hwnd):
            self._hwnd = win32gui.FindWindow(None, self.window_title)
        return self._hwnd
