import ctypes
import os
import time
import threading
import logging

VK_SPACE = 0x20
GA_ROOT = 2

class PauseController:
    """
    背景守護執行緒熱鍵與前景視窗焦點控制器 (PauseController - Background Daemon Edition)
    
    核心機制：
    1. 【獨立背景守護執行緒 (Background Daemon Thread)】：
       每 10ms 獨立在背景採樣按鍵與焦點狀態，完全不受主執行緒 OpenCV / OCR / 子流程阻塞的影響！
    2. 【相鄰節奏間隔判定 (Cadence Interval Timeout)】：
       只要每次按鍵與上一按鍵間隔不超過 1.5 秒 (cadence_timeout_sec = 1.5)，即視為連續敲擊。
       連按 3 次即刻標記 toggle_event_pending = True。
    3. 【即時進度提示】：
       每按一次即時輸出 [*] [空白鍵 1/3] 於 1.5 秒內再按 2 次切換暫停/繼續...
    4. 【雙路徑雙重保障】：
       - 終端機 (CMD / PowerShell / Windows Terminal / VS Code)：msvcrt.kbhit()
       - 遊戲視窗：GetAsyncKeyState(VK_SPACE) 配合視窗標題與頂層 HWND 比對。
    """

    def __init__(self, capturer=None, required_taps: int = 3, cadence_timeout_sec: float = 1.5, debounce_sec: float = 0.05, start_thread: bool = True):
        self.capturer = capturer
        self.required_taps = required_taps
        self.cadence_timeout_sec = cadence_timeout_sec
        self.debounce_sec = debounce_sec
        self.key_pressed = False
        self.last_press_time = 0.0
        self.last_tap_time = 0.0
        self.tap_count = 0
        self.toggle_event_pending = False
        self._lock = threading.Lock()
        self._running = True

        if start_thread:
            self._thread = threading.Thread(target=self._background_loop, daemon=True, name="PauseControllerThread")
            self._thread.start()
        else:
            self._thread = None

    def stop(self):
        """
        停止背景監聽執行緒。
        """
        self._running = False

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

    def _on_tap_detected(self, now: float) -> bool:
        """
        記錄一次有效敲擊，採用相鄰節奏間隔 (cadence_timeout_sec) 判定。
        """
        with self._lock:
            if now - self.last_tap_time > self.cadence_timeout_sec:
                self.tap_count = 1
            else:
                self.tap_count += 1

            self.last_tap_time = now
            self.last_press_time = now

            if self.tap_count >= self.required_taps:
                self.tap_count = 0
                self.toggle_event_pending = True
                try:
                    print(f"\r[*] [空白鍵 3/3 達成] 正在切換暫停/繼續狀態...                    \n", flush=True)
                except Exception:
                    pass
                return True
            else:
                remaining = self.required_taps - self.tap_count
                try:
                    print(f"\r[*] [空白鍵 {self.tap_count}/3] 於 {self.cadence_timeout_sec:.1f} 秒內再按 {remaining} 次切換暫停/繼續...", end="", flush=True)
                except Exception:
                    pass
                return False

    def check_toggle_triggered(self) -> bool:
        """
        主執行緒檢查是否有暫停/恢復切換事件。
        若未啟動背景執行緒 (例如在單步測試中)，會同步執行一次 _poll_once()。
        
        :return: True 代表成功觸發切換；False 代表無事件或次數未滿
        """
        if not self._thread or not self._thread.is_alive():
            self._poll_once()

        with self._lock:
            if self.toggle_event_pending:
                self.toggle_event_pending = False
                return True
            return False

    def _background_loop(self):
        """
        獨立背景守護執行緒主迴圈，每 10ms 採樣一次按鍵。
        """
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logging.debug(f"[PauseController] 背景監聽異常: {e}")
            time.sleep(0.01)

    def _poll_once(self, now=None):
        """
        單次按鍵採樣檢測。
        """
        if now is None:
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
                        return self._on_tap_detected(now)
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
                        return self._on_tap_detected(now)
                else:
                    self.key_pressed = False
            else:
                self.key_pressed = False
        except Exception as e:
            logging.debug(f"[PauseController] 按鍵檢測異常: {e}")

        return False
