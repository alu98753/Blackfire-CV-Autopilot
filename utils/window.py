"""Windows 視窗控制代碼的共用存取介面與多實例列舉選單。"""

import ctypes
from ctypes import wintypes
import logging
from typing import Optional, List, Dict, Any, Tuple
import win32gui
import win32process

from config import WINDOW_TITLE

DESKTOP_READOBJECTS = 0x0001
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class WindowHandle:
    """依視窗標題或指定 HWND 取得並快取有效的 Windows HWND。"""

    def __init__(self, window_title: Optional[str] = None, hwnd: Optional[int] = None):
        self.window_title = window_title or WINDOW_TITLE
        self._hwnd = hwnd if (hwnd and win32gui.IsWindow(hwnd)) else None

    def get(self) -> Optional[int]:
        """回傳有效 HWND；快取失效時依標題重新查找。"""
        if not self._hwnd or not win32gui.IsWindow(self._hwnd):
            self._hwnd = win32gui.FindWindow(None, self.window_title)
        return self._hwnd


def find_all_game_windows(keyword: str = WINDOW_TITLE) -> List[Dict[str, Any]]:
    """
    掃描系統桌面，找出所有標題包含特定關鍵字的遊戲視窗資訊。
    支援識別 Sandboxie-Plus 沙盒實例。
    """
    user32 = ctypes.windll.user32
    h_desk = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    windows: List[Dict[str, Any]] = []

    def enum_cb(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if keyword in title and "Antigravity" not in title and "CLI" not in title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                rect = win32gui.GetClientRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
                windows.append({
                    "hwnd": hwnd,
                    "pid": pid,
                    "title": title,
                    "width": w,
                    "height": h,
                    "is_sandbox": "[#]" in title
                })
        return True

    cb_func = WNDENUMPROC(enum_cb)
    if h_desk:
        user32.EnumDesktopWindows(h_desk, cb_func, 0)
    else:
        user32.EnumWindows(cb_func, 0)

    # 排序：本機實例優先，接著按 PID
    windows.sort(key=lambda x: (x["is_sandbox"], x["pid"]))
    return windows


def select_game_window(target: Optional[str] = None, auto_prompt: bool = True) -> Tuple[Optional[int], str]:
    """
    依據傳入的 target 參數或提示使用者互動選擇目標遊戲視窗。
    回傳: (hwnd, title)
    """
    windows = find_all_game_windows()

    if not windows:
        return None, WINDOW_TITLE

    if len(windows) == 1 and not target:
        w = windows[0]
        return w["hwnd"], w["title"]

    # 處理 target 參數指定
    if target:
        target_lower = target.strip().lower()
        if target_lower in ["sandbox", "sandboxed", "box", "sb"]:
            for w in windows:
                if w["is_sandbox"]:
                    return w["hwnd"], w["title"]
        elif target_lower in ["native", "host", "main"]:
            for w in windows:
                if not w["is_sandbox"]:
                    return w["hwnd"], w["title"]
        elif target_lower.isdigit():
            idx = int(target_lower) - 1
            if 0 <= idx < len(windows):
                return windows[idx]["hwnd"], windows[idx]["title"]
        elif target_lower.startswith("0x"):
            try:
                target_hwnd = int(target_lower, 16)
                for w in windows:
                    if w["hwnd"] == target_hwnd:
                        return w["hwnd"], w["title"]
            except ValueError:
                pass

        logging.warning(f"⚠️ 指定的目標 --target '{target}' 未匹配到任何實例，切換至選單選擇...")

    # 若不需互動 prompt 則預設返回第一筆
    if not auto_prompt:
        return windows[0]["hwnd"], windows[0]["title"]

    # CLI 互動選單
    print("\n" + "=" * 60)
    print("[*] 偵測到多個 Blackfire Crusade 遊戲實例：")
    print("-" * 60)
    for i, w in enumerate(windows, 1):
        tag = "【沙盒 Steam】" if w["is_sandbox"] else "【本機 Steam】"
        print(f"  [{i}] {tag} {w['title']}")
        print(f"      -> PID: {w['pid']} | HWND: {hex(w['hwnd'])} | 解析度: {w['width']}x{w['height']}\n")
    print("-" * 60)

    while True:
        try:
            choice = input(f"請選擇要控制的遊戲視窗 (1-{len(windows)}) [預設 1]: ").strip()
            if not choice:
                selected = windows[0]
                break
            if choice.isdigit() and 1 <= int(choice) <= len(windows):
                selected = windows[int(choice) - 1]
                break
            print(f"輸入無效，請輸入 1 至 {len(windows)} 之間的數字。")
        except (KeyboardInterrupt, EOFError):
            print("\n已取消選擇，使用預設第一個視窗。")
            selected = windows[0]
            break

    print(f"[+] 已選擇目標: [{selected['title']}] (PID: {selected['pid']}, HWND: {hex(selected['hwnd'])})")
    print("=" * 60 + "\n")
    return selected["hwnd"], selected["title"]

