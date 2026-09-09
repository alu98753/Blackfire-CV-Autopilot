import time
import unittest
from unittest.mock import MagicMock, patch

from config import GAME_CONFIGS, PRIMARY_MODES
from states.handlers.navigation import NavigationHandler
from utils.quest_mapper import QuestMapper


class TestStageQuestSubStageRouting(unittest.TestCase):
    """Regression coverage for quest routes overriding Tier 4 fallback choices."""

    def _build_final_quest_config(self):
        with patch.dict(
            PRIMARY_MODES["stage"],
            {"tier4_stage_level": 7, "tier4_sub_stage": "six"},
        ):
            node = QuestMapper().parse_quest("清除野豬")
            return node.to_config_dict(base_config=GAME_CONFIGS["daily"])

    def test_stage_quest_config_drops_tier4_stage_selection(self):
        config = self._build_final_quest_config()

        self.assertEqual(config["stage_level"], 1)
        self.assertEqual(config["sub_stage"], "final")
        self.assertEqual(config["stage_target"], "stages/boss_skull.png")
        self.assertNotIn("tier4_stage_level", config)
        self.assertNotIn("tier4_sub_stage", config)

    @patch("os.path.exists", return_value=True)
    def test_final_quest_rejects_top_page_skull_despite_stale_tier4_hint(
        self, _mock_exists
    ):
        machine = MagicMock()
        machine.STATE_DIAMOND_COLLECTION = "DIAMOND_COLLECTION"
        machine.STATE_BREAD_COLLECTION = "BREAD_COLLECTION"
        machine.STATE_LOBBY = "LOBBY"
        machine.STATE_DUNGEON_EXPLORING = "DUNGEON_EXPLORING"
        machine.STATE_BAG_CLEANING = "BAG_CLEANING"
        machine.STATE_COLLECT_ONLY = "COLLECT_ONLY"
        machine.diamond_window_opened = False
        machine.bread_window_opened = False
        machine.need_bag_cleaning = False
        machine.need_diamond_collection = False
        machine.enable_bread = False
        machine.need_bread_collection = False
        machine.is_daily_pipeline_active.return_value = False
        machine.has_available_dungeon.return_value = False
        machine.dungeon_cooldowns = {}

        machine.config = self._build_final_quest_config()
        # Simulate an old or externally constructed route that still carries the
        # conflicting profile field. Active quest selection must still win.
        machine.config["tier4_sub_stage"] = "six"
        setattr(
            machine,
            "missing_time_stages/boss_skull.png",
            time.time() - 2.0,
        )
        machine.last_stage_scroll_time = 0.0
        machine.matcher.match_mutually_exclusive_tabs.return_value = (
            True,
            False,
            (0, 0),
            0.95,
        )

        def fake_match(_img, template, threshold=0.8, *args, **kwargs):
            if template == "stages/stage_label.png":
                return ((100, 200), 0.95)
            if template == "stages/first_stage.png":
                return ((100, 269), 0.98)
            if template == "stages/six_stage.png":
                return ((100, 422), 0.90)
            if template == "stages/boss_skull.png":
                return ((500, 570), 0.96)
            return (None, 0.0)

        machine.matcher.match.side_effect = fake_match
        handler = NavigationHandler(machine)
        handler.card_alignment_tab = "stage"

        handler.handle(
            MagicMock(),
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        )

        machine.mouse.click.assert_not_called()
        machine.mouse.drag.assert_called_once_with(960, 740, 960, 340)


if __name__ == "__main__":
    unittest.main()
