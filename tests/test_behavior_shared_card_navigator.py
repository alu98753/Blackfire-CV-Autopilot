import unittest

from utils.navigation_catalog import NavigationCatalogEntry
from utils.shared_card_navigator import (
    CardNavigatorState,
    SharedCardNavigator,
    SwipeDirection,
)


CATALOG = [
    NavigationCatalogEntry(1, "one", "cards/one.png"),
    NavigationCatalogEntry(2, "two", "cards/two.png"),
    NavigationCatalogEntry(3, "three", "cards/three.png"),
    NavigationCatalogEntry(4, "four", "cards/four.png"),
]


class Matcher:
    def __init__(self, matches):
        self.matches = matches
        self.calls = []

    def match(self, _screen, template):
        self.calls.append(template)
        return self.matches.get(template, (None, 0.0))


class TestSharedCardNavigator(unittest.TestCase):
    def test_target_initially_visible_short_circuits(self):
        matcher = Matcher({"cards/three.png": ((30, 40), 0.95)})
        navigator = SharedCardNavigator(CATALOG, "three")

        result = navigator.observe(object(), matcher)

        self.assertEqual(result.state, CardNavigatorState.FOUND)
        self.assertEqual(result.visible_indices, frozenset({3}))
        self.assertEqual(matcher.calls, ["cards/three.png"])
        self.assertEqual(navigator.swipe_history, ())
        self.assertIsNone(result.swipe_request)

    def test_lower_visible_indices_request_higher_index_direction(self):
        matcher = Matcher(
            {
                "cards/one.png": ((1, 1), 0.9),
                "cards/two.png": ((2, 2), 0.9),
            }
        )
        result = SharedCardNavigator(CATALOG, "four").observe(object(), matcher)

        self.assertEqual(result.state, CardNavigatorState.TRACKING)
        self.assertEqual(result.visible_indices, frozenset({1, 2}))
        self.assertEqual(result.direction, SwipeDirection.LEFT)
        self.assertEqual(len(navigator_swipes(result)), 1)

    def test_higher_visible_indices_request_lower_index_direction(self):
        matcher = Matcher({"cards/three.png": ((3, 3), 0.9)})
        navigator = SharedCardNavigator(CATALOG, "two")
        result = navigator.observe(object(), matcher)
        self.assertEqual(result.direction, SwipeDirection.RIGHT)

    def test_target_index_inside_observed_range_is_contradictory(self):
        matcher = Matcher(
            {
                "cards/one.png": ((1, 1), 0.9),
                "cards/four.png": ((4, 4), 0.9),
            }
        )
        result = SharedCardNavigator(CATALOG, "three").observe(object(), matcher)

        self.assertEqual(result.state, CardNavigatorState.CONTRADICTORY)
        self.assertIsNone(result.swipe_request)

    def test_tracking_only_matches_committed_target(self):
        first_matcher = Matcher({"cards/one.png": ((1, 1), 0.9)})
        navigator = SharedCardNavigator(CATALOG, "four")
        navigator.observe(object(), first_matcher)

        tracking_matcher = Matcher({"cards/four.png": ((4, 4), 0.9)})
        result = navigator.observe(object(), tracking_matcher)

        self.assertEqual(result.state, CardNavigatorState.FOUND)
        self.assertEqual(tracking_matcher.calls, ["cards/four.png"])

    def test_tracking_misses_relocalize_at_default_catalog_bound(self):
        navigator = SharedCardNavigator(CATALOG, "four")
        navigator.observe(object(), Matcher({"cards/one.png": ((1, 1), 0.9)}))

        for miss in range(1, len(CATALOG) + 1):
            result = navigator.observe(object(), Matcher({}))
            expected = (
                CardNavigatorState.RELOCALIZE
                if miss == len(CATALOG)
                else CardNavigatorState.TRACKING
            )
            self.assertEqual(result.state, expected)
            self.assertEqual(result.tracking_misses, miss)

    def test_localization_without_reliable_evidence_requests_reset_left(self):
        matcher = Matcher(
            {
                "cards/one.png": ((1, 1), 0.4),
                "cards/two.png": ((2, 2), 0.4),
            }
        )
        result = SharedCardNavigator(CATALOG, "four").observe(object(), matcher)

        self.assertEqual(result.state, CardNavigatorState.NEED_RESET_LEFT)
        self.assertEqual(result.visible_indices, frozenset())
        self.assertIsNone(result.swipe_request)

    def test_swipe_history_never_creates_an_exact_current_index(self):
        matcher = Matcher({"cards/one.png": ((1, 1), 0.9)})
        navigator = SharedCardNavigator(CATALOG, "four")

        result = navigator.observe(object(), matcher)

        self.assertEqual(result.direction, SwipeDirection.LEFT)
        self.assertFalse(hasattr(navigator, "current_index"))
        self.assertEqual(navigator.swipe_history, (SwipeDirection.LEFT,))


def navigator_swipes(result):
    return [result.swipe_request] if result.swipe_request is not None else []


if __name__ == "__main__":
    unittest.main()
