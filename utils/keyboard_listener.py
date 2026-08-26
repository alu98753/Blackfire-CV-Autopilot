import ctypes
import os
import time
import logging

VK_SPACE = 0x20
GA_ROOT = 2

class PauseController:
    """
    熱鍵與前景視窗焦點控制器 (PauseController)
    
    雙路徑雙重保障：
    1. 【終端機焦點路徑】：透過 msvcrt.kbhit() 監聽標準輸入流。
       只要終端機 (CMD / PowerShell / Windows Terminal / VS Code Terminal) 有焦點並按空白鍵，100% 必定捕獲！
    2. 【遊戲與終端機前景物理按鍵】：透過 GetAsyncKeyState(VK_SPACE) 配合視窗標題/HWND 根層級判定。
       當使用者在遊戲視窗或終端機視窗上按空白鍵時，精確觸發暫停/恢復，且不干擾瀏覽器等其他程式。
    """

    def __init__(self, capturer=None, debounce_sec: float = 0.3):
        self.capturer = capturer
        self.debounce_sec = debounce_sec
        self.key_pressed = False
        self.last_toggle_time = 0.0

    def get_console_hwnd(self):
        """
        取得目前 Python 運行的終端機 (Console) 視窗控制代碼。
        """
        try:
            return ctypes.windll.kernel32.GetConsoleWindow()
        except Exception:
            return None

    def get_game_hwnd(self):
        """
        取得遊戲視窗控制代碼 (HWND) 或其頂層根視窗。
        """
        if self.capturer and getattr(self.capturer, "hwnd", None):
            try:
                root_hwnd = ctypes.windll.user32.GetAncestor(self.capturer.hwnd, GA_ROOT)
                return root_hwnd if root_hwnd else self.capturer.hwnd
            except Exception:
                return self.capturer.hwnd
        return None

    def is_console_window_active(self) -> bool:
        """
        判定當前前景視窗是否為終端機視窗 (Console / Terminal / PowerShell / CMD)。
        """
        try:
            fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not fg_hwnd:
                return False

            console_hwnd = self.get_console_hwnd()
            if console_hwnd and fg_hwnd == console_hwnd:
                return True

            length = ctypes.windll.user32.GetWindowTextLengthW(fg_hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(fg_hwnd, buff, length + 1)
                title = buff.value.lower()
                if any(k in title for k in ["cmd", "powershell", "terminal", "python", "掛機"]):
                    return True

            return False
        except Exception:
            return False

    def is_game_window_active(self) -> bool:
        """
        判定當前前景視窗是否為遊戲視窗。
        """
        try:
            fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not fg_hwnd:
                return False

            game_hwnd = self.get_game_hwnd()
            if game_hwnd:
                if fg_hwnd == game_hwnd:
                    return True
                fg_root = ctypes.windll.user32.GetAncestor(fg_hwnd, GA_ROOT)
                if fg_root and fg_root == game_hwnd:
                    return True

            length = ctypes.windll.user32.GetWindowTextLengthW(fg_hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(fg_hwnd, buff, length + 1)
                title = buff.value.lower()
                if "blackfire" in title or "crusade" in title:
                    return True

            return False
        except Exception:
            return False

    def is_target_window_active(self) -> bool:
        """
        判定當前前景視窗是否為目標視窗 (終端機 或 遊戲視窗)。
        """
        return self.is_console_window_active() or self.is_game_window_active()

    def check_toggle_triggered(self) -> bool:
        """
        檢查是否在目標視窗按下了 [Space 空白鍵]。
        
        :return: True 代表觸發切換；False 代表無事件或被過濾
        """
        now = time.time()
        if now - self.last_toggle_time < self.debounce_sec:
            return False

        # -------------------------------------------------------------
        # 路徑 1：終端機直接字元流 (msvcrt.kbhit) - 最可靠！
        # -------------------------------------------------------------
        try:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b' ':
                    self.last_toggle_time = now
                    return True
        except Exception:
            pass

        # -------------------------------------------------------------
        # 路徑 2：遊戲或終端機前景物理按鍵 (GetAsyncKeyState)
        # -------------------------------------------------------------
        try:
            if self.is_target_window_active():
                state = ctypes.windll.user32.GetAsyncKeyState(VK_SPACE)
                is_down = bool(state & 0x8000)

                if is_down:
                    if not self.key_pressed:
                        self.key_pressed = True
                        self.last_toggle_time = now
                        return True
                else:
                    self.key_pressed = False
            else:
                self.key_pressed = False
        except Exception as e:
            logging.debug(f"[PauseController] 按鍵檢測異常: {e}")

        return False
