import unittest
import numpy as np
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

    @patch("os.path.exists", return_value=True)
    def test_ambiguous_tabs_and_shared_locked_cards_remain_lobby_other(self, _mock_exists):
        """Shared lobby cards must not guess Stage or Dungeon when tab evidence is ambiguous."""
        self.mock_machine.config = {
            "type": "mix",
            "stage_templates": ["stages/level2_barren_rocks.png"],
            "dungeon_entries": [],
        }
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (
            False,
            False,
            0.9028,
            0.8968,
        )

        def match_side_effect(_img, template, threshold=0.8):
            if template == "goback_town.png":
                return ((64, 726), 0.92)
            if template == "stages/level2_barren_rocks.png":
                confidence = 0.7711
                return (((281, 522), confidence) if confidence >= threshold else (None, confidence))
            if template == "common/locked_entry.png":
                return ((300, 400), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        scene = self.detector.detect("domains_lobby_frame", machine=self.mock_machine)

        self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
        self.assertEqual(scene.active_tabs, [])

    @patch("os.path.exists", return_value=True)
    def test_high_confidence_tab_conflict_blocks_high_confidence_card_fallback(
        self, _mock_exists
    ):
        """Conflicting tab anchors cannot be overruled by a shared card match."""
        self.mock_machine.config = {
            "type": "stage",
            "stage_templates": ["stages/level1_sky_plains.png"],
            "dungeon_entries": [],
        }
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (
            False,
            False,
            0.91,
            0.90,
        )

        def match_side_effect(_img, template, threshold=0.8):
            if template == "goback_town.png":
                return ((64, 726), 0.95)
            if template == "stages/level1_sky_plains.png":
                return ((300, 400), 0.97)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        scene = self.detector.detect("conflicting_frame", machine=self.mock_machine)

        self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
        self.assertEqual(scene.active_tabs, [])
        matched_templates = [call.args[1] for call in self.mock_matcher.match.call_args_list]
        self.assertNotIn("stages/level1_sky_plains.png", matched_templates)

    @patch("os.path.exists", return_value=True)
    def test_domain_selected_requires_active_tab_postcondition(self, _mock_exists):
        self.mock_machine.config = {
            "type": "domain",
            "domain_tab_btn": "domains/Domains_entry.png",
            "domain_tab_after_btn": "domains/Domains_entry_after.png",
            "stage_templates": [],
            "dungeon_entries": [],
        }

        def match_side_effect(_img, template, threshold=0.8):
            if template == "goback_town.png":
                return ((64, 726), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        def tab_side_effect(_img, template_a, _template_b, **_kwargs):
            if template_a == "domains/Domains_entry_after.png":
                return (is_active, not is_active, 0.93 if is_active else 0.40, 0.40 if is_active else 0.92)
            return (False, False, 0.40, 0.40)

        self.mock_matcher.match_mutually_exclusive_tabs.side_effect = tab_side_effect

        # 情況 1: 未選中 (after 分數低於 before 或無優勢) -> 保持 LOBBY_OTHER
        is_active = False
        inactive = self.detector.detect("lobby_frame", machine=self.mock_machine)
        self.assertEqual(inactive.scene_type, SceneType.LOBBY_OTHER)
        self.assertEqual(inactive.active_tabs, [])

        # 情況 2: 已選中 (after 具備明確相對優勢) -> 確立 DOMAIN_SELECT
        is_active = True
        selected = self.detector.detect("lobby_frame", machine=self.mock_machine)
        self.assertEqual(selected.scene_type, SceneType.DOMAIN_SELECT)
        self.assertEqual(selected.active_tabs, ["domain"])


    @patch("os.path.exists", return_value=True)
    def test_lord_and_demon_lord_selected_scenes_are_distinct(self, _mock_exists):
        def match_side_effect(_img, template, threshold=0.8):
            if template == "goback_town.png":
                return ((64, 726), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        cases = (
            (
                "lord_boss",
                "load/Lord_entry_after.png",
                SceneType.LORD_SELECT,
                "lord",
            ),
            (
                "demon_lords",
                "demon_lords/demon_lords_entry_after.png",
                SceneType.DEMON_LORD_SELECT,
                "demon_lord",
            ),
        )
        for config_type, active_template, expected_scene, expected_tab in cases:
            with self.subTest(config_type=config_type):
                self.mock_machine.config = {
                    "type": config_type,
                    "stage_templates": [],
                    "dungeon_entries": [],
                }

                def tab_side_effect(_img, template_a, _template_b, **_kwargs):
                    if template_a == active_template:
                        return (True, False, 0.92, 0.40)
                    return (False, False, 0.40, 0.40)

                self.mock_matcher.match_mutually_exclusive_tabs.side_effect = tab_side_effect
                scene = self.detector.detect("lobby_frame", machine=self.mock_machine)
                self.assertEqual(scene.scene_type, expected_scene)
                self.assertEqual(scene.active_tabs, [expected_tab])

    @patch("os.path.exists", return_value=True)
    def test_detect_lobby_start_skips_expensive_stage_search(self, mock_exists):
        """A detected Start button identifies the lobby without scanning stage islands."""
        self.mock_machine.config = {
            "type": "stage",
            "lobby_start_btn": "stages/start.png",
            "stage_templates": ["stages/level2_Barren_Rocky_Ground.png"],
            "dungeon_entries": [],
        }

        def match_side_effect(img, tmpl, threshold=0.8):
            if tmpl in {"goback_town.png", "stages/start.png"}:
                return ((10, 10), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        scene = self.detector.detect("lobby_frame", machine=self.mock_machine)

        self.assertEqual(scene.scene_type, SceneType.LOBBY_OTHER)
        self.assertIn("stages/start.png", scene.matched_elements)
        matched_templates = [call.args[1] for call in self.mock_matcher.match.call_args_list]
        self.assertNotIn("stages/level2_Barren_Rocky_Ground.png", matched_templates)
        self.mock_matcher.match_mutually_exclusive_tabs.assert_not_called()

    @patch("os.path.exists", return_value=True)
    def test_detect_lobby_start_is_evaluated_again_for_next_frame(self, mock_exists):
        """Scene information is frame-local and must never be reused on a later tick."""
        self.mock_machine.config = {
            "type": "stage",
            "lobby_start_btn": "stages/start.png",
            "stage_templates": [],
            "dungeon_entries": [],
        }
        self.mock_matcher.match.side_effect = (
            lambda img, tmpl, threshold=0.8: ((10, 10), 0.95)
            if tmpl in {"goback_town.png", "stages/start.png"}
            else (None, 0.0)
        )

        self.detector.detect("first_frame", machine=self.mock_machine)
        self.detector.detect("second_frame", machine=self.mock_machine)

        start_calls = [
            call for call in self.mock_matcher.match.call_args_list
            if call.args[1] == "stages/start.png"
        ]
        self.assertEqual(len(start_calls), 2)
        self.assertEqual([call.args[0] for call in start_calls], ["first_frame", "second_frame"])


if __name__ == "__main__":
    unittest.main()
