"""Behavioral domain tests for S1-S7 supervisor and game lifecycle recovery scenarios."""

import os
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.supervisor import (
    MANUAL_EXIT_CODE,
    is_manual_exit,
    prepare_resume_command,
    supervise,
)
from utils.game_process import is_window_hung, terminate_game_process
from utils.steam_launcher import SteamGameLauncher
from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow


class TestBehaviorSupervisorLifecycle(unittest.TestCase):
    """
    Test suite verifying Scenario Matrix S1 through S7 for game and process lifecycle.
    """

    # -------------------------------------------------------------------------
    # Scenario S1: Daily Scheduled Restart (08:00 AM)
    # -------------------------------------------------------------------------
    def test_scenario_s1_daily_scheduled_restart_injects_restart_game(self):
        """S1: When daily maintenance triggers, Supervisor must inject --restart-game."""
        base_cmd = ["python", "main.py", "--profile", "native", "--target", "native"]
        heartbeat = {"profile": "native", "target": "native"}

        # Verification at prepare_resume_command contract
        resumed = prepare_resume_command(base_cmd, heartbeat, restart_game=True)
        self.assertIn("--restart-game", resumed)
        self.assertIn("--resume", resumed)

        # Verification inside supervise loop on daily_scheduled_restart
        mock_child = MagicMock()
        mock_child.poll.side_effect = [None, 0]
        mock_child.pid = 9999

        with patch("subprocess.Popen", return_value=mock_child) as mock_popen, \
             patch("runtime.supervisor.daily_restart_is_eligible", return_value=True), \
             patch("runtime.supervisor.daily_restart_is_due", return_value=True), \
             patch("runtime.supervisor.record_scheduled_restart", return_value=True), \
             patch("runtime.supervisor.write_incident") as mock_incident, \
             patch("runtime.supervisor._stop_child") as mock_stop, \
             patch("runtime.supervisor.time.sleep", side_effect=KeyboardInterrupt):
            try:
                supervise(base_cmd, Path("dummy_heartbeat.json"), daily_restart_hour=8)
            except KeyboardInterrupt:
                pass

            # Ensure child was stopped gracefully
            mock_stop.assert_called_once_with(mock_child)
            # Ensure scheduled maintenance incident was logged
            maintenance_calls = [
                call for call in mock_incident.call_args_list
                if len(call[0]) > 2 and call[0][2] == "daily_scheduled_restart"
            ]
            self.assertTrue(len(maintenance_calls) > 0)

    # -------------------------------------------------------------------------
    # Scenario S2: Heartbeat Stale (>180s)
    # -------------------------------------------------------------------------
    def test_scenario_s2_heartbeat_stale_injects_restart_game(self):
        """S2: When heartbeat age exceeds threshold, Supervisor terminates child and injects --restart-game."""
        base_cmd = ["python", "main.py", "--profile", "sandbox", "--target", "sandbox", "--resume"]
        heartbeat = {"profile": "sandbox", "target": "sandbox"}

        resumed = prepare_resume_command(base_cmd, heartbeat, restart_game=True)
        self.assertIn("--restart-game", resumed)
        self.assertIn("--resume", resumed)

        mock_child = MagicMock()
        mock_child.poll.side_effect = [None, 1]
        mock_child.pid = 8888

        with patch("subprocess.Popen", return_value=mock_child), \
             patch("runtime.supervisor.heartbeat_is_current", return_value=True), \
             patch("runtime.supervisor.heartbeat_age_seconds", return_value=200.0), \
             patch("runtime.supervisor.write_incident") as mock_incident, \
             patch("runtime.supervisor._stop_child") as mock_stop, \
             patch("runtime.supervisor.time.sleep", side_effect=KeyboardInterrupt):
            try:
                supervise(base_cmd, Path("dummy_heartbeat.json"), timeout_seconds=180.0, daily_restart_hour=None)
            except KeyboardInterrupt:
                pass

            mock_stop.assert_called_once_with(mock_child)
            stale_calls = [
                call for call in mock_incident.call_args_list
                if len(call[0]) > 2 and call[0][2] == "heartbeat_stale"
            ]
            self.assertTrue(len(stale_calls) > 0)

    # -------------------------------------------------------------------------
    # Scenario S3: Hung Window Detected Auto-Escalation
    # -------------------------------------------------------------------------
    def test_scenario_s3_hung_window_auto_escalates_to_restart_game(self):
        """S3: If window is hung (IsHungAppWindow=True), launch escalates to force_relaunch."""
        launcher = SteamGameLauncher(game_title="Blackfire Crusade", hwnd=12345)

        with patch("utils.game_process.ctypes.windll.user32.IsHungAppWindow", return_value=1):
            self.assertTrue(is_window_hung(12345))

        with patch.object(launcher, "is_game_open", return_value=False), \
             patch.object(launcher, "run_launch_subflow", return_value=True) as mock_launch, \
             patch("utils.game_process.terminate_game_process", return_value=True) as mock_terminate:
            res = launcher.ensure_game_ready(force_relaunch=True)
            self.assertTrue(res)
            mock_terminate.assert_called_once_with(game_title="Blackfire Crusade", hwnd=12345)
            mock_launch.assert_called_once()

    # -------------------------------------------------------------------------
    # Scenario S4: Runtime Capture Failure / Exception Relaunch
    # -------------------------------------------------------------------------
    def test_scenario_s4_runtime_capture_failure_triggers_game_relaunch(self):
        """S4: In-game Watchdog / capture failure uses GameRelaunchSubflow and calls terminate_game_process."""
        machine = MagicMock()
        machine.window_title = "Blackfire Crusade"
        machine.capturer.get_hwnd.return_value = 54321
        machine.exception_watchdog.consecutive_stuck_count = 2

        subflow = GameRelaunchSubflow()
        with patch("states.exceptions.subflows.game_relaunch.terminate_game_process", return_value=True) as mock_term, \
             patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready", return_value=True) as mock_ready, \
             patch("time.sleep", return_value=None):
            result = subflow.execute(machine, reason="capture_failure_threshold_exceeded")

        self.assertTrue(result)
        mock_term.assert_called_once_with(game_title="Blackfire Crusade", hwnd=54321)
        mock_ready.assert_called_once()
        machine.transition_to.assert_called_once_with(machine.STATE_UNKNOWN)

    # -------------------------------------------------------------------------
    # Scenario S5: Normal Exception Crash Fast-Resume
    # -------------------------------------------------------------------------
    def test_scenario_s5_unhandled_crash_fast_resumes_without_restart_game(self):
        """S5: Standard Python crash does NOT restart the game; it attaches quickly."""
        base_cmd = ["python", "main.py", "--profile", "native", "--target", "native"]
        heartbeat = {"profile": "native", "target": "native"}

        resumed = prepare_resume_command(base_cmd, heartbeat, restart_game=False)
        self.assertNotIn("--restart-game", resumed)
        self.assertIn("--resume", resumed)

    # -------------------------------------------------------------------------
    # Scenario S6: KeyboardInterrupt (Ctrl+C) Fast-Resume
    # -------------------------------------------------------------------------
    def test_scenario_s6_keyboard_interrupt_fast_resumes_without_restart_game(self):
        """S6: Ctrl+C initiates child restart with fast resume (no game restart)."""
        base_cmd = ["python", "main.py", "--profile", "native"]
        heartbeat = {"profile": "native"}

        resumed = prepare_resume_command(base_cmd, heartbeat, restart_game=False)
        self.assertNotIn("--restart-game", resumed)
        self.assertIn("--resume", resumed)

    # -------------------------------------------------------------------------
    # Scenario S7: Dedicated Manual Exit (Ctrl+Shift+Q -> Exit 75)
    # -------------------------------------------------------------------------
    def test_scenario_s7_manual_exit_stops_supervisor_without_restart(self):
        """S7: Exit Code 75 stops the supervisor completely without restart or game kill."""
        self.assertTrue(is_manual_exit(MANUAL_EXIT_CODE))
        self.assertTrue(is_manual_exit(75))
        self.assertFalse(is_manual_exit(0))
        self.assertFalse(is_manual_exit(1))

        mock_child = MagicMock()
        mock_child.poll.return_value = MANUAL_EXIT_CODE
        mock_child.pid = 7777

        with patch("subprocess.Popen", return_value=mock_child), \
             patch("runtime.supervisor.write_incident") as mock_incident:
            exit_code = supervise(["python", "main.py", "--profile", "native"], Path("dummy.json"), timeout_seconds=180.0)
            self.assertEqual(exit_code, 0)
            mock_incident.assert_called_once()
            self.assertEqual(mock_incident.call_args[0][2], "manual_exit_hotkey")

    # -------------------------------------------------------------------------
    # Single-use Consumption Protection for --restart-game
    # -------------------------------------------------------------------------
    def test_restart_game_flag_is_single_use_consumed(self):
        """Ensure --restart-game is stripped when subsequent recovery has restart_game=False."""
        cmd_with_flag = ["python", "main.py", "--profile", "native", "--resume", "--restart-game"]
        heartbeat = {"profile": "native"}

        # Next recovery has restart_game=False -> MUST strip --restart-game
        resumed = prepare_resume_command(cmd_with_flag, heartbeat, restart_game=False)
        self.assertNotIn("--restart-game", resumed)
        self.assertIn("--resume", resumed)

        # Subsequent restart_game=True -> re-adds --restart-game without duplicates
        resumed_again = prepare_resume_command(resumed, heartbeat, restart_game=True)
        self.assertEqual(resumed_again.count("--restart-game"), 1)

    # -------------------------------------------------------------------------
    # Safety: Terminate Game Process Guards Against Self PID
    # -------------------------------------------------------------------------
    def test_terminate_game_process_safety_guards_self_pid(self):
        """terminate_game_process must never kill the calling script's PID."""
        my_pid = os.getpid()

        with patch("utils.game_process.find_game_window", return_value=12345), \
             patch("utils.game_process.get_window_pid", return_value=my_pid), \
             patch("subprocess.run") as mock_sub:
            result = terminate_game_process(game_title="Blackfire Crusade", hwnd=12345, script_pid=my_pid)
            self.assertFalse(result)
            mock_sub.assert_not_called()


if __name__ == "__main__":
    unittest.main()
