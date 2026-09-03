import unittest
from unittest.mock import MagicMock, patch

from utils.detector_registry import DetectorGroup, DetectorRegistry
from utils.scene_detector import SceneDetector, SceneType
from utils.scene_snapshot import DetectionProfileId


class TestBehaviorDetectorRegistry(unittest.TestCase):
    def setUp(self):
        self.matcher = MagicMock()
        self.matcher.match.return_value = (None, 0.0)
        self.matcher.match_mutually_exclusive_tabs.return_value = (
            False,
            False,
            0.0,
            0.0,
        )
        self.detector = SceneDetector(self.matcher)
        self.machine = MagicMock()
        self.machine.config = {
            "type": "mix",
            "lobby_start_btn": "stages/start.png",
            "stage_templates": ["stages/level4_desert_ruins.png"],
            "dungeon_entries": ["dungeons/Slime_entry.png"],
        }
        self.machine.diamond_window_opened = False
        self.machine.bread_window_opened = False

    def test_lobby_profile_excludes_town_and_dungeon_groups(self):
        registry = DetectorRegistry()
        groups = registry.groups_for(DetectionProfileId.LOBBY)

        self.assertIn(DetectorGroup.LOBBY, groups)
        self.assertIn(DetectorGroup.TABS, groups)
        self.assertNotIn(DetectorGroup.TOWN, groups)
        self.assertNotIn(DetectorGroup.DUNGEON, groups)

    @patch("os.path.exists", return_value=True)
    def test_lobby_profile_does_not_run_town_or_dungeon_matchers(self, _exists):
        self.detector.detect(
            MagicMock(),
            machine=self.machine,
            profile=DetectionProfileId.LOBBY,
        )

        templates = [call.args[1] for call in self.matcher.match.call_args_list]
        self.assertIn("goback_town.png", templates)
        self.assertIn("common/bread.png", templates)
        self.assertIn("stages/start.png", templates)
        self.assertNotIn("common/door.png", templates)
        self.assertNotIn("diamond.png", templates)
        self.assertNotIn("dungeons/leave.png", templates)

    @patch("os.path.exists", return_value=True)
    def test_unknown_profile_keeps_global_relocation_detection(self, _exists):
        def match(_image, template, **_kwargs):
            if template == "common/door.png":
                return ((100, 200), 0.95)
            return (None, 0.0)

        self.matcher.match.side_effect = match

        scene = self.detector.detect(MagicMock(), machine=self.machine)

        self.assertEqual(scene.scene_type, SceneType.TOWN)
        self.assertTrue(scene.is_town)

    @patch("os.path.exists", return_value=True)
    def test_same_template_and_options_are_matched_once_per_frame(self, _exists):
        self.machine.config["lobby_start_btn"] = "common/bread.png"
        self.matcher.match.side_effect = lambda _img, template, **_kwargs: (
            ((50, 60), 0.9) if template == "common/bread.png" else (None, 0.0)
        )

        self.detector.detect(
            MagicMock(),
            machine=self.machine,
            profile=DetectionProfileId.LOBBY,
        )

        bread_calls = [
            call
            for call in self.matcher.match.call_args_list
            if call.args[1] == "common/bread.png"
        ]
        self.assertEqual(len(bread_calls), 1)


if __name__ == "__main__":
    unittest.main()
