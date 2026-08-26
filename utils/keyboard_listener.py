import ctypes
import os
import time
import threading
import logging

VK_CONTROL = 0x11
VK_SPACE = 0x20
GA_ROOT = 2

TRIGGER_MODE_CTRL_SPACE = "ctrl_space"
TRIGGER_MODE_TRIPLE_SPACE = "triple_space"

class PauseController:
    """
    可插拔熱鍵策略與前景視窗焦點控制器 (PauseController - Pluggable Strategy Edition)
    
    支援可插拔觸發策略 (Pluggable Trigger Modes)：
    1. 【TRIGGER_MODE_CTRL_SPACE ("ctrl_space")】(預設推薦)：
       按下 Ctrl + Space 立即切換暫停/繼續。乾脆俐落、手感極佳、且絕對不會在遊戲內走位或打字時誤觸。
    2. 【TRIGGER_MODE_TRIPLE_SPACE ("triple_space")】：
       在 1.5 秒內連續敲擊 3 次空白鍵觸發，附帶即時進度反饋。
       
    核心架構：
    - 獨立背景守護執行緒 (Background Daemon Thread，每 10ms 採樣) 確保主執行緒 OpenCV/OCR 阻塞時 100% 毫秒級捕獲。
    - 嚴格雙視窗焦點過濾 (Terminal 或 Game 視窗聚焦時生效，第三方視窗 100% 忽略)。
    """

    def __init__(
        self,
        capturer=None,
        trigger_mode: str = TRIGGER_MODE_CTRL_SPACE,
        required_taps: int = 3,
        cadence_timeout_sec: float = 1.5,
        debounce_sec: float = 0.08,
        start_thread: bool = True
    ):
        self.capturer = capturer
        self.trigger_mode = trigger_mode
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

        # 策略字典映射 (Function Strategy Pattern)
        self._strategies = {
            TRIGGER_MODE_CTRL_SPACE: self._poll_ctrl_space,
            TRIGGER_MODE_TRIPLE_SPACE: self._poll_triple_space,
        }

        if start_thread:
            self._thread = threading.Thread(target=self._background_loop, daemon=True, name="PauseControllerThread")
            self._thread.start()
        else:
            self._thread = None

    def set_trigger_mode(self, mode: str):
        """
        動態切換熱鍵策略模式 ('ctrl_space' | 'triple_space' | 'single_space')。
        """
        with self._lock:
            if mode in self._strategies:
                self.trigger_mode = mode
                self.tap_count = 0
                self.key_pressed = False
                logging.info(f"🔄 [PauseController] 已切換熱鍵策略模式為: {mode}")

    def get_trigger_hint(self) -> str:
        """
        取得當前模式的使用者提示文字。
        """
        if self.trigger_mode == TRIGGER_MODE_CTRL_SPACE:
            return "按 [Ctrl + Space] 隨時暫停/繼續"
        elif self.trigger_mode == TRIGGER_MODE_TRIPLE_SPACE:
            return "【連按 3 次空白鍵】隨時暫停/繼續"
        else:
            return "按 [Space 空白鍵] 隨時暫停/繼續"

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

    # =========================================================================
    # 策略 1：Ctrl + Space 組合鍵監聽策略 (預設推薦)
    # =========================================================================
    def _poll_ctrl_space(self, now: float) -> bool:
        # 1. 終端機直接字元流檢查 (Ctrl+Space 在 msvcrt 中常為 b'\x00' 或搭配 Ctrl 狀態)
        try:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                ctrl_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                if (ch == b'\x00' or ch == b' ') and ctrl_down:
                    if now - self.last_press_time >= self.debounce_sec:
                        with self._lock:
                            self.toggle_event_pending = True
                            self.last_press_time = now
                            try:
                                print(f"\r[*] [Ctrl + Space 觸發] 正在切換暫停/繼續狀態...                    \n", flush=True)
                            except Exception:
                                pass
                            return True
        except Exception:
            pass

        # 2. 物理按鍵檢測 (Ctrl 與 Space 同時處於按下狀態)
        try:
            if self.is_target_window_active():
                ctrl_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                space_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_SPACE) & 0x8000)

                if ctrl_down and space_down:
                    if not self.key_pressed and (now - self.last_press_time >= self.debounce_sec):
                        self.key_pressed = True
                        with self._lock:
                            self.toggle_event_pending = True
                            self.last_press_time = now
                            try:
                                print(f"\r[*] [Ctrl + Space 觸發] 正在切換暫停/繼續狀態...                    \n", flush=True)
                            except Exception:
                                pass
                            return True
                else:
                    if not (ctrl_down and space_down):
                        self.key_pressed = False
            else:
                self.key_pressed = False
        except Exception as e:
            logging.debug(f"[PauseController] Ctrl+Space 檢測異常: {e}")

        return False

    # =========================================================================
    # 策略 2：Triple-Space 連按 3 次空白鍵策略
    # =========================================================================
    def _on_triple_tap_registered(self, now: float) -> bool:
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

    def _poll_triple_space(self, now: float) -> bool:
        try:
            import msvcrt
            while msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b' ':
                    if now - self.last_press_time >= self.debounce_sec:
                        return self._on_triple_tap_registered(now)
        except Exception:
            pass

        try:
            if self.is_target_window_active():
                state = ctypes.windll.user32.GetAsyncKeyState(VK_SPACE)
                is_down = bool(state & 0x8000)
                # 排除同時按下 Ctrl 的情況
                ctrl_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

                if is_down and not ctrl_down:
                    if not self.key_pressed and (now - self.last_press_time >= self.debounce_sec):
                        self.key_pressed = True
                        return self._on_triple_tap_registered(now)
                else:
                    self.key_pressed = False
            else:
                self.key_pressed = False
        except Exception as e:
            logging.debug(f"[PauseController] Triple-Space 檢測異常: {e}")

        return False

    # =========================================================================
    # 主執行緒調度與背景執行緒
    # =========================================================================
    def check_toggle_triggered(self) -> bool:
        """
        主執行緒檢查是否有暫停/恢復切換事件。
        若未啟動背景執行緒 (例如在單步測試中)，會同步執行一次目前策略之 _poll_once()。
        
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
        獨立背景守護執行緒主迴圈，每 10ms 依當前策略採樣一次按鍵。
        """
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logging.debug(f"[PauseController] 背景監聽異常: {e}")
            time.sleep(0.01)

    def _poll_once(self, now=None):
        """
        依據目前策略分發單次按鍵檢測。
        """
        if now is None:
            now = time.time()

        strategy_func = self._strategies.get(self.trigger_mode, self._poll_ctrl_space)
        return strategy_func(now)
