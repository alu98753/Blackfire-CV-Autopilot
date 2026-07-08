import mss
import numpy as np
import cv2
import logging
import win32gui
import win32api
import win32con
import win32ui

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ScreenCapturer:
    def __init__(self, window_title="Blackfire Crusade", backend_mode=False):
        self.window_title = window_title
        self.backend_mode = backend_mode
        self.sct = mss.mss()
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

            # 取得視窗設備上下文
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # 使用 BitBlt 複製
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCOPY)
            
            # 轉換為 numpy array 格式的 BGR 影像
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
            
            # 釋放所有 GDI 資源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            # 去除 Alpha Channel 轉為 BGR
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 檢查截圖有效性 (防範某些 3D/硬體加速渲染在後台時截出全黑畫面)
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
                # 取得當前視窗所在螢幕的 DPI 因子
                dpi_factor = 1.0
                if hwnd:
                    try:
                        import ctypes
                        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                        dpi_factor = dpi / 96.0
                    except Exception:
                        pass
                
                # 將物理 rect 轉換為 mss 庫底層所需的邏輯座標
                monitor = {
                    "left": int(rect["left"] / dpi_factor),
                    "top": int(rect["top"] / dpi_factor),
                    "width": int(rect["width"] / dpi_factor),
                    "height": int(rect["height"] / dpi_factor)
                }
            
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 如果有縮放，將截圖重新縮放回物理尺寸，確保寬高和物理像素精確重合
            if rect is not None and abs(dpi_factor - 1.0) > 0.01:
                img_bgr = cv2.resize(img_bgr, (rect["width"], rect["height"]), interpolation=cv2.INTER_LINEAR)
                
            return img_bgr
        except Exception as e:
            logging.warning(f"mss 擷取失敗 ({e})，嘗試使用 PIL ImageGrab 作為備份方案...")
            try:
                from PIL import ImageGrab
                if rect is None:
                    img_pil = ImageGrab.grab()
                else:
                    bbox = (
                        int(rect["left"] / dpi_factor),
                        int(rect["top"] / dpi_factor),
                        int((rect["left"] + rect["width"]) / dpi_factor),
                        int((rect["top"] + rect["height"]) / dpi_factor)
                    )
                    img_pil = ImageGrab.grab(bbox)
                img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                
                if rect is not None and abs(dpi_factor - 1.0) > 0.01:
                    img_bgr = cv2.resize(img_bgr, (rect["width"], rect["height"]), interpolation=cv2.INTER_LINEAR)
                    
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
