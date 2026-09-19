import unittest
from unittest.mock import MagicMock, call, patch

from config import get_canonical_domain_mode_configs
from states.handlers.navigation import NavigationHandler
from utils.navigation_catalog import domain_navigation_catalog
from utils.scene_detector import SceneInfo, SceneType
from utils.shared_card_navigator import CardNavigatorState, SwipeDirection


class TestDomainSharedNavigationIntegration(unittest.TestCase):
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
            "type": "domain",
            "domain": "coldoath_citadel",
            "domain_entry_btn": "domains/coldoath_citadel/coldoath_citadel.png",
            "navigation_path": [
                "domains/coldoath_citadel/coldoath_citadel.png",
                "domains/common/start_btn.png",
            ],
        }
        self.handler = NavigationHandler(self.machine)
        self.rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.screen = object()
        self.scene = SceneInfo(
            scene_type=SceneType.LOBBY_OTHER,
            is_lobby=True,
            active_tabs=["domain"],
        )
        self.catalog = domain_navigation_catalog(get_canonical_domain_mode_configs())
        self.target = "domains/coldoath_citadel/coldoath_citadel.png"

    def _evidence(self, visible=()):
        visible = set(visible)

        def match(_screen, template, **_kwargs):
            if template in visible:
                return (100, 200), 0.95
            return None, 0.0

        self.machine.matcher.match.side_effect = match

    @patch("states.handlers.navigation.time.sleep")
    def test_initial_target_visible_has_no_reset(self, _sleep):
        self._evidence([self.target])

        handled = self.handler._handle_domain_shared_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertFalse(handled)
        self.assertTrue(self.handler._domain_card_handoff)
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.navigation.time.sleep")
    def test_lower_visible_index_swipes_toward_higher_domain_index(self, _sleep):
        self._evidence(["domains/golden_empire/entry.png"])

        self.assertTrue(
            self.handler._handle_domain_shared_navigation(
                self.screen, self.rect, self.scene
            )
        )
        self.assertEqual(
            self.handler.domain_card_navigator.swipe_history,
            (SwipeDirection.LEFT,),
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_higher_visible_index_swipes_toward_lower_domain_index(self, _sleep):
        self.machine.config["domain"] = "golden_empire"
        self.machine.config["domain_entry_btn"] = "domains/golden_empire/entry.png"
        self._evidence(["domains/coldoath_citadel/coldoath_citadel.png"])

        self.assertTrue(
            self.handler._handle_domain_shared_navigation(
                self.screen, self.rect, self.scene
            )
        )
        self.assertEqual(
            self.handler.domain_card_navigator.swipe_history,
            (SwipeDirection.RIGHT,),
        )

    @patch("states.handlers.navigation.time.sleep")
    def test_tracking_misses_repeat_direction_until_relocalize(self, _sleep):
        self._evidence(["domains/golden_empire/entry.png"])
        self.handler._handle_domain_shared_navigation(self.screen, self.rect, self.scene)
        navigator = self.handler.domain_card_navigator

        self._evidence([])
        for _ in range(len(self.catalog) - 1):
            result = navigator.observe(self.screen, self.machine.matcher)
            self.assertEqual(result.state, CardNavigatorState.TRACKING)
            self.assertEqual(result.direction, SwipeDirection.LEFT)
            self.assertIsNotNone(result.swipe_request)

        result = navigator.observe(self.screen, self.machine.matcher)
        self.assertEqual(result.state, CardNavigatorState.RELOCALIZE)
        self.assertIsNone(result.swipe_request)

    @patch("states.handlers.navigation.CardListNavigator.align_first_card")
    def test_localization_without_evidence_uses_reset_left_fallback(self, align):
        from utils.card_navigator import CardAlignmentStatus

        self._evidence([])
        align.return_value = (CardAlignmentStatus.RETRYING, 1, 0.0)

        handled = self.handler._handle_domain_shared_navigation(
            self.screen, self.rect, self.scene
        )

        self.assertTrue(handled)
        align.assert_called_once()

    @patch("states.handlers.navigation.time.sleep")
    def test_target_change_and_leaving_domain_clear_session(self, _sleep):
        self._evidence(["domains/golden_empire/entry.png"])
        self.handler._handle_domain_shared_navigation(self.screen, self.rect, self.scene)
        first_navigator = self.handler.domain_card_navigator

        self.machine.config["domain"] = "golden_empire"
        self._evidence([self.target])
        self.handler._handle_domain_shared_navigation(self.screen, self.rect, self.scene)
        self.assertIsNot(self.handler.domain_card_navigator, first_navigator)
        self.assertEqual(self.handler.domain_card_target_key, "golden_empire")

        self.handler._handle_domain_shared_navigation(
            self.screen,
            self.rect,
            SceneInfo(scene_type=SceneType.LOBBY_OTHER, active_tabs=[]),
        )
        self.assertIsNone(self.handler.domain_card_navigator)
        self.assertIsNone(self.handler.domain_card_target_key)

    @patch("states.handlers.navigation.time.sleep")
    def test_found_hands_back_to_existing_domain_entry_flow(self, _sleep):
        self._evidence([self.target])
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.machine.matcher
        self.handler.scene_detector.detect.return_value = self.scene

        self.handler.handle(self.screen, self.rect)

        self.machine.mouse.click.assert_called_once()
        self.assertIsNone(self.handler.domain_card_navigator)

    @patch("states.handlers.navigation.os.path.exists", return_value=False)
    @patch("states.handlers.navigation.time.sleep")
    def test_real_handler_tracking_matches_only_committed_target(self, _sleep, _exists):
        self.handler.scene_detector = MagicMock()
        self.handler.scene_detector.matcher = self.machine.matcher
        self.handler.scene_detector.detect.return_value = self.scene
        self._evidence(["domains/golden_empire/entry.png"])

        self.handler.handle(self.screen, self.rect)
        self.assertTrue(self.handler.domain_card_session.owns_tracking)

        self.machine.matcher.reset_mock()
        self._evidence([])
        self.handler.handle(self.screen, self.rect)

        self.assertEqual(
            [call.args[1] for call in self.machine.matcher.match.call_args_list],
            [self.target],
        )
        self.handler.scene_detector.detect.assert_called_once()

    def test_canonical_domain_addition_gets_catalog_index_without_branch(self):
        canonical = get_canonical_domain_mode_configs()
        extended = dict(canonical)
        extended["new_domain"] = {
            "domain": "new_domain",
            "domain_entry_btn": "domains/new_domain/entry.png",
        }

        catalog = domain_navigation_catalog(extended)

        self.assertEqual(catalog[-1].key, "new_domain")
        self.assertEqual(catalog[-1].index, len(catalog))


if __name__ == "__main__":
    unittest.main()
