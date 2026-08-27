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


SANDBOX_WINDOW_TITLE = f"[#] {WINDOW_TITLE} [#]"


def select_game_window(target: Optional[str] = None, auto_prompt: bool = True) -> Tuple[Optional[int], str]:
    """
    依據傳入的 target 參數或提示使用者互動選擇目標遊戲實例環境 (本機 vs 沙盒)。
    回傳: (hwnd, title)
    """
    windows = find_all_game_windows()
    native_win = next((w for w in windows if not w["is_sandbox"]), None)
    sandbox_win = next((w for w in windows if w["is_sandbox"]), None)

    # 1. 處理 CLI 命令列 --target 參數明確指定
    if target:
        target_lower = target.strip().lower()
        if target_lower in ["sandbox", "sandboxed", "box", "sb", "2"]:
            hwnd = sandbox_win["hwnd"] if sandbox_win else None
            return hwnd, (sandbox_win["title"] if sandbox_win else SANDBOX_WINDOW_TITLE)
        elif target_lower in ["native", "host", "main", "1"]:
            hwnd = native_win["hwnd"] if native_win else None
            return hwnd, (native_win["title"] if native_win else WINDOW_TITLE)
        elif target_lower.startswith("0x"):
            try:
                target_hwnd = int(target_lower, 16)
                for w in windows:
                    if w["hwnd"] == target_hwnd:
                        return w["hwnd"], w["title"]
            except ValueError:
                pass
        logging.warning(f"⚠️ 指定的目標 --target '{target}' 未匹配到已知選項，切換至互動選單...")

    # 若不需互動 prompt 則預設返回第一筆或本機實例
    if not auto_prompt:
        if native_win:
            return native_win["hwnd"], native_win["title"]
        elif sandbox_win:
            return sandbox_win["hwnd"], sandbox_win["title"]
        return None, WINDOW_TITLE

    # 2. CLI 互動選單 (每次啟動時皆提示，預設為 1: 本機 Steam)
    print("\n" + "=" * 60)
    print("[*] 請選擇要掛機的遊戲實例環境：")
    print("-" * 60)

    # 選項 1: 本機 Steam
    if native_win:
        nat_status = f"已在線 (PID: {native_win['pid']}, 解析度: {native_win['width']}x{native_win['height']})"
    else:
        nat_status = "未開啟 (啟動時將自動直連啟動)"
    print(f"  [1] 【本機 Steam】 (預設)\n      -> 狀態: {nat_status}\n")

    # 選項 2: 沙盒 Steam
    if sandbox_win:
        sb_status = f"已在線 (PID: {sandbox_win['pid']}, 解析度: {sandbox_win['width']}x{sandbox_win['height']})"
    else:
        sb_status = "未開啟 (啟動時將透過 Sandboxie 自動啟動)"
    print(f"  [2] 【沙盒 Steam (Sandboxie)】\n      -> 狀態: {sb_status}\n")
    print("-" * 60)

    while True:
        try:
            choice = input("請選擇目標實例 [1-2] (直接 Enter 預設為 1: 本機 Steam): ").strip()
            if not choice or choice == "1":
                hwnd = native_win["hwnd"] if native_win else None
                title = native_win["title"] if native_win else WINDOW_TITLE
                tag = "【本機 Steam】"
                break
            elif choice == "2":
                hwnd = sandbox_win["hwnd"] if sandbox_win else None
                title = sandbox_win["title"] if sandbox_win else SANDBOX_WINDOW_TITLE
                tag = "【沙盒 Steam】"
                break
            print("輸入無效，請輸入 1 (本機) 或 2 (沙盒)。")
        except (KeyboardInterrupt, EOFError):
            print("\n已取消選擇，使用預設本機 Steam。")
            hwnd = native_win["hwnd"] if native_win else None
            title = native_win["title"] if native_win else WINDOW_TITLE
            tag = "【本機 Steam】"
            break

    h_str = f"HWND: {hex(hwnd)}" if hwnd else "將自動啟動"
    print(f"[+] 已選擇目標實例: {tag} [{title}] ({h_str})")
    print("=" * 60 + "\n")
    return hwnd, title

