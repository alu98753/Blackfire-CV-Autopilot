import mss
import numpy as np
import cv2
import logging
import win32gui
import win32api
import win32con
import win32ui
import ctypes
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ScreenCapturer:
    def __init__(self, window_title="Blackfire Crusade", backend_mode=False):
        self.window_title = window_title
        self.backend_mode = backend_mode
        self.sct = mss.MSS()
        self._hwnd = None

    def get_hwnd(self):
        """
        取得或快取遊戲視窗控制代碼 (hwnd)。
        """
        if self._hwnd is None or not win32gui.IsWindow(self._hwnd):
            self._hwnd = win32gui.FindWindow(None, self.window_title)
        return self._hwnd

    def get_window_rect(self):
        """
        取得指定視窗在虛擬螢幕座標系下的絕對位置與大小。
        """
        try:
            hwnd = self.get_hwnd()
            if not hwnd:
                logging.warning(f"找不到視窗標題為 '{self.window_title}' 的視窗。")
                return None
            
            if win32gui.IsIconic(hwnd):
                logging.warning(f"偵測到視窗 '{self.window_title}' 已最小化，請還原視窗以進行截圖。")
                return None

            rect = win32gui.GetWindowRect(hwnd)
            return {
                "left": rect[0],
                "top": rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
                "title": self.window_title
            }
        except Exception as e:
            logging.error(f"取得視窗座標時發生錯誤: {e}")
            return None

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
                
                # 物理左上角與右下角
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

        # Fallback 備份方案：使用子進程獲取
        if hasattr(self, "_cached_phys_rect") and self._cached_phys_rect == phys_rect:
            if hasattr(self, "_cached_log_rect") and self._cached_log_rect is not None:
                return self._cached_log_rect
                
        log_rect = None
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
        利用 Windows API BitBlt 進行後台視窗複製 (第一防線)
        """
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            if width <= 0 or height <= 0:
                return None

            # 輸出視窗與虛擬桌面座標資訊以供診斷
            v_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            v_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            v_w = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            v_h = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            v_right = v_left + v_w
            v_bottom = v_top + v_h
            
            logging.debug(f"📸 [後台截圖] 視窗座標: (left={left}, top={top}, right={right}, bottom={bottom})，尺寸: {width}x{height}")
            # 檢查是否有部分視窗超出整個虛擬桌面邊界，只輸出一次警告以防洗版
            if left < v_left or top < v_top or right > v_right or bottom > v_bottom:
                if not getattr(self, "_boundary_warning_logged", False):
                    logging.warning(f"⚠️ [後台截圖警報] 視窗有部分超出螢幕邊界！(桌面總範圍: {v_left},{v_top} ~ {v_right},{v_bottom})。超出邊界的部分在後台 GDI 截圖中會變成純黑色塊！請將視窗拖回螢幕內。")
                    self._boundary_warning_logged = True
            else:
                self._boundary_warning_logged = False

            # 取得視窗設備上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # 使用 BitBlt 複製
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            # 轉換為 numpy array 格式的 BGR 影像
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 檢查是否為大面積黑畫面 (如 > 50% 黑色)，防範 3D/硬體加速渲染在後台時截出黑底
            black_pixels = np.sum((img_bgr[:, :, 0] == 0) & (img_bgr[:, :, 1] == 0) & (img_bgr[:, :, 2] == 0))
            total_pixels = img_bgr.shape[0] * img_bgr.shape[1]
            
            if (black_pixels / total_pixels) > 0.50:
                logging.debug(f"⚠️ 偵測到後台 BitBlt 截圖呈現大面積黑畫面 ({black_pixels/total_pixels*100:.1f}%)，嘗試使用 PrintWindow (PW_RENDERFULLCONTENT=2) 作為後備後台截圖方案...")
                try:
                    # PW_RENDERFULLCONTENT = 2
                    res = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
                    if res:
                        bmpstr_pw = saveBitMap.GetBitmapBits(True)
                        img_pw = np.frombuffer(bmpstr_pw, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
                        img_bgr_pw = cv2.cvtColor(img_pw, cv2.COLOR_BGRA2BGR)
                        
                        black_pixels_pw = np.sum((img_bgr_pw[:, :, 0] == 0) & (img_bgr_pw[:, :, 1] == 0) & (img_bgr_pw[:, :, 2] == 0))
                        if (black_pixels_pw / total_pixels) < 0.50:
                            logging.debug("✨ PrintWindow 備份後台截圖成功！")
                            img_bgr = img_bgr_pw
                except Exception as e_pw:
                    logging.debug(f"PrintWindow 備份方案執行失敗: {e_pw}")

            # 釋放所有 GDI 資源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            # 再次檢查最終截圖有效性 (若連 PrintWindow 都回傳全黑，回傳 None 以便退回前台截圖)
            if np.all(img_bgr == 0):
                return None
                
            return img_bgr
        except Exception as e:
            logging.debug(f"後台 BitBlt 截圖失敗: {e}")
            return None

    def capture(self, rect=None):
        """
        擷取螢幕或指定區域，回傳 OpenCV 格式 (BGR) 影像。
        """
        hwnd = self.get_hwnd()
        
        # 後台模式優先嘗試 BitBlt 後台截圖 (無遮擋限制)
        if self.backend_mode and hwnd:
            img = self._capture_backend(hwnd)
            if img is not None:
                # 診斷：將 BitBlt 擷取結果存檔 (已註解)
                # try:
                #     cv2.imwrite("debug_bitblt.png", img)
                #     logging.info(f"📸 [後台 BitBlt 截圖成功] 尺寸: {img.shape}，已存檔為 debug_bitblt.png")
                # except Exception:
                #     pass
                return img
                
        # 退回前台 / MSS 跨螢幕絕對座標裁剪 (第二防線)
        if rect is None:
            rect = self.get_window_rect()
            
        try:
            if rect is None:
                logging.info("將擷取主螢幕畫面作為備用方案...")
                monitor = self.sct.monitors[1]
                dpi_factor = 1.0
            else:
                monitor = {
                    "left": rect["left"],
                    "top": rect["top"],
                    "width": rect["width"],
                    "height": rect["height"]
                }
                dpi_factor = 1.0
            
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 診斷：將 MSS 擷取結果存檔 (已註解)
            # try:
            #     cv2.imwrite("debug_mss.png", img_bgr)
            #     logging.info(f"📸 [前台 MSS 截圖成功] 邏輯座標: {monitor}，物理尺寸: {img_bgr.shape}，已存檔為 debug_mss.png")
            # except Exception:
            #     pass
                
            return img_bgr
        except Exception as e:
            logging.warning(f"mss 擷取失敗 ({e})，嘗試使用 PIL ImageGrab 作為備份方案...")
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
                    img_pil = ImageGrab.grab(bbox)
                img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                return img_bgr
            except Exception as e_pil:
                logging.error(f"備份方案 PIL ImageGrab 擷取亦失敗: {e_pil}")
                return None

if __name__ == "__main__":
    # 簡單的測試
    capturer = ScreenCapturer()
    rect = capturer.get_window_rect()
    if rect:
        print(f"找到視窗: {rect['title']} | 座標: ({rect['left']}, {rect['top']}), 大小: {rect['width']}x{rect['height']}")
        img = capturer.capture(rect)
        if img is not None:
            print(f"擷取成功，畫面大小: {img.shape}")
            cv2.imwrite("test_captured.png", img)
            print("測試畫面已儲存至 test_captured.png")
    else:
        print("未找到指定視窗，擷取主螢幕...")
        img = capturer.capture()
        if img is not None:
            cv2.imwrite("test_full_screen.png", img)
            print("測試全螢幕畫面已儲存至 test_full_screen.png")
