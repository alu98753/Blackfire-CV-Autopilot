import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from utils.steam_launcher import SteamGameLauncher, LauncherPhase


class TestSteamGameLauncherStateMachine(unittest.TestCase):
    """
    SteamGameLauncher 狀態機單元測試。
    註釋：本單元測試預設使用 unittest.mock 隔離實體 Steam 遊戲與 subprocess 啟動。
    只有在需要手動實體測試遊戲啟動時，才可解除 Popen 的 Mock。
    """
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_matcher = MagicMock()
        self.patcher_popen = patch("subprocess.Popen")
        self.mock_popen = self.patcher_popen.start()
        self.addCleanup(self.patcher_popen.stop)

        self.launcher = SteamGameLauncher(
            capturer=self.mock_capturer,
            mouse=self.mock_mouse,
            matcher=self.mock_matcher,
            game_title="Blackfire Crusade",
            action_cooldown=0.0
        )
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

    def test_state_machine_full_happy_path(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.side_effect = [None, {"left": 0, "top": 0, "width": 1920, "height": 1080}]

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)

    def test_state_machine_unstuck_path(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)

    def test_state_machine_shortcut_transition(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)

    def test_state_machine_timeout_fails(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = None

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=0.05, poll_interval=0.01)

        self.assertFalse(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.FAILED)


if __name__ == "__main__":
    unittest.main()
