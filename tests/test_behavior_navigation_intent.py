import unittest
from dataclasses import FrozenInstanceError

from states.navigation_intent import (
    ActionId,
    DecisionKind,
    IntentId,
    IntentSnapshot,
    NavigationIntentPolicy,
    PrimaryPayload,
    ReasonCode,
)
from utils.scene_detector import SceneInfo, SceneType
from utils.scene_snapshot import (
    DetectionProfileId,
    ElementId,
    ElementMatch,
    SceneId,
    SceneSnapshot,
    snapshot_from_scene_info,
)


class TestBehaviorNavigationIntent(unittest.TestCase):
    def setUp(self):
        self.policy = NavigationIntentPolicy()

    @staticmethod
    def _match(element, template):
        return {
            element: ElementMatch(
                client_x=100,
                client_y=200,
                confidence=0.95,
                template_name=template,
            )
        }

    def test_scene_snapshot_is_immutable(self):
        snapshot = SceneSnapshot(
            frame_id=1,
            captured_at=10.0,
            scene=SceneId.TOWN,
            elements=self._match(ElementId.DOOR, "common/door.png"),
        )

        with self.assertRaises(FrozenInstanceError):
            snapshot.scene = SceneId.LOBBY
        with self.assertRaises(TypeError):
            snapshot.elements[ElementId.START] = snapshot.elements[ElementId.DOOR]

    def test_legacy_scene_info_adapter_builds_semantic_snapshot(self):
        scene_info = SceneInfo(
            scene_type=SceneType.LOBBY_OTHER,
            is_lobby=True,
            matched_elements={
                "goback_town.png": ((10, 20), 0.91),
                "stages/start.png": ((30, 40), 0.96),
            },
        )

        snapshot = snapshot_from_scene_info(
            scene_info,
            frame_id=7,
            captured_at=12.5,
            start_template="stages/start.png",
        )

        self.assertEqual(snapshot.scene, SceneId.LOBBY)
        self.assertEqual(snapshot.detection_profile, DetectionProfileId.LOBBY)
        self.assertTrue(snapshot.has(ElementId.GOBACK_TOWN))
        self.assertTrue(snapshot.has(ElementId.START))

    def test_intent_snapshot_normalizes_disabled_bread(self):
        snapshot = IntentSnapshot.from_legacy(
            need_diamond_collection=False,
            enable_bread=False,
            need_bread_collection=True,
            primary_mode="stage",
        )

        self.assertFalse(snapshot.bread_pending)

    def test_intent_selection_is_diamond_then_bread_then_primary(self):
        both = IntentSnapshot(True, True, PrimaryPayload("stage"))
        bread = IntentSnapshot(False, True, PrimaryPayload("stage"))
        primary = IntentSnapshot(False, False, PrimaryPayload("dungeon", "ghost"))

        self.assertEqual(self.policy.select_intent(both).intent_id, IntentId.COLLECT_DIAMOND)
        self.assertEqual(self.policy.select_intent(bread).intent_id, IntentId.COLLECT_BREAD)
        selected = self.policy.select_intent(primary)
        self.assertEqual(selected.intent_id, IntentId.PRIMARY_NAVIGATION)
        self.assertEqual(selected.primary_payload.target, "ghost")

    def test_bread_intent_ignores_start_on_same_lobby_snapshot(self):
        elements = {
            **self._match(ElementId.BREAD_ENTRY, "common/bread.png"),
            **self._match(ElementId.START, "stages/start.png"),
            **self._match(ElementId.GOBACK_TOWN, "goback_town.png"),
        }
        scene = SceneSnapshot(1, 1.0, SceneId.LOBBY, elements=elements)
        intent = self.policy.select_intent(
            IntentSnapshot(False, True, PrimaryPayload("stage"))
        )

        decision = self.policy.resolve(scene, intent)

        self.assertEqual(decision.kind, DecisionKind.CLICK)
        self.assertEqual(decision.action, ActionId.OPEN_BREAD)
        self.assertEqual(decision.reason, ReasonCode.BREAD_ENTRY_READY)

    def test_diamond_intent_returns_to_town_instead_of_starting(self):
        elements = {
            **self._match(ElementId.GOBACK_TOWN, "goback_town.png"),
            **self._match(ElementId.START, "stages/start.png"),
        }
        scene = SceneSnapshot(1, 1.0, SceneId.LOBBY, elements=elements)
        intent = self.policy.select_intent(
            IntentSnapshot(True, False, PrimaryPayload("stage"))
        )

        decision = self.policy.resolve(scene, intent)

        self.assertEqual(decision.action, ActionId.RETURN_TOWN)
        self.assertEqual(decision.reason, ReasonCode.DIAMOND_RETURN_TO_TOWN)

    def test_primary_intent_uses_start_when_available(self):
        scene = SceneSnapshot(
            1,
            1.0,
            SceneId.LOBBY,
            elements=self._match(ElementId.START, "stages/start.png"),
        )
        intent = self.policy.select_intent(
            IntentSnapshot(False, False, PrimaryPayload("stage"))
        )

        decision = self.policy.resolve(scene, intent)

        self.assertEqual(decision.action, ActionId.START_PRIMARY)
        self.assertEqual(decision.reason, ReasonCode.PRIMARY_START_READY)

    def test_collection_waits_when_scene_evidence_is_insufficient(self):
        scene = SceneSnapshot(1, 1.0, SceneId.UNKNOWN)
        intent = self.policy.select_intent(
            IntentSnapshot(False, True, PrimaryPayload("stage"))
        )

        first = self.policy.resolve(scene, intent)
        second = self.policy.resolve(scene, intent)

        self.assertEqual(first, second)
        self.assertEqual(first.kind, DecisionKind.WAIT)
        self.assertIsNone(first.action)


if __name__ == "__main__":
    unittest.main()
