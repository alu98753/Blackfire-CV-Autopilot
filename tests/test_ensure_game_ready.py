import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from utils.steam_launcher import SteamGameLauncher


class TestEnsureGameReady(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_matcher = MagicMock()
        self.launcher = SteamGameLauncher(
            capturer=self.mock_capturer,
            mouse=self.mock_mouse,
            matcher=self.mock_matcher,
            game_title="Blackfire Crusade",
            action_cooldown=0.0
        )
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

    @patch("win32gui.FindWindow")
    @patch("win32gui.IsWindow")
    def test_is_game_open_true(self, mock_is_window, mock_find_window):
        mock_find_window.return_value = 12345
        mock_is_window.return_value = True

        self.assertTrue(self.launcher.is_game_open())
        mock_find_window.assert_called_with(None, "Blackfire Crusade")

    @patch("win32gui.FindWindow")
    def test_is_game_open_false(self, mock_find_window):
        mock_find_window.return_value = 0
        self.assertFalse(self.launcher.is_game_open())

    def test_wait_and_handle_login_game_window_crop(self):
        # 測試在「遊戲視窗」(非全螢幕) 捕捉 login.png 並觸發點擊登入
        rect = {"left": 100, "top": 50, "width": 1920, "height": 1080}
        self.mock_capturer.get_window_rect.return_value = rect
        self.mock_capturer.capture.return_value = self.fake_img

        def fake_match(img, tpl, threshold=0.75):
            if tpl == "login/login.png":
                return (960, 540), 0.9
            if tpl == "login/login_confirm.png":
                return (960, 793), 0.95
            return None, 0.0

        self.mock_matcher.match.side_effect = fake_match

        res = self.launcher.wait_and_handle_login(timeout=1.0, poll_interval=0.01)

        self.assertTrue(res)
        # 驗證使用遊戲視窗 rect 進行擷取
        self.mock_capturer.capture.assert_called_with(rect)

    def test_ensure_game_ready_when_game_not_open(self):
        # 當遊戲未開啟時，應跑 Steam 啟動流程 run_launch_subflow，接著跑 wait_and_handle_login
        with patch.object(self.launcher, "is_game_open", return_value=False), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch, \
             patch.object(self.launcher, "wait_and_handle_login", return_value=True) as mock_login:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_called_once()
            mock_login.assert_called_once()

    def test_ensure_game_ready_when_game_already_open(self):
        # 當遊戲已開啟時，跳過 Steam 啟動流程，直接跑 wait_and_handle_login
        with patch.object(self.launcher, "is_game_open", return_value=True), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch, \
             patch.object(self.launcher, "wait_and_handle_login", return_value=True) as mock_login:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_not_called()
            mock_login.assert_called_once()


if __name__ == "__main__":
    unittest.main()
