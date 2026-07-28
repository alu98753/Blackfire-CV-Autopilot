import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from utils.steam_launcher import SteamGameLauncher, LauncherPhase


class TestSteamGameLauncherStateMachine(unittest.TestCase):
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

    def test_state_machine_full_happy_path(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.side_effect = [None, {"left": 0, "top": 0, "width": 1920, "height": 1080}]

        steam_clicked = False

        def fake_match(img, tpl, threshold=0.75):
            nonlocal steam_clicked
            if self.launcher.phase == LauncherPhase.SEARCH_WINDOWS:
                if tpl == SteamGameLauncher.TPL_SEARCH:
                    return (100, 200), 0.9
            elif self.launcher.phase == LauncherPhase.LAUNCH_STEAM:
                if tpl == SteamGameLauncher.TPL_STEAM and not steam_clicked:
                    steam_clicked = True
                    return (300, 400), 0.9
                elif steam_clicked and tpl == SteamGameLauncher.TPL_START_GAME:
                    return (500, 600), 0.95
            elif self.launcher.phase == LauncherPhase.START_OR_UNSTUCK_GAME:
                if tpl == SteamGameLauncher.TPL_START_GAME:
                    return (500, 600), 0.95
            return None, 0.0

        self.mock_matcher.match.side_effect = fake_match

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)
        # 點擊搜尋 (1) + 點擊 Steam 圖示 (2) + 點擊開始遊戲 (3)
        self.assertEqual(self.mock_mouse.click.call_count, 3)

    def test_state_machine_unstuck_path(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        step = 0
        def fake_match(img, tpl, threshold=0.75):
            nonlocal step
            if self.launcher.phase == LauncherPhase.SEARCH_WINDOWS:
                if tpl == SteamGameLauncher.TPL_SEARCH:
                    return (100, 200), 0.9
            elif self.launcher.phase == LauncherPhase.LAUNCH_STEAM:
                if tpl == SteamGameLauncher.TPL_START_GAME or tpl == SteamGameLauncher.TPL_STOP_GAME:
                    return (500, 600), 0.9
            elif self.launcher.phase == LauncherPhase.START_OR_UNSTUCK_GAME:
                if step == 0 and tpl == SteamGameLauncher.TPL_STOP_GAME:
                    step += 1
                    return (500, 600), 0.9  # 第一次看到卡死按鈕，點擊解卡
                elif step >= 1 and tpl == SteamGameLauncher.TPL_START_GAME:
                    return (500, 600), 0.95 # 第二次看到開始遊戲
            return None, 0.0

        self.mock_matcher.match.side_effect = fake_match

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)
        # 點擊 search (1) + 點擊 stop_game (2) + 點擊 start_game (3)
        self.assertEqual(self.mock_mouse.click.call_count, 3)

    def test_state_machine_shortcut_transition(self):
        # 畫面一開始就已經在 Steam 開始遊戲介面
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.mock_matcher.match.side_effect = lambda img, tpl, threshold=0.75: (
            ((500, 600), 0.9) if tpl == SteamGameLauncher.TPL_START_GAME else (None, 0.0)
        )

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=5.0, poll_interval=0.01)

        self.assertTrue(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.COMPLETED)

    def test_state_machine_timeout_fails(self):
        self.mock_capturer.capture.return_value = self.fake_img
        self.mock_capturer.get_window_rect.return_value = None
        self.mock_matcher.match.return_value = (None, 0.0)

        with patch("time.sleep", return_value=None):
            res = self.launcher.run_launch_subflow(timeout=0.05, poll_interval=0.01)

        self.assertFalse(res)
        self.assertEqual(self.launcher.phase, LauncherPhase.FAILED)


if __name__ == "__main__":
    unittest.main()
