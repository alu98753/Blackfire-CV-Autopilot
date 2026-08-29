import unittest
from unittest.mock import MagicMock, patch

from states.state_machine import GameStateMachine


class TestRuntimeConfigRefresh(unittest.TestCase):
    def _machine(self):
        return GameStateMachine(
            capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock(), preload_ocr=False
        )

    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_applies_changed_mode_at_loop_boundary(self, _reload, get_mode):
        initial_base = {"type": "dungeon", "bless_mode": "combat", "cooldown_map": {1: 300.0}}
        changed_base = {"type": "dungeon", "bless_mode": "exp", "cooldown_map": {1: 42.0}}
        get_mode.return_value = changed_base
        machine = self._machine()
        machine.config = initial_base.copy()
        machine.primary_config = initial_base.copy()
        machine.enable_runtime_config_refresh("dungeon", initial_base)

        self.assertTrue(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["bless_mode"], "exp")
        self.assertEqual(machine.config["cooldown_map"][1], 42.0)

    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_profile_snapshot_replaces_startup_override(self, _reload, get_mode):
        initial_base = {"type": "dungeon", "bless_mode": "combat", "cooldown_map": {1: 300.0}}
        selected_config = {"type": "dungeon", "bless_mode": "life", "cooldown_map": {1: 300.0}}
        changed_base = {"type": "dungeon", "bless_mode": "exp", "cooldown_map": {1: 42.0}}
        get_mode.return_value = changed_base
        machine = self._machine()
        machine.config = selected_config.copy()
        machine.primary_config = selected_config.copy()
        machine.enable_runtime_config_refresh("dungeon", selected_config)

        machine.refresh_config_at_safe_point()

        self.assertEqual(machine.config["bless_mode"], "exp")
        self.assertEqual(machine.config["cooldown_map"][1], 42.0)

    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_profile_reload_updates_collection_policies(self, _reload, get_mode):
        initial = {"type": "mix", "auto_bread": True, "auto_diamond": True}
        changed = {"type": "mix", "auto_bread": False, "auto_diamond": False}
        get_mode.return_value = changed
        machine = self._machine()
        machine.config = initial.copy()
        machine.primary_config = initial.copy()
        machine.bread_collection_available = True
        machine.enable_bread = True
        machine.need_bread_collection = True
        machine.need_diamond_collection = True
        machine.enable_runtime_config_refresh("daily", initial)

        self.assertTrue(machine.refresh_config_at_safe_point())
        self.assertFalse(machine.enable_bread)
        self.assertFalse(machine.need_bread_collection)
        self.assertFalse(machine.need_diamond_collection)

    def test_disabled_profile_diamond_policy_does_not_retrigger_collection(self):
        machine = self._machine()
        machine.config = {"type": "mix", "auto_diamond": False}
        machine.last_diamond_collection_time = 0.0

        machine.check_collection_trigger(None)

        self.assertFalse(machine.need_diamond_collection)

    def test_lord_boss_targets_only_return_selected_ready_bosses(self):
        machine = self._machine()
        machine.config = {"lord_boss_targets": ["lord_spider"]}
        machine.daily_manager = MagicMock()
        machine.daily_manager.get_available_lord_bosses.return_value = [
            "lord_spectre", "lord_spider"
        ]

        self.assertEqual(machine.get_available_selected_lord_bosses(), ["lord_spider"])
        self.assertTrue(machine.has_available_selected_lord_boss())

        machine.config["lord_boss_targets"] = []
        self.assertEqual(machine.get_available_selected_lord_bosses(), [])
        self.assertFalse(machine.has_available_selected_lord_boss())

    @patch("states.state_machine.refresh_runtime_config", return_value=False)
    def test_does_not_change_running_config_without_a_valid_new_snapshot(self, _reload):
        machine = self._machine()
        machine.runtime_config_key = "dungeon"
        machine.config = {"type": "dungeon", "bless_mode": "life"}

        self.assertFalse(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["bless_mode"], "life")

    @patch("states.state_machine.get_stage_configs")
    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_rebuilds_stage_target_from_reloaded_tier4_selection(
        self, _reload, get_mode, get_stage_configs
    ):
        stage_configs = {
            "6": {
                "name": "Level 6",
                "entry": "stages/level6.png",
                "sub_stages": {
                    "six": "stages/six_stage.png",
                    "final": "stages/level6_final.png",
                },
            },
        }
        initial = {
            "type": "mix", "enable_stage_farming": True,
            "tier4_stage_level": 6, "tier4_sub_stage": "final",
        }
        changed = {**initial, "tier4_sub_stage": "six"}
        get_mode.return_value = changed
        get_stage_configs.return_value = stage_configs
        machine = self._machine()
        machine.config = {**initial, "stage_target": "stages/level6_final.png"}
        machine.primary_config = machine.config.copy()
        machine.enable_runtime_config_refresh("daily", machine.config)

        self.assertTrue(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["stage_target"], "stages/six_stage.png")
        self.assertIn("stages/six_stage.png", machine.config["stage_navigation_path"])

    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_rebuilds_dungeon_target_from_reloaded_tier4_selection(
        self, _reload, get_mode
    ):
        dungeon_entries = [
            "dungeons/Slime_entry.png",
            "dungeons/Ghost_entry.png",
            "dungeons/Forest_entry.png",
            "dungeons/Ruins_entry.png",
            "dungeons/dark_prison.png",
            "dungeons/Ice_entry.png"
        ]
        dungeon_names = ["黏糊糊的石窟", "幽影地穴", "森林迷宮", "神秘遺跡", "幽暗監獄", "冰雪洞窟"]
        initial = {
            "type": "mix",
            "dungeon_entries": dungeon_entries,
            "dungeon_names": dungeon_names,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 3,
            "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        }
        changed = {
            "type": "mix",
            "dungeon_entries": dungeon_entries,
            "dungeon_names": dungeon_names,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 1,
            "navigation_path": ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        }
        get_mode.return_value = changed
        machine = self._machine()
        machine.config = initial.copy()
        machine.primary_config = initial.copy()
        machine.enable_runtime_config_refresh("daily", machine.config)

        # 初始啟動時應已正確更新為第 4 關 (Ruins)
        self.assertEqual(machine.config["tier4_dungeon_index"], 3)
        self.assertIn("dungeons/Ruins_entry.png", machine.config["navigation_path"])

        # 安全點熱重載後應更新為第 2 關 (Ghost)
        self.assertTrue(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["tier4_dungeon_index"], 1)
        self.assertIn("dungeons/Ghost_entry.png", machine.config["navigation_path"])

