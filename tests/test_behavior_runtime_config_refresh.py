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
        get_mode.side_effect = [initial_base, changed_base]
        machine = self._machine()
        machine.config = initial_base.copy()
        machine.primary_config = initial_base.copy()
        machine.enable_runtime_config_refresh("dungeon", initial_base)

        self.assertTrue(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["bless_mode"], "exp")
        self.assertEqual(machine.config["cooldown_map"][1], 42.0)

    @patch("states.state_machine.get_runtime_game_config")
    @patch("states.state_machine.refresh_runtime_config", return_value=True)
    def test_preserves_interactive_selection_while_other_values_refresh(self, _reload, get_mode):
        initial_base = {"type": "dungeon", "bless_mode": "combat", "cooldown_map": {1: 300.0}}
        selected_config = {"type": "dungeon", "bless_mode": "life", "cooldown_map": {1: 300.0}}
        changed_base = {"type": "dungeon", "bless_mode": "exp", "cooldown_map": {1: 42.0}}
        get_mode.side_effect = [initial_base, changed_base]
        machine = self._machine()
        machine.config = selected_config.copy()
        machine.primary_config = selected_config.copy()
        machine.enable_runtime_config_refresh("dungeon", selected_config)

        machine.refresh_config_at_safe_point()

        self.assertEqual(machine.config["bless_mode"], "life")
        self.assertEqual(machine.config["cooldown_map"][1], 42.0)

    @patch("states.state_machine.refresh_runtime_config", return_value=False)
    def test_does_not_change_running_config_without_a_valid_new_snapshot(self, _reload):
        machine = self._machine()
        machine.runtime_config_key = "dungeon"
        machine.config = {"type": "dungeon", "bless_mode": "life"}

        self.assertFalse(machine.refresh_config_at_safe_point())
        self.assertEqual(machine.config["bless_mode"], "life")

