import unittest

from states.navigation_intent import ActionId, IntentId, PostconditionId
from states.navigation_table import NavigationTable, V1_NAVIGATION_EDGES
from utils.scene_snapshot import ElementId, ElementMatch, SceneId, SceneSnapshot


class TestBehaviorNavigationTable(unittest.TestCase):
    @staticmethod
    def _element(element_id):
        return {
            element_id: ElementMatch(
                client_x=10,
                client_y=20,
                confidence=0.95,
                template_name=f"{element_id.value}.png",
            )
        }

    def test_v1_table_contains_only_declared_navigation_edges(self):
        routes = {
            (edge.intent_id, edge.source, edge.target)
            for edge in V1_NAVIGATION_EDGES
        }

        self.assertEqual(len(V1_NAVIGATION_EDGES), 15)
        self.assertIn(
            (IntentId.COLLECT_BREAD, SceneId.TOWN, SceneId.LOBBY), routes
        )
        self.assertIn(
            (
                IntentId.COLLECT_DIAMOND,
                SceneId.TOWN,
                SceneId.DIAMOND_WINDOW,
            ),
            routes,
        )
        self.assertIn(
            (IntentId.PRIMARY_NAVIGATION, SceneId.TOWN, SceneId.LOBBY), routes
        )
        self.assertIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.LOBBY,
                SceneId.LOADING,
            ),
            routes,
        )
        self.assertIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.STAGE_SELECT,
                SceneId.LOADING,
            ),
            routes,
        )
        self.assertIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.DUNGEON_SELECT,
                SceneId.LOADING,
            ),
            routes,
        )
        self.assertIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.LOBBY,
                SceneId.LOBBY,
            ),
            routes,
        )
        self.assertNotIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.STAGE_SELECT,
                SceneId.STAGE_SELECT,
            ),
            routes,
        )
        self.assertIn(
            (
                IntentId.PRIMARY_NAVIGATION,
                SceneId.DUNGEON_SELECT,
                SceneId.DUNGEON_SELECT,
            ),
            routes,
        )

    def test_edge_requires_matching_intent_scene_and_element(self):
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.TOWN,
            elements=self._element(ElementId.DOOR),
        )

        edge = NavigationTable().next_edge(scene, IntentId.COLLECT_BREAD)

        self.assertEqual(edge.action, ActionId.ENTER_LOBBY)
        self.assertEqual(edge.postcondition, PostconditionId.LOBBY)
        self.assertIsNone(
            NavigationTable().next_edge(scene, IntentId.COLLECT_DIAMOND)
        )

    def test_primary_navigation_enters_lobby_from_town_door(self):
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.TOWN,
            elements=self._element(ElementId.DOOR),
        )

        edge = NavigationTable().next_edge(
            scene, IntentId.PRIMARY_NAVIGATION
        )

        self.assertEqual(edge.action, ActionId.ENTER_LOBBY)
        self.assertEqual(edge.postcondition, PostconditionId.LOBBY)

    def test_declaration_order_prioritizes_overlay_before_go_back(self):
        elements = {
            **self._element(ElementId.CLOSE_OVERLAY),
            **self._element(ElementId.GOBACK_TOWN),
        }
        scene = SceneSnapshot(1, 1.0, SceneId.LOBBY, elements=elements)

        edge = NavigationTable().next_edge(scene, IntentId.COLLECT_DIAMOND)

        self.assertEqual(edge.action, ActionId.DISMISS_OVERLAY)

    def test_table_does_not_search_or_invent_an_edge(self):
        scene = SceneSnapshot(1, 1.0, SceneId.UNKNOWN)

        self.assertIsNone(
            NavigationTable().next_edge(scene, IntentId.PRIMARY_NAVIGATION)
        )

    def test_primary_stage_select_with_close_overlay_does_not_dismiss(self):
        """
        [Regression] STAGE_SELECT 抽屜自帶 common/quit.png (CLOSE_OVERLAY)，不得被誤判為 blocking overlay。
        必須 resolve 為 CONTINUE_PRIMARY (PRIMARY_ROUTE_DELEGATED)。
        """
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.STAGE_SELECT,
            elements=self._element(ElementId.CLOSE_OVERLAY),
        )
        edge = NavigationTable().next_edge(scene, IntentId.PRIMARY_NAVIGATION)
        self.assertIsNone(edge)

        from states.navigation_intent import NavigationIntentPolicy, ActiveIntent, ReasonCode
        policy = NavigationIntentPolicy()
        decision = policy.resolve(scene, ActiveIntent(IntentId.PRIMARY_NAVIGATION))
        self.assertNotEqual(decision.action, ActionId.DISMISS_OVERLAY)
        self.assertEqual(decision.action, ActionId.CONTINUE_PRIMARY)
        self.assertEqual(decision.reason, ReasonCode.PRIMARY_ROUTE_DELEGATED)

    def test_primary_stage_select_with_start_resolves_to_start_primary(self):
        """
        STAGE_SELECT 出現 start 按鈕時應觸發 START_PRIMARY。
        """
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.STAGE_SELECT,
            elements=self._element(ElementId.START),
        )
        edge = NavigationTable().next_edge(scene, IntentId.PRIMARY_NAVIGATION)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.action, ActionId.START_PRIMARY)
        self.assertEqual(edge.postcondition, PostconditionId.LOADING_OR_BATTLE)


if __name__ == "__main__":
    unittest.main()

