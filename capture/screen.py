import logging
import time
import ctypes
import numpy as np
import cv2
import mss
import win32gui
import win32ui
import win32con
from typing import Optional, Tuple, Dict, Any

from config import WINDOW_TITLE
from utils.window import WindowHandle


class ScreenCapturer:
    def __init__(self, window_title=WINDOW_TITLE, backend_mode=False, monitor_index=1, resume_event=None, hwnd=None):
        """
        :param window_title:  遊戲視窗標題，預設讀取 config.WINDOW_TITLE。
        :param backend_mode:  True 時使用後台截圖 (PrintWindow/BitBlt)，False 時使用前台 mss 截圖。
        :param monitor_index: 目標顯示器索引（1-indexed，對應 win32api.EnumDisplayMonitors 回傳順序）。
                              1 = 系統第一台顯示器（筆電主螢幕），2 = 外接第二台，以此類推。
        :param resume_event:  全域通行門閥 (threading.Event)，暫停時於截圖前沿原地定格 (Freeze-in-Place)。
        :param hwnd:          明確指定目標視窗 HWND（多開/雙開時優先鎖定）。
        """
        # 已關閉 DPI Awareness 宣告以符合專案與使用者需求
        self.window_title = window_title
        self.backend_mode = backend_mode
        self.monitor_index = monitor_index
        self._resume_event = resume_event
        self.sct = mss.MSS()
        self._window = WindowHandle(window_title=window_title, hwnd=hwnd)
        self.last_monitor = None
        self._backend_printwindow_supported = True

    def close(self):
        """Release the persistent MSS handle during a controlled shutdown."""
        sct, self.sct = self.sct, None
        if sct is not None:
            try:
                sct.close()
            except Exception as exc:
                logging.debug("[ScreenCapturer] Failed to close MSS handle: %s", exc)

    def _release_backend_resources(self, save_bitmap, save_dc, mfc_dc, hwnd, hwnd_dc):
        """Best-effort cleanup for every Win32 capture path, including errors."""
        if save_bitmap is not None:
            try:
                win32gui.DeleteObject(save_bitmap.GetHandle())
            except Exception:
                pass
        if save_dc is not None:
            try:
                save_dc.DeleteDC()
            except Exception:
                pass
        if mfc_dc is not None:
            try:
                mfc_dc.DeleteDC()
            except Exception:
                pass
        if hwnd_dc is not None:
            try:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
            except Exception:
                pass

    def get_hwnd(self):
        """
        取得遊戲視窗控制代碼 (HWnd)，包含防快取失效重查。
        """
        return self._window.get()

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

            client_pt = win32gui.ClientToScreen(hwnd, (0, 0))
            client_rect = win32gui.GetClientRect(hwnd)
            return {
                "left": client_pt[0],
                "top": client_pt[1],
                "width": client_rect[2],
                "height": client_rect[3],
                "title": self.window_title
            }
        except Exception as e:
            if not quiet:
                logging.error(f"取得視窗座標時發生錯誤: {e}")
            return None

    def ensure_window_on_monitor(self, monitor_index: Optional[int] = None) -> bool:
        """
        將遊戲視窗自動移動並定位到指定的顯示器 (預設 self.monitor_index 筆電螢幕 1)。
        修復邏輯：若視窗處於最大化或最小化狀態，必須先 SW_RESTORE 解除，否則 Windows 禁止 SetWindowPos 跨顯示器移動！
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
            # Early Return 1：無效的 monitor_index（T4-D）
            if not (0 < target_idx <= len(monitors)):
                return False

            mon_rect = self._get_monitor_rect(monitors, target_idx)
            is_on_target, is_zoomed, is_iconic = self._check_window_state(hwnd, mon_rect, target_idx)

            # Early Return 2：已在目標顯示器且已最大化，無需任何操作（T4-A）
            if is_on_target and is_zoomed:
                logging.info(f"✅ [ScreenCapturer] 遊戲視窗已在 Monitor {target_idx} 上且已處於最大化狀態。")
                return True

            logging.info(f"🚚 [ScreenCapturer] 執行跨螢幕傳送至 Monitor {target_idx} ({mon_rect[0]}, {mon_rect[1]})...")

            self._restore_if_needed(hwnd, is_zoomed, is_iconic)    # T4-C
            self._move_to_monitor_if_needed(hwnd, mon_rect, target_idx)  # T4-B 不進此分支
            self._maximize_window(hwnd)
            return self._verify_on_monitor(hwnd, mon_rect, target_idx)

        except Exception as e:
            logging.error(f"❌ 自動移動視窗至 Monitor {target_idx} 失敗: {e}", exc_info=True)
        return False

    # ── ensure_window_on_monitor 私有子方法 ────────────────────────────

    def _get_monitor_rect(self, monitors, target_idx: int) -> Tuple:
        """解析 EnumDisplayMonitors 回傳，取得目標顯示器的 (left, top, right, bottom)。"""
        import win32api
        hmon, _, _ = monitors[target_idx - 1]
        info = win32api.GetMonitorInfo(hmon)
        return info["Monitor"]  # (left, top, right, bottom)

    def _check_window_state(self, hwnd, mon_rect: Tuple, target_idx: int):
        """
        取得視窗目前的位置狀態。
        :return: (is_on_target_mon: bool, is_zoomed: bool, is_iconic: bool)
        """
        mon_l, mon_t, mon_r, mon_b = mon_rect
        w_left, w_top, w_right, w_bottom = win32gui.GetWindowRect(hwnd)
        w_center_x = (w_left + w_right) // 2
        w_center_y = (w_top + w_bottom) // 2
        is_on_target = (mon_l <= w_center_x < mon_r) and (mon_t <= w_center_y < mon_b)
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(hwnd))
        is_iconic = bool(ctypes.windll.user32.IsIconic(hwnd))

        logging.info(
            f"🔍 [ScreenCapturer Debug] 視窗 HWND: {hwnd}, 當前 Rect: ({w_left}, {w_top}, {w_right}, {w_bottom}), "
            f"中心點: ({w_center_x}, {w_center_y}), 已最大化: {is_zoomed} | "
            f"目標 Monitor {target_idx} 範圍: ({mon_l}, {mon_t})~({mon_r}, {mon_b}), 已在目標螢幕: {is_on_target}"
        )
        return is_on_target, is_zoomed, is_iconic

    def _restore_if_needed(self, hwnd, is_zoomed: bool, is_iconic: bool) -> None:
        """若視窗處於最大化或最小化狀態，先 SW_RESTORE 解除，讓 SetWindowPos 可以跨螢幕移動。"""
        if is_zoomed or is_iconic:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

    def _move_to_monitor_if_needed(self, hwnd, mon_rect: Tuple, target_idx: int) -> None:
        """
        重新偵測視窗位置，唯有當視窗「不在目標顯示器上」時，才發起 SetWindowPos 跨螢幕移動。
        避免同一顯示器解最小化時產生 10px 偏移抖動。
        """
        mon_l, mon_t, mon_r, mon_b = mon_rect
        w_left, w_top, w_right, w_bottom = win32gui.GetWindowRect(hwnd)
        w_center_x = (w_left + w_right) // 2
        w_center_y = (w_top + w_bottom) // 2
        is_still_off = not ((mon_l <= w_center_x < mon_r) and (mon_t <= w_center_y < mon_b))

        if is_still_off:
            logging.info(f"🚚 [ScreenCapturer] 視窗不在 Monitor {target_idx}，執行 SetWindowPos 跨螢幕移動...")
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                mon_l + 10,
                mon_t + 10,
                0,
                0,
                win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            time.sleep(0.1)

    def _maximize_window(self, hwnd) -> None:
        """搶佔前景焦點並 SW_SHOWMAXIMIZED；雙重護欄：若未即時生效，補發 SC_MAXIMIZE。"""
        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        time.sleep(0.15)

        # 雙重護欄：若仍未處於 IsZoomed 狀態，對 HWND 發送標題列最大化按鈕訊息
        if not bool(ctypes.windll.user32.IsZoomed(hwnd)):
            logging.info("🔄 [ScreenCapturer] SW_SHOWMAXIMIZED 未即時生效，對視窗發送 SC_MAXIMIZE 強制最大化...")
            win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MAXIMIZE, 0)
            time.sleep(0.2)

    def _verify_on_monitor(self, hwnd, mon_rect: Tuple, target_idx: int) -> bool:
        """驗證移動結果，回傳視窗是否成功抵達目標顯示器。"""
        mon_l, mon_t, mon_r, mon_b = mon_rect
        new_rect = win32gui.GetWindowRect(hwnd)
        new_cx = (new_rect[0] + new_rect[2]) // 2
        new_cy = (new_rect[1] + new_rect[3]) // 2
        success = (mon_l <= new_cx < mon_r) and (mon_t <= new_cy < mon_b)
        logging.info(
            f"🎉 [ScreenCapturer] 視窗傳送結果: 新 Rect: {new_rect}, 新中心: ({new_cx}, {new_cy}), "
            f"是否成功到達 Monitor {target_idx}: {success}"
        )
        return success



    def _capture_backend(self, hwnd):
        """
        後台視窗複製：優先使用 PrintWindow (flag=3) 以相容 GPU 硬體加速，
        若 PrintWindow 失敗則降階為 BitBlt 複製。若繪製結果為全黑空影像，自動回傳 None 以降階前台截圖。
        """
        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        try:
            client_rect = win32gui.GetClientRect(hwnd)
            width = client_rect[2]
            height = client_rect[3]
            
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
            
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 🛡️ 關鍵防護：若後台擷取出的圖片全為 0 (全黑無效影像)，回傳 None 以自動降階 mss 前台截圖
            if np.all(img_bgr == 0):
                return None
                
            return img_bgr
        except Exception as e:
            logging.debug(f"後台截圖發生錯誤: {e}")
            return None
        finally:
            self._release_backend_resources(saveBitMap, saveDC, mfcDC, hwnd, hwndDC)

    def capture(self, rect=None, full_screen: bool = False):
        """
        擷取螢幕或指定區域，回傳 OpenCV 格式 (BGR) 影像。
        3 層備援截圖瀑布：後台 PrintWindow/BitBlt 優先 ➔ 前台 mss 備用 ➔ PIL ImageGrab 末線防護。
        """
        if getattr(self, "_resume_event", None) is not None:
            self._resume_event.wait()

        if full_screen:
            rect = None

        hwnd = self.get_hwnd()
        
        # 1. 後台模式優先嘗試 BitBlt/PrintWindow 後台截圖 (全螢幕模式除外)
        if self.backend_mode and hwnd and not full_screen:
            img = self._capture_backend(hwnd)
            if img is not None:
                return img
                
        # 2. 前台 / MSS 螢幕區域截圖 (第二防線)
        if rect is None and not full_screen:
            rect = self.get_window_rect()

        if self.sct is None:
            logging.error("[ScreenCapturer] Capture requested after MSS handle was closed.")
            return None

        try:
            if rect is None or full_screen:
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
