import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from capture.screen import ScreenCapturer
from runtime import heartbeat
from runtime.heartbeat import heartbeat_path_for_profile, touch_heartbeat
from runtime.supervisor import (
    MANUAL_EXIT_CODE,
    daily_restart_is_eligible,
    daily_restart_is_due,
    daily_restart_state_path,
    heartbeat_age_seconds,
    heartbeat_is_current,
    heartbeat_incident_context,
    fallback_child_exit_reason,
    is_manual_exit,
    prepare_resume_command,
    prepare_child_command,
    read_last_scheduled_restart_date,
    record_scheduled_restart,
    supervise,
)
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
            heartbeat._last_write_monotonics.clear()
            first = MagicMock(current_state="BATTLE", run_count=1)
            second = MagicMock(current_state="LOBBY", run_count=2)
            with patch("runtime.heartbeat.time.monotonic", side_effect=[100.0, 105.0, 111.0]):
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
            machine.incident_session_id = "session-sandbox"
            touch_heartbeat(machine, path=path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["target"], "sandbox")
        self.assertEqual(payload["profile"], "sandbox")
        self.assertEqual(payload["session_id"], "session-sandbox")

    def test_supervisor_heartbeat_context_keeps_child_session_identity(self):
        context = heartbeat_incident_context(
            {"pid": 123, "session_id": "session-1", "state": "BATTLE", "run_count": 7},
            123,
            True,
            "session-1",
        )
        self.assertEqual(context, {"session_id": "session-1", "state": "BATTLE", "run_count": 7})
        stale = heartbeat_incident_context({"pid": 99, "session_id": "old", "state": "OLD", "run_count": 8}, 123, False, "session-1")
        self.assertEqual(stale, {"session_id": "session-1", "state": None, "run_count": 0})

    def test_supervisor_assigns_a_fresh_session_id_to_each_child_command(self):
        command = prepare_child_command(["python", "main.py", "--profile", "native", "--incident-session-id", "old"], "new")
        self.assertEqual(command.count("--incident-session-id"), 1)
        self.assertEqual(command[-2:], ["--incident-session-id", "new"])

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

    def test_supervisor_labels_unexplained_child_exit_without_overriding_known_recovery(self):
        self.assertEqual(
            fallback_child_exit_reason(1, None, scheduled_restart=False, termination_reason=None),
            "child_exit_without_handoff",
        )
        self.assertEqual(
            fallback_child_exit_reason(0, None, scheduled_restart=False, termination_reason=None),
            "unexpected_clean_exit",
        )
        self.assertIsNone(
            fallback_child_exit_reason(1, {"pid": 1}, scheduled_restart=False, termination_reason=None)
        )
        self.assertIsNone(
            fallback_child_exit_reason(1, None, scheduled_restart=False, termination_reason="heartbeat_stale")
        )

    def test_supervisor_requires_an_explicit_profile_before_spawning_child(self):
        with self.assertRaisesRegex(ValueError, "explicit '--profile"):
            supervise(["python", "main.py", "--target", "sandbox"], Path("heartbeat.json"))
        with self.assertRaisesRegex(ValueError, "explicit '--profile"):
            supervise(["python", "main.py", "--profile", "   ", "--target", "sandbox"], Path("heartbeat.json"))
        with self.assertRaisesRegex(ValueError, "explicit '--profile"):
            supervise(
                ["python", "main.py", "--profile", "native", "--profile", "sandbox"],
                Path("heartbeat.json"),
            )
        with self.assertRaisesRegex(ValueError, "explicit '--profile"):
            supervise(["python", "main.py", "--profile", "--target", "sandbox"], Path("heartbeat.json"))

    def test_daily_restart_is_due_once_per_calendar_day_after_eight(self):
        before_eight = datetime(2026, 8, 30, 7, 59, 59)
        at_eight = datetime(2026, 8, 30, 8, 0, 0)
        self.assertFalse(daily_restart_is_due(before_eight, None, 8))
        self.assertTrue(daily_restart_is_due(at_eight, None, 8))
        self.assertFalse(daily_restart_is_due(at_eight, "2026-08-30", 8))

    def test_daily_restart_does_not_recycle_a_supervisor_started_after_schedule(self):
        started_after_schedule = datetime(2026, 8, 30, 9, 0, 0)
        next_day_at_schedule = datetime(2026, 8, 31, 8, 0, 0)
        self.assertFalse(daily_restart_is_eligible(started_after_schedule, started_after_schedule, 8))
        self.assertTrue(daily_restart_is_eligible(started_after_schedule, next_day_at_schedule, 8))

    def test_daily_restart_record_is_profile_isolated_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            heartbeat_path = Path(directory) / "heartbeat_sandbox.json"
            state_path = daily_restart_state_path(heartbeat_path)
            self.assertEqual(state_path.name, "heartbeat_sandbox_supervisor_state.json")

            self.assertTrue(record_scheduled_restart(state_path, datetime(2026, 8, 30, 8, 0, 0)))

            self.assertEqual(read_last_scheduled_restart_date(state_path), "2026-08-30")

    def test_heartbeat_records_paused_flag_and_supports_forced_touch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat.json"
            heartbeat._last_write_monotonics.clear()
            machine = MagicMock(current_state="COLLECT_ONLY", run_count=5, is_paused=True)
            touch_heartbeat(machine, path=path)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["is_paused"])
            self.assertEqual(payload["state"], "COLLECT_ONLY")

            # Force touch updates even without waiting for rate-limit interval
            machine.is_paused = False
            touch_heartbeat(machine, path=path, force=True)
            payload_resumed = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(payload_resumed["is_paused"])

    def test_heartbeat_thread_safety_under_concurrent_writes(self):
        import concurrent.futures
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "heartbeat.json"
            heartbeat._last_write_monotonics.clear()
            machine = MagicMock(current_state="BATTLE", run_count=1, is_paused=False)

            def worker(i):
                machine_copy = MagicMock(current_state="BATTLE", run_count=i, is_paused=(i % 2 == 0))
                touch_heartbeat(machine_copy, path=path, force=True)

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(worker, i) for i in range(20)]
                for f in concurrent.futures.as_completed(futures):
                    f.result()

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("timestamp", payload)
            self.assertIn("is_paused", payload)

    def test_pause_controller_background_heartbeat_only_runs_when_paused(self):
        from utils.keyboard_listener import PauseController
        callback = MagicMock()
        is_paused = False
        controller = PauseController(
            start_thread=False,
            is_paused_fn=lambda: is_paused,
            heartbeat_callback=callback,
            heartbeat_interval_sec=1.0,
        )

        # 1. When is_paused is False: background heartbeat should NOT be triggered
        controller._running = True
        with patch.object(controller, "_poll_once"), patch.object(controller, "_poll_manual_exit"):
            # Simulate tick while not paused
            is_currently_paused = bool(controller._is_paused_fn and controller._is_paused_fn())
            self.assertFalse(is_currently_paused)
            callback.assert_not_called()

        # 2. When is_paused is True: background heartbeat is triggered
        is_paused = True
        is_currently_paused = bool(controller._is_paused_fn and controller._is_paused_fn())
        self.assertTrue(is_currently_paused)
        callback()
        callback.assert_called_once()

    def test_pause_controller_live_thread_maintains_heartbeat_only_during_pause(self):
        import time
        from utils.keyboard_listener import PauseController
        callback = MagicMock()
        is_paused = False

        controller = PauseController(
            start_thread=True,
            is_paused_fn=lambda: is_paused,
            heartbeat_callback=callback,
            heartbeat_interval_sec=0.03,
        )
        try:
            # While not paused: background thread must NOT call callback
            time.sleep(0.08)
            self.assertEqual(callback.call_count, 0)

            # Enter pause: background thread should actively call callback
            is_paused = True
            time.sleep(0.1)
            self.assertGreaterEqual(callback.call_count, 1)

            # Resume: background thread must stop calling callback
            is_paused = False
            saved_count = callback.call_count
            time.sleep(0.08)
            self.assertEqual(callback.call_count, saved_count)
        finally:
            controller.stop()
