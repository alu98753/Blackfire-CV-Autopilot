import unittest
from unittest.mock import MagicMock, patch
from utils.scene_detector import SceneDetector, SceneType, SceneInfo


class TestSceneDetector(unittest.TestCase):
    def setUp(self):
        self.mock_matcher = MagicMock()
        self.detector = SceneDetector(matcher=self.mock_matcher)
        self.mock_machine = MagicMock()
        self.mock_machine.config = {"type": "mix", "stage_templates": [], "dungeon_entries": []}
        self.mock_machine.diamond_window_opened = False
        self.mock_machine.bread_window_opened = False

    @patch("os.path.exists", return_value=True)
    def test_detect_popup_task_complete(self, mock_exists):
        self.mock_matcher.match.side_effect = lambda img, tmpl, threshold=0.8: ((100, 100), 0.85) if tmpl == "task_complete.png" else (None, 0.0)
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.POPUP_TASK_COMPLETE)
        self.assertIn("task_complete.png", scene.matched_elements)

    def test_detect_window_diamond_and_bread(self):
        self.mock_machine.diamond_window_opened = True
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.WINDOW_DIAMOND)

        self.mock_machine.diamond_window_opened = False
        self.mock_machine.bread_window_opened = True
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.WINDOW_BREAD)

    @patch("os.path.exists", return_value=True)
    def test_detect_in_dungeon(self, mock_exists):
        self.mock_matcher.match.side_effect = lambda img, tmpl, threshold=0.8: ((50, 50), 0.90) if tmpl == "dungeons/leave.png" else (None, 0.0)
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.IN_DUNGEON)
        self.assertTrue(scene.is_in_dungeon)

    @patch("os.path.exists", return_value=True)
    def test_detect_dungeon_prepare(self, mock_exists):
        self.mock_matcher.match.side_effect = lambda img, tmpl, threshold=0.8: ((200, 200), 0.88) if tmpl == "dungeons/dungeon_fight.png" else (None, 0.0)
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.DUNGEON_PREPARE)
        self.assertTrue(scene.is_dungeon_prepare)

    @patch("os.path.exists", return_value=True)
    def test_detect_town(self, mock_exists):
        self.mock_matcher.match.side_effect = lambda img, tmpl, threshold=0.8: ((300, 300), 0.85) if tmpl == "common/door.png" else (None, 0.0)
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.TOWN)
        self.assertTrue(scene.is_town)

    @patch("os.path.exists", return_value=True)
    def test_detect_lobby_stage_and_dungeon(self, mock_exists):
        # Test Lobby Stage
        def match_side_effect(img, tmpl, threshold=0.8):
            if tmpl == "goback_town.png":
                return ((10, 10), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.85, 0.40)

        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.LOBBY_STAGE)
        self.assertTrue(scene.is_lobby)
        self.assertEqual(scene.active_tabs, ["stage"])

        # Test Lobby Dungeon
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (False, True, 0.40, 0.85)
        scene = self.detector.detect("dummy_img", machine=self.mock_machine)
        self.assertEqual(scene.scene_type, SceneType.LOBBY_DUNGEON)
        self.assertEqual(scene.active_tabs, ["dungeon"])


if __name__ == "__main__":
    unittest.main()
