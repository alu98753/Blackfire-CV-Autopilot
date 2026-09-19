import unittest
from unittest.mock import MagicMock, call, patch

from states.handlers.demon_lords import DemonLordsHandler, DemonSubScene
from utils.navigation_catalog import demon_lord_navigation_catalog
from utils.scene_snapshot import SceneSnapshot, TabId
from utils.scene_types import SceneId
from utils.shared_card_navigator import CardNavigatorState, SwipeDirection


class TestDemonLordSharedNavigationIntegration(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.mouse = MagicMock()
        self.machine.matcher = MagicMock()
        self.machine.config = {
            "targets": ["boss_c", "boss_b"],
            "target_boss": "boss_c",
            "bosses": {
                "boss_a": {"template": "demon_lords/boss_a.png", "name": "A"},
                "boss_b": {"template": "demon_lords/boss_b.png", "name": "B"},
                "boss_c": {"template": "demon_lords/boss_c.png", "name": "C"},
            },
            "stone_selection": {},
        }
        self.machine.daily_manager = MagicMock()
        self.machine.daily_manager.is_demon_lords_available.return_value = (True, "ok")
        self.machine.daily_manager.get_available_demon_lords.return_value = ["boss_c"]
        self.handler = DemonLordsHandler(self.machine)
        self.rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.screen = object()
        self.catalog = demon_lord_navigation_catalog(self.machine.config["bosses"])

    def _evidence(self, visible=()):
        visible = set(visible)

        def match(_screen, template, **_kwargs):
            if template in visible:
                return (100, 200), 0.95
            return None, 0.0

        self.machine.matcher.match.side_effect = match

    @patch("states.handlers.demon_lords.os.path.exists", return_value=True)
    @patch("states.handlers.demon_lords.time.sleep")
    def test_visible_target_clicks_without_reset_and_keeps_stone_handoff(
        self, _sleep, _exists
    ):
        self._evidence(["demon_lords/boss_c.png"])

        handled = self.handler._step_select_boss_card(self.screen, self.rect)

        self.assertTrue(handled)
        self.machine.mouse.drag.assert_not_called()
        self.machine.mouse.click.assert_called_once_with(100, 200)
        self.assertEqual(self.handler.current_target_boss, "boss_c")
        self.assertIsNotNone(self.handler.pending_stone_queue)
        self.assertIsNone(self.handler.demon_card_navigator)

    @patch("states.handlers.demon_lords.time.sleep")
    def test_lower_visible_index_swipes_toward_higher_target(self, _sleep):
        self._evidence(["demon_lords/boss_a.png"])

        self.assertTrue(self.handler._step_select_boss_card(self.screen, self.rect))
        self.assertEqual(
            self.handler.demon_card_navigator.swipe_history,
            (SwipeDirection.LEFT,),
        )

    @patch("states.handlers.demon_lords.time.sleep")
    def test_higher_visible_index_swipes_toward_lower_target(self, _sleep):
        self.machine.daily_manager.get_available_demon_lords.return_value = ["boss_a"]
        self._evidence(["demon_lords/boss_c.png"])

        self.assertTrue(self.handler._step_select_boss_card(self.screen, self.rect))
        self.assertEqual(
            self.handler.demon_card_navigator.swipe_history,
            (SwipeDirection.RIGHT,),
        )

    @patch("states.handlers.demon_lords.time.sleep")
    def test_tracking_miss_repeats_direction_then_relocalizes(self, _sleep):
        self._evidence(["demon_lords/boss_a.png"])
        self.handler._step_select_boss_card(self.screen, self.rect)
        navigator = self.handler.demon_card_navigator

        self._evidence([])
        for _ in range(len(self.catalog) - 1):
            self.assertTrue(self.handler._step_select_boss_card(self.screen, self.rect))
            self.assertEqual(navigator.swipe_history[-1], SwipeDirection.LEFT)

        self.machine.mouse.reset_mock()
        self.assertTrue(self.handler._step_select_boss_card(self.screen, self.rect))
        self.assertEqual(navigator.state, CardNavigatorState.RELOCALIZE)
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.demon_lords.CardListNavigator.align_first_card")
    def test_no_localization_evidence_uses_reset_left_fallback(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self._evidence([])
        align.return_value = (CardAlignmentStatus.RETRYING, 1, 0.0)

        self.assertTrue(self.handler._step_select_boss_card(self.screen, self.rect))
        align.assert_called_once()
        self.machine.mouse.drag.assert_not_called()
        self.assertEqual(self.handler.card_reset_attempts, 1)

    @patch("states.handlers.demon_lords.time.sleep")
    def test_target_change_replaces_session_and_catalog_keeps_physical_index(self, _sleep):
        self._evidence(["demon_lords/boss_a.png"])
        self.handler._step_select_boss_card(self.screen, self.rect)
        first_navigator = self.handler.demon_card_navigator

        self.machine.daily_manager.get_available_demon_lords.return_value = ["boss_b"]
        self._evidence(["demon_lords/boss_a.png"])
        self.handler._step_select_boss_card(self.screen, self.rect)

        self.assertIsNot(self.handler.demon_card_navigator, first_navigator)
        self.assertEqual(self.handler.demon_card_target_key, "boss_b")
        self.assertEqual(
            [(entry.key, entry.index) for entry in self.catalog],
            [("boss_a", 1), ("boss_b", 2), ("boss_c", 3)],
        )

    @patch("states.handlers.demon_lords.execute_lobby_tab_route", return_value=False)
    def test_leaving_card_selection_clears_session(self, _route):
        self.machine.daily_manager.is_demon_lords_available.return_value = (True, "ok")
        self.handler.demon_card_navigator = object()
        self.handler.demon_card_target_key = "boss_c"
        self.handler.classify_subscene = MagicMock(return_value=DemonSubScene.UNKNOWN)

        self.handler.handle(self.screen, self.rect)

        self.assertIsNone(self.handler.demon_card_navigator)
        self.assertIsNone(self.handler.demon_card_target_key)

    def test_reset_state_clears_session(self):
        self.handler.demon_card_navigator = object()
        self.handler.demon_card_target_key = "boss_c"

        self.handler.reset_state()

        self.assertIsNone(self.handler.demon_card_navigator)
        self.assertIsNone(self.handler.demon_card_target_key)

    @patch("states.handlers.demon_lords.execute_lobby_tab_route", return_value=False)
    @patch("states.handlers.demon_lords.time.sleep")
    def test_real_handler_tracking_matches_only_committed_target(self, _sleep, _route):
        self.handler._handle_popup_guards = MagicMock(return_value=False)
        self.handler.classify_subscene = MagicMock(
            return_value=DemonSubScene.CARD_SELECTION
        )
        self._evidence(["demon_lords/boss_a.png"])

        self.handler.handle(self.screen, self.rect)
        self.assertTrue(self.handler.demon_card_session.owns_tracking)

        self.machine.matcher.reset_mock()
        self._evidence([])
        self.handler.handle(self.screen, self.rect)

        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            ["demon_lords/boss_c.png"],
        )
        self.handler.classify_subscene.assert_called_once()

    @patch("states.handlers.demon_lords.time.sleep")
    def test_policy_target_change_invalidates_before_old_target_match(self, _sleep):
        scene = SceneSnapshot(
            frame_id=1,
            captured_at=0.0,
            scene=SceneId.DEMON_LORD_SELECT,
            active_tabs=frozenset({TabId.DEMON_LORD}),
        )
        self._evidence(["demon_lords/boss_a.png"])
        self.handler._step_select_boss_card(
            self.screen, self.rect, verified_scene=scene
        )
        self.machine.daily_manager.get_available_demon_lords.return_value = ["boss_b"]
        self.machine.matcher.reset_mock()

        self.assertFalse(self.handler._handle_demon_tracking_fast_path(self.screen, self.rect))
        self.assertIsNone(self.handler.demon_card_session)
        self.assertNotIn(
            "demon_lords/boss_c.png",
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
        )


if __name__ == "__main__":
    unittest.main()
