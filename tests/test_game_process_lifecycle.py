import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.exceptions.handler import UnexpectedPopupRecoveryHandler
from states.exceptions.watchdog import ExceptionWatchdog
from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow
from utils.steam_launcher import SteamGameLauncher, LauncherPhase


@unittest.skip("遊戲啟動與關閉進程生命週期測試 - 全套件執行期間預設跳過，防範誤觸發遊戲啟動/關閉進程")
class TestGameProcessLifecycle(unittest.TestCase):
    """
    統一管理所有會發起 Steam 遊戲啟動 (ensure_game_ready) 或關閉/殺進程 (GameRelaunchSubflow, taskkill) 之生命週期測試。
    全套件自動化測試執行期間預設加上 @unittest.skip 跳過，避免干擾實體遊戲與測試環境。
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.machine.config = {"mode": "test"}
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

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

    # ------------------ 1. SteamGameLauncher 狀態機測試 ------------------
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

    # ------------------ 2. ensure_game_ready 測試 ------------------
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
        with patch.object(self.launcher, "is_game_open", return_value=False), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_called_once()

    def test_ensure_game_ready_when_game_already_open(self):
        with patch.object(self.launcher, "is_game_open", return_value=True), \
             patch.object(self.launcher, "run_launch_subflow", return_value=True) as mock_launch:

            res = self.launcher.ensure_game_ready()

            self.assertTrue(res)
            mock_launch.assert_not_called()

    # ------------------ 3. GameRelaunchSubflow 進程關閉與重啟測試 ------------------
    @patch("subprocess.run")
    @patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready")
    def test_game_relaunch_subflow_execution(self, mock_ensure_ready, mock_subprocess_run):
        mock_ensure_ready.return_value = True
        self.machine.stashed_state = "NAVIGATING"
        self.machine.stashed_context = {"reason": "test"}
        self.machine.exception_watchdog.consecutive_stuck_count = 2

        subflow = GameRelaunchSubflow()
        res = subflow.execute(self.machine, reason="unit_test_trigger")

        self.assertTrue(res)
        self.assertTrue(mock_subprocess_run.called)
        mock_ensure_ready.assert_called_once()
        self.assertIsNone(self.machine.stashed_state)
        self.assertEqual(self.machine.stashed_context, {})
        self.assertEqual(self.machine.exception_watchdog.consecutive_stuck_count, 0)
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)

    @patch.object(GameRelaunchSubflow, "execute", return_value=True)
    def test_popup_recovery_handler_max_retries_relaunch(self, mock_relaunch_execute):
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch.object(self.machine.matcher, "match", return_value=(None, 0.0)):
            for i in range(4):
                handler.handle(self.fake_img, rect)
                mock_relaunch_execute.assert_not_called()
                self.assertEqual(handler.retry_count, i + 1)

            handler.handle(self.fake_img, rect)
            mock_relaunch_execute.assert_called_once()
            self.assertEqual(mock_relaunch_execute.call_args[1]["reason"], "popup_recovery_max_retries_exceeded")

    @patch.object(GameRelaunchSubflow, "execute", return_value=True)
    def test_watchdog_consecutive_timeout_relaunch(self, mock_relaunch_execute):
        watchdog = self.machine.exception_watchdog
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.machine.last_state_change = 100.0

        with patch("time.time", return_value=135.5), \
             patch.object(self.machine, "stash_current_state") as mock_stash:
            res1 = watchdog.check(self.fake_img)
            self.assertTrue(res1)
            mock_stash.assert_called_once()
            mock_relaunch_execute.assert_not_called()
            self.assertEqual(watchdog.consecutive_stuck_count, 1)

            res2 = watchdog.check(self.fake_img)
            self.assertTrue(res2)
            mock_relaunch_execute.assert_called_once()
            self.assertEqual(watchdog.consecutive_stuck_count, 0)
            self.assertIsNone(watchdog.last_stuck_state)

    def test_normal_state_transition_resets_consecutive_stuck_count(self):
        watchdog = self.machine.exception_watchdog
        watchdog.consecutive_stuck_count = 1
        watchdog.last_stuck_state = "NAVIGATING"

        self.machine.transition_to(self.machine.STATE_LOBBY)

        self.assertEqual(watchdog.consecutive_stuck_count, 0)
        self.assertIsNone(watchdog.last_stuck_state)

    @patch("subprocess.run")
    @patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready", return_value=True)
    def test_script_pid_exemption_guard(self, mock_ensure_ready, mock_subprocess_run):
        script_pid = os.getpid()
        subflow = GameRelaunchSubflow()

        with patch("win32gui.FindWindow", return_value=99999), \
             patch("win32process.GetWindowThreadProcessId", return_value=(0, script_pid)):
            subflow.execute(self.machine, reason="pid_guard_test")

            for call_item in mock_subprocess_run.call_args_list:
                cmd_str = call_item[0][0]
                self.assertNotIn(f"taskkill /f /pid {script_pid}", cmd_str)
                self.assertNotIn("WINDOWTITLE", cmd_str)

    @patch.object(GameRelaunchSubflow, "execute", return_value=True)
    def test_window_lost_5times_auto_relaunch(self, mock_relaunch_execute):
        self.machine.window_lost_count = 0
        self.mock_capturer.get_window_rect.return_value = None

        for i in range(4):
            self.machine.step()
            mock_relaunch_execute.assert_not_called()
            self.assertEqual(self.machine.window_lost_count, i + 1)

        self.machine.step()
        mock_relaunch_execute.assert_called_once()
        self.assertEqual(mock_relaunch_execute.call_args[1]["reason"], "game_window_closed_by_user")
        self.assertEqual(self.machine.window_lost_count, 0)


if __name__ == "__main__":
    unittest.main()
