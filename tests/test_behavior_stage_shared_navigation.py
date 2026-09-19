import unittest
from unittest.mock import MagicMock, patch

from config import BASE_STAGE_LEVELS
from states.handlers.navigation import NavigationHandler
from utils.navigation_catalog import stage_navigation_catalog
from utils.scene_detector import SceneInfo, SceneType
from utils.shared_card_navigator import CardNavigatorState, SwipeDirection


class TestStageSharedNavigationIntegration(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.mouse = MagicMock()
        self.machine.matcher = MagicMock()
        self.machine.capturer = MagicMock()
        self.machine.need_bag_cleaning = False
        self.machine.need_diamond_collection = False
        self.machine.need_bread_collection = False
        self.machine.enable_bread = False
        self.machine.is_daily_pipeline_active.return_value = False
        self.machine.has_available_dungeon.return_value = False
        self.machine.config = {
            "type": "stage",
            "tier4_stage_level": "6",
            "stage_entry": "stages/level6_ice_cave.png",
            "stage_navigation_path": [
                "stages/level6_ice_cave.png",
                "stages/stage_label.png",
                "stages/first_stage.png",
            ],
            "navigation_path": [
                "stages/level6_ice_cave.png",
                "stages/stage_label.png",
                "stages/first_stage.png",
            ],
        }
        self.handler = NavigationHandler(self.machine)
        self.rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.screen = object()
        self.scene = SceneInfo(
            scene_type=SceneType.LOBBY_STAGE,
            is_lobby=True,
            active_tabs=["stage"],
        )
        self.catalog = stage_navigation_catalog(BASE_STAGE_LEVELS)
        self.target = "stages/level6_ice_cave.png"

    def _evidence(self, visible=()):
        visible = set(visible)

        def match(_screen, template, **_kwargs):
            if template in visible:
                return (100, 200), 0.95
            return None, 0.0

        self.machine.matcher.match.side_effect = match

    @patch("states.handlers.navigation.time.sleep")
    def test_initial_target_visible_hands_back_without_reset(self, _sleep):
        self._evidence([self.target])

        handled = self.handler._handle_stage_shared_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertFalse(handled)
        self.assertTrue(self.handler._stage_card_handoff)
        self.assertIsNone(self.handler.stage_card_navigator)
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.navigation.time.sleep")
    def test_lower_visible_card_uses_common_higher_index_swipe(self, _sleep):
        self._evidence(["stages/level1_sky_plains.png"])

        self.assertTrue(
            self.handler._handle_stage_shared_navigation(
                self.screen, self.rect, self.scene
            )
        )

        self.assertEqual(
            self.handler.stage_card_navigator.swipe_history,
            (SwipeDirection.LEFT,),
        )
        self.machine.mouse.drag.assert_called_once_with(
            600, 400, 400, 400, duration=0.8, inertia=False
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_higher_visible_card_uses_common_lower_index_swipe(self, _sleep):
        self._evidence(["stages/level8_fiery_volcano.png"])

        self.assertTrue(
            self.handler._handle_stage_shared_navigation(
                self.screen, self.rect, self.scene
            )
        )

        self.assertEqual(
            self.handler.stage_card_navigator.swipe_history,
            (SwipeDirection.RIGHT,),
        )
        self.machine.mouse.drag.assert_called_once_with(
            400, 400, 600, 400, duration=0.8, inertia=False
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_tracking_miss_repeats_direction_then_relocalizes_at_bound(self, _sleep):
        self._evidence(["stages/level1_sky_plains.png"])
        self.handler._handle_stage_shared_navigation(self.screen, self.rect, self.scene)
        navigator = self.handler.stage_card_navigator

        self._evidence([])
        for _ in range(len(self.catalog) - 1):
            result = navigator.observe(self.screen, self.machine.matcher)
            self.assertEqual(result.state, CardNavigatorState.TRACKING)
            self.assertEqual(result.direction, SwipeDirection.LEFT)
            self.assertIsNotNone(result.swipe_request)
            result.swipe_request.execute(self.machine.mouse, self.rect)

        result = navigator.observe(self.screen, self.machine.matcher)
        self.assertEqual(result.state, CardNavigatorState.RELOCALIZE)
        self.assertIsNone(result.swipe_request)
        self.assertEqual(len(navigator.swipe_history), len(self.catalog))

    @patch("states.handlers.navigation.CardListNavigator.align_first_card")
    def test_localization_without_evidence_uses_bounded_reset_left(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self._evidence([])
        align.return_value = (CardAlignmentStatus.RETRYING, 1, 0.0)

        handled = self.handler._handle_stage_shared_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertTrue(handled)
        align.assert_called_once()
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.navigation.time.sleep")
    def test_target_change_replaces_session_and_leaving_stage_clears_it(self, _sleep):
        self._evidence(["stages/level1_sky_plains.png"])
        self.handler._handle_stage_shared_navigation(self.screen, self.rect, self.scene)
        first_navigator = self.handler.stage_card_navigator

        self.machine.config["tier4_stage_level"] = "7"
        self.machine.config["stage_entry"] = "stages/level7_forgotten_wasteland.png"
        self._evidence(["stages/level1_sky_plains.png"])
        self.handler._handle_stage_shared_navigation(self.screen, self.rect, self.scene)

        self.assertIsNot(self.handler.stage_card_navigator, first_navigator)
        self.assertEqual(self.handler.stage_card_target_key, "7")

        self.handler._handle_stage_shared_navigation(
            self.screen,
            self.rect,
            SceneInfo(scene_type=SceneType.LOBBY_OTHER, active_tabs=[]),
        )
        self.assertIsNone(self.handler.stage_card_navigator)
        self.assertIsNone(self.handler.stage_card_target_key)

    @patch.object(NavigationHandler, "_handle_primary_card_alignment")
    @patch("states.handlers.navigation.time.sleep")
    def test_handle_handoff_preserves_existing_stage_flow(self, _sleep, legacy_alignment):
        legacy_alignment.return_value = False
        self._evidence([self.target, "stages/first_stage.png"])
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.machine.matcher
        self.handler.scene_detector.detect.return_value = self.scene

        self.handler.handle(self.screen, self.rect)

        self.machine.mouse.click.assert_called_once()
        legacy_alignment.assert_not_called()
        self.assertIsNone(self.handler.stage_card_navigator)


if __name__ == "__main__":
    unittest.main()
