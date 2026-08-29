import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from capture.screen import ScreenCapturer
from runtime import heartbeat
from runtime.heartbeat import heartbeat_path_for_profile, touch_heartbeat
from runtime.supervisor import MANUAL_EXIT_CODE, heartbeat_age_seconds, heartbeat_is_current, is_manual_exit, prepare_resume_command
from states.state_machine import GameStateMachine


class TestLongRunResilience(unittest.TestCase):
    def test_backend_resource_cleanup_releases_every_handle(self):
        with patch("capture.screen.mss.MSS", return_value=MagicMock()):
            capturer = ScreenCapturer(window_title="TestWindow")
        bitmap = MagicMock()
        save_dc = MagicMock()
        mfc_dc = MagicMock()

        with patch("capture.screen.win32gui.DeleteObject") as delete_object, \
             patch("capture.screen.win32gui.ReleaseDC") as release_dc:
            capturer._release_backend_resources(bitmap, save_dc, mfc_dc, 101, 202)

        delete_object.assert_called_once_with(bitmap.GetHandle())
        save_dc.DeleteDC.assert_called_once_with()
        mfc_dc.DeleteDC.assert_called_once_with()
        release_dc.assert_called_once_with(101, 202)
        capturer.close()

    def test_close_releases_mss_handle_once(self):
        fake_sct = MagicMock()
        with patch("capture.screen.mss.MSS", return_value=fake_sct):
            capturer = ScreenCapturer(window_title="TestWindow")

        capturer.close()

        self.assertIsNone(capturer.sct)
        fake_sct.close.assert_called_once_with()

    def test_repeated_capture_failure_relaunches_game(self):
        capturer = MagicMock()
        capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        capturer.capture.return_value = None
        machine = GameStateMachine(capturer, MagicMock(), MagicMock(), preload_ocr=False)

        with patch("states.exceptions.subflows.game_relaunch.GameRelaunchSubflow.execute", return_value=True) as relaunch:
            for _ in range(machine.capture_failure_limit):
                machine.step()

        relaunch.assert_called_once_with(machine, reason="capture_failure_threshold_exceeded")
        self.assertEqual(machine.capture_failure_count, 0)

    def test_successful_capture_clears_failure_counter(self):
        capturer = MagicMock()
        capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        capturer.capture.return_value = np.zeros((4, 4, 3), dtype=np.uint8)
        machine = GameStateMachine(capturer, MagicMock(), MagicMock(), preload_ocr=False)
        machine.capture_failure_count = 2
        machine.exception_watchdog.check = MagicMock(return_value=True)

        machine.step()

        self.assertEqual(machine.capture_failure_count, 0)

    def test_heartbeat_is_atomic_json_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat.json"
            machine = MagicMock(current_state="BATTLE", run_count=12)
            touch_heartbeat(machine, path=path)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(heartbeat_age_seconds(path), 0.0)

        self.assertEqual(payload["state"], "BATTLE")
        self.assertEqual(payload["run_count"], 12)

    def test_heartbeat_write_is_rate_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat.json"
            heartbeat._last_write_times.clear()
            first = MagicMock(current_state="BATTLE", run_count=1)
            second = MagicMock(current_state="LOBBY", run_count=2)
            with patch("runtime.heartbeat.time.time", side_effect=[100.0, 105.0, 111.0]):
                touch_heartbeat(first, path=path)
                touch_heartbeat(second, path=path)
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["state"], "BATTLE")
                touch_heartbeat(second, path=path)
                payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["state"], "LOBBY")

    def test_heartbeat_uses_profile_specific_path_and_records_restart_identity(self):
        self.assertNotEqual(heartbeat_path_for_profile("native"), heartbeat_path_for_profile("sandbox"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat_sandbox.json"
            machine = MagicMock(current_state="BATTLE", run_count=12)
            machine.restart_target = "sandbox"
            machine.restart_profile = "sandbox"
            touch_heartbeat(machine, path=path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "sandbox")
        self.assertEqual(payload["profile"], "sandbox")

    def test_supervisor_ignores_heartbeat_left_by_previous_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat.json"
            path.write_text("{}", encoding="utf-8")
            os.utime(path, (100.0, 100.0))

            self.assertFalse(heartbeat_is_current(path, 101.0))
            self.assertTrue(heartbeat_is_current(path, 99.0))

    def test_supervisor_restart_command_restores_identity_without_duplicate_options(self):
        resumed = prepare_resume_command(
            ["python", "main.py", "--mode", "daily"],
            {"target": "sandbox", "profile": "sandbox"},
        )
        self.assertEqual(resumed[-5:], ["--target", "sandbox", "--profile", "sandbox", "--resume"])

        preserved = prepare_resume_command(
            ["python", "main.py", "--target", "native", "--profile", "native"],
            {"target": "sandbox", "profile": "sandbox"},
        )
        self.assertEqual(preserved.count("--target"), 1)
        self.assertEqual(preserved.count("--profile"), 1)
        self.assertIn("--resume", preserved)

    def test_only_dedicated_manual_exit_code_stops_supervisor(self):
        self.assertTrue(is_manual_exit(MANUAL_EXIT_CODE))
        self.assertFalse(is_manual_exit(0))
        self.assertFalse(is_manual_exit(1))
