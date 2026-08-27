import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.mouse import MouseController

class TestMouseCoordinates(unittest.TestCase):
    def setUp(self):
        # 以 callback 注入取代 state_machine 直接倘注 (Issue #11)
        self.on_success_count = [0]
        self.mouse = MouseController(
            on_action_success=lambda: self.on_success_count.__setitem__(0, self.on_success_count[0] + 1),
            is_paused_fn=lambda: False,  # 預設不暂停
        )

    @patch('actions.mouse.win32gui.IsWindow', return_value=True)
    @patch('actions.mouse.win32gui.ClientToScreen')
    def test_screen_to_client(self, mock_client_to_screen, mock_is_window):
        """
        測試螢幕座標轉客戶區相對座標 (Client Coordinates) 轉換。
        """
        # 模擬 ClientToScreen 回傳客戶區在螢幕上的起點 (X=100, Y=200)
        mock_client_to_screen.return_value = (100, 200)
        
        # 傳入絕對螢幕座標 (1100, 700)
        cx, cy = self.mouse._screen_to_client(12345, 1100, 700)
        
        # 預期：1100 - 100 = 1000, 700 - 200 = 500
        self.assertEqual(cx, 1000)
        self.assertEqual(cy, 500)

    @patch('actions.mouse.win32gui.PostMessage')
    @patch('actions.mouse.win32gui.IsWindow', return_value=True)
    @patch('actions.mouse.win32gui.ClientToScreen')
    def test_click_backend_mode_client_coords(self, mock_client_to_screen, mock_is_window, mock_post_message):
        """
        測試在後台模式下發送以 Client 座標為基底的 PostMessage。
        """
        self.mouse.backend_mode = True
        self.mouse.get_hwnd = MagicMock(return_value=12345)
        mock_client_to_screen.return_value = (0, 0)
        
        # 點擊 (500, 300)，偏移 range=(0, 0)
        success = self.mouse.click(500, 300, offset_range=(0, 0))
        self.assertTrue(success)
        self.assertTrue(mock_post_message.called)

    @patch('actions.mouse.pyautogui.mouseUp')
    @patch('actions.mouse.pyautogui.mouseDown')
    @patch('actions.mouse.pyautogui.moveTo')
    @patch('actions.mouse.win32gui.IsWindow', return_value=True)
    @patch('actions.mouse.win32gui.ClientToScreen')
    def test_click_foreground_mode_client_to_screen(self, mock_client_to_screen, mock_is_window, mock_move_to, mock_down, mock_up):
        """
        測試在前台模式下透過 ClientToScreen 轉換為實體螢幕座標並點擊。
        """
        self.mouse.backend_mode = False
        self.mouse.get_hwnd = MagicMock(return_value=12345)
        # 模擬 ClientToScreen: (0,0)->(100, 200)，(500, 300)->(600, 500)
        def client_to_screen_side_effect(hwnd, pt):
            return (pt[0] + 100, pt[1] + 200)
        mock_client_to_screen.side_effect = client_to_screen_side_effect
        
        # 點擊 (500, 300)，偏移 range=(0, 0)
        success = self.mouse.click(600, 500, offset_range=(0, 0))
        self.assertTrue(success)
        mock_move_to.assert_any_call(600, 500)
        self.assertTrue(mock_down.called)
        self.assertTrue(mock_up.called)

if __name__ == "__main__":
    unittest.main()
