import unittest
from unittest.mock import patch

from utils.window import WindowHandle, select_game_window


class TestWindowHandle(unittest.TestCase):
    @patch("utils.window.win32gui.IsWindow", return_value=True)
    @patch("utils.window.win32gui.FindWindow", return_value=12345)
    def test_get_reuses_valid_cached_handle(self, mock_find_window, _mock_is_window):
        handle = WindowHandle("Test Game")

        self.assertEqual(handle.get(), 12345)
        self.assertEqual(handle.get(), 12345)
        mock_find_window.assert_called_once_with(None, "Test Game")

    @patch("utils.window.win32gui.IsWindow", return_value=False)
    @patch("utils.window.win32gui.FindWindow", side_effect=[12345, 67890])
    def test_get_refreshes_invalid_handle_with_same_title(self, mock_find_window, _mock_is_window):
        handle = WindowHandle("Test Game")

        self.assertEqual(handle.get(), 12345)
        self.assertEqual(handle.get(), 67890)
        self.assertEqual(mock_find_window.call_args_list[1].args, (None, "Test Game"))

    @patch("utils.window.win32gui.IsWindow", return_value=True)
    def test_get_with_explicit_valid_hwnd(self, _mock_is_window):
        handle = WindowHandle("Test Game", hwnd=0xABCDE)
        self.assertEqual(handle.get(), 0xABCDE)

    @patch("utils.window.win32gui.IsWindow", side_effect=[False, True])
    @patch("utils.window.win32gui.FindWindow", return_value=0x99999)
    def test_get_with_invalid_explicit_hwnd_falls_back_to_title(self, mock_find_window, _mock_is_window):
        handle = WindowHandle("Test Game", hwnd=0xABCDE)
        self.assertEqual(handle.get(), 0x99999)
        mock_find_window.assert_called_once_with(None, "Test Game")


class TestSelectGameWindow(unittest.TestCase):
    def setUp(self):
        self.mock_windows = [
            {"hwnd": 0x1111, "pid": 1001, "title": "Blackfire Crusade", "width": 1920, "height": 1080, "is_sandbox": False},
            {"hwnd": 0x2222, "pid": 1002, "title": "[#] Blackfire Crusade [#]", "width": 1920, "height": 1080, "is_sandbox": True},
        ]

    @patch("utils.window.find_all_game_windows", return_value=[])
    def test_select_window_none_found(self, _mock_find):
        hwnd, title = select_game_window()
        self.assertIsNone(hwnd)
        self.assertEqual(title, "Blackfire Crusade")

    @patch("utils.window.find_all_game_windows")
    def test_select_window_single_found(self, mock_find):
        mock_find.return_value = [self.mock_windows[0]]
        hwnd, title = select_game_window()
        self.assertEqual(hwnd, 0x1111)
        self.assertEqual(title, "Blackfire Crusade")

    @patch("utils.window.find_all_game_windows")
    def test_select_window_target_sandbox(self, mock_find):
        mock_find.return_value = self.mock_windows
        hwnd, title = select_game_window(target="sandbox")
        self.assertEqual(hwnd, 0x2222)
        self.assertEqual(title, "[#] Blackfire Crusade [#]")

    @patch("utils.window.find_all_game_windows")
    def test_select_window_target_native(self, mock_find):
        mock_find.return_value = self.mock_windows
        hwnd, title = select_game_window(target="native")
        self.assertEqual(hwnd, 0x1111)
        self.assertEqual(title, "Blackfire Crusade")

    @patch("utils.window.find_all_game_windows")
    def test_select_window_target_index(self, mock_find):
        mock_find.return_value = self.mock_windows
        hwnd, title = select_game_window(target="2")
        self.assertEqual(hwnd, 0x2222)

    @patch("utils.window.find_all_game_windows")
    def test_select_window_target_hex_hwnd(self, mock_find):
        mock_find.return_value = self.mock_windows
        hwnd, title = select_game_window(target="0x2222")
        self.assertEqual(hwnd, 0x2222)
        self.assertEqual(title, "[#] Blackfire Crusade [#]")

    @patch("builtins.input", return_value="2")
    @patch("utils.window.find_all_game_windows")
    def test_select_window_interactive_prompt(self, mock_find, _mock_input):
        mock_find.return_value = self.mock_windows
        hwnd, title = select_game_window(auto_prompt=True)
        self.assertEqual(hwnd, 0x2222)
        self.assertEqual(title, "[#] Blackfire Crusade [#]")
