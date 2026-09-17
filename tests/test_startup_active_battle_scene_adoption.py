"""Focused coverage for evidence-driven cold-start battle adoption."""

import unittest
from unittest.mock import MagicMock, patch

from states.state_machine import GameStateMachine
from utils.scene_detector import SceneDetector
from utils.scene_snapshot import DetectionProfileId, SceneDetectionRequest, LobbyTabScope
from utils.scene_types import SceneId, SceneInfo


class TestStartupActiveBattleSceneAdoption(unittest.TestCase):
    def test_battle_anchor_is_available_under_expected_tab_profile(self):
        matcher = MagicMock()
        matcher.match.side_effect = lambda _image, name, **_kwargs: (
            ((100, 100), 0.91) if name == "common/auto.png" else (None, 0.0)
        )
        detector = SceneDetector(matcher=matcher)
        request = SceneDetectionRequest(
            profile=DetectionProfileId.DUNGEON_SELECT,
            expected_tab="dungeon",
            tab_scope=LobbyTabScope.EXPECTED_TAB,
            reason="navigation_steady",
        )

        with patch("utils.scene_detector.os.path.exists", return_value=True):
            scene = detector.detect("battle-frame", request=request)

        self.assertEqual(scene.scene_type, SceneId.BATTLE)
        self.assertIn("common/auto.png", scene.matched_elements)

    def test_global_cold_start_adopts_battle_and_creates_owned_session(self):
        machine = GameStateMachine(
            capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock(), preload_ocr=False
        )
        machine.matcher.match.return_value = (None, 0.0)
        machine.config = {"type": "stage"}
        observed = SceneInfo(scene_type=SceneId.BATTLE)

        with patch.object(SceneDetector, "detect", return_value=observed):
            machine.detect_current_state("battle-frame", {"left": 0, "top": 0})

        self.assertEqual(machine.current_state, machine.STATE_BATTLE)
        self.assertTrue(machine.battle_session.is_active)
        self.assertEqual(machine.battle_session.entry_state, machine.STATE_UNKNOWN)

    def test_intent_and_expected_tab_without_visual_battle_do_not_adopt(self):
        machine = GameStateMachine(
            capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock(), preload_ocr=False
        )
        machine.matcher.match.return_value = (None, 0.0)
        machine.config = {"type": "dungeon"}
        machine.need_diamond_collection = True
        observed = SceneInfo(scene_type=SceneId.UNKNOWN)

        with patch.object(SceneDetector, "detect", return_value=observed):
            machine.detect_current_state("unknown-frame", {"left": 0, "top": 0})

        self.assertNotEqual(machine.current_state, machine.STATE_BATTLE)
        self.assertFalse(machine.battle_session.is_active)

    def test_global_lobby_observation_remains_non_battle(self):
        machine = GameStateMachine(
            capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock(), preload_ocr=False
        )
        machine.matcher.match.return_value = (None, 0.0)
        machine.config = {"type": "stage"}

        with patch.object(
            SceneDetector,
            "detect",
            return_value=SceneInfo(scene_type=SceneId.LOBBY),
        ):
            machine.detect_current_state("lobby-frame", {"left": 0, "top": 0})

        self.assertNotEqual(machine.current_state, machine.STATE_BATTLE)
        self.assertFalse(machine.battle_session.is_active)


if __name__ == "__main__":
    unittest.main()
