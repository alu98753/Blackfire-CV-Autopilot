import unittest
from unittest.mock import MagicMock, call, patch

import numpy as np

from states.handlers.navigation import NavigationHandler
from utils.dungeon_catalog import DungeonCatalog
from utils.navigation_catalog import dungeon_navigation_catalog
from utils.scene_detector import SceneInfo, SceneType
from utils.shared_card_navigator import CardNavigatorState, SwipeDirection


class TestDungeonSharedNavigationIntegration(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.mouse = MagicMock()
        self.machine.matcher = MagicMock()
        self.machine.capturer = MagicMock()
        self.machine.config = {
            "type": "dungeon",
            "dungeon_index": 3,
            "dungeon_names": ["A", "B", "C", "D"],
            "dungeon_entries": [
                "dungeons/a.png",
                "dungeons/b.png",
                "dungeons/c.png",
                "dungeons/d.png",
            ],
        }
        self.machine.need_bag_cleaning = False
        self.machine.need_diamond_collection = False
        self.machine.need_bread_collection = False
        self.machine.enable_bread = False
        self.machine.is_daily_pipeline_active.return_value = False
        self.machine.dungeon_cooldowns = {}
        self.machine.stamina_retreat_start_time = None
        self.machine.original_config = None
        self.handler = NavigationHandler(self.machine)
        self.rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.screen = object()
        self.scene = SceneInfo(
            scene_type=SceneType.LOBBY_DUNGEON,
            is_lobby=True,
            active_tabs=["dungeon"],
        )
        self.catalog = dungeon_navigation_catalog(
            self.machine.config["dungeon_names"],
            self.machine.config["dungeon_entries"],
        )

    def _evidence(self, visible=()):
        visible = set(visible)

        def match(_screen, template, **_kwargs):
            if template in visible:
                return (100, 200), 0.95
            return None, 0.0

        self.machine.matcher.match.side_effect = match

    @patch("states.handlers.navigation.time.sleep")
    def test_fixed_target_visible_found_without_reset_or_unrelated_scan(self, _sleep):
        self._evidence(["dungeons/c.png"])

        result = self.handler._handle_fixed_dungeon_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertEqual(result, "FOUND")
        self.machine.mouse.drag.assert_not_called()
        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            ["dungeons/c.png"],
        )
        self.assertIsNone(self.handler.dungeon_card_navigator)

    @patch("states.handlers.navigation.time.sleep")
    def test_lower_visible_index_swipes_toward_higher_target(self, _sleep):
        self._evidence(["dungeons/a.png"])

        self.assertEqual(
            self.handler._handle_fixed_dungeon_navigation(
                self.screen, self.rect, self.scene
            ),
            "HANDLED",
        )
        self.assertEqual(
            self.handler.dungeon_card_navigator.swipe_history,
            (SwipeDirection.LEFT,),
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_higher_visible_index_swipes_toward_lower_target(self, _sleep):
        self.machine.config["dungeon_index"] = 1
        self._evidence(["dungeons/c.png"])

        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)

        self.assertEqual(
            self.handler.dungeon_card_navigator.swipe_history,
            (SwipeDirection.RIGHT,),
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_tracking_misses_repeat_direction_and_only_match_target(self, _sleep):
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        navigator = self.handler.dungeon_card_navigator
        self.machine.matcher.reset_mock()
        self._evidence([])

        for _ in range(len(self.catalog) - 1):
            self.assertEqual(
                self.handler._handle_fixed_dungeon_navigation(
                    self.screen, self.rect, self.scene
                ),
                "HANDLED",
            )
            self.assertEqual(navigator.swipe_history[-1], SwipeDirection.LEFT)

        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            ["dungeons/c.png"] * (len(self.catalog) - 1),
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_miss_bound_relocalizes_without_blind_swipe(self, _sleep):
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        navigator = self.handler.dungeon_card_navigator
        self._evidence([])

        for _ in range(len(self.catalog)):
            result = self.handler._handle_fixed_dungeon_navigation(
                self.screen, self.rect, self.scene
            )

        self.assertEqual(result, "HANDLED")
        self.assertEqual(navigator.state, CardNavigatorState.RELOCALIZE)
        self.assertEqual(len(navigator.swipe_history), len(self.catalog))

    @patch("states.handlers.navigation.CardListNavigator.align_first_card")
    def test_no_localization_evidence_uses_bounded_reset_left(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self._evidence([])
        align.return_value = (CardAlignmentStatus.RETRYING, 1, 0.0)

        result = self.handler._handle_fixed_dungeon_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertEqual(result, "HANDLED")
        align.assert_called_once()
        self.machine.mouse.drag.assert_not_called()
        self.assertEqual(self.handler.card_alignment_attempts, 1)

    @patch("states.handlers.navigation.time.sleep")
    def test_target_change_and_leaving_dungeon_clear_session(self, _sleep):
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        first_navigator = self.handler.dungeon_card_navigator

        self.machine.config["dungeon_index"] = 4
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        self.assertIsNot(self.handler.dungeon_card_navigator, first_navigator)
        self.assertEqual(self.handler.dungeon_card_target_key, "D")

        self.handler._handle_fixed_dungeon_navigation(
            self.screen,
            self.rect,
            SceneInfo(scene_type=SceneType.LOBBY_STAGE, active_tabs=["stage"]),
        )
        self.assertIsNone(self.handler.dungeon_card_navigator)
        self.assertIsNone(self.handler.dungeon_card_target_key)

    def test_greedy_without_committed_target_keeps_legacy_boundary(self):
        self.machine.config["greedy_dungeon"] = True
        self._evidence(["dungeons/a.png"])

        result = self.handler._handle_fixed_dungeon_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertIsNone(result)
        self.assertIsNone(self.handler.dungeon_card_navigator)

    def test_dungeon_catalog_remains_index_authority(self):
        self.assertEqual(
            [(entry.index, entry.key, entry.template) for entry in self.catalog],
            [
                (1, "A", "dungeons/a.png"),
                (2, "B", "dungeons/b.png"),
                (3, "C", "dungeons/c.png"),
                (4, "D", "dungeons/d.png"),
            ],
        )
        self.assertEqual(
            DungeonCatalog.resolve_index_from_nav_path(
                ["dungeons/c.png"], self.machine.config["dungeon_entries"]
            ),
            3,
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_target_change_invalidates_before_old_target_match(self, _sleep):
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        self.machine.config["dungeon_index"] = 4
        self.machine.matcher.reset_mock()

        self.assertFalse(
            self.handler._handle_dungeon_tracking_fast_path(self.screen, self.rect)
        )
        self.assertIsNone(self.handler.dungeon_card_session)
        self.assertNotIn(
            "dungeons/c.png",
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_same_index_with_changed_semantic_entry_invalidates(self, _sleep):
        self._evidence(["dungeons/a.png"])
        self.handler._handle_fixed_dungeon_navigation(self.screen, self.rect, self.scene)
        self.machine.config["dungeon_entries"][2] = "dungeons/c_reloaded.png"
        self.machine.matcher.reset_mock()

        self.assertFalse(
            self.handler._handle_dungeon_tracking_fast_path(self.screen, self.rect)
        )
        self.assertIsNone(self.handler.dungeon_card_session)
        self.assertNotIn(
            "dungeons/c.png",
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
        )

    @patch.object(NavigationHandler, "_handle_primary_card_alignment", return_value=False)
    @patch("states.handlers.navigation.NavigationDecisionExecutor.execute", return_value=False)
    @patch("states.handlers.navigation.os.path.exists", return_value=False)
    @patch("states.handlers.navigation.time.sleep")
    def test_real_handler_tracking_matches_only_committed_target(
        self, _sleep, _exists, _route, _alignment
    ):
        screen = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.machine.matcher
        self.handler.scene_detector.detect.return_value = self.scene
        self._evidence(["dungeons/a.png"])

        self.handler.handle(screen, self.rect)
        self.assertTrue(self.handler.dungeon_card_session.owns_tracking)

        self.machine.matcher.reset_mock()
        self._evidence([])
        self.handler.handle(screen, self.rect)

        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            ["dungeons/c.png"],
        )
        self.handler.scene_detector.detect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
