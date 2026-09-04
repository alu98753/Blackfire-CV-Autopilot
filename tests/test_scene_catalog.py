import unittest

from utils.scene_catalog import SceneCatalog
from utils.scene_detector import SceneInfo, SceneType
from utils.scene_snapshot import (
    DetectionProfileId,
    SceneId,
    snapshot_from_scene_info,
)


class TestSceneCatalog(unittest.TestCase):
    def test_catalog_registers_every_v1_scene(self):
        self.assertEqual(SceneCatalog.registered_scenes(), frozenset(SceneId))

    def test_scene_families_select_their_scoped_profiles(self):
        expected = {
            SceneId.TOWN: DetectionProfileId.TOWN,
            SceneId.LOBBY: DetectionProfileId.LOBBY,
            SceneId.STAGE_SELECT: DetectionProfileId.STAGE_SELECT,
            SceneId.DUNGEON_SELECT: DetectionProfileId.DUNGEON_SELECT,
            SceneId.DOMAIN_SELECT: DetectionProfileId.DOMAIN_SELECT,
            SceneId.LORD_SELECT: DetectionProfileId.LORD_SELECT,
            SceneId.DEMON_LORD_SELECT: DetectionProfileId.DEMON_LORD_SELECT,
            SceneId.LOADING: DetectionProfileId.LOADING,
            SceneId.BATTLE: DetectionProfileId.BATTLE,
            SceneId.RESULT: DetectionProfileId.RESULT,
            SceneId.DOMAIN_EXPLORE: DetectionProfileId.DOMAIN,
        }

        for scene_id, profile in expected.items():
            with self.subTest(scene_id=scene_id):
                self.assertEqual(SceneCatalog.profile_for(scene_id), profile)

    def test_legacy_stage_and_dungeon_tabs_keep_distinct_scene_identity(self):
        cases = (
            (
                SceneType.LOBBY_STAGE,
                SceneId.STAGE_SELECT,
                DetectionProfileId.STAGE_SELECT,
            ),
            (
                SceneType.LOBBY_DUNGEON,
                SceneId.DUNGEON_SELECT,
                DetectionProfileId.DUNGEON_SELECT,
            ),
            (
                SceneType.DUNGEON_PREPARE,
                SceneId.DUNGEON_LOBBY,
                DetectionProfileId.DUNGEON_SELECT,
            ),
            (
                SceneType.DOMAIN_EXPLORE,
                SceneId.DOMAIN_EXPLORE,
                DetectionProfileId.DOMAIN,
            ),
            (
                SceneType.DOMAIN_SELECT,
                SceneId.DOMAIN_SELECT,
                DetectionProfileId.DOMAIN_SELECT,
            ),
            (
                SceneType.LORD_SELECT,
                SceneId.LORD_SELECT,
                DetectionProfileId.LORD_SELECT,
            ),
            (
                SceneType.DEMON_LORD_SELECT,
                SceneId.DEMON_LORD_SELECT,
                DetectionProfileId.DEMON_LORD_SELECT,
            ),
        )

        for scene_type, scene_id, profile in cases:
            with self.subTest(scene_type=scene_type):
                snapshot = snapshot_from_scene_info(
                    SceneInfo(scene_type=scene_type),
                    frame_id=1,
                    captured_at=1.0,
                )
                self.assertEqual(snapshot.scene, scene_id)
                self.assertEqual(snapshot.detection_profile, profile)


if __name__ == "__main__":
    unittest.main()
