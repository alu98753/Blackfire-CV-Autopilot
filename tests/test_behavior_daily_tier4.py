"""Daily Tier 4 player selection and route behavior."""

import unittest
from unittest.mock import MagicMock, patch

from cli.tier4_setup import setup_daily_tier4_config
from states.state_machine import GameStateMachine
from utils.tier4_config import build_tier4_fallback_config


class TestDailyTier4Behavior(unittest.TestCase):
    @patch("cli.tier4_setup.setup_stage_config")
    @patch("cli.tier4_setup.persist_mode_updates")
    @patch("builtins.input", return_value="1")
    def test_stage_mode_opens_stage_submenu_and_persists_player_choice(
        self, _input, persist, setup_stage
    ):
        config = {
            "_config_mode_key": "daily",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_stage_farming": False,
        }
        setup_stage.side_effect = lambda cfg, **_kwargs: cfg.update(
            {"stage_name": "冰凍峽谷 (final)"}
        )

        setup_daily_tier4_config(config)

        setup_stage.assert_called_once()
        persist.assert_called_once_with(
            config, {"tier4_mode": "stage", "enable_stage_farming": True}
        )
        self.assertEqual(config["tier4_mode"], "stage")
        self.assertTrue(config["enable_stage_farming"])

    @patch("cli.tier4_setup.persist_mode_updates")
    @patch("builtins.input", side_effect=["2", "1"])
    def test_domain_mode_opens_domain_submenu_and_persists_player_choice(
        self, _input, persist
    ):
        config = {
            "_config_mode_key": "daily",
            "tier4_mode": "stage",
            "tier4_stage_level": 6,
            "enable_stage_farming": True,
        }

        setup_daily_tier4_config(config)

        persist.assert_called_once_with(
            config,
            {
                "tier4_mode": "domain",
                "tier4_domain": "golden_empire",
                "enable_stage_farming": False,
            },
        )
        self.assertEqual(config["tier4_domain"], "golden_empire")
        self.assertFalse(config["enable_stage_farming"])

    def test_domain_fallback_preserves_daily_timed_activity_policy(self):
        daily = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_dungeon": True,
            "enable_lord_boss": False,
            "keep_colors": ["purple"],
        }
        modes = {
            "golden_empire": {
                "name": "黃金古國",
                "type": "domain",
                "domain": "golden_empire",
                "navigation_path": ["domains/golden_empire/entry.png"],
                "explore_priorities": ["domains/golden_empire/explore_btn.png"],
            }
        }

        fallback = build_tier4_fallback_config(daily, modes)

        self.assertEqual(fallback["type"], "domain")
        self.assertEqual(fallback["domain"], "golden_empire")
        self.assertTrue(fallback["enable_dungeon"])
        self.assertFalse(fallback["enable_lord_boss"])
        self.assertEqual(fallback["keep_colors"], ["purple"])

    def test_domain_fallback_remains_daily_and_checks_dungeon_policy(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_dungeon": True,
            "enable_lord_boss": True,
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0],
        }

        machine.apply_tier4_fallback_config()

        self.assertEqual(machine.config["type"], "domain")
        self.assertTrue(machine.config["is_tier4_fallback"])
        self.assertTrue(machine.is_daily_pipeline_active())
        self.assertTrue(machine.has_available_daily_dungeon())

    def test_ready_timed_dungeon_preempts_domain_route(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_pending_town_subflows.return_value = []
        machine.daily_manager.get_available_lord_bosses.return_value = []
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "name": "Daily",
            "type": "mix",
            "tier4_mode": "domain",
            "tier4_domain": "golden_empire",
            "enable_town_daily": False,
            "enable_demon_lords": False,
            "enable_lord_boss": False,
            "enable_dungeon": True,
            "dungeon_entries": ["dungeons/Slime_entry.png"],
            "dungeon_names": ["Slime"],
            "greedy_dungeon": True,
            "greedy_allowed_indices": [0],
        }
        machine.apply_tier4_fallback_config()
        machine.current_state = machine.STATE_DOMAIN_EXPLORE

        self.assertTrue(machine.evaluate_next_activity())

        self.assertEqual(machine.config["type"], "mix")
        self.assertEqual(
            machine.config["navigation_path"],
            ["common/door.png", "dungeons/dungeon.png"],
        )
        self.assertTrue(machine.config["is_tier4_fallback"])

    def test_daily_profile_can_disable_timed_lord_activity(self):
        machine = GameStateMachine(
            MagicMock(), MagicMock(), MagicMock(), preload_ocr=False
        )
        machine.runtime_config_key = "daily"
        machine.primary_config = {
            "_config_mode_key": "daily",
            "enable_lord_boss": False,
            "lord_boss_targets": ["lord_spider"],
        }
        machine.config = {
            "type": "domain",
            "enable_lord_boss": False,
            "lord_boss_targets": ["lord_spider"],
        }
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]

        self.assertEqual(machine.get_available_selected_lord_bosses(), [])
        self.assertFalse(machine.has_available_selected_lord_boss())

    @patch("cli.mode_setup.setup_daily_tier4_config")
    @patch("cli.mode_setup.setup_dungeon_config")
    def test_daily_mode_prompts_dungeon_selection_when_enabled(
        self, mock_setup_dungeon, mock_setup_tier4
    ):
        from cli.mode_setup import setup_mode_config

        args = MagicMock()
        args.subflow = None
        args.mode = "daily"
        args.backend = "win32"
        args.enable_lord_boss = None
        args.enable_dungeon = None
        args.enable_stage_farming = None
        args.enable_town_daily = None
        args.enable_demon_lords = None
        args.resume = False

        cfg = setup_mode_config(args)

        mock_setup_dungeon.assert_called_once_with(cfg, args, allow_disable=True)
        mock_setup_tier4.assert_called_once_with(cfg)


if __name__ == "__main__":
    unittest.main()
