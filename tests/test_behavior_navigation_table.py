import unittest

from states.navigation_intent import ActionId, IntentId, PostconditionId, ReasonCode
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

        self.assertEqual(len(V1_NAVIGATION_EDGES), 22)
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
                SceneId.DOMAIN_SELECT,
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


    def test_primary_domain_start_contract_matches_start_element(self):
        """
        [Test 1] mode = golden_empire 時，含有 domains/common/start_btn.png 的 scene_info
        經由 snapshot_from_scene_info (使用 defaults.toml 中的 lobby_start_btn) 必須包含 ElementId.START。
        """
        from config import PRIMARY_MODES
        from utils.scene_snapshot import snapshot_from_scene_info
        from utils.scene_types import SceneInfo

        cfg = PRIMARY_MODES.get("golden_empire", {})
        self.assertEqual(cfg.get("lobby_start_btn"), "domains/common/start_btn.png")


        info = SceneInfo(
            scene_type=SceneId.DOMAIN_SELECT,
            matched_elements={"domains/common/start_btn.png": ((640, 500), 0.95)},
        )
        snapshot = snapshot_from_scene_info(
            info,
            frame_id=1,
            captured_at=1.0,
            start_template=cfg.get("lobby_start_btn"),
        )
        self.assertTrue(snapshot.has(ElementId.START))
        self.assertEqual(snapshot.elements[ElementId.START].client_x, 640)
        self.assertEqual(snapshot.elements[ElementId.START].client_y, 500)

    def test_primary_domain_select_start_routing(self):
        """
        [Test 2] PRIMARY_NAVIGATION + DOMAIN_SELECT + START 必須宣告式路由至 START_PRIMARY 與 LOADING_OR_BATTLE。
        """
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.DOMAIN_SELECT,
            elements=self._element(ElementId.START),
        )
        edge = NavigationTable().next_edge(scene, IntentId.PRIMARY_NAVIGATION)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.action, ActionId.START_PRIMARY)
        self.assertEqual(edge.postcondition, PostconditionId.LOADING_OR_BATTLE)

    def test_primary_domain_panel_with_close_and_start_must_not_dismiss(self):
        """
        [Test 3] 正常 Domain preparation panel 同時出現 START 與 CLOSE_OVERLAY 時，
        決策必須為 START_PRIMARY，絕對不得為 DISMISS_OVERLAY。
        """
        from states.navigation_intent import (
            ActiveIntent,
            NavigationIntentPolicy,
            PrimaryPayload,
        )

        elements = {
            **self._element(ElementId.CLOSE_OVERLAY),
            **self._element(ElementId.START),
        }
        for scene_id in (SceneId.DOMAIN_SELECT, SceneId.LOBBY):
            scene = SceneSnapshot(1, 1.0, scene_id, elements=elements)
            intent = ActiveIntent(
                IntentId.PRIMARY_NAVIGATION,
                primary_payload=PrimaryPayload(mode="golden_empire", target="黃金古國"),
            )
            policy = NavigationIntentPolicy()
            decision = policy.resolve(scene, intent)
            self.assertEqual(decision.action, ActionId.START_PRIMARY)
            self.assertNotEqual(decision.action, ActionId.DISMISS_OVERLAY)

    def test_primary_domain_panel_with_temporary_start_miss_must_not_dismiss(self):
        """
        [Test 4 - 核心] Domain preparation panel 下，若某幀 CV 暫時漏失 START (僅含 CLOSE_OVERLAY)，
        不得因為 common/quit.png 存在就派發 DISMISS_OVERLAY 殺死正常面板，必須安全 fallback 為 CONTINUE_PRIMARY。
        """
        from states.navigation_intent import (
            ActiveIntent,
            NavigationIntentPolicy,
            PrimaryPayload,
            ReasonCode,
        )

        for scene_id in (SceneId.DOMAIN_SELECT, SceneId.LOBBY):
            scene = SceneSnapshot(
                1,
                1.0,
                scene_id,
                elements=self._element(ElementId.CLOSE_OVERLAY),
            )
            for mode in ("golden_empire", "domain"):
                intent = ActiveIntent(
                    IntentId.PRIMARY_NAVIGATION,
                    primary_payload=PrimaryPayload(mode=mode),
                )
                policy = NavigationIntentPolicy()
                decision = policy.resolve(scene, intent)
                self.assertNotEqual(decision.action, ActionId.DISMISS_OVERLAY)
                self.assertEqual(decision.action, ActionId.CONTINUE_PRIMARY)
                self.assertEqual(decision.reason, ReasonCode.PRIMARY_ROUTE_DELEGATED)

    def test_preserve_legacy_dungeon_lobby_close_recovery(self):
        """
        [Test 5 - Compatibility] 在非 domain 模式 (例如 mode="dungeon") 時，
        LOBBY + CLOSE_OVERLAY 仍保留舊有已驗證之彈窗關閉行為，派發 DISMISS_OVERLAY。

        Note: This preserves current verified legacy behavior; CLOSE_OVERLAY alone is not
        considered sufficient long-term semantic evidence. Future OverlayId migration will
        model real blocking overlays explicitly.
        """
        from states.navigation_intent import (
            ActiveIntent,
            NavigationIntentPolicy,
            PrimaryPayload,
            ReasonCode,
        )

        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.LOBBY,
            elements=self._element(ElementId.CLOSE_OVERLAY),
        )
        intent = ActiveIntent(
            IntentId.PRIMARY_NAVIGATION,
            primary_payload=PrimaryPayload(mode="dungeon"),
        )
        policy = NavigationIntentPolicy()
        decision = policy.resolve(scene, intent)
        self.assertEqual(decision.action, ActionId.DISMISS_OVERLAY)
        self.assertEqual(decision.reason, ReasonCode.PRIMARY_CLOSE_OVERLAY)

    def test_stage_mode_in_lobby_still_dismisses_real_overlay(self):
        """
        [Regression] Stage 模式下，若在 LOBBY 遇到真正的阻擋彈窗 (CLOSE_OVERLAY)，
        必須正常派發 DISMISS_OVERLAY 進行關閉自癒，不得被過度保護。
        """
        from states.navigation_intent import (
            ActiveIntent,
            NavigationIntentPolicy,
            PrimaryPayload,
            ReasonCode,
        )

        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.LOBBY,
            elements=self._element(ElementId.CLOSE_OVERLAY),
        )
        intent = ActiveIntent(
            IntentId.PRIMARY_NAVIGATION,
            primary_payload=PrimaryPayload(mode="stage"),
        )
        policy = NavigationIntentPolicy()
        decision = policy.resolve(scene, intent)
        self.assertEqual(decision.action, ActionId.DISMISS_OVERLAY)
        self.assertEqual(decision.reason, ReasonCode.PRIMARY_CLOSE_OVERLAY)

    def test_collect_diamond_returns_town_from_domain_and_boss_select_scenes(self):
        """
        驗證在 DOMAIN_SELECT, LORD_SELECT, DEMON_LORD_SELECT 場景下，
        若需要領鑽石 (COLLECT_DIAMOND) 且畫面上存在 GOBACK_TOWN，
        導航路由表能正確匹配出 RETURN_TOWN 邊。
        """
        target_scenes = [
            SceneId.DOMAIN_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
        ]
        table = NavigationTable()
        for s in target_scenes:
            scene = SceneSnapshot(
                1,
                1.0,
                s,
                elements=self._element(ElementId.GOBACK_TOWN),
            )
            edge = table.next_edge(scene, IntentId.COLLECT_DIAMOND)
            self.assertIsNotNone(edge, f"Scene {s} should have edge for COLLECT_DIAMOND")
            self.assertEqual(edge.action, ActionId.RETURN_TOWN)
            self.assertEqual(edge.target, SceneId.TOWN)
            self.assertEqual(edge.reason, ReasonCode.DIAMOND_RETURN_TO_TOWN)

    def test_collect_bread_opens_bread_from_domain_and_boss_select_scenes(self):
        """
        驗證在 DOMAIN_SELECT, LORD_SELECT, DEMON_LORD_SELECT 場景下，
        若需要領麵包 (COLLECT_BREAD) 且畫面上存在 BREAD_ENTRY，
        導航路由表能正確匹配出 OPEN_BREAD 邊。
        """
        target_scenes = [
            SceneId.DOMAIN_SELECT,
            SceneId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT,
        ]
        table = NavigationTable()
        for s in target_scenes:
            scene = SceneSnapshot(
                1,
                1.0,
                s,
                elements=self._element(ElementId.BREAD_ENTRY),
            )
            edge = table.next_edge(scene, IntentId.COLLECT_BREAD)
            self.assertIsNotNone(edge, f"Scene {s} should have edge for COLLECT_BREAD")
            self.assertEqual(edge.action, ActionId.OPEN_BREAD)
            self.assertEqual(edge.target, SceneId.BREAD_WINDOW)
            self.assertEqual(edge.reason, ReasonCode.BREAD_ENTRY_READY)


if __name__ == "__main__":
    unittest.main()




