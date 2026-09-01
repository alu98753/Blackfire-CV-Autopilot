import unittest
from unittest.mock import MagicMock

from config import get_navigation_progress_settings
from states.navigation_intent import ActionId, IntentId, PostconditionId
from states.navigation_progress import (
    CollectionOutcome,
    NavigationProgress,
    NavigationProgressSettings,
    ProgressStatus,
)
from states.state_machine import GameStateMachine
from utils.scene_snapshot import SceneId, SceneSnapshot


class TestBehaviorNavigationProgress(unittest.TestCase):
    def setUp(self):
        self.progress = NavigationProgress(
            NavigationProgressSettings(
                action_timeout_seconds=5.0,
                action_max_attempts=2,
                collection_backoff_seconds=60.0,
                collection_recovery_failure_limit=2,
            )
        )

    def _begin_diamond(self, frame_id, now):
        return self.progress.begin(
            IntentId.COLLECT_DIAMOND,
            ActionId.OPEN_DIAMOND,
            PostconditionId.DIAMOND_WINDOW,
            frame_id,
            now,
        )

    def test_only_one_action_is_in_flight(self):
        first = self._begin_diamond(1, 10.0)
        second = self.progress.begin(
            IntentId.COLLECT_BREAD,
            ActionId.OPEN_BREAD,
            PostconditionId.BREAD_WINDOW,
            1,
            11.0,
        )

        self.assertNotEqual(first, second)
        self.assertEqual(self.progress.in_flight, second)

    def test_new_frame_with_expected_scene_confirms_progress(self):
        self._begin_diamond(1, 10.0)
        scene = SceneSnapshot(2, 11.0, SceneId.DIAMOND_WINDOW)

        status = self.progress.observe(scene, 11.0)

        self.assertEqual(status, ProgressStatus.PROGRESSED)
        self.assertIsNone(self.progress.in_flight)

    def test_same_frame_cannot_confirm_a_click(self):
        self._begin_diamond(1, 10.0)
        scene = SceneSnapshot(1, 10.0, SceneId.DIAMOND_WINDOW)

        self.assertEqual(
            self.progress.observe(scene, 20.0), ProgressStatus.WAITING
        )

    def test_repeated_timeout_defers_collection_without_completing_it(self):
        self._begin_diamond(1, 10.0)
        unknown_2 = SceneSnapshot(2, 16.0, SceneId.UNKNOWN)
        self.assertEqual(
            self.progress.observe(unknown_2, 16.0),
            ProgressStatus.TIMED_OUT,
        )

        self._begin_diamond(2, 16.0)
        unknown_3 = SceneSnapshot(3, 22.0, SceneId.UNKNOWN)
        self.assertEqual(
            self.progress.observe(unknown_3, 22.0),
            ProgressStatus.DEFERRED,
        )
        self.assertTrue(self.progress.is_deferred(IntentId.COLLECT_DIAMOND, 81.9))
        self.assertFalse(self.progress.is_deferred(IntentId.COLLECT_DIAMOND, 82.0))
        self.assertEqual(
            self.progress.outcomes[IntentId.COLLECT_DIAMOND],
            CollectionOutcome.DEFERRED,
        )

    def test_success_clears_backoff_and_records_outcome(self):
        self.progress.defer(IntentId.COLLECT_BREAD, 10.0)

        self.progress.complete(
            IntentId.COLLECT_BREAD, CollectionOutcome.COOLDOWN
        )

        self.assertFalse(self.progress.is_deferred(IntentId.COLLECT_BREAD, 11.0))
        self.assertEqual(
            self.progress.outcomes[IntentId.COLLECT_BREAD],
            CollectionOutcome.COOLDOWN,
        )

    def test_repeated_defer_requests_recovery_once(self):
        self.progress.defer(IntentId.COLLECT_BREAD, 10.0)
        self.assertIsNone(self.progress.take_recovery_intent())
        self.progress.defer(IntentId.COLLECT_BREAD, 80.0)

        self.assertEqual(
            self.progress.take_recovery_intent(), IntentId.COLLECT_BREAD
        )
        self.assertIsNone(self.progress.take_recovery_intent())

    def test_runtime_settings_are_loaded_from_toml(self):
        settings = get_navigation_progress_settings()

        self.assertGreater(settings["action_timeout_seconds"], 0)
        self.assertGreater(settings["action_max_attempts"], 0)
        self.assertGreater(settings["collection_backoff_seconds"], 0)
        self.assertGreater(settings["collection_recovery_failure_limit"], 0)

    def test_tier4_fallback_does_not_destroy_pending_collection_intents(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.primary_config = {
            "name": "Tier 4 baseline",
            "type": "mix",
            "enable_dungeon": False,
            "enable_stage_farming": True,
        }
        machine.need_diamond_collection = True
        machine.enable_bread = True
        machine.need_bread_collection = True

        machine.apply_tier4_fallback_config()

        self.assertTrue(machine.need_diamond_collection)
        self.assertTrue(machine.need_bread_collection)


if __name__ == "__main__":
    unittest.main()
