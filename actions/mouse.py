import pyautogui
import random
import time
import logging
import win32gui
import win32api
import win32con
import cv2
import numpy as np

from config import WINDOW_TITLE
from utils.window import WindowHandle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 啟用 PyAutoGUI 的安全機制 (滑鼠移到左上角 (0, 0) 會引發 FailSafeException 終止程式)
pyautogui.FAILSAFE = True
# 每次呼叫 pyautogui 後暫停微小的時間
pyautogui.PAUSE = 0.002

SAFE_AREA_CLIENT_POS = (15, 15)

class MouseController:
    def __init__(self, human_like=False, window_title=WINDOW_TITLE,
                 on_action_success=None, is_paused_fn=None, capturer=None, resume_event=None, hwnd=None):
        self.human_like = human_like
        self.window_title = window_title
        self.last_action_time = 0.0
        self.last_target_pos = None
        # --- Callback / Event 注入 (取代跨層直接存取 state_machine) ---
        # Callable[[], None]：每次動作成功後呼叫，由外部通知上層狀態機重置卡死計數
        self._on_action_success = on_action_success
        # Callable[[], bool]：查詢目前是否處於手動暫停狀態
        self._is_paused_fn = is_paused_fn
        # threading.Event：全域通行門閥，暫停時自動原地定格等待 (Freeze-in-Place)
        self._resume_event = resume_event
        # 截圖器參考 (可選)：供 _draw_debug_click 擷取畫面
        self._capturer = capturer
        self._window = WindowHandle(window_title=window_title, hwnd=hwnd)

    def _finalize_action(self, target_pos=None, cooldown: float = 0.0, move_safe: bool = True) -> bool:
        """
        統一動作成功後的狀態更新、冷卻與安全區復位。
        透過 _on_action_success callback 通知上層狀態機，不直接存取其內部屬性。
        """
        if target_pos is not None:
            self.last_target_pos = target_pos
        else:
            try:
                self.last_target_pos = pyautogui.position()
            except Exception:
                self.last_target_pos = None

        self.last_action_time = time.time()

        if self._on_action_success:
            self._on_action_success()

        if cooldown > 0:
            time.sleep(cooldown)

        if move_safe:
            self.move_to_safe_area()

        return True

    def get_hwnd(self):
        """
        取得或快取遊戲視窗控制代碼 (hwnd)。
        """
        return self._window.get()

    def _screen_to_client(self, hwnd, x, y):
        """
        將螢幕座標 (或視窗相對座標) 統一轉換為視窗內部客戶區座標 (Client Coordinates)。
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return int(x), int(y)
        try:
            client_pt = win32gui.ClientToScreen(hwnd, (0, 0))
            client_x = int(x) - client_pt[0]
            client_y = int(y) - client_pt[1]
            return client_x, client_y
        except Exception:
            return int(x), int(y)

    def _draw_debug_click(self, hwnd, rx_physical, ry_physical):
        """
        擷取當前畫面並繪製點擊位置紅圈，存檔為 debug_click.png 供調試排查。
        需於構造時注入 capturer 參考，否則 no-op。
        """
        if self._capturer:
            img = self._capturer.capture()
            if img is not None:
                from states.debug import DebugVisualizer
                DebugVisualizer.draw_detection(
                    img,
                    click_pos=(rx_physical, ry_physical),
                    labels={"click": f"Click ({rx_physical}, {ry_physical})"},
                    filename="debug_click.png"
                )


    def _wait_if_paused(self):
        """
        [原地定格門閥 Freeze-in-Place Gate]
        若注入了 _resume_event，當使用者觸發手動暫停時，底層動作執行緒將在此原地等待，
        直到使用者恢復掛機 (resume) 時 0 延遲無縫放行繼續執行。
        """
        if self._resume_event is not None:
            self._resume_event.wait()

    def check_user_intervention(self):
        """
        透過 _is_paused_fn callback 查詢目前是否處於手動暫停狀態。
        若未注入 callback 則永遠回傳 False（不攔截）。
        """
        if self._is_paused_fn and self._is_paused_fn():
            return True
        return False

    def click(self, x, y, offset_range=(-3, 3), move_duration=(0.03, 0.07)):
        """
        進行點擊，防作弊隨機偏移。
        以視窗內部客戶區座標 (Client Coordinates) 為核心：
        - 後台模式直接發送 Client 座標之 PostMessage 訊息，免除螢幕與 DPI 干擾；
        - 前台模式透過 ClientToScreen 自動換算為當前螢幕之實體滑鼠座標。
        
        :param x: 目標 X 座標 (支援 Client 座標或全域絕對座標)
        :param y: 目標 Y 座標 (支援 Client 座標或全域絕對座標)
        """
        raise NotImplementedError("Select BackendMouseController or ForegroundMouseController")
    def click_relative(self, rect, rel_x, rel_y, offset_range=(-3, 3), move_duration=(0.05, 0.12)):
        if rect is None:
            logging.error("無法進行相對座標點擊，因為 rect 為 None")
            return False
        abs_x = rect["left"] + rel_x
        abs_y = rect["top"] + rel_y
        return self.click(abs_x, abs_y, offset_range, move_duration)

    def scroll(self, clicks, x=None, y=None):
        """
        滾動滑鼠滾輪。
        在後台模式下發送 WM_MOUSEWHEEL 訊息給視窗，在前台模式下使用 pyautogui.scroll。
        """
        raise NotImplementedError("Select BackendMouseController or ForegroundMouseController")
    def drag(self, start_x, start_y, end_x, end_y, duration=0.5, inertia=True):
        """
        在絕對螢幕座標上執行滑鼠左鍵拖曳。
        在後台模式下發送 WM_LBUTTONDOWN -> MOUSEMOVE -> LBUTTONUP，在前台使用 pyautogui.dragTo。
        """
        raise NotImplementedError("Select BackendMouseController or ForegroundMouseController")
    def move_to_safe_area(self):
        """
        將滑鼠游標移動到遊戲視窗邊角的安全區域（左上角 15, 15），
        以清除遊戲中因為滑鼠懸停 (hover) 產生的亮邊或高亮效果，避免干擾模板匹配。
        若找不到視窗 hwnd，則 no-op（遊戲關閉時由 ExceptionWatchdog 負責重啟）。
        """
        raise NotImplementedError("Select BackendMouseController or ForegroundMouseController")
