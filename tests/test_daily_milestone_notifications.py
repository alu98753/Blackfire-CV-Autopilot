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
from unittest.mock import MagicMock, patch

from config import get_notification_language
from runtime.notification_i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    format_daily_claim_deadline_alarm,
    format_milestone1,
    format_milestone2,
    format_subflow_status,
    format_supervisor_crash_alarm,
    normalize_language,
)
from ports.notification_port import (
    DeleteResult,
    NotificationPort,
    NotificationResult,
)
from runtime.discord_payload_builder import (
    build_alarm_payload,
    build_milestone_payload,
)
from runtime.json_notification_history_store import JsonNotificationHistoryStore
from states.daily_pipeline_notifier import DailyPipelineNotifier, NullDailyPipelineNotifier
from states.handlers.bulletin_board import BulletinBoardHandler
from utils.daily_manager import DailyManager


class TestDailyMilestonePayloads(unittest.TestCase):
    """Verify pure payload builder functions create correct Discord Embed structures."""

    def test_build_milestone_payload_structure(self):
        # Test English footer when language="en"
        payload_en = build_milestone_payload(
            title="Daily Claim Phase Completed",
            description="All town subflows completed.",
            fields={"Quests Accepted": ["Quest 1", "Quest 2"]},
            language="en",
        )
        self.assertIn("embeds", payload_en)
        self.assertEqual(len(payload_en["embeds"]), 1)
        embed_en = payload_en["embeds"][0]
        self.assertEqual(embed_en["title"], "✅ Daily Claim Phase Completed")
        self.assertEqual(embed_en["color"], 0x2ECC71)
        self.assertEqual(embed_en["footer"]["text"], "Automation Running Normally")
        self.assertEqual(len(embed_en["fields"]), 1)
        self.assertEqual(embed_en["fields"][0]["name"], "Quests Accepted")

        # Test default zh-TW footer
        payload_zh = build_milestone_payload(
            title="每日城鎮速領完成",
            description="已完成。",
        )
        self.assertEqual(payload_zh["embeds"][0]["footer"]["text"], "自動掛機運行正常")

    def test_build_alarm_payload_structure(self):
        # Test English footer when language="en"
        payload_en = build_alarm_payload(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title="Daily Claim Deadline Exceeded",
            reason="Timeout after 30 minutes.",
            details={"Pending Subflows": "bulletin_board"},
            language="en",
        )
        self.assertIn("embeds", payload_en)
        self.assertEqual(len(payload_en["embeds"]), 1)
        embed_en = payload_en["embeds"][0]
        self.assertEqual(embed_en["title"], "🚨 Daily Claim Deadline Exceeded")
        self.assertEqual(embed_en["color"], 0xE74C3C)
        self.assertEqual(embed_en["footer"]["text"], "Automation Requires Manual Intervention")
        field_names = [f["name"] for f in embed_en["fields"]]
        self.assertIn("Alarm Code", field_names)
        self.assertIn("Reason", field_names)
        self.assertIn("Pending Subflows", field_names)

        # Test default zh-TW footer
        payload_zh = build_alarm_payload(
            code="DAILY_CLAIM_DEADLINE_EXCEEDED",
            title="每日速領超時卡死警報",
            reason="超時",
        )
        self.assertEqual(payload_zh["embeds"][0]["footer"]["text"], "自動掛機需要人工介入處理")


class TestNotificationI18n(unittest.TestCase):
    """Verify multi-language notification formatting and fail-fast validation."""

    def test_normalize_language_valid_aliases(self):
        self.assertEqual(normalize_language(None), "zh-TW")
        self.assertEqual(normalize_language("zh-TW"), "zh-TW")
        self.assertEqual(normalize_language("zh_tw"), "zh-TW")
        self.assertEqual(normalize_language("ZH"), "zh-TW")
        self.assertEqual(normalize_language("en"), "en")
        self.assertEqual(normalize_language("EN"), "en")
        self.assertEqual(normalize_language("en_us"), "en")
        self.assertEqual(normalize_language("en-US"), "en")

    def test_normalize_language_fail_fast_on_invalid(self):
        invalid_cases = ["fr", "ja", "ko", "invalid", "", "123", 42]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError) as cm:
                    normalize_language(case)
                self.assertTrue(
                    "不支援的通知語言設定" in str(cm.exception)
                    or "通知語言設定必須為字串" in str(cm.exception)
                )

    def test_format_subflow_status_bilingual(self):
        # Traditional Chinese
        zh_status = format_subflow_status("chest", completed=True, language="zh-TW")
        self.assertEqual(zh_status, "寶箱 (Chest)(✓)")
        zh_uncompleted = format_subflow_status("bulletin_board", completed=False, language="zh-TW")
        self.assertEqual(zh_uncompleted, "懸賞告示牌 (Bulletin Board)(✗)")

        # English
        en_status = format_subflow_status("chest", completed=True, language="en")
        self.assertEqual(en_status, "Chest(✓)")
        en_uncompleted = format_subflow_status("bulletin_board", completed=False, language="en")
        self.assertEqual(en_uncompleted, "Bulletin Board(✗)")

    def test_format_milestone1_bilingual(self):
        # zh-TW
        title_zh, desc_zh, fields_zh, footer_zh = format_milestone1(
            profile="test",
            accepted_quests=["Quest A"],
            subflow_statuses=["寶箱 (Chest)(✓)"],
            language="zh-TW",
            now_dt=datetime(2026, 9, 12, 8, 15, 0),
        )
        self.assertEqual(title_zh, "每日城鎮速領完成")
        self.assertIn("告示牌懸賞任務", desc_zh)
        self.assertIn("已接取懸賞", fields_zh)
        self.assertIn("城鎮子流程", fields_zh)
        self.assertEqual(footer_zh, "自動掛機運行正常")

        # en
        title_en, desc_en, fields_en, footer_en = format_milestone1(
            profile="test",
            accepted_quests=["Quest A"],
            subflow_statuses=["Chest(✓)"],
            language="en",
            now_dt=datetime(2026, 9, 12, 8, 15, 0),
        )
        self.assertEqual(title_en, "Daily Claim Phase Completed")
        self.assertIn("bulletin board bounty quests", desc_en)
        self.assertIn("Quests Accepted", fields_en)
        self.assertIn("Town Subflows", fields_en)
        self.assertEqual(footer_en, "Automation Running Normally")

    def test_format_milestone2_bilingual(self):
        # zh-TW
        title_zh, desc_zh, fields_zh, footer_zh = format_milestone2(
            profile="test",
            fallback_mode="loop_battle",
            language="zh-TW",
            now_dt=datetime(2026, 9, 12, 9, 30, 0),
            cleared_count=5,
            cleared_quests=["Q1", "Q2"],
        )
        self.assertEqual(title_zh, "每日懸賞任務已全部完成")
        self.assertIn("完成任務數", fields_zh)
        self.assertIn("已核銷懸賞", fields_zh)
        self.assertIn("後續目標", fields_zh)
        self.assertEqual(footer_zh, "自動掛機運行正常")

        # en
        title_en, desc_en, fields_en, footer_en = format_milestone2(
            profile="test",
            fallback_mode="loop_battle",
            language="en",
            now_dt=datetime(2026, 9, 12, 9, 30, 0),
            cleared_count=5,
            cleared_quests=["Q1", "Q2"],
        )
        self.assertEqual(title_en, "All Daily Bounty Quests Completed")
        self.assertIn("Cleared Quests Count", fields_en)
        self.assertIn("Cleared Quests", fields_en)
        self.assertIn("Next Target", fields_en)
        self.assertEqual(footer_en, "Automation Running Normally")

    def test_format_deadline_alarm_bilingual(self):
        # zh-TW
        title_zh, reason_zh, fields_zh, desc_zh, footer_zh = format_daily_claim_deadline_alarm(
            profile="test",
            deadline_minutes=30,
            pending_subflows=["bulletin_board"],
            current_state="STATE_NAVIGATING",
            language="zh-TW",
            now_dt=datetime(2026, 9, 12, 8, 35, 0),
        )
        self.assertEqual(title_zh, "每日速領超時卡死警報")
        self.assertIn("超過 30 分鐘", reason_zh)
        self.assertIn("未完成子流程", fields_zh)
        self.assertEqual(footer_zh, "自動掛機需要人工介入處理")

        # en
        title_en, reason_en, fields_en, desc_en, footer_en = format_daily_claim_deadline_alarm(
            profile="test",
            deadline_minutes=30,
            pending_subflows=["bulletin_board"],
            current_state="STATE_NAVIGATING",
            language="en",
            now_dt=datetime(2026, 9, 12, 8, 35, 0),
        )
        self.assertEqual(title_en, "Daily Claim Deadline Exceeded")
        self.assertIn("within 30 minutes", reason_en)
        self.assertIn("Pending Subflows", fields_en)
        self.assertEqual(footer_en, "Automation Requires Manual Intervention")

    def test_format_supervisor_crash_alarm_bilingual(self):
        # zh-TW
        title_zh, reason_zh, fields_zh, desc_zh, footer_zh = format_supervisor_crash_alarm(
            profile="test",
            restarts=6,
            max_restarts=5,
            window_duration_str="15m",
            window_seconds=900.0,
            language="zh-TW",
            now_dt=datetime(2026, 9, 12, 10, 0, 0),
        )
        self.assertEqual(title_zh, "Supervisor 崩潰循環超限警報")
        self.assertIn("超過上限 5 次", reason_zh)
        self.assertIn("重啟次數", fields_zh)
        self.assertEqual(footer_zh, "自動掛機需要人工介入處理")

        # en
        title_en, reason_en, fields_en, desc_en, footer_en = format_supervisor_crash_alarm(
            profile="test",
            restarts=6,
            max_restarts=5,
            window_duration_str="15m",
            window_seconds=900.0,
            language="en",
            now_dt=datetime(2026, 9, 12, 10, 0, 0),
        )
        self.assertEqual(title_en, "Supervisor Crash Loop Exceeded")
        self.assertIn("exceeded 5 restarts", reason_en)
        self.assertIn("Restart Count", fields_en)
        self.assertEqual(footer_en, "Automation Requires Manual Intervention")

    def test_get_notification_language_and_profile_override(self):
        # Default global
        self.assertEqual(get_notification_language(None), "zh-TW")

        # Profile with language = "en"
        with patch("config.get_defaults_config", return_value={"notification": {"language": "en"}}):
            self.assertEqual(get_notification_language("en_profile"), "en")

        # Profile with invalid language -> Fail-Fast ValueError
        with patch("config.get_defaults_config", return_value={"notification": {"language": "invalid_lang"}}):
            with self.assertRaises(ValueError):
                get_notification_language("bad_profile")


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
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
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
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
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
        self.assertEqual(call_kwargs["details"].get("當前狀態機狀態") or call_kwargs["details"].get("Current State"), "NAVIGATING")

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
            history_store=JsonNotificationHistoryStore(history_file_path=os.path.join(self.test_dir, "clean_history.json")),
        )
        self.assertFalse(coord_clean_check := coord_clean.check_daily_claim_deadline(now_dt=dt_0836))

    def test_milestone_and_alarm_respects_language(self):
        dt_0820 = datetime(2026, 9, 12, 8, 20, 0)
        for sf in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            self.dm.record_subflow_completed(sf)

        # 1. Default zh-TW coordinator
        self.coordinator.evaluate_tier1_completion("bulletin_board", now_dt=dt_0820)
        self.mock_notifier.notify_milestone.assert_called_once()
        zh_call = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(zh_call["title"], "每日城鎮速領完成")
        self.assertEqual(zh_call["footer_text"], "自動掛機運行正常")

        # 2. English coordinator
        self.mock_notifier.reset_mock()
        en_coord = DailyPipelineNotifier(
            notification_port=self.mock_notifier,
            daily_manager=self.dm,
            profile="en_profile",
            history_store=JsonNotificationHistoryStore(history_file_path=os.path.join(self.test_dir, "en_history.json")),
            language="en",
        )
        en_coord.evaluate_tier1_completion("bulletin_board", now_dt=dt_0820)
        self.mock_notifier.notify_milestone.assert_called_once()
        en_call = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(en_call["title"], "Daily Claim Phase Completed")
        self.assertEqual(en_call["footer_text"], "Automation Running Normally")
        self.assertIn("Quests Accepted", en_call["fields"])

    def test_milestone_not_recorded_on_dispatch_failure(self):
        dt_0820 = datetime(2026, 9, 12, 8, 20, 0)
        self.mock_notifier.notify_milestone.return_value = NotificationResult(
            success=False, error="Connection refused"
        )
        res = self.coordinator.on_bounty_quests_cleared(now_dt=dt_0820)
        self.assertFalse(res.success)
        # Crucial invariant: network failure must NOT latch today's milestone
        self.assertTrue(self.coordinator.is_milestone_eligible("milestone2", dt_0820))
        history = self.coordinator.history_store.load_history()
        self.assertEqual(history.get("last_milestone2_date", ""), "")
        self.assertEqual(len(history.get("dispatched_messages", [])), 0)



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
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
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
        mock_machine.pop_and_next_town_subflow = MagicMock(
            side_effect=lambda: mock_machine.daily_pipeline_notifier.evaluate_tier1_completion()
        )

        handler = BulletinBoardHandler(machine=mock_machine)
        handler.accepted_quest_titles = ["清除骷髏", "清除蜘蛛"]

        # Trigger completion
        handler._record_completion()

        # Assert notify_milestone was called
        self.mock_notifier.notify_milestone.assert_called_once()
        call_kwargs = self.mock_notifier.notify_milestone.call_args[1]
        self.assertEqual(call_kwargs["title"], "每日城鎮速領完成")
        self.assertEqual(set(call_kwargs["fields"]["已接取懸賞"]), {"清除骷髏", "清除蜘蛛"})

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
        self.assertEqual(call_kwargs["title"], "每日懸賞任務已全部完成")

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


class TestDailyPipelineNotifierInterfaceParity(unittest.TestCase):
    """Verify NullDailyPipelineNotifier strictly implements all DailyPipelineNotifier public methods."""

    def test_null_object_implements_all_public_methods_with_exact_signatures(self):
        import inspect
        from states.daily_pipeline_notifier import DailyPipelineNotifier, NullDailyPipelineNotifier

        real_methods = {
            name: inspect.signature(getattr(DailyPipelineNotifier, name))
            for name, attr in inspect.getmembers(DailyPipelineNotifier, predicate=inspect.isfunction)
            if not name.startswith("_")
        }

        null_methods = {
            name: inspect.signature(getattr(NullDailyPipelineNotifier, name))
            for name, attr in inspect.getmembers(NullDailyPipelineNotifier, predicate=inspect.isfunction)
            if not name.startswith("_")
        }

        for method_name, real_sig in real_methods.items():
            self.assertIn(method_name, null_methods, f"NullDailyPipelineNotifier missing method: {method_name}")
            null_sig = null_methods[method_name]
            self.assertEqual(
                real_sig, null_sig,
                f"Signature mismatch for {method_name}: real={real_sig}, null={null_sig}"
            )


class TestProductionBootstrapWiring(unittest.TestCase):
    """Verify that production bootstrap explicitly injects real DailyPipelineNotifier (not Null)."""

    @patch("builtins.print")
    @patch("runtime.bootstrap.ScreenCapturer")
    @patch("runtime.bootstrap.TemplateMatcher")
    @patch("runtime.bootstrap.MouseController")
    @patch("runtime.bootstrap.check_mode_templates", return_value=[])
    @patch("runtime.bootstrap.os.path.exists", return_value=True)
    def test_bootstrap_injects_real_daily_pipeline_notifier(
        self, _exists, _tmpl, _mouse, _matcher, _capturer, _print
    ):
        from runtime.bootstrap import init_state_machine_system
        from states.daily_pipeline_notifier import DailyPipelineNotifier, NullDailyPipelineNotifier

        args = MagicMock()
        args.mode = "mix"
        args.title = "Blackfire Crusade"
        args.backend = False
        args.subflow = None
        args.profile = "native"
        args.monitor = 0
        args.interval = 0.05

        config = {"name": "Mix", "type": "mix", "auto_bread": False, "auto_diamond": False}

        sm = init_state_machine_system(args, config, target_hwnd=123)

        self.assertIsInstance(sm.daily_pipeline_notifier, DailyPipelineNotifier)
        self.assertNotIsInstance(sm.daily_pipeline_notifier, NullDailyPipelineNotifier)
        self.assertEqual(sm.daily_pipeline_notifier.profile, "native")
        self.assertIs(sm.daily_pipeline_notifier.daily_manager, sm.daily_manager)



class TestHistoricalMessageReconciliation(unittest.TestCase):
    """Verify 07:00 Desired-State Reconciliation and Crash Consistency invariants."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="reconcile_test_")
        self.history_file = os.path.join(self.test_dir, "notification_history.json")
        self.mock_port = MagicMock(spec=NotificationPort)
        self.mock_dm = MagicMock(spec=DailyManager)
        self.notifier = DailyPipelineNotifier(
            notification_port=self.mock_port,
            daily_manager=self.mock_dm,
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_track_dispatched_message(self):
        dt = datetime(2026, 9, 12, 10, 0)
        self.notifier.track_dispatched_message("msg_123", tag="milestone1", now_dt=dt)
        self.notifier.track_dispatched_message("msg_123", tag="milestone1", now_dt=dt)  # duplicate
        self.notifier.track_dispatched_message("", tag="invalid", now_dt=dt)  # empty

        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 1)
        item = self.notifier.history["dispatched_messages"][0]
        self.assertEqual(item["id"], "msg_123")
        self.assertEqual(item["date"], "2026-09-12")
        self.assertEqual(item["tag"], "milestone1")

        # Verify disk persistence
        reloaded = DailyPipelineNotifier(
            notification_port=self.mock_port,
            daily_manager=self.mock_dm,
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
        )
        self.assertEqual(len(reloaded.history["dispatched_messages"]), 1)
        self.assertEqual(reloaded.history["dispatched_messages"][0]["id"], "msg_123")

    def test_reconcile_before_0700_is_noop(self):
        # 06:59:59 should not run reconciliation
        dt = datetime(2026, 9, 12, 6, 59, 59)
        self.notifier.history["dispatched_messages"] = [
            {"id": "old_1", "date": "2026-09-11", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0}
        ]
        self.notifier._save_history()

        reconciled = self.notifier.reconcile_expired_messages(now_dt=dt)
        self.assertEqual(reconciled, 0)
        self.mock_port.delete_message.assert_not_called()
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 1)

    def test_reconcile_check_throttle_without_force(self):
        dt = datetime(2026, 9, 12, 7, 5, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_past_1", "date": "2026-09-10", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0},
            {"id": "msg_past_2", "date": "2026-09-11", "tag": "milestone2", "last_attempt_time": 0.0, "retry_after": 0.0},
        ]
        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=204)

        # 1st call executes check and deletes 1 message
        self.assertEqual(self.notifier.reconcile_expired_messages(now_dt=dt), 1)
        self.assertEqual(self.mock_port.delete_message.call_count, 1)

        # Immediate 2nd call without force is throttled by check_interval (600s / 10m) -> returns 0
        self.assertEqual(self.notifier.reconcile_expired_messages(now_dt=dt), 0)
        self.assertEqual(self.mock_port.delete_message.call_count, 1)

    def test_reconcile_after_0700_purges_expired_and_retains_today(self):
        # 07:05:00 on 2026-09-12: delete 2026-09-11 and 2026-09-10, retain 2026-09-12
        dt = datetime(2026, 9, 12, 7, 5, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_past_1", "date": "2026-09-10", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0},
            {"id": "msg_past_2", "date": "2026-09-11", "tag": "milestone2", "last_attempt_time": 0.0, "retry_after": 0.0},
            {"id": "msg_today", "date": "2026-09-12", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0},
        ]
        self.notifier._save_history()

        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=204)

        # One-delete-per-call: step 1 deletes msg_past_1
        res1 = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(res1, 1)
        self.assertEqual(self.mock_port.delete_message.call_count, 1)

        # Step 2 deletes msg_past_2
        res2 = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(res2, 1)
        self.assertEqual(self.mock_port.delete_message.call_count, 2)

        # Step 3: only msg_today remains, nothing to delete
        res3 = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(res3, 0)
        self.assertEqual(self.mock_port.delete_message.call_count, 2)

        called_ids = [call[0][0] for call in self.mock_port.delete_message.call_args_list]
        self.assertIn("msg_past_1", called_ids)
        self.assertIn("msg_past_2", called_ids)
        self.assertNotIn("msg_today", called_ids)

        # Ensure only today's message remains in memory and on disk
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 1)
        self.assertEqual(self.notifier.history["dispatched_messages"][0]["id"], "msg_today")

        reloaded = DailyPipelineNotifier(
            notification_port=self.mock_port,
            daily_manager=self.mock_dm,
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
        )
        self.assertEqual(len(reloaded.history["dispatched_messages"]), 1)
        self.assertEqual(reloaded.history["dispatched_messages"][0]["id"], "msg_today")

    def test_reconcile_404_treated_as_idempotent_success(self):
        dt = datetime(2026, 9, 12, 7, 10, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_gone", "date": "2026-09-11", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0}
        ]
        self.notifier._save_history()

        # Discord returns 404
        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=404)

        reconciled = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(reconciled, 1)
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 0)

        # Check persistence
        reloaded = DailyPipelineNotifier(
            notification_port=self.mock_port,
            daily_manager=self.mock_dm,
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
        )
        self.assertEqual(len(reloaded.history["dispatched_messages"]), 0)

    def test_reconcile_cooldown_and_429_retry_after(self):
        dt = datetime(2026, 9, 12, 7, 15, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_rate_limited", "date": "2026-09-11", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0}
        ]
        self.notifier._save_history()

        # First attempt: 429 Too Many Requests with retry_after 120s
        self.mock_port.delete_message.return_value = DeleteResult(
            success=False, status_code=429, retry_after_seconds=120.0, error="Rate limited"
        )

        reconciled = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(reconciled, 0)
        self.mock_port.delete_message.assert_called_once()
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 1)

        # Second attempt before cooldown expires is skipped by monotonic cooldown
        self.mock_port.delete_message.reset_mock()
        reconciled_early = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(reconciled_early, 0)
        self.mock_port.delete_message.assert_not_called()

    def test_crash_consistency_recovery(self):
        dt = datetime(2026, 9, 12, 7, 20, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_unconfirmed", "date": "2026-09-11", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0}
        ]
        self.notifier._save_history()

        # 1. Crash-before-save simulation:
        # Delete succeeded at Discord side, but app died before saving history.
        # When app restarts, Discord returns 404 (already deleted).
        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=404)
        reconciled = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(reconciled, 1)
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 0)

        # 2. Crash-after-save simulation:
        # Message A was evicted and saved to disk. Now app crashes and restarts.
        restart_notifier = DailyPipelineNotifier(
            notification_port=self.mock_port,
            daily_manager=self.mock_dm,
            history_store=JsonNotificationHistoryStore(history_file_path=self.history_file),
        )
        self.assertEqual(len(restart_notifier.history["dispatched_messages"]), 0)
        self.mock_port.delete_message.reset_mock()

        # Reconcile again: queue is empty, no delete calls are made
        reconciled_after_restart = restart_notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(reconciled_after_restart, 0)
        self.mock_port.delete_message.assert_not_called()

    def test_iteration_safety_multiple_deletions(self):
        dt = datetime(2026, 9, 12, 7, 30, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": f"msg_old_{i}", "date": "2026-09-10", "tag": f"tag_{i}", "last_attempt_time": 0.0, "retry_after": 0.0}
            for i in range(5)
        ]
        self.notifier._save_history()

        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=204)
        deleted_count = 0
        while True:
            res = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
            if res == 0:
                break
            deleted_count += res

        self.assertEqual(deleted_count, 5)
        self.assertEqual(len(self.notifier.history["dispatched_messages"]), 0)

    def test_daily_completion_latch_skips_further_checks(self):
        dt = datetime(2026, 9, 12, 7, 5, 0)
        self.notifier.history["dispatched_messages"] = [
            {"id": "msg_past", "date": "2026-09-11", "tag": "milestone1", "last_attempt_time": 0.0, "retry_after": 0.0},
        ]
        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=204)

        # Call 1: deletes the single expired message -> triggers latch to 2026-09-12
        res1 = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(res1, 1)
        self.assertEqual(self.notifier.history.get("last_reconciled_date"), "2026-09-12")

        # Call 2: even with force=False and time passed, latch causes immediate O(1) early return 0
        self.notifier._next_reconcile_check_ts = 0.0  # bypass throttle to test latch directly
        res2 = self.notifier.reconcile_expired_messages(now_dt=dt, force=False)
        self.assertEqual(res2, 0)
        self.assertEqual(self.mock_port.delete_message.call_count, 1)  # No extra delete call

    def test_historical_message_injection_invalidates_latch(self):
        dt = datetime(2026, 9, 12, 10, 0, 0)
        # Initially latched as clean today
        self.notifier.history["last_reconciled_date"] = "2026-09-12"
        self.notifier.history["dispatched_messages"] = []
        self.notifier._save_history()

        # Invariant check: Injected/recovered historical message from yesterday
        past_dt = datetime(2026, 9, 11, 20, 0, 0)
        self.notifier.track_dispatched_message("msg_injected", tag="recovered", now_dt=past_dt)

        # Latch must be automatically invalidated (reset to "")
        self.assertEqual(self.notifier.history.get("last_reconciled_date"), "")

        # Reconcile can now clean it up
        self.mock_port.delete_message.return_value = DeleteResult(success=True, status_code=204)
        res = self.notifier.reconcile_expired_messages(now_dt=dt, force=True)
        self.assertEqual(res, 1)
        self.mock_port.delete_message.assert_called_once_with("msg_injected")
        # And latched again once clean
        self.assertEqual(self.notifier.history.get("last_reconciled_date"), "2026-09-12")

    def test_null_daily_pipeline_notifier_reconcile_and_track_noop(self):
        null_notifier = NullDailyPipelineNotifier()
        null_notifier.track_dispatched_message("123", tag="test")
        self.assertEqual(null_notifier.reconcile_expired_messages(), 0)
        self.assertEqual(null_notifier.get_today_date_tag(), "")


if __name__ == "__main__":
    unittest.main()


