import unittest
from unittest.mock import MagicMock, call, patch

from states.handlers.lord_boss import LordBossHandler
from utils.navigation_catalog import lord_navigation_catalog
from utils.shared_card_navigator import CardNavigatorState, SwipeDirection


class TestLordSharedNavigationIntegration(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.mouse = MagicMock()
        self.machine.matcher = MagicMock()
        self.machine.daily_manager = MagicMock()
        self.machine.config = {
            "bosses": {
                "boss_a": {"template": "lords/boss_a.png"},
                "boss_b": {"template": "lords/boss_b.png"},
                "boss_c": {"template": "lords/boss_c.png"},
            },
            "entry_after_btn": "load/Lord_entry_after.png",
            "entry_btn": "load/Lord_entry.png",
        }
        self.machine.get_available_selected_lord_bosses.return_value = ["boss_c"]
        self.handler = LordBossHandler(self.machine)
        self.rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.screen = object()
        self.catalog = lord_navigation_catalog(self.machine.config["bosses"])

    def _evidence(self, visible=()):
        visible = set(visible)

        def match(_screen, template, **_kwargs):
            if template in visible:
                return (100, 200), 0.95
            return None, 0.0

        self.machine.matcher.match.side_effect = match

    def _navigate(self):
        return self.handler._handle_lord_shared_navigation(
            self.screen,
            self.rect,
            True,
            self.machine.get_available_selected_lord_bosses.return_value,
        )

    @patch("states.handlers.lord_boss.time.sleep")
    def test_visible_target_uses_full_catalog_without_reset(self, _sleep):
        self._evidence(["lords/boss_c.png"])

        result = self._navigate()

        self.assertEqual(result, "FOUND")
        self.machine.mouse.drag.assert_not_called()
        self.assertIsNone(self.handler.lord_card_navigator)
        self.assertEqual(self.handler.lord_navigation_target, "boss_c")
        self.assertEqual(
            [(entry.key, entry.index) for entry in self.catalog],
            [("boss_a", 1), ("boss_b", 2), ("boss_c", 3)],
        )

    @patch("states.handlers.lord_boss.time.sleep")
    def test_lower_visible_index_swipes_toward_higher_target(self, _sleep):
        self._evidence(["lords/boss_a.png"])

        self.assertEqual(self._navigate(), "HANDLED")
        self.assertEqual(
            self.handler.lord_card_navigator.swipe_history,
            (SwipeDirection.LEFT,),
        )

    @patch("states.handlers.lord_boss.time.sleep")
    def test_higher_visible_index_swipes_toward_lower_target(self, _sleep):
        self.machine.get_available_selected_lord_bosses.return_value = ["boss_a"]
        self._evidence(["lords/boss_c.png"])

        self.assertEqual(self._navigate(), "HANDLED")
        self.assertEqual(
            self.handler.lord_card_navigator.swipe_history,
            (SwipeDirection.RIGHT,),
        )

    @patch("states.handlers.lord_boss.time.sleep")
    def test_tracking_miss_repeats_direction_then_relocalizes(self, _sleep):
        self._evidence(["lords/boss_a.png"])
        self._navigate()
        navigator = self.handler.lord_card_navigator
        self._evidence([])

        for _ in range(len(self.catalog) - 1):
            self.assertEqual(self._navigate(), "HANDLED")
            self.assertEqual(navigator.swipe_history[-1], SwipeDirection.LEFT)

        self.machine.mouse.reset_mock()
        self.assertEqual(self._navigate(), "HANDLED")
        self.assertEqual(navigator.state, CardNavigatorState.RELOCALIZE)
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.lord_boss.CardListNavigator.align_first_card")
    def test_no_localization_evidence_uses_bounded_reset_fallback(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self.handler.has_reset_to_left = False
        self.handler.reset_swipe_count = 7
        self._evidence([])
        align.return_value = (CardAlignmentStatus.ALIGNED, 1, 0.0)

        self.assertEqual(self._navigate(), "HANDLED")
        align.assert_called_once()
        self.assertEqual(self.handler.lord_card_reset_attempts, 0)
        self.assertFalse(self.handler.has_reset_to_left)
        self.assertEqual(self.handler.reset_swipe_count, 7)

    @patch("states.handlers.lord_boss.CardListNavigator.align_first_card")
    def test_shared_recovery_then_target_clear_reenters_shared_navigation(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self._evidence([])
        align.return_value = (CardAlignmentStatus.ALIGNED, 1, 0.0)
        self.assertEqual(self._navigate(), "HANDLED")
        self.handler._clear_lord_card_session()

        self._evidence(["lords/boss_c.png"])
        self.assertEqual(self._navigate(), "FOUND")
        self.assertEqual(self.handler.lord_navigation_target, "boss_c")
        self.assertIsNone(self.handler.lord_card_session)

    def test_target_change_and_surface_exit_clear_session(self):
        self._evidence(["lords/boss_a.png"])
        self._navigate()
        self.assertIsNotNone(self.handler.lord_card_navigator)

        self.machine.get_available_selected_lord_bosses.return_value = ["boss_b"]
        self._evidence([])
        self._navigate()
        self.assertEqual(self.handler.lord_navigation_target, "boss_b")

        self._navigate_is_closed()
        self.assertIsNone(self.handler.lord_card_navigator)
        self.assertIsNone(self.handler.lord_navigation_target)

    @patch("states.handlers.lord_boss.execute_lobby_tab_route", return_value=False)
    @patch("states.handlers.lord_boss.os.path.exists", return_value=False)
    @patch("states.handlers.lord_boss.time.sleep")
    def test_real_handler_tracking_matches_only_committed_target(
        self, _sleep, _exists, _route
    ):
        self.handler.match_mutually_exclusive_tabs = MagicMock(
            return_value=(True, None, None, None)
        )
        self._evidence(["lords/boss_a.png"])

        self.handler.handle(self.screen, self.rect)
        self.assertTrue(self.handler.lord_card_session.owns_tracking)

        self.machine.matcher.reset_mock()
        self._evidence([])
        self.handler.handle(self.screen, self.rect)

        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            ["lords/boss_c.png"],
        )
        self.handler.match_mutually_exclusive_tabs.assert_called_once()

    def test_availability_change_invalidates_before_old_target_match(self):
        self._evidence(["lords/boss_a.png"])
        self._navigate()
        self.machine.get_available_selected_lord_bosses.return_value = ["boss_b"]
        self.machine.matcher.reset_mock()

        self.assertFalse(
            self.handler._handle_lord_tracking_fast_path(
                self.screen, self.rect, ["boss_b"]
            )
        )
        self.assertIsNone(self.handler.lord_card_session)
        self.assertNotIn(
            "lords/boss_c.png",
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
        )

        self.handler.lord_navigation_target = "boss_b"
        self.handler.lord_card_navigator = object()
        self.handler.reset_state()
        self.assertIsNone(self.handler.lord_card_navigator)
        self.assertIsNone(self.handler.lord_navigation_target)

    def _navigate_is_closed(self):
        return self.handler._handle_lord_shared_navigation(
            self.screen, self.rect, False, ["boss_b"]
        )


if __name__ == "__main__":
    unittest.main()
