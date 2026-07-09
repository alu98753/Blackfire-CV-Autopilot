import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import ctypes

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.screen import ScreenCapturer

class TestCaptureLogic(unittest.TestCase):
    def setUp(self):
        self.capturer = ScreenCapturer(window_title="Blackfire Crusade")
        
        # 手動 Mock ctypes DLL 函數以避開動態加載屬性無法 patch 的問題
        self.original_api = getattr(ctypes.windll.user32, 'PhysicalToLogicalPointForWindow', None)
        self.mock_phys_to_log = MagicMock()
        ctypes.windll.user32.PhysicalToLogicalPointForWindow = self.mock_phys_to_log

    def tearDown(self):
        # 還原 DLL 狀態
        if self.original_api is not None:
            ctypes.windll.user32.PhysicalToLogicalPointForWindow = self.original_api
        else:
            try:
                delattr(ctypes.windll.user32, 'PhysicalToLogicalPointForWindow')
            except AttributeError:
                pass

    @patch('capture.screen.win32gui.FindWindow')
    def test_get_logical_window_rect_success(self, mock_find_window):
        """
        測試當 Windows PhysicalToLogicalPointForWindow API 成功時的座標轉換。
        """
        mock_find_window.return_value = 12345
        
        # 模擬 PhysicalToLogicalPointForWindow 修改傳入的 POINT 結構
        # 第一次呼叫 (tl) 將 POINT 改為 (0, 0)
        # 第二次呼叫 (br) 將 POINT 改為 (1550, 830)
        def side_effect(hwnd, pt_ref):
            pt = pt_ref._obj
            if pt.x == -8 and pt.y == 1071:
                pt.x = 0
                pt.y = 0
            elif pt.x == 1930 and pt.y == 2109:
                pt.x = 1550
                pt.y = 830
            return True
            
        self.mock_phys_to_log.side_effect = side_effect
        
        phys_rect = {
            "left": -8,
            "top": 1071,
            "width": 1938,
            "height": 1038
        }
        
        log_rect = self.capturer.get_logical_window_rect(phys_rect)
        
        self.assertIsNotNone(log_rect)
        self.assertEqual(log_rect["left"], 0)
        self.assertEqual(log_rect["top"], 0)
        self.assertEqual(log_rect["width"], 1550)
        self.assertEqual(log_rect["height"], 830)

    @patch('capture.screen.win32gui.FindWindow')
    @patch('capture.screen.subprocess.check_output')
    def test_get_logical_window_rect_fallback(self, mock_subprocess, mock_find_window):
        """
        測試當 API 失敗時，退回到子進程 Fallback 的方案。
        """
        mock_find_window.return_value = 12345
        # API 回傳 0 代表失敗
        self.mock_phys_to_log.return_value = 0
        
        # 模擬子進程回傳的 stdout (以 DPI Unaware 執行 win32gui.GetWindowRect)
        mock_subprocess.return_value = b"(0, 0, 1550, 830)\n"
        
        phys_rect = {
            "left": -8,
            "top": 1071,
            "width": 1938,
            "height": 1038
        }
        
        log_rect = self.capturer.get_logical_window_rect(phys_rect)
        
        self.assertIsNotNone(log_rect)
        self.assertEqual(log_rect["left"], 0)
        self.assertEqual(log_rect["top"], 0)
        self.assertEqual(log_rect["width"], 1550)
        self.assertEqual(log_rect["height"], 830)

if __name__ == "__main__":
    unittest.main()
