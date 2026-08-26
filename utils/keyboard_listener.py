import ctypes
import os
import time
import logging

VK_SPACE = 0x20
GA_ROOT = 2

class PauseController:
    """
    熱鍵與前景視窗焦點控制器 (PauseController - Triple-Space Edition)
    
    核心機制：
    1. 【連敲 3 次空白鍵觸發 (Triple-Space)】：在 1.2 秒內連續按下 3 次空白鍵，才切換暫停/繼續，徹底防止遊戲或打字時單次誤觸。
    2. 【即時回饋提示】：每按一次空白鍵即時印出進度提示 (1/3 -> 2/3 -> 3/3 達成)。
    3. 【雙路徑雙重保障】：
       - 終端機 (CMD / PowerShell / Windows Terminal / VS Code)：透過 msvcrt.kbhit() 監聽標準輸入流。
       - 遊戲視窗：透過 GetAsyncKeyState(VK_SPACE) 配合視窗標題與頂層 HWND 比對。
    """

    def __init__(self, capturer=None, required_taps: int = 3, window_sec: float = 1.2, debounce_sec: float = 0.05):
        self.capturer = capturer
        self.required_taps = required_taps
        self.window_sec = window_sec
        self.debounce_sec = debounce_sec
        self.key_pressed = False
        self.last_press_time = 0.0
        self.tap_timestamps = []

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

    def _register_tap(self, now: float) -> bool:
        """
        記錄一次有效空白鍵敲擊，並檢查是否在時間窗口內湊滿 3 次。
        """
        # 清除超出時間窗口的過期敲擊記錄
        self.tap_timestamps = [t for t in self.tap_timestamps if now - t <= self.window_sec]
        self.tap_timestamps.append(now)
        self.last_press_time = now

        current_count = len(self.tap_timestamps)
        if current_count >= self.required_taps:
            self.tap_timestamps.clear()
            try:
                print(f"\r[*] [空白鍵 3/3 達成] 正在切換暫停/繼續狀態...                    \n", flush=True)
            except Exception:
                pass
            return True
        else:
            remaining = self.required_taps - current_count
            try:
                print(f"\r[*] [空白鍵 {current_count}/3] 於 {self.window_sec:.1f} 秒內再按 {remaining} 次切換暫停/繼續...", end="", flush=True)
            except Exception:
                pass
            return False

    def check_toggle_triggered(self) -> bool:
        """
        檢查是否在目標視窗連續按下了 3 次 [Space 空白鍵]。
        
        :return: True 代表成功觸發暫停/恢復切換；False 代表次數未滿或被過濾
        """
        now = time.time()

        # -------------------------------------------------------------
        # 路徑 1：終端機直接字元流 (msvcrt.kbhit)
        # -------------------------------------------------------------
        try:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b' ':
                    if now - self.last_press_time >= self.debounce_sec:
                        return self._register_tap(now)
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
                    if not self.key_pressed and (now - self.last_press_time >= self.debounce_sec):
                        self.key_pressed = True
                        return self._register_tap(now)
                else:
                    self.key_pressed = False
            else:
                self.key_pressed = False
        except Exception as e:
            logging.debug(f"[PauseController] 按鍵檢測異常: {e}")

        return False
