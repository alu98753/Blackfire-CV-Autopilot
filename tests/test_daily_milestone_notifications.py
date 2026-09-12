"""Unit tests for Daily Pipeline Milestone Notifications & Deadline Alarm.

Strictly follows:
- 100% mocked notification port (ZERO outbound network I/O).
- Tests pure state inspection on DailyManager (no notification pollution).
- Tests DailyPipelineNotifier coordinator (isolated history file, idempotency, deadline check).
- Tests integration wiring between BulletinBoardHandler / GameStateMachine and DailyPipelineNotifier.
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
from states.daily_pipeline_notifier import DailyPipelineNotifier
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


class TestDailyManagerPureStateQueries(unittest.TestCase):
    """Verify DailyManager provides pure state queries without notification state pollution."""

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


class TestDailyPipelineNotifierLogic(unittest.TestCase):
    """Verify DailyPipelineNotifier idempotency, profile-isolated persistence, and deadline calculations."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.test_dir, "notification_history.json")
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.dm = DailyManager(status_file=self.status_file)
        self.mock_notifier = MagicMock(spec=NotificationPort)
        self.coordinator = DailyPipelineNotifier(
            notification_port=self.mock_notifier,
            daily_manager=self.dm,
            profile="test_profile",
            history_file_path=self.history_file,
            deadline_minutes=30,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_milestone_eligibility_and_idempotency(self):
        now_dt = datetime(2026, 9, 12, 8, 20, 0)
        self.assertTrue(self.coordinator.is_milestone_eligible("milestone1", now_dt))

        # Record notified
        self.coordinator.record_milestone_notified("milestone1", now_dt)
        self.assertFalse(self.coordinator.is_milestone_eligible("milestone1", now_dt))

        # Milestone 2 is still eligible
        self.assertTrue(self.coordinator.is_milestone_eligible("milestone2", now_dt))

        # Reload from disk: persistence verified
        coord2 = DailyPipelineNotifier(
            notification_port=self.mock_notifier,
            daily_manager=self.dm,
            profile="test_profile",
            history_file_path=self.history_file,
        )
        self.assertFalse(coord2.is_milestone_eligible("milestone1", now_dt))
        self.assertTrue(coord2.is_milestone_eligible("milestone2", now_dt))

    def test_check_daily_claim_deadline(self):
        # Subflows incomplete
        # 1. At 08:20 (15 min after 08:05 reset): not exceeded
        dt_0820 = datetime(2026, 9, 12, 8, 20, 0)
        self.assertFalse(self.coordinator.check_daily_claim_deadline(now_dt=dt_0820))
        self.mock_notifier.notify_alarm.assert_not_called()

        # 2. At 08:34 (29 min after reset): not exceeded
        dt_0834 = datetime(2026, 9, 12, 8, 34, 0)
        self.assertFalse(self.coordinator.check_daily_claim_deadline(now_dt=dt_0834))
        self.mock_notifier.notify_alarm.assert_not_called()

        # 3. At 08:36 (31 min after reset): exceeded!
        dt_0836 = datetime(2026, 9, 12, 8, 36, 0)
        self.assertTrue(self.coordinator.check_daily_claim_deadline(current_state="NAVIGATING", now_dt=dt_0836))
        self.mock_notifier.notify_alarm.assert_called_once()
        call_kwargs = self.mock_notifier.notify_alarm.call_args[1]
        self.assertEqual(call_kwargs["code"], "DAILY_CLAIM_DEADLINE_EXCEEDED")
        self.assertEqual(call_kwargs["details"]["Current State"], "NAVIGATING")

        # 4. Once notified, it becomes ineligible (idempotent)
        self.mock_notifier.reset_mock()
        self.assertFalse(self.coordinator.check_daily_claim_deadline(current_state="NAVIGATING", now_dt=dt_0836))
        self.mock_notifier.notify_alarm.assert_not_called()

        # 5. If all tier1 subflows are completed, deadline is never triggered
        clean_status = os.path.join(self.test_dir, "clean_status.json")
        dm_clean = DailyManager(status_file=clean_status)
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            dm_clean.record_subflow_completed(sf)
        coord_clean = DailyPipelineNotifier(
            notification_port=self.mock_notifier,
            daily_manager=dm_clean,
            profile="test_profile",
            history_file_path=os.path.join(self.test_dir, "clean_history.json"),
        )
        self.assertFalse(coord_clean.check_daily_claim_deadline(now_dt=dt_0836))


class TestMilestoneEventWiring(unittest.TestCase):
    """Verify that BulletinBoardHandler and GameStateMachine delegate to DailyPipelineNotifier."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.test_dir, "notification_history.json")
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.dm = DailyManager(status_file=self.status_file)
        self.mock_notifier = MagicMock(spec=NotificationPort)
        self.coordinator = DailyPipelineNotifier(
            notification_port=self.mock_notifier,
            daily_manager=self.dm,
            profile="test_profile",
            history_file_path=self.history_file,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_bulletin_board_triggers_milestone1_when_tier1_completed(self):
        # Pre-complete other subflows so bulletin_board is the final one
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop"]:
            self.dm.record_subflow_completed(sf)

        mock_machine = MagicMock()
        mock_machine.daily_manager = self.dm
        mock_machine.daily_pipeline_notifier = self.coordinator
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

        # Assert recorded in coordinator history
        self.assertFalse(self.coordinator.is_milestone_eligible("milestone1"))

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
            daily_pipeline_notifier=self.coordinator,
        )
        sm.daily_manager = self.dm
        sm.config = {"name": "Tier 4 Loop (mix)"}

        # Simulate quest scheduler complete
        mock_scheduler = MagicMock()
        mock_scheduler.is_all_completed.return_value = True
        sm.quest_scheduler = mock_scheduler

        # Trigger check_and_advance_quest_target
        res = sm.check_and_advance_quest_target()
        self.assertIsNone(res)

        # Assert called
        self.mock_notifier.notify_milestone.assert_called_once()
        call_kwargs = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(call_kwargs["title"], "Bounty Quests Cleared")

        # Second invocation does not notify again
        self.mock_notifier.reset_mock()
        self.coordinator.on_bounty_quests_cleared()
        self.mock_notifier.notify_milestone.assert_not_called()

    def test_state_machine_step_triggers_deadline_alarm(self):
        from states.state_machine import GameStateMachine

        mock_capturer = MagicMock()
        mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        mock_matcher = MagicMock()
        mock_matcher.match.return_value = (None, 0.0)
        mock_mouse = MagicMock()

        mock_coordinator = MagicMock()
        sm = GameStateMachine(
            capturer=mock_capturer,
            matcher=mock_matcher,
            mouse=mock_mouse,
            preload_ocr=False,
            notification_port=self.mock_notifier,
            daily_pipeline_notifier=mock_coordinator,
        )
        sm.daily_manager = self.dm
        sm.config = {"name": "test_mode", "type": "mix"}

        sm.step()

        # Assert state_machine stepped and called check_daily_claim_deadline directly without if guard
        mock_coordinator.check_daily_claim_deadline.assert_called_once()

    def test_state_machine_defaults_to_null_notifier(self):
        from states.daily_pipeline_notifier import NullDailyPipelineNotifier
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
        )
        sm.daily_manager = self.dm
        sm.config = {"name": "test_mode", "type": "mix"}

        self.assertIsInstance(sm.daily_pipeline_notifier, NullDailyPipelineNotifier)
        # step() executes seamlessly with Null Object, zero AttributeErrors
        sm.step()


if __name__ == "__main__":
    unittest.main()
