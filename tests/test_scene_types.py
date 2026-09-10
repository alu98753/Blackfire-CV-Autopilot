import unittest
from utils.scene_types import (
    SceneId,
    SceneType,
    SceneInfo,
    SceneAnchorSpec,
    LobbyTabDefinition,
    LOBBY_TAB_DEFINITIONS,
)
from utils.scene_snapshot import SceneSnapshot, ElementId


class TestSceneTypes(unittest.TestCase):
    def test_scene_id_and_scene_type_aliasing(self):
        """驗證 SceneType 與 SceneId 完全同一型別且別名完全對齊。"""
        self.assertIs(SceneType, SceneId)
        self.assertEqual(SceneId.STAGE_SELECT, SceneType.LOBBY_STAGE)
        self.assertEqual(SceneId.DUNGEON_SELECT, SceneType.LOBBY_DUNGEON)
        self.assertEqual(SceneId.LOBBY, SceneType.LOBBY_OTHER)
        self.assertEqual(SceneId.STAGE_SELECT.value, "stage_select")
        self.assertEqual(SceneId.DUNGEON_SELECT.value, "dungeon_select")

    def test_scene_anchor_spec_properties(self):
        """驗證聲明式場景錨點規則宣告結構。"""
        spec = SceneAnchorSpec(
            scene_id=SceneId.TOWN,
            required_any=("common/door.png", "diamond.png"),
            min_confidence=0.80,
        )
        self.assertEqual(spec.scene_id, SceneId.TOWN)
        self.assertIn("common/door.png", spec.required_any)
        self.assertEqual(spec.min_confidence, 0.80)
        self.assertEqual(spec.excluded_any, ())

    def test_lobby_tab_definitions_completeness(self):
        """驗證 5 大大廳頁籤聲明規格齊備。"""
        names = [tab.name for tab in LOBBY_TAB_DEFINITIONS]
        self.assertEqual(names, ["stage", "dungeon", "domain", "lord", "demon_lord"])
        self.assertEqual(len(LOBBY_TAB_DEFINITIONS), 5)
        for tab in LOBBY_TAB_DEFINITIONS:
            self.assertTrue(tab.active_template.endswith(".png"))
            self.assertTrue(tab.inactive_template.endswith(".png"))
            self.assertIsInstance(tab.scene_type, SceneId)

    def test_scene_info_defaults_and_scene_id_property(self):
        """驗證 SceneInfo 初始值與 scene_id 屬性。"""
        info = SceneInfo(scene_type=SceneId.DUNGEON_SELECT, is_lobby=True)
        self.assertEqual(info.scene_type, SceneId.DUNGEON_SELECT)
        self.assertEqual(info.scene_id, SceneId.DUNGEON_SELECT)
        self.assertTrue(info.is_lobby)
        self.assertFalse(info.is_town)
        self.assertEqual(info.active_tabs, [])
        self.assertEqual(info.matched_elements, {})

    def test_scene_info_to_snapshot_bridge(self):
        """驗證 SceneInfo.to_snapshot() 能成功產出 Greenfield-lite SceneSnapshot。"""
        info = SceneInfo(
            scene_type=SceneId.DUNGEON_SELECT,
            is_lobby=True,
            active_tabs=["dungeon"],
            matched_elements={"goback_town.png": ((100, 200), 0.95)},
        )
        snapshot = info.to_snapshot(frame_id=42, captured_at=123.45)
        self.assertIsInstance(snapshot, SceneSnapshot)
        self.assertEqual(snapshot.frame_id, 42)
        self.assertEqual(snapshot.scene, SceneId.DUNGEON_SELECT)
        self.assertTrue(snapshot.has(ElementId.GOBACK_TOWN))


if __name__ == "__main__":
    unittest.main()
