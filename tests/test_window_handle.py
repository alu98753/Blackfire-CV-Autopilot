import unittest
from unittest.mock import patch

from utils.window import WindowHandle


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
