import pyautogui
import random
import time
import logging
import win32gui
import win32api
import win32con
import ctypes
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 啟用 PyAutoGUI 的安全機制 (滑鼠移到左上角 (0, 0) 會引發 FailSafeException 終止程式)
pyautogui.FAILSAFE = True
# 每次呼叫 pyautogui 後暫停微小的時間
pyautogui.PAUSE = 0.002

class MouseController:
    def __init__(self, human_like=False, backend_mode=False, window_title="Blackfire Crusade"):
        self.human_like = human_like
        self.backend_mode = backend_mode
        self.window_title = window_title
        self.last_action_time = 0.0
        self.last_target_pos = None
        self.state_machine = None
        self._hwnd = None

    def get_hwnd(self):
        """
        取得或快取遊戲視窗控制代碼 (hwnd)。
        """
        if self._hwnd is None or not win32gui.IsWindow(self._hwnd):
            self._hwnd = win32gui.FindWindow(None, self.window_title)
        return self._hwnd

    def get_dpi_factor(self, hwnd):
        """
        獲取視窗所在顯示器的 DPI 縮放因子。
        如果 Windows 版本太舊不支持 GetDpiForWindow，則預設回傳 1.0。
        """
        try:
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            return dpi / 96.0
        except Exception:
            return 1.0

    def _draw_debug_click(self, hwnd, rx_physical, ry_physical):
        """
        擷取當前畫面並繪製點擊位置紅圈，存檔為 debug_click.png 供調試排查。
        因為 rx_physical, ry_physical 就是相對於整個視窗左上角的物理座標，
        直接在截圖的對應座標繪製即可，不需扣除任何邊框或標題列偏置。
        """
        if self.state_machine and self.state_machine.capturer:
            # 取得最新截圖
            img = self.state_machine.capturer.capture()
            if img is not None:
                try:
                    img_x = rx_physical
                    img_y = ry_physical
                    
                    # 畫一個紅色的空心圓
                    cv2.circle(img, (img_x, img_y), 15, (0, 0, 255), 2)
                    # 畫十字架
                    cv2.line(img, (img_x - 25, img_y), (img_x + 25, img_y), (0, 0, 255), 2)
                    cv2.line(img, (img_x, img_y - 25), (img_x, img_y + 25), (0, 0, 255), 2)
                    # 標註座標
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = f"Click: ({rx_physical}, {ry_physical})"
                    cv2.putText(img, text, (img_x + 20, img_y - 10), font, 0.6, (0, 0, 255), 2)
                    
                    cv2.imwrite("debug_click.png", img)
                except Exception as e:
                    logging.debug(f"無法寫入 debug_click.png: {e}")

    def check_user_intervention(self):
        """
        檢查使用者是否手動移動了滑鼠。如果是，則更新狀態機為暫停狀態並回傳 True。
        """
        if self.state_machine is None:
            return False
            
        if self.state_machine.user_operating:
            return True

        cur_pos = pyautogui.position()
        if self.last_target_pos is not None:
            # 只有當距離上次腳本動作時間極短（如 0.5 秒內）
            # 才需要在 click 呼叫前比對位移，防範在連點間隙中使用者動了滑鼠
            last_action_diff = time.time() - self.last_action_time
            if last_action_diff < 0.5:
                is_inside = True
                if self.backend_mode:
                    hwnd = self.get_hwnd()
                    if hwnd:
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            mx, my = cur_pos
                            is_inside = (rect[0] <= mx <= rect[2] and rect[1] <= my <= rect[3])
                        except Exception:
                            is_inside = False
                    else:
                        is_inside = False
                
                if is_inside:
                    dx = abs(cur_pos[0] - self.last_target_pos[0])
                    dy = abs(cur_pos[1] - self.last_target_pos[1])
                    if dx > 5 or dy > 5:
                        logging.warning(f"⚠️ [MouseController] 偵測到使用者在連點間隙中操作滑鼠 (移至 {cur_pos})，禁止腳本移動滑鼠。")
                        self.state_machine.user_operating = True
                        self.state_machine.last_user_operation_time = time.time()
                        return True
        else:
            # 首次運行，初始化
            self.last_target_pos = cur_pos
        return False

    def click(self, x, y, offset_range=(-3, 3), move_duration=(0.03, 0.07)):
        """
        進行點擊，防作弊隨機偏移。
        在後台模式下發送 PostMessage 訊息，在前台模式下使用 pyautogui 移動並點擊。
        
        :param x: 全域絕對目標 X 座標
        :param y: 全域絕對目標 Y 座標
        """
        if self.check_user_intervention():
            logging.info("🚫 使用者介入中，取消點擊動作。")
            return False

        # 後台點擊模擬 (第一防線)
        if self.backend_mode:
            hwnd = self.get_hwnd()
            if hwnd:
                try:
                    # 優先使用狀態機當前幀快取的正確物理 rect，防範 win32gui.GetWindowRect 在跨 DPI 螢幕時隨機發生的 DPI 虛擬化回退
                    if self.state_machine and getattr(self.state_machine, "last_rect", None) is not None:
                        rect_box = self.state_machine.last_rect
                        rect = (rect_box["left"], rect_box["top"], rect_box["left"] + rect_box["width"], rect_box["top"] + rect_box["height"])
                    else:
                        rect = win32gui.GetWindowRect(hwnd)
                        
                    rx_physical = int(x) - rect[0]
                    ry_physical = int(y) - rect[1]
                    
                    dx = random.randint(offset_range[0], offset_range[1])
                    dy = random.randint(offset_range[0], offset_range[1])
                    rx_offset_phys = rx_physical + dx
                    ry_offset_phys = ry_physical + dy
                    
                    # 暫緩延伸螢幕 DPI 自適應對齊開發，優先確保大螢幕 (DPI=1.0) 後台點擊無偏置
                    dpi_factor = 1.0
                    rx_logical = int(rx_offset_phys / dpi_factor)
                    ry_logical = int(ry_offset_phys / dpi_factor)
                    
                    logging.info(f"[後台點擊] 物理相對: ({rx_offset_phys}, {ry_offset_phys}) -> 邏輯相對: ({rx_logical}, {ry_logical}) [DPI 縮放: {dpi_factor}]")
                    
                    # 繪製 Debug 紅圈圖檔
                    self._draw_debug_click(hwnd, rx_offset_phys, ry_offset_phys)
                    
                    lParam = win32api.MAKELONG(rx_logical, ry_logical)
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                    time.sleep(0.04) # 模擬按下的物理延遲
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                    
                    time.sleep(0.04) # 點擊後冷卻
                    
                    # 鎖定實體滑鼠當前位置，避免點擊訊息引發防搶誤判
                    self.last_target_pos = pyautogui.position()
                    self.last_action_time = time.time()
                    if self.state_machine is not None:
                        self.state_machine.consecutive_stuck_count = 0
                    return True
                except Exception as e:
                    logging.error(f"[後台] 點擊操作失敗: {e}")
                    return False

        # 前台模式實體點擊
        try:
            dx = random.randint(offset_range[0], offset_range[1])
            dy = random.randint(offset_range[0], offset_range[1])
            target_x = x + dx
            target_y = y + dy

            logging.info(f"準備點擊座標: ({target_x}, {target_y})，隨機偏移: ({dx}, {dy})")

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

            self.last_target_pos = (target_x, target_y)
            self.last_action_time = time.time()
            if self.state_machine is not None:
                self.state_machine.consecutive_stuck_count = 0
            return True
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
                    if self.state_machine and getattr(self.state_machine, "last_rect", None) is not None:
                        rect_box = self.state_machine.last_rect
                        rect = (rect_box["left"], rect_box["top"], rect_box["left"] + rect_box["width"], rect_box["top"] + rect_box["height"])
                    else:
                        rect = win32gui.GetWindowRect(hwnd)
                    center_x = rect[0] + (rect[2] - rect[0]) // 2
                    center_y = rect[1] + (rect[3] - rect[1]) // 2
                    
                    target_x = x if x is not None else center_x
                    target_y = y if y is not None else center_y
                    
                    wheel_delta = clicks * 120
                    wparam = win32api.MAKELONG(0, wheel_delta)
                    lparam = win32api.MAKELONG(target_x, target_y)
                    
                    # 1. 計算用於 WM_MOUSEMOVE 的視窗相對座標 (Client Coordinates)
                    rx_client = target_x - rect[0]
                    ry_client = target_y - rect[1]
                    lparam_move = win32api.MAKELONG(rx_client, ry_client)
                    
                    # 2. 先在後台將滑鼠焦點移入滾動區域
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam_move)
                    time.sleep(0.05)  # 提供微小延遲讓遊戲引擎響應移入
                    
                    # 3. 發送滾動消息 (lparam 為螢幕絕對座標)
                    logging.info(f"[後台滾輪] delta={wheel_delta}, 目標座標: ({target_x}, {target_y})")
                    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)
                    
                    self.last_target_pos = pyautogui.position()
                    self.last_action_time = time.time()
                    if self.state_machine is not None:
                        self.state_machine.consecutive_stuck_count = 0
                    time.sleep(0.3)
                    return True
                except Exception as e:
                    logging.error(f"[後台] 滾動操作失敗: {e}")
                    return False

        # 前台模式實體滾動
        try:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
                self.last_target_pos = (x, y)
            else:
                self.last_target_pos = pyautogui.position()
            pyautogui.scroll(clicks)
            self.last_action_time = time.time()
            if self.state_machine is not None:
                self.state_machine.consecutive_stuck_count = 0
            time.sleep(0.3)
            return True
        except Exception as e:
            logging.error(f"滾動操作失敗: {e}")
            return False

    def drag(self, start_x, start_y, end_x, end_y, duration=0.5):
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
                    # 優先使用狀態機當前幀快取的正確物理 rect，防範 win32gui.GetWindowRect 在跨 DPI 螢幕時隨機發生的 DPI 虛擬化回退
                    if self.state_machine and getattr(self.state_machine, "last_rect", None) is not None:
                        rect_box = self.state_machine.last_rect
                        rect = (rect_box["left"], rect_box["top"], rect_box["left"] + rect_box["width"], rect_box["top"] + rect_box["height"])
                    else:
                        rect = win32gui.GetWindowRect(hwnd)
                        
                    rsx_phys = int(start_x) - rect[0]
                    rsy_phys = int(start_y) - rect[1]
                    rex_phys = int(end_x) - rect[0]
                    rey_phys = int(end_y) - rect[1]
                    
                    # 暫緩延伸螢幕 DPI 自適應對齊開發，優先確保大螢幕 (DPI=1.0) 後台拖曳無偏置
                    dpi_factor = 1.0
                    rsx_logical = int(rsx_phys / dpi_factor)
                    rsy_logical = int(rsy_phys / dpi_factor)
                    rex_logical = int(rex_phys / dpi_factor)
                    rey_logical = int(rey_phys / dpi_factor)
                    
                    logging.info(f"[後台拖曳] 物理相對起點 ({rsx_phys}, {rsy_phys}) -> 邏輯相對起點 ({rsx_logical}, {rsy_logical}) [DPI 縮放: {dpi_factor}]")
                    
                    # 1. 按下
                    lparam_start = win32api.MAKELONG(rsx_logical, rsy_logical)
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam_start)
                    time.sleep(0.05)
                    
                    # 2. 插值模擬移動軌跡
                    steps = 8
                    for i in range(1, steps + 1):
                        curr_x_phys = int(rsx_phys + (rex_phys - rsx_phys) * (i / steps))
                        curr_y_phys = int(rsy_phys + (rey_phys - rsy_phys) * (i / steps))
                        curr_x_logical = int(curr_x_phys / dpi_factor)
                        curr_y_logical = int(curr_y_phys / dpi_factor)
                        
                        lparam_move = win32api.MAKELONG(curr_x_logical, curr_y_logical)
                        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, lparam_move)
                        time.sleep(0.02)
                        
                    # 3. 釋放
                    lparam_end = win32api.MAKELONG(rex_logical, rey_logical)
                    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam_end)
                    
                    self.last_target_pos = pyautogui.position()
                    self.last_action_time = time.time()
                    if self.state_machine is not None:
                        self.state_machine.consecutive_stuck_count = 0
                    time.sleep(0.3)
                    return True
                except Exception as e:
                    logging.error(f"[後台] 拖曳操作失敗: {e}")
                    return False

        # 前台拖曳實體點擊
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration, button='left')
            self.last_target_pos = (end_x, end_y)
            self.last_action_time = time.time()
            if self.state_machine is not None:
                self.state_machine.consecutive_stuck_count = 0
            time.sleep(0.3)
            return True
        except Exception as e:
            logging.error(f"拖曳操作失敗: {e}")
            return False
