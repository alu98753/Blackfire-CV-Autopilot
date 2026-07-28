import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import os
import sys

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.screen import ScreenCapturer


class TestScreenCapturerArchitecture(unittest.TestCase):
    """
    ScreenCapturer 4 大核心架構單元測試套件：
    1. get_window_rect: IsZoomed + ClientToScreen 客戶區座標精準對齊
    2. ensure_window_on_monitor: 跨螢幕 3 步驟傳送與最大化全螢幕
    3. capture / _capture_backend: 3 層備援截圖瀑布 (後台 BitBlt ➔ 前台 mss ➔ PIL 末線)
    4. 乾淨架構：確保 API 簡潔穩定，無冗餘 full_screen / GDI 重複分支
    """

    def setUp(self):
        self.capturer = ScreenCapturer(window_title="Blackfire Crusade", backend_mode=True)
        self.fake_bgr = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.fake_bgr[10:20, 10:20] = 255  # 非全黑測試影像

    @patch("win32gui.GetClientRect")
    @patch("win32gui.ClientToScreen")
    @patch("win32gui.FindWindow")
    def test_1_get_window_rect_client_to_screen_alignment(
        self, mock_find_window, mock_client_to_screen, mock_get_client_rect
    ):
        """
        測試 1：當視窗最大化 (IsZoomed == True) 時，get_window_rect 是否使用 ClientToScreen 消除 -8px 邊界
        """
        mock_find_window.return_value = 123456
        mock_client_to_screen.return_value = (0, 0)
        mock_get_client_rect.return_value = (0, 0, 1920, 1080)

        with patch("ctypes.windll.user32.IsZoomed", return_value=True):
            rect = self.capturer.get_window_rect()

            self.assertIsNotNone(rect)
            self.assertEqual(rect["left"], 0)
            self.assertEqual(rect["top"], 0)
            self.assertEqual(rect["width"], 1920)
            self.assertEqual(rect["height"], 1080)
            mock_client_to_screen.assert_called_once_with(123456, (0, 0))

    @patch("win32gui.ShowWindow")
    @patch("win32gui.SetWindowPos")
    @patch("win32gui.GetWindowRect")
    @patch("win32api.GetMonitorInfo")
    @patch("win32api.EnumDisplayMonitors")
    @patch("capture.screen.ScreenCapturer.get_hwnd")
    def test_2_ensure_window_on_monitor_3step_transition(
        self, mock_get_hwnd, mock_enum_monitors, mock_get_mon_info, mock_get_win_rect, mock_set_pos, mock_show_win
    ):
        """
        測試 2：ensure_window_on_monitor 是否成功執行 SW_RESTORE ➔ SetWindowPos ➔ SW_MAXIMIZE 3 步驟傳送
        """
        mock_get_hwnd.return_value = 123456
        mock_enum_monitors.return_value = [("hmon1", None, None)]
        mock_get_mon_info.return_value = {"Monitor": (1, 1080, 1921, 2160), "Device": r"\\.\DISPLAY1"}
        # 模擬移動前在 (0, 0)，移動後抵達目標螢幕 (1, 1080)
        mock_get_win_rect.side_effect = [(0, 0, 1280, 720), (1, 1080, 1921, 2160)]

        with patch("ctypes.windll.user32.IsZoomed", return_value=False), \
             patch("ctypes.windll.user32.IsIconic", return_value=False):
            res = self.capturer.ensure_window_on_monitor(monitor_index=1)

            self.assertTrue(res)
            mock_set_pos.assert_called_once()
            self.assertTrue(mock_show_win.called)

    @patch.object(ScreenCapturer, "_capture_backend")
    @patch.object(ScreenCapturer, "get_hwnd")
    def test_3_capture_tier1_backend_bitblt_priority(self, mock_get_hwnd, mock_capture_backend):
        """
        測試 3.1：後台模式 (backend_mode=True) 下，優先嘗試 Tier 1 後台 BitBlt 截圖
        """
        mock_get_hwnd.return_value = 123456
        mock_capture_backend.return_value = self.fake_bgr
        self.capturer.backend_mode = True

        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        img = self.capturer.capture(rect)

        self.assertIsNotNone(img)
        mock_capture_backend.assert_called_once_with(123456)

    @patch("capture.screen.np.array")
    @patch.object(ScreenCapturer, "_capture_backend", return_value=None)
    @patch.object(ScreenCapturer, "get_hwnd", return_value=123456)
    def test_3_capture_tier2_mss_foreground_fallback(self, mock_get_hwnd, mock_backend, mock_np_array):
        """
        測試 3.2：若後台截圖回傳 None，自動降階至 Tier 2 前台 mss 擷取
        """
        self.capturer.backend_mode = True
        fake_bgra = np.zeros((1080, 1920, 4), dtype=np.uint8)
        self.capturer.sct.grab = MagicMock(return_value=fake_bgra)
        mock_np_array.return_value = fake_bgra

        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        img = self.capturer.capture(rect)

        self.assertIsNotNone(img)
        self.capturer.sct.grab.assert_called_once()

    @patch("PIL.ImageGrab.grab")
    @patch.object(ScreenCapturer, "_capture_backend", return_value=None)
    @patch.object(ScreenCapturer, "get_hwnd", return_value=123456)
    def test_3_capture_tier3_pil_imagegrab_final_fallback(self, mock_get_hwnd, mock_backend, mock_pil_grab):
        """
        測試 3.3：若 mss 拋出 Exception 異常，自動降階至 Tier 3 PIL ImageGrab 末線防護
        """
        self.capturer.backend_mode = False
        self.capturer.sct.grab = MagicMock(side_effect=Exception("MSS grab error"))

        fake_pil = MagicMock()
        fake_pil_array = np.zeros((1080, 1920, 3), dtype=np.uint8)
        mock_pil_grab.return_value = fake_pil

        with patch("capture.screen.np.array", return_value=fake_pil_array):
            rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
            img = self.capturer.capture(rect)

            self.assertIsNotNone(img)
            mock_pil_grab.assert_called_once()


if __name__ == "__main__":
    unittest.main()
