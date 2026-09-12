"""Unit tests for Supervisor crash loop detection, sliding window, and recovery policy."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from runtime.crash_tracker import (
    CrashLoopTracker,
    is_stabilized_active_state,
)
from runtime.supervisor import load_supervisor_config


class TestSupervisorCrashTracker(unittest.TestCase):
    """Verify sliding-window crash loop tracking and recovery stabilization logic."""

    def test_load_supervisor_config_defaults(self):
        cfg = load_supervisor_config()
        self.assertEqual(cfg["watchdog_timeout"], 90.0)
        self.assertEqual(cfg["relaunch_buffer_seconds"], 30.0)
        self.assertEqual(cfg["max_restarts"], 5)

    def test_get_supervisor_settings_and_constants(self):
        from config import (
            DEFAULT_SUPERVISOR_MAX_RESTARTS,
            DEFAULT_SUPERVISOR_RELAUNCH_BUFFER_SECONDS,
            DEFAULT_SUPERVISOR_WATCHDOG_TIMEOUT,
            get_supervisor_settings,
        )
        self.assertEqual(DEFAULT_SUPERVISOR_WATCHDOG_TIMEOUT, 90.0)
        self.assertEqual(DEFAULT_SUPERVISOR_RELAUNCH_BUFFER_SECONDS, 30.0)
        self.assertEqual(DEFAULT_SUPERVISOR_MAX_RESTARTS, 5)

        settings = get_supervisor_settings()
        self.assertEqual(settings["watchdog_timeout"], 90.0)
        self.assertEqual(settings["relaunch_buffer_seconds"], 30.0)
        self.assertEqual(settings["max_restarts"], 5)

        # CrashLoopTracker defaults match config constants
        tracker = CrashLoopTracker()
        self.assertEqual(tracker.max_restarts, 5)
        self.assertEqual(tracker.relaunch_buffer, 30.0)
        self.assertEqual(tracker.watchdog_timeout, 90.0)

    def test_sliding_window_dimensions(self):
        tracker = CrashLoopTracker(
            max_restarts=5,
            relaunch_buffer_seconds=30.0,
            watchdog_timeout=90.0,
        )
        self.assertEqual(tracker.t_relaunch, 120.0)
        self.assertEqual(tracker.t_window, 600.0)

    def test_crash_loop_trigger_at_threshold(self):
        tracker = CrashLoopTracker(
            max_restarts=5,
            relaunch_buffer_seconds=30.0,
            watchdog_timeout=90.0,
        )
        t0 = 1000.0

        # Failures 1 to 4 do not exceed threshold
        for i in range(4):
            exceeded = tracker.record_failure(now=t0 + i * 30.0)
            self.assertFalse(exceeded)
            self.assertEqual(tracker.restart_count, i + 1)

        # 5th failure exceeds threshold
        exceeded = tracker.record_failure(now=t0 + 4 * 30.0)
        self.assertTrue(exceeded)
        self.assertEqual(tracker.restart_count, 5)

        # Immediate 6th failure is throttled (less than t_relaunch elapsed)
        exceeded_throttled = tracker.record_failure(now=t0 + 4 * 30.0 + 10.0)
        self.assertFalse(exceeded_throttled)

    def test_sliding_window_prunes_stale_failures(self):
        tracker = CrashLoopTracker(
            max_restarts=5,
            relaunch_buffer_seconds=30.0,
            watchdog_timeout=90.0,
        )
        t0 = 1000.0

        # 3 failures long ago (outside 600s window)
        for i in range(3):
            tracker.record_failure(now=t0 + i * 10.0)

        self.assertEqual(len(tracker.restart_timestamps), 3)

        # Next failure arrives at t0 + 700s (more than 600s after first failures)
        tracker.record_failure(now=t0 + 700.0)
        # Old 3 failures should have been pruned
        self.assertEqual(len(tracker.restart_timestamps), 1)

    def test_stabilization_resets_restart_counter(self):
        tracker = CrashLoopTracker(
            max_restarts=5,
            relaunch_buffer_seconds=30.0,
            watchdog_timeout=90.0,
        )
        # 3 failures recorded
        for i in range(3):
            tracker.record_failure(now=1000.0 + i * 10.0)
        self.assertEqual(tracker.restart_count, 3)

        # Stabilization check with insufficient uptime (< 120s) does not reset
        self.assertFalse(tracker.check_stabilized(uptime=100.0, state="NAVIGATING"))
        self.assertEqual(tracker.restart_count, 3)

        # Stabilization check with recovery/unknown state does not reset
        self.assertFalse(tracker.check_stabilized(uptime=130.0, state="POPUP_RECOVERY"))
        self.assertFalse(tracker.check_stabilized(uptime=130.0, state="UNKNOWN"))
        self.assertEqual(tracker.restart_count, 3)

        # Stabilization check with active state (NAVIGATING) and >= 120s resets
        self.assertTrue(tracker.check_stabilized(uptime=125.0, state="NAVIGATING"))
        self.assertEqual(tracker.restart_count, 0)
        self.assertEqual(len(tracker.restart_timestamps), 0)

    def test_is_stabilized_active_state(self):
        self.assertTrue(is_stabilized_active_state("NAVIGATING"))
        self.assertTrue(is_stabilized_active_state("BATTLE"))
        self.assertTrue(is_stabilized_active_state("COLLECT_ONLY"))
        self.assertFalse(is_stabilized_active_state("UNKNOWN"))
        self.assertFalse(is_stabilized_active_state("POPUP_RECOVERY"))
        self.assertFalse(is_stabilized_active_state(None))

    def test_clean_restart_resets_consecutive_count(self):
        tracker = CrashLoopTracker()
        tracker.record_failure(now=1000.0)
        self.assertEqual(tracker.restart_count, 1)

        tracker.record_clean_restart()
        self.assertEqual(tracker.restart_count, 0)


if __name__ == "__main__":
    unittest.main()
