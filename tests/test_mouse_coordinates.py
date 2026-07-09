import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.mouse import MouseController

class TestMouseCoordinates(unittest.TestCase):
    def setUp(self):
        # 建立 Mock 的 state_machine
        self.mock_state_machine = MagicMock()
        self.mouse = MouseController()
        self.mouse.state_machine = self.mock_state_machine
        
    @patch('actions.mouse.win32gui.ClientToScreen')
    @patch('actions.mouse.ctypes.windll.user32.GetDpiForWindow')
    def test_phys_to_logical_100_percent_dpi(self, mock_get_dpi, mock_client_to_screen):
        """
        測試在大螢幕 (100% DPI 縮放) 下的物理到邏輯座標轉換。
        """
        # 模擬 GetDpiForWindow 回傳 96 (100% DPI)
        mock_get_dpi.return_value = 96
        
        # 模擬 ClientToScreen 回傳客戶區起點 (X=9, Y=38)
        # 假設視窗外框左上角為 (0, 0)
        mock_client_to_screen.return_value = (9, 38)
        
        # 模擬視窗物理外框 Rect
        rect = (0, 0, 1550, 830)
        
        # 輸入物理座標 (比如匹配到的按鈕中心)
        phys_x = 1000
        phys_y = 500
        
        lx, ly, factor = self.mouse._phys_to_logical(None, rect, phys_x, phys_y)
        
        # 預期：
        # border_left = 9 - 0 = 9
        # border_top = 38 - 0 = 38
        # lx = phys_x - border_left = 1000 - 9 = 991
        # ly = phys_y - border_top = 500 - 38 = 462
        self.assertEqual(factor, 1.0)
        self.assertEqual(lx, 991)
        self.assertEqual(ly, 462)

    @patch('actions.mouse.win32gui.ClientToScreen')
    @patch('actions.mouse.ctypes.windll.user32.GetDpiForWindow')
    def test_phys_to_logical_125_percent_dpi(self, mock_get_dpi, mock_client_to_screen):
        """
        測試在筆電螢幕 (125% DPI 縮放) 下的物理到邏輯座標轉換。
        """
        # 模擬 GetDpiForWindow 回傳 120 (125% DPI)
        mock_get_dpi.return_value = 120
        
        # 模擬 ClientToScreen 回傳客戶區起點 (X=9, Y=38)
        mock_client_to_screen.return_value = (9, 38)
        
        # 模擬視窗物理外框 Rect
        rect = (0, 0, 1938, 1038)
        
        phys_x = 1105
        phys_y = 899
        
        lx, ly, factor = self.mouse._phys_to_logical(None, rect, phys_x, phys_y)
        
        # 預期：
        # border_left = 9
        # border_top = 38
        # lx = 1105 - 9 = 1096
        # ly = 899 - 38 = 861
        self.assertEqual(factor, 1.25)
        self.assertEqual(lx, 1096)
        self.assertEqual(ly, 861)

if __name__ == "__main__":
    unittest.main()
