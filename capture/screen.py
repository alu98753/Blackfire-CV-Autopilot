import logging
import sys
import os
import subprocess
import time
import ctypes
import numpy as np
import cv2
import mss
import win32gui
import win32ui
import win32con
from typing import Optional, Tuple, Dict, Any


class ScreenCapturer:
    def __init__(self, window_title="Blackfire Crusade", backend_mode=False, monitor_index=1):
        # 已關閉 DPI Awareness 宣告以符合專案與使用者需求
        self.window_title = window_title
        self.backend_mode = backend_mode
        self.monitor_index = monitor_index
        self.sct = mss.MSS()
        self._hwnd = None
        self.last_monitor = None
        self._backend_printwindow_supported = True
        self._cached_phys_rect = None
        self._cached_log_rect = None

    def get_hwnd(self):
        """
        取得遊戲視窗控制代碼 (HWnd)，包含防快取失效重查。
        """
        if not self._hwnd or not win32gui.IsWindow(self._hwnd):
            self._hwnd = win32gui.FindWindow(None, self.window_title)
        return self._hwnd

    def get_window_rect(self, quiet: bool = False):
        """
        取得指定視窗在虛擬螢幕座標系下的絕對位置與大小。
        """
        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                if not quiet:
                    logging.warning(f"找不到視窗標題為 '{self.window_title}' 的視窗。")
                return None
            
            if win32gui.IsIconic(hwnd):
                if not quiet:
                    logging.info(f"🔄 偵測到視窗 '{self.window_title}' 被最小化，自動發起 ensure_window_on_monitor 還原並置頂最大化...")
                self.ensure_window_on_monitor()
                if win32gui.IsIconic(hwnd):
                    if not quiet:
                        logging.warning(f"⚠️ 嘗試自動還原最小化視窗 '{self.window_title}' 失敗。")
                    return None

            if bool(ctypes.windll.user32.IsZoomed(hwnd)):
                client_pt = win32gui.ClientToScreen(hwnd, (0, 0))
                client_rect = win32gui.GetClientRect(hwnd)
                return {
                    "left": client_pt[0],
                    "top": client_pt[1],
                    "width": client_rect[2],
                    "height": client_rect[3],
                    "title": self.window_title
                }

            rect = win32gui.GetWindowRect(hwnd)
            return {
                "left": rect[0],
                "top": rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
                "title": self.window_title
            }
        except Exception as e:
            if not quiet:
                logging.error(f"取得視窗座標時發生錯誤: {e}")
            return None

    def ensure_window_on_monitor(self, monitor_index: Optional[int] = None) -> bool:
        """
        將遊戲視窗自動移動並定位到指定的顯示器 (預設 self.monitor_index 筆電螢幕 1)。
        修復邏輯：若視窗處於最大化狀態，必須先 SW_RESTORE 解除最大化，否則 Windows 禁止 SetWindowPos 跨顯示器移動！
        移動後再調用 SW_MAXIMIZE 在目標顯示器上最大化全螢幕。
        """
        target_idx = monitor_index if monitor_index is not None else self.monitor_index
        if target_idx is None:
            return False

        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                logging.warning(f"⚠️ [ScreenCapturer] ensure_window_on_monitor 找不到標題為 '{self.window_title}' 的視窗。")
                return False

            import win32api
            monitors = win32api.EnumDisplayMonitors(None, None)
            if 0 < target_idx <= len(monitors):
                hmon, _, _ = monitors[target_idx - 1]
                info = win32api.GetMonitorInfo(hmon)
                mon_rect = info["Monitor"]  # (left, top, right, bottom)
                mon_l, mon_t = mon_rect[0], mon_rect[1]
                mon_r, mon_b = mon_rect[2], mon_rect[3]

                w_left, w_top, w_right, w_bottom = win32gui.GetWindowRect(hwnd)
                w_center_x = (w_left + w_right) // 2
                w_center_y = (w_top + w_bottom) // 2

                is_on_target_mon = (mon_l <= w_center_x < mon_r) and (mon_t <= w_center_y < mon_b)
                is_zoomed = bool(ctypes.windll.user32.IsZoomed(hwnd))
                is_iconic = bool(ctypes.windll.user32.IsIconic(hwnd))

                logging.info(
                    f"🔍 [ScreenCapturer Debug] 視窗 HWND: {hwnd}, 當前 Rect: ({w_left}, {w_top}, {w_right}, {w_bottom}), "
                    f"中心點: ({w_center_x}, {w_center_y}), 已最大化: {is_zoomed} | "
                    f"目標 Monitor {target_idx} 範圍: ({mon_l}, {mon_t})~({mon_r}, {mon_b}), 已在目標螢幕: {is_on_target_mon}"
                )

                if not is_on_target_mon or not is_zoomed:
                    logging.info(f"🚚 [ScreenCapturer] 執行跨螢幕傳送至 Monitor {target_idx} ({mon_l}, {mon_t})...")

                    # 1. 關鍵步驟：若目前處於最大化或最小化狀態，必須先 SW_RESTORE，否則 Win32 禁止 SetWindowPos 跨螢幕移動
                    if is_zoomed or is_iconic:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.15)

                    # 2. 將未最大化的視窗移入目標顯示器內部
                    win32gui.SetWindowPos(
                        hwnd,
                        win32con.HWND_TOP,
                        mon_l + 50,
                        mon_t + 50,
                        1280,
                        720,
                        win32con.SWP_SHOWWINDOW
                    )
                    time.sleep(0.15)

                    # 3. 搶佔前景焦點並發起 SW_SHOWMAXIMIZED / SC_MAXIMIZE 強制填滿全螢幕
                    try:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                    time.sleep(0.2)

                    # 雙重護欄：若仍未處於 IsZoomed 狀態，對 HWND 發送標題列最大化按鈕訊息 (WM_SYSCOMMAND, SC_MAXIMIZE)
                    if not bool(ctypes.windll.user32.IsZoomed(hwnd)):
                        logging.info("🔄 [ScreenCapturer] SW_SHOWMAXIMIZED 未即時生效，對視窗發送 SC_MAXIMIZE 標題列訊息強制最大化...")
                        win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MAXIMIZE, 0)
                        time.sleep(0.2)

                    # 4. 驗證移動結果
                    new_rect = win32gui.GetWindowRect(hwnd)
                    new_center_x = (new_rect[0] + new_rect[2]) // 2
                    new_center_y = (new_rect[1] + new_rect[3]) // 2
                    new_on_target = (mon_l <= new_center_x < mon_r) and (mon_t <= new_center_y < mon_b)
                    logging.info(f"🎉 [ScreenCapturer] 視窗傳送結果: 新 Rect: {new_rect}, 新中心: ({new_center_x}, {new_center_y}), 是否成功到達 Monitor {target_idx}: {new_on_target}")
                    return new_on_target
                else:
                    logging.info(f"✅ [ScreenCapturer] 遊戲視窗已在 Monitor {target_idx} 上且已處於最大化狀態。")
                    return True
        except Exception as e:
            logging.error(f"❌ 自動移動視窗至 Monitor {target_idx} 失敗: {e}", exc_info=True)
        return False

    def get_logical_window_rect(self, phys_rect):
        """
        優先使用 Windows 原生 PhysicalToLogicalPointForWindow API 獲取 100% 精準的邏輯座標。
        若 API 呼叫失敗，則退回使用 DPI Unaware 子進程快取方案。
        """
        if phys_rect is None:
            return None
            
        hwnd = self.get_hwnd()
        if hwnd:
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                
                pt_tl = POINT(phys_rect["left"], phys_rect["top"])
                pt_br = POINT(phys_rect["left"] + phys_rect["width"], phys_rect["top"] + phys_rect["height"])
                
                res_tl = ctypes.windll.user32.PhysicalToLogicalPointForWindow(hwnd, ctypes.byref(pt_tl))
                res_br = ctypes.windll.user32.PhysicalToLogicalPointForWindow(hwnd, ctypes.byref(pt_br))
                
                if res_tl and res_br:
                    log_rect = {
                        "left": pt_tl.x,
                        "top": pt_tl.y,
                        "width": pt_br.x - pt_tl.x,
                        "height": pt_br.y - pt_tl.y
                    }
                    return log_rect
            except Exception as e_api:
                logging.debug(f"使用 PhysicalToLogicalPointForWindow API 轉換失敗: {e_api}")

        # ⚡ 恢復舊版快取機制：若座標無變化，直接傳回快取結果避開 subprocess 開銷
        if hasattr(self, "_cached_phys_rect") and self._cached_phys_rect == phys_rect:
            if hasattr(self, "_cached_log_rect") and self._cached_log_rect is not None:
                return self._cached_log_rect

        # 🛡️ 補上新版保底容錯：預設等於 phys_rect
        log_rect = phys_rect
        try:
            cmd = [
                sys.executable,
                "-c",
                f"import win32gui; hwnd = win32gui.FindWindow(None, '{self.window_title}'); print(win32gui.GetWindowRect(hwnd)) if hwnd else print('None')"
            ]
            out = subprocess.check_output(cmd, timeout=0.8).decode().strip()
            if out and out != "None":
                val = eval(out)
                log_rect = {
                    "left": val[0],
                    "top": val[1],
                    "width": val[2] - val[0],
                    "height": val[3] - val[1]
                }
        except Exception as e:
            logging.debug(f"獲取邏輯座標失敗: {e}")
            
        self._cached_phys_rect = phys_rect
        self._cached_log_rect = log_rect
        return log_rect

    def _capture_backend(self, hwnd):
        """
        後台視窗複製：優先使用 PrintWindow (flag=3) 以相容 GPU 硬體加速，
        若 PrintWindow 失敗則降階為 BitBlt 複製。若繪製結果為全黑空影像，自動回傳 None 以降階前台截圖。
        """
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            if width <= 0 or height <= 0:
                return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            result = False
            if getattr(self, "_backend_printwindow_supported", True):
                try:
                    result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
                except Exception:
                    self._backend_printwindow_supported = False
                    
            if not result:
                saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
                
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img = img.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
            
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 🛡️ 關鍵防護：若後台擷取出的圖片全為 0 (全黑無效影像)，回傳 None 以自動降階 mss 前台截圖
            if np.all(img_bgr == 0):
                return None
                
            return img_bgr
        except Exception as e:
            logging.debug(f"後台截圖發生錯誤: {e}")
            return None

    def capture(self, rect=None):
        """
        擷取螢幕或指定區域，回傳 OpenCV 格式 (BGR) 影像。
        3 層備援截圖瀑布：後台 PrintWindow/BitBlt 優先 ➔ 前台 mss 備用 ➔ PIL ImageGrab 末線防護。
        """
        hwnd = self.get_hwnd()
        
        # 1. 後台模式優先嘗試 BitBlt/PrintWindow 後台截圖
        if self.backend_mode and hwnd:
            img = self._capture_backend(hwnd)
            if img is not None:
                return img
                
        # 2. 前台 / MSS 螢幕區域截圖 (第二防線)
        if rect is None:
            rect = self.get_window_rect()
            
        try:
            if rect is None:
                logging.info("將擷取主螢幕畫面作為備用方案...")
                monitor = self.sct.monitors[1]
            else:
                monitor = {
                    "left": rect["left"],
                    "top": rect["top"],
                    "width": rect["width"],
                    "height": rect["height"]
                }
            
            self.last_monitor = monitor
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            logging.warning(f"mss 截圖失敗 ({e})，嘗試使用 PIL ImageGrab 作為備用方案...")
            try:
                from PIL import ImageGrab
                if rect is None:
                    img_pil = ImageGrab.grab()
                else:
                    bbox = (
                        rect["left"],
                        rect["top"],
                        rect["left"] + rect["width"],
                        rect["top"] + rect["height"]
                    )
                    img_pil = ImageGrab.grab(bbox=bbox)
                return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            except Exception as e2:
                logging.error(f"備份方案 PIL ImageGrab 擷取亦失敗: {e2}")
                return None
