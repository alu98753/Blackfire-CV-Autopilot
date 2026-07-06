import mss
import numpy as np
import cv2
import pygetwindow as gw
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ScreenCapturer:
    def __init__(self, window_title="Blackfire Crusade"):
        self.window_title = window_title
        self.sct = mss.mss()

    def get_window_rect(self):
        """
        取得指定視窗的座標與大小。
        """
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                logging.warning(f"找不到視窗標題含有 '{self.window_title}' 的視窗。")
                return None
            
            # 尋找精確匹配或第一個匹配且長度大於 0 的視窗
            target_win = None
            for w in windows:
                if w.title == self.window_title:
                    target_win = w
                    break
            if not target_win:
                target_win = windows[0]

            if target_win.isMinimized:
                logging.warning(f"偵測到視窗 '{target_win.title}' 已最小化，請還原視窗以進行截圖。")
                return None

            return {
                "left": target_win.left,
                "top": target_win.top,
                "width": target_win.width,
                "height": target_win.height,
                "title": target_win.title
            }
        except Exception as e:
            logging.error(f"取得視窗座標時發生錯誤: {e}")
            return None

    def capture(self, rect=None):
        """
        擷取螢幕或指定區域，回傳 OpenCV 格式 (BGR) 影像。
        """
        if rect is None:
            # 預設嘗試擷取遊戲視窗
            rect = self.get_window_rect()
            
        try:
            if rect is None:
                # 找不到視窗時的備案：擷取主螢幕
                logging.info("將擷取主螢幕畫面作為備用方案...")
                monitor = self.sct.monitors[1]  # 1 代表主螢幕
            else:
                monitor = {
                    "left": rect["left"],
                    "top": rect["top"],
                    "width": rect["width"],
                    "height": rect["height"]
                }
            
            # 擷取畫面
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img_bgr
        except Exception as e:
            logging.warning(f"mss 擷取失敗 ({e})，嘗試使用 PIL ImageGrab 作為備份方案...")
            try:
                from PIL import ImageGrab
                if rect is None:
                    img_pil = ImageGrab.grab()
                else:
                    # PIL.ImageGrab.grab 接收 (left, top, right, bottom)
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
