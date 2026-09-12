"""Unit tests for Phase 3: Daily Milestone Notifications & Deadline Alarm.

Strictly follows:
- 100% mocked notification port (ZERO outbound network I/O).
- Asserts notify_milestone and notify_alarm calls, arguments, and idempotency.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from runtime.notifier import (
    NotificationPort,
    build_alarm_payload,
    build_milestone_payload,
)
from states.handlers.bulletin_board import BulletinBoardHandler
from utils.daily_manager import DailyManager


class TestDailyMilestonePayloads(unittest.TestCase):
    """Verify pure payload builder functions create correct Discord Embed structures."""

    def test_build_milestone_payload_structure(self):
        payload = build_milestone_payload(
            title="Daily Claim Phase Completed",
            description="All town subflows completed.",
            fields={"Quests Accepted": ["Quest 1", "Quest 2"]},
        )
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]
        self.assertEqual(embed["title"], "✅ Daily Claim Phase Completed")
        self.assertEqual(embed["color"], 0x2ECC71)
        self.assertEqual(embed["footer"]["text"], "Blackfire Crusade • Automation Healthy")
        self.assertEqual(len(embed["fields"]), 1)
        self.assertEqual(embed["fields"][0]["name"], "Quests Accepted")

    def test_build_alarm_payload_structure(self):
        payload = build_alarm_payload(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title="Daily Claim Deadline Exceeded",
            reason="Timeout after 30 minutes.",
            details={"Pending Subflows": "bulletin_board"},
        )
        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]
        self.assertEqual(embed["title"], "🚨 Daily Claim Deadline Exceeded")
        self.assertEqual(embed["color"], 0xE74C3C)
        self.assertEqual(embed["footer"]["text"], "Blackfire Crusade • Operator Action Required")
        field_names = [f["name"] for f in embed["fields"]]
        self.assertIn("Alarm Code", field_names)
        self.assertIn("Reason", field_names)
        self.assertIn("Pending Subflows", field_names)


class TestDailyManagerMilestoneLogic(unittest.TestCase):
    """Verify DailyManager milestone eligibility, tracking, and deadline calculations."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.dm = DailyManager(status_file=self.status_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tier1_daily_claim_completion_check(self):
        # Initial: subflows not completed
        self.assertFalse(self.dm.is_tier1_daily_claim_completed())
        pending = self.dm.get_pending_tier1_subflows()
        self.assertIn("chest", pending)
        self.assertIn("bulletin_board", pending)

        # Complete all tier1 subflows
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            self.dm.record_subflow_completed(sf)

        self.assertTrue(self.dm.is_tier1_daily_claim_completed())
        self.assertEqual(self.dm.get_pending_tier1_subflows(), [])

    def test_milestone_eligibility_and_idempotency(self):
        now_dt = datetime(2026, 9, 12, 8, 20, 0)
        self.assertTrue(self.dm.is_milestone_eligible("milestone1", now_dt))

        # Record notified
        self.dm.record_milestone_notified("milestone1", now_dt)
        self.assertFalse(self.dm.is_milestone_eligible("milestone1", now_dt))

        # Milestone 2 is still eligible
        self.assertTrue(self.dm.is_milestone_eligible("milestone2", now_dt))

        # Reload from disk: persistence verified
        dm2 = DailyManager(status_file=self.status_file)
        self.assertFalse(dm2.is_milestone_eligible("milestone1", now_dt))
        self.assertTrue(dm2.is_milestone_eligible("milestone2", now_dt))

    def test_is_daily_claim_deadline_exceeded(self):
        # Subflows incomplete
        # 1. At 08:20 (15 min after 08:05 reset): not exceeded
        dt_0820 = datetime(2026, 9, 12, 8, 20, 0)
        self.assertFalse(self.dm.is_daily_claim_deadline_exceeded(now_dt=dt_0820, deadline_minutes=30))

        # 2. At 08:34 (29 min after reset): not exceeded
        dt_0834 = datetime(2026, 9, 12, 8, 34, 0)
        self.assertFalse(self.dm.is_daily_claim_deadline_exceeded(now_dt=dt_0834, deadline_minutes=30))

        # 3. At 08:36 (31 min after reset): exceeded!
        dt_0836 = datetime(2026, 9, 12, 8, 36, 0)
        self.assertTrue(self.dm.is_daily_claim_deadline_exceeded(now_dt=dt_0836, deadline_minutes=30))

        # 4. Once notified, it becomes ineligible (idempotent)
        self.dm.record_milestone_notified("deadline_alarm", dt_0836)
        self.assertFalse(self.dm.is_daily_claim_deadline_exceeded(now_dt=dt_0836, deadline_minutes=30))

        # 5. If all tier1 subflows are completed, deadline is never exceeded
        dm_clean = DailyManager(status_file=os.path.join(self.test_dir, "clean_status.json"))
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            dm_clean.record_subflow_completed(sf)
        self.assertFalse(dm_clean.is_daily_claim_deadline_exceeded(now_dt=dt_0836, deadline_minutes=30))


class TestMilestoneEventWiring(unittest.TestCase):
    """Verify that BulletinBoardHandler and GameStateMachine dispatch milestone notifications."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.dm = DailyManager(status_file=self.status_file)
        self.mock_notifier = MagicMock(spec=NotificationPort)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_bulletin_board_triggers_milestone1_when_tier1_completed(self):
        # Pre-complete other subflows so bulletin_board is the final one
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop"]:
            self.dm.record_subflow_completed(sf)

        mock_machine = MagicMock()
        mock_machine.daily_manager = self.dm
        mock_machine.notification_port = self.mock_notifier
        mock_machine.pop_and_next_town_subflow = MagicMock()

        handler = BulletinBoardHandler(machine=mock_machine)
        handler.accepted_quest_titles = ["清除骷髏", "清除蜘蛛"]

        # Trigger completion
        handler._record_completion()

        # Assert notify_milestone was called
        self.mock_notifier.notify_milestone.assert_called_once()
        call_kwargs = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(call_kwargs["title"], "Daily Claim Phase Completed")
        self.assertEqual(set(call_kwargs["fields"]["Quests Accepted"]), {"清除骷髏", "清除蜘蛛"})

        # Assert recorded in DailyManager
        self.assertFalse(self.dm.is_milestone_eligible("milestone1"))

        # Second completion does not notify again (idempotent)
        self.mock_notifier.reset_mock()
        handler._record_completion()
        self.mock_notifier.notify_milestone.assert_not_called()

    def test_state_machine_triggers_milestone2_when_quests_cleared(self):
        from states.state_machine import GameStateMachine

        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()

        sm = GameStateMachine(
            capturer=mock_capturer,
            matcher=mock_matcher,
            mouse=mock_mouse,
            preload_ocr=False,
            notification_port=self.mock_notifier,
        )
        sm.daily_manager = self.dm

        # Trigger milestone 2 helper
        sm._notify_milestone2_if_eligible()

        # Assert called
        self.mock_notifier.notify_milestone.assert_called_once()
        call_kwargs = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(call_kwargs["title"], "Bounty Quests Cleared")

        # Second invocation does not notify again
        self.mock_notifier.reset_mock()
        sm._notify_milestone2_if_eligible()
        self.mock_notifier.notify_milestone.assert_not_called()

    def test_state_machine_step_triggers_deadline_alarm(self):
        from states.state_machine import GameStateMachine

        mock_capturer = MagicMock()
        mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = (None, 0.0)
        mock_mouse = MagicMock()

        sm = GameStateMachine(
            capturer=mock_capturer,
            matcher=mock_matcher,
            mouse=mock_mouse,
            preload_ocr=False,
            notification_port=self.mock_notifier,
        )
        sm.daily_manager = self.dm
        sm.config = {"name": "test_mode", "type": "mix"}

        # Force deadline exceeded
        self.dm.is_daily_claim_deadline_exceeded = MagicMock(return_value=True)

        sm.step()

        self.mock_notifier.notify_alarm.assert_called_once()
        call_kwargs = self.mock_notifier.notify_alarm.call_args[1]
        self.assertEqual(call_kwargs["code"], "DAILY_CLAIM_DEADLINE_EXCEEDED")
        self.assertEqual(call_kwargs["title"], "Daily Claim Deadline Exceeded")


if __name__ == "__main__":
    unittest.main()
