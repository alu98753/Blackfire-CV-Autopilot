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

    def test_ensure_game_ready_when_game_not_open(self):
        # 當遊戲未開啟時，應跑 Steam 啟動流程 run_launch_subflow，定位最大化視窗後立即返回 True 交給主狀態機
        with patch.object(self.launcher, "is_game_open", return_value=False), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_called_once()

    def test_ensure_game_ready_when_game_already_open(self):
        # 當遊戲已開啟時，跳過 Steam 啟動流程，直接定位最大化視窗並返回 True
        with patch.object(self.launcher, "is_game_open", return_value=True), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
