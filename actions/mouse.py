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
    def __init__(self, human_like=False, backend_mode=False, window_title=WINDOW_TITLE):
        self.human_like = human_like
        self.backend_mode = backend_mode
        self.window_title = window_title
        self.last_action_time = 0.0
        self.last_target_pos = None
        self.state_machine = None
        self._window = WindowHandle(window_title)

    def _finalize_action(self, target_pos=None, cooldown: float = 0.0, move_safe: bool = True) -> bool:
        """
        統一動作成功後的狀態更新、冷卻與安全區復位。
        """
        if target_pos is not None:
            self.last_target_pos = target_pos
        else:
            try:
                self.last_target_pos = pyautogui.position()
            except Exception:
                self.last_target_pos = None

        self.last_action_time = time.time()
        if self.state_machine is not None:
            self.state_machine.consecutive_stuck_count = 0

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
        """
        if self.state_machine and self.state_machine.capturer:
            img = self.state_machine.capturer.capture()
            if img is not None:
                from states.debug import DebugVisualizer
                DebugVisualizer.draw_detection(
                    img,
                    click_pos=(rx_physical, ry_physical),
                    labels={"click": f"Click ({rx_physical}, {ry_physical})"},
                    filename="debug_click.png"
                )


    def check_user_intervention(self):
        """
        檢查狀態機是否處於手動暫停狀態。若是則回傳 True。
        """
        if self.state_machine is None:
            return False
            
        if getattr(self.state_machine, "is_paused", False):
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
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消點擊動作。")
            return False

        # 後台點擊模擬 (第一防線)
        if self.backend_mode:
            hwnd = self.get_hwnd()
            if hwnd:
                try:
                    client_x, client_y = self._screen_to_client(hwnd, x, y)
                    
                    dx = random.randint(offset_range[0], offset_range[1])
                    dy = random.randint(offset_range[0], offset_range[1])
                    cx = client_x + dx
                    cy = client_y + dy
                    
                    # 繪製 Debug 紅圈圖檔，保存為 debug_click.png
                    self._draw_debug_click(hwnd, cx, cy)
                    
                    lParam = win32api.MAKELONG(int(cx), int(cy))
                    # 先發送滑鼠移動消息以在後台觸發按鈕的 Hover (懸停) 狀態
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
                    time.sleep(0.01) # 微小延遲供遊戲引擎反應
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                    time.sleep(0.04) # 模擬按下的物理延遲
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                    
                    time.sleep(0.04) # 點擊後冷卻
                    return self._finalize_action(move_safe=True)
                except Exception as e:
                    logging.error(f"[後台] 點擊操作失敗: {e}")
                    return False

        # 前台模式實體點擊
        try:
            dx = random.randint(offset_range[0], offset_range[1])
            dy = random.randint(offset_range[0], offset_range[1])
            
            hwnd = self.get_hwnd()
            if hwnd:
                client_x, client_y = self._screen_to_client(hwnd, x, y)
                screen_pt = win32gui.ClientToScreen(hwnd, (int(client_x + dx), int(client_y + dy)))
                target_x, target_y = screen_pt[0], screen_pt[1]
            else:
                target_x = int(x) + dx
                target_y = int(y) + dy

            if self.human_like:
                duration = random.uniform(move_duration[0], move_duration[1])
                pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeOutQuad)
                time.sleep(random.uniform(0.01, 0.02))
            else:
                pyautogui.moveTo(target_x, target_y)

            pyautogui.mouseDown()
            time.sleep(0.04)
            pyautogui.mouseUp()
            time.sleep(0.04)

            return self._finalize_action(target_pos=(target_x, target_y), move_safe=True)
        except pyautogui.FailSafeException:
            logging.error("🔴 觸發 PyAutoGUI 安全終止 (FailSafe) 機制！滑鼠已移至螢幕角落。")
            raise
        except Exception as e:
            logging.error(f"點擊操作失敗: {e}")
            return False

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
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消滾動動作。")
            return False

        # 後台模式模擬
        if self.backend_mode:
            hwnd = self.get_hwnd()
            if hwnd:
                try:
                    client_rect = win32gui.GetClientRect(hwnd)
                    center_x = client_rect[2] // 2
                    center_y = client_rect[3] // 2
                    
                    if x is not None and y is not None:
                        client_x, client_y = self._screen_to_client(hwnd, x, y)
                    else:
                        client_x, client_y = center_x, center_y
                        
                    wheel_delta = clicks * 120
                    wparam = win32api.MAKELONG(0, wheel_delta)
                    lparam_move = win32api.MAKELONG(int(client_x), int(client_y))
                    
                    # 1. 先在後台將滑鼠焦點移入滾動區域
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam_move)
                    time.sleep(0.05)
                    
                    # 2. 獲取螢幕實體座標以傳遞給 WM_MOUSEWHEEL
                    screen_pt = win32gui.ClientToScreen(hwnd, (int(client_x), int(client_y)))
                    lparam_wheel = win32api.MAKELONG(screen_pt[0], screen_pt[1])
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam_wheel)
                    
                    return self._finalize_action(cooldown=0.3, move_safe=False)
                except Exception as e:
                    logging.error(f"[後台] 滾動操作失敗: {e}")
                    return False

        # 前台模式實體滾動
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
                pos = (x, y)
            else:
                pos = None
            pyautogui.scroll(clicks)
            return self._finalize_action(target_pos=pos, cooldown=0.3, move_safe=False)
        except Exception as e:
            logging.error(f"滾動操作失敗: {e}")
            return False

    def drag(self, start_x, start_y, end_x, end_y, duration=0.5, inertia=True):
        """
        在絕對螢幕座標上執行滑鼠左鍵拖曳。
        在後台模式下發送 WM_LBUTTONDOWN -> MOUSEMOVE -> LBUTTONUP，在前台使用 pyautogui.dragTo。
        """
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消拖曳動作。")
            return False

        # 後台拖曳模擬
        if self.backend_mode:
            hwnd = self.get_hwnd()
            if hwnd:
                try:
                    rsx, rsy = self._screen_to_client(hwnd, start_x, start_y)
                    rex, rey = self._screen_to_client(hwnd, end_x, end_y)
                    
                    # 1. 預先將滑鼠游標移動到起點 (不帶 MK_LBUTTON)，強迫遊戲引擎更新滑鼠座標快取
                    lparam_start = win32api.MAKELONG(int(rsx), int(rsy))
                    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam_start)
                    time.sleep(0.03)
                    
                    # 2. 按下 (使用 SendMessage 確保同步按下)
                    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam_start)
                    time.sleep(0.05)
                    
                    # 3. 插值模擬移動軌跡
                    steps = max(5, int(duration / 0.02))
                    step_sleep = duration / steps
                    for i in range(1, steps + 1):
                        curr_x = int(rsx + (rex - rsx) * (i / steps))
                        curr_y = int(rsy + (rey - rsy) * (i / steps))
                        lparam_move = win32api.MAKELONG(curr_x, curr_y)
                        win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam_move)
                        time.sleep(step_sleep)
                        
                    # 3.5 停頓以消除釋放慣性並確保釋放穩定性
                    if not inertia:
                        time.sleep(0.15)
                    else:
                        time.sleep(0.02)
                    
                    # 4. 確保最後一個移動點和釋放動作使用 SendMessage 同步發送
                    lparam_end = win32api.MAKELONG(int(rex), int(rey))
                    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam_end)
                    time.sleep(0.02)
                    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam_end)
                    
                    return self._finalize_action(cooldown=0.3, move_safe=True)
                except Exception as e:
                    logging.error(f"[後台] 拖曳操作失敗: {e}")
                    return False

        # 前台拖曳實體點擊
        try:
            hwnd = self.get_hwnd()
            if hwnd:
                rsx, rsy = self._screen_to_client(hwnd, start_x, start_y)
                rex, rey = self._screen_to_client(hwnd, end_x, end_y)
                pt_start = win32gui.ClientToScreen(hwnd, (int(rsx), int(rsy)))
                pt_end = win32gui.ClientToScreen(hwnd, (int(rex), int(rey)))
                s_x, s_y = pt_start[0], pt_start[1]
                e_x, e_y = pt_end[0], pt_end[1]
            else:
                s_x, s_y = int(start_x), int(start_y)
                e_x, e_y = int(end_x), int(end_y)

            if inertia:
                pyautogui.moveTo(s_x, s_y)
                pyautogui.dragTo(e_x, e_y, duration=duration, button='left')
            else:
                pyautogui.moveTo(s_x, s_y)
                pyautogui.mouseDown(button='left')
                pyautogui.moveTo(e_x, e_y, duration=duration)
                time.sleep(0.1)  # 關鍵暫停：消除釋放時的慣性速度
                pyautogui.mouseUp(button='left')
            return self._finalize_action(target_pos=(end_x, end_y), cooldown=0.3, move_safe=True)
        except Exception as e:
            logging.error(f"拖曳操作失敗: {e}")
            return False

    def move_to_safe_area(self):
        """
        將滑鼠游標移動到遊戲視窗邊角的安全區域（左上角 15, 15），
        以清除遊戲中因為滑鼠懸停 (hover) 產生的亮邊或高亮效果，避免干擾模板匹配。
        """
        safe_x, safe_y = SAFE_AREA_CLIENT_POS
        hwnd = self.get_hwnd()

        if self.backend_mode:
            if hwnd:
                lparam = win32api.MAKELONG(safe_x, safe_y)
                win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
            return

        # 前台模式
        if hwnd:
            try:
                screen_pt = win32gui.ClientToScreen(hwnd, (safe_x, safe_y))
                pyautogui.moveTo(screen_pt[0], screen_pt[1])
                return
            except Exception:
                pass

        if self.state_machine and getattr(self.state_machine, "last_rect", None) is not None:
            rect_box = self.state_machine.last_rect
            pyautogui.moveTo(rect_box["left"] + safe_x, rect_box["top"] + safe_y)
