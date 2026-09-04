import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from states.handlers.navigation import NavigationHandler
from utils.card_navigator import CardAlignmentStatus, CardListNavigator
from utils.scene_detector import SceneInfo, SceneType


class TestCardAlignmentContract(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.mouse = MagicMock()
        self.machine.matcher = MagicMock()
        self.machine.capturer = MagicMock()
        self.machine.config = {
            "type": "stage",
            "stage_templates": ["stages/level1_sky_plains.png"],
            "stage_reset_max_attempts": 7,
        }
        self.machine.matcher.match.return_value = (None, 0.0)
        self.handler = NavigationHandler(self.machine)
        self.rect = {"left": 100, "top": 50, "width": 1000, "height": 800}
        self.screen = np.zeros((800, 1000, 3), dtype=np.uint8)

    @patch("states.handlers.navigation.time.sleep")
    def test_stage_selected_page_performs_bounded_reset(self, _mock_sleep):
        scene = SceneInfo(
            scene_type=SceneType.LOBBY_STAGE,
            is_lobby=True,
            active_tabs=["stage"],
        )

        handled = self.handler._handle_primary_card_alignment(
            self.screen, self.rect, scene
        )

        self.assertTrue(handled)
        self.machine.mouse.drag.assert_called_once_with(
            300, 450, 900, 450, duration=0.8, inertia=False
        )
        self.assertEqual(self.handler.card_alignment_attempts, 1)

    def test_stage_intent_cannot_reset_unconfirmed_page(self):
        scene = SceneInfo(scene_type=SceneType.LOBBY_OTHER, is_lobby=True)

        handled = self.handler._handle_primary_card_alignment(
            self.screen, self.rect, scene
        )

        self.assertFalse(handled)
        self.machine.mouse.drag.assert_not_called()

    @patch("states.handlers.navigation.time.sleep")
    def test_dungeon_selected_page_uses_same_reset_contract(self, _mock_sleep):
        self.machine.config = {
            "type": "dungeon",
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_reset_max_attempts": 7,
        }
        scene = SceneInfo(
            scene_type=SceneType.LOBBY_DUNGEON,
            is_lobby=True,
            active_tabs=["dungeon"],
        )

        handled = self.handler._handle_primary_card_alignment(
            self.screen, self.rect, scene
        )

        self.assertTrue(handled)
        self.machine.mouse.drag.assert_called_once_with(
            300, 450, 900, 450, duration=0.8, inertia=False
        )
        self.assertEqual(self.handler.card_alignment_attempts, 1)

    def test_alignment_limit_is_failure_not_success(self):
        status, attempts, _ = CardListNavigator.align_first_card(
            self.screen,
            self.machine.matcher,
            self.machine.mouse,
            self.rect,
            "stages/level1_sky_plains.png",
            7,
            max_attempts=7,
        )

        self.assertEqual(status, CardAlignmentStatus.EXHAUSTED)
        self.assertEqual(attempts, 7)
        self.machine.mouse.drag.assert_not_called()


if __name__ == "__main__":
    unittest.main()
