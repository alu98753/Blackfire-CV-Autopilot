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
        :param window_title:  ?閬?璅?嚗?閮剛???config.WINDOW_TITLE??        :param backend_mode:  True ?蝙?典??唳??(PrintWindow/BitBlt)嚗alse ?蝙?典???mss ?芸???        :param monitor_index: ?格?憿舐內?函揣撘?1-indexed嚗???win32api.EnumDisplayMonitors ???嚗?                              1 = 蝟餌絞蝚砌??圈＊蝷箏嚗??颱蜓?Ｗ?嚗?2 = 憭蝚砌??堆?隞交迨憿??        :param resume_event:  ?典??????(threading.Event)嚗???潭??瘝踹??啣???(Freeze-in-Place)??        :param hwnd:          ?Ⅱ???格?閬? HWND嚗????????摰???        """
        # 撌脤???DPI Awareness 摰??隞亦泵??獢?雿輻??瘙?        self.window_title = window_title
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
        ???閬??批隞?Ⅳ (HWnd)嚗??恍敹怠?憭望????        """
        return self._window.get()

    def get_window_rect(self, quiet: bool = False):
        """
        ????閬??刻??祈撟漣璅頂銝?蝯?雿蔭?之撠?        """
        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                if not quiet:
                    logging.warning(f"?曆??啗?蝒?憿 '{self.window_title}' ??蝒?)
                return None
            
            if win32gui.IsIconic(hwnd):
                if not quiet:
                    logging.info(f"?? ?菜葫?啗?蝒?'{self.window_title}' 鋡急?撠?嚗?韏?ensure_window_on_monitor ??銝衣蔭??憭批?...")
                self.ensure_window_on_monitor()
                if win32gui.IsIconic(hwnd):
                    if not quiet:
                        logging.warning(f"?? ?岫?芸????撠?閬? '{self.window_title}' 憭望???)
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
                logging.error(f"??閬?摨扳???隤? {e}")
            return None

    def ensure_window_on_monitor(self, monitor_index: Optional[int] = None) -> bool:
        """
        撠??脰?蝒?宏?蒂摰??唳?摰?憿舐內??(?身 self.monitor_index 蝑?Ｗ? 1)??        靽桀儔?摩嚗閬???憭批???撠????敹???SW_RESTORE 閫?嚗??Windows 蝳迫 SetWindowPos 頝券＊蝷箏蝘餃?嚗?        蝘餃?敺?隤輻 SW_MAXIMIZE ?函璅＊蝷箏銝?憭批??刻撟?        """
        target_idx = monitor_index if monitor_index is not None else self.monitor_index
        if target_idx is None:
            return False

        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                logging.warning(f"?? [ScreenCapturer] ensure_window_on_monitor ?曆??唳?憿 '{self.window_title}' ??蝒?)
                return False

            import win32api
            monitors = win32api.EnumDisplayMonitors(None, None)
            # Early Return 1嚗?? monitor_index嚗4-D嚗?            if not (0 < target_idx <= len(monitors)):
                return False

            mon_rect = self._get_monitor_rect(monitors, target_idx)
            is_on_target, is_zoomed, is_iconic = self._check_window_state(hwnd, mon_rect, target_idx)

            # Early Return 2嚗歇?函璅＊蝷箏銝歇?憭批?嚗?隞颱???嚗4-A嚗?            if is_on_target and is_zoomed:
                logging.info(f"??[ScreenCapturer] ?閬?撌脣 Monitor {target_idx} 銝?撌脰??潭?憭批????)
                return True

            logging.info(f"?? [ScreenCapturer] ?瑁?頝刻撟? Monitor {target_idx} ({mon_rect[0]}, {mon_rect[1]})...")

            self._restore_if_needed(hwnd, is_zoomed, is_iconic)    # T4-C
            self._move_to_monitor_if_needed(hwnd, mon_rect, target_idx)  # T4-B 銝脫迨?
            self._maximize_window(hwnd)
            return self._verify_on_monitor(hwnd, mon_rect, target_idx)

        except Exception as e:
            logging.error(f"???芸?蝘餃?閬???Monitor {target_idx} 憭望?: {e}", exc_info=True)
        return False

    # ?? ensure_window_on_monitor 蝘?摮瘜?????????????????????????????

    def _get_monitor_rect(self, monitors, target_idx: int) -> Tuple:
        """閫?? EnumDisplayMonitors ?嚗?敺璅＊蝷箏??(left, top, right, bottom)??""
        import win32api
        hmon, _, _ = monitors[target_idx - 1]
        info = win32api.GetMonitorInfo(hmon)
        return info["Monitor"]  # (left, top, right, bottom)

    def _check_window_state(self, hwnd, mon_rect: Tuple, target_idx: int):
        """
        ??閬??桀???蝵桃???        :return: (is_on_target_mon: bool, is_zoomed: bool, is_iconic: bool)
        """
        mon_l, mon_t, mon_r, mon_b = mon_rect
        w_left, w_top, w_right, w_bottom = win32gui.GetWindowRect(hwnd)
        w_center_x = (w_left + w_right) // 2
        w_center_y = (w_top + w_bottom) // 2
        is_on_target = (mon_l <= w_center_x < mon_r) and (mon_t <= w_center_y < mon_b)
        is_zoomed = bool(ctypes.windll.user32.IsZoomed(hwnd))
        is_iconic = bool(ctypes.windll.user32.IsIconic(hwnd))

        logging.info(
            f"?? [ScreenCapturer Debug] 閬? HWND: {hwnd}, ?嗅? Rect: ({w_left}, {w_top}, {w_right}, {w_bottom}), "
            f"銝剖?暺? ({w_center_x}, {w_center_y}), 撌脫?憭批?: {is_zoomed} | "
            f"?格? Monitor {target_idx} 蝭?: ({mon_l}, {mon_t})~({mon_r}, {mon_b}), 撌脣?格??Ｗ?: {is_on_target}"
        )
        return is_on_target, is_zoomed, is_iconic

    def _restore_if_needed(self, hwnd, is_zoomed: bool, is_iconic: bool) -> None:
        """?亥?蝒??潭?憭批???撠??????SW_RESTORE 閫?嚗? SetWindowPos ?臭誑頝刻撟宏??""
        if is_zoomed or is_iconic:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

    def _move_to_monitor_if_needed(self, hwnd, mon_rect: Tuple, target_idx: int) -> None:
        """
        ??菜葫閬?雿蔭嚗?閬????函璅＊蝷箏銝?嚗??潸絲 SetWindowPos 頝刻撟宏??        ?踹???憿舐內?刻圾?撠????10px ?宏????        """
        mon_l, mon_t, mon_r, mon_b = mon_rect
        w_left, w_top, w_right, w_bottom = win32gui.GetWindowRect(hwnd)
        w_center_x = (w_left + w_right) // 2
        w_center_y = (w_top + w_bottom) // 2
        is_still_off = not ((mon_l <= w_center_x < mon_r) and (mon_t <= w_center_y < mon_b))

        if is_still_off:
            logging.info(f"?? [ScreenCapturer] 閬?銝 Monitor {target_idx}嚗銵?SetWindowPos 頝刻撟宏??..")
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
        """?嗡???阡?銝?SW_SHOWMAXIMIZED嚗??風甈??交?單???嚗???SC_MAXIMIZE??""
        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        time.sleep(0.15)

        # ??霅瑟?嚗隞? IsZoomed ???撠?HWND ?潮?憿??憭批???閮
        if not bool(ctypes.windll.user32.IsZoomed(hwnd)):
            logging.info("?? [ScreenCapturer] SW_SHOWMAXIMIZED ?芸????撠?蝒??SC_MAXIMIZE 撘瑕?憭批?...")
            win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MAXIMIZE, 0)
            time.sleep(0.2)

    def _verify_on_monitor(self, hwnd, mon_rect: Tuple, target_idx: int) -> bool:
        """撽?蝘餃?蝯?嚗??唾?蝒?行???璅＊蝷箏??""
        mon_l, mon_t, mon_r, mon_b = mon_rect
        new_rect = win32gui.GetWindowRect(hwnd)
        new_cx = (new_rect[0] + new_rect[2]) // 2
        new_cy = (new_rect[1] + new_rect[3]) // 2
        success = (mon_l <= new_cx < mon_r) and (mon_t <= new_cy < mon_b)
        logging.info(
            f"?? [ScreenCapturer] 閬??喲??? ??Rect: {new_rect}, ?唬葉敹? ({new_cx}, {new_cy}), "
            f"?臬???圈? Monitor {target_idx}: {success}"
        )
        return success



    def _capture_backend(self, hwnd):
        """
        敺閬?銴ˊ嚗?蝙??PrintWindow (flag=3) 隞亦摰?GPU 蝖祇???
        ??PrintWindow 憭望???? BitBlt 銴ˊ?蝜芾ˊ蝯??箏暺征敶勗?嚗????None 隞仿????唳??        """
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
            
            # ?儭???脰風嚗敺?瑕??箇????函 0 (?券??⊥?敶勗?)嚗???None 隞亥????mss ??芸?
            if np.all(img_bgr == 0):
                return None
                
            return img_bgr
        except Exception as e:
            logging.debug(f"敺?芸??潛??航炊: {e}")
            return None
        finally:
            self._release_backend_resources(saveBitMap, saveDC, mfcDC, hwnd, hwndDC)

    def capture(self, rect=None, full_screen: bool = False):
        """Capture BGR data with the selected runtime I/O mode.

        Backend mode uses only the backend HWND path and fails closed for missing
        or invalid HWNDs, backend failures, and unsupported full-screen capture.
        Foreground mode uses MSS with PIL fallback.
        """
        if getattr(self, "_resume_event", None) is not None:
            self._resume_event.wait()

        if full_screen:
            rect = None

        hwnd = self.get_hwnd()
        
        # 1. 敺璅∪??芸??岫 BitBlt/PrintWindow 敺?芸? (?刻撟芋撘憭?
        if self.backend_mode:
            if full_screen:
                logging.error("[ScreenCapturer] Backend mode does not support full-screen capture; refusing foreground fallback.")
                return None
            if not isinstance(hwnd, int) or hwnd <= 0:
                logging.error("[ScreenCapturer] Backend capture requires a valid HWND; refusing foreground fallback.")
                return None
            img = self._capture_backend(hwnd)
            if img is not None:
                return img
            logging.error("[ScreenCapturer] Backend capture failed; refusing foreground fallback.")
            return None
                
        # 2. ? / MSS ?Ｗ?????(蝚砌??脩?)
        if rect is None and not full_screen:
            rect = self.get_window_rect()

        if self.sct is None:
            logging.error("[ScreenCapturer] Capture requested after MSS handle was closed.")
            return None

        try:
            if rect is None or full_screen:
                logging.info("撠?蜓?Ｗ??恍雿??寞?...")
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
            logging.warning(f"mss ?芸?憭望? ({e})嚗?閰虫蝙??PIL ImageGrab 雿??寞?...")
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
                logging.error(f"?遢?寞? PIL ImageGrab ?瑕?鈭血仃?? {e2}")
                return None
