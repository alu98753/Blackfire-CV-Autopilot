import unittest
from unittest.mock import MagicMock, patch

from states.handlers.battle import BattleHandler


class TestNemesisTemplatePolicyRouting(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.config = {"type": "dungeon", "nemesis_action": "flee", "nemesis_templates": ["stale.png"]}
        self.machine.primary_config = {"nemesis_action": "pause", "flee_bosses": ["stale.png"]}
        self.machine.battle_start_time = 1.0
        self.handler = BattleHandler(self.machine)

    def test_intervene_policy_starts_existing_timed_intervention(self):
        intervention = MagicMock()
        self.machine.nemesis_intervention = intervention
        self.machine.matcher.match.return_value = ((10, 20), 0.91)

        with patch("states.handlers.battle.get_nemesis_policy", return_value={
            "intervene": ["nemesis/domain/golden_empire/golden_king.png"],
            "flee": [],
        }), patch("states.handlers.battle.os.path.exists", return_value=True):
            self.assertTrue(self.handler._check_and_handle_nemesis_encounter(object(), {}))

        intervention.start.assert_called_once()
        self.machine.pause.assert_not_called()

    def test_flee_policy_uses_existing_flee_subflow(self):
        self.machine.matcher.match.return_value = ((10, 20), 0.91)
        with patch.object(self.handler, "_run_nemesis_flee_subflow", return_value=True) as flee, \
             patch("states.handlers.battle.get_nemesis_policy", return_value={
                 "intervene": [],
                 "flee": ["nemesis/dungeon/dragon_karsos.png"],
             }), patch("states.handlers.battle.os.path.exists", return_value=True):
            self.assertTrue(self.handler._check_and_handle_nemesis_encounter(object(), "rect"))
        flee.assert_called_once_with("rect")

    def test_legacy_mode_keys_cannot_route_or_supply_templates(self):
        with patch("states.handlers.battle.get_nemesis_policy", return_value={"intervene": [], "flee": []}), \
             patch("states.handlers.battle.os.path.exists", return_value=True):
            self.assertFalse(self.handler._check_and_handle_nemesis_encounter(object(), {}))
        self.machine.matcher.match.assert_not_called()

    def test_missing_templates_are_bounded_and_zero_valid_is_fail_open(self):
        with self.assertLogs(level="WARNING") as logs, \
             patch("states.handlers.battle.get_nemesis_policy", return_value={
                 "intervene": ["missing.png"], "flee": []
             }), patch("states.handlers.battle.os.path.exists", return_value=False):
            self.assertFalse(self.handler._check_and_handle_nemesis_encounter(object(), {}))
            self.handler.nemesis_check_done = False
            self.assertFalse(self.handler._check_and_handle_nemesis_encounter(object(), {}))
        missing = [line for line in logs.output if "missing.png" in line]
        self.assertEqual(len(missing), 1)
        self.assertTrue(any("zero valid template files" in line for line in logs.output))
        self.machine.matcher.match.assert_not_called()


class TestNemesisPolicyValidation(unittest.TestCase):
    def test_duplicate_policy_path_is_rejected(self):
        import config
        with self.assertRaises(ValueError):
            config._validate_nemesis_policy({
                "intervene": ["nemesis/a.png"],
                "flee": ["nemesis/a.png"],
            })

    def test_profile_override_replaces_global_lists(self):
        import config
        with patch.object(config, "_get_override_config", return_value={
            "nemesis": {"intervene": ["custom/a.png"]}
        }):
            policy = config.get_nemesis_policy()
        self.assertEqual(policy["intervene"], ["custom/a.png"])
        self.assertEqual(policy["flee"], config.get_canonical_defaults()["nemesis"]["flee"])


if __name__ == "__main__":
    unittest.main()
