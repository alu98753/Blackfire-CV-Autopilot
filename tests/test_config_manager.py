import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from utils.config_manager import ConfigLoadError, JsonConfigManager


class TestJsonConfigManager(unittest.TestCase):
    def test_hot_reload_publishes_new_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"revision": 1}), encoding="utf-8")
            manager = JsonConfigManager(path)

            self.assertEqual(manager.snapshot(), {"revision": 1})
            path.write_text(json.dumps({"revision": 2, "enabled": True}), encoding="utf-8")

            self.assertEqual(manager.snapshot(), {"revision": 2, "enabled": True})

    def test_invalid_edit_keeps_last_known_good_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"enabled": True}), encoding="utf-8")
            manager = JsonConfigManager(path)
            self.assertEqual(manager.snapshot(), {"enabled": True})

            path.write_text("{ invalid json", encoding="utf-8")

            self.assertEqual(manager.snapshot(), {"enabled": True})
            self.assertIsInstance(manager.last_error, ConfigLoadError)

    def test_returns_copy_to_protect_published_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"nested": {"value": 1}}), encoding="utf-8")
            manager = JsonConfigManager(path)

            config = manager.snapshot()
            config["nested"]["value"] = 99

            self.assertEqual(manager.snapshot()["nested"]["value"], 1)

    def test_toml_manager_loads_declarative_defaults(self):
        from config import get_defaults_config

        settings = get_defaults_config()

        self.assertEqual(settings["config_version"], 1)
        self.assertIn("dungeon", settings["primary_modes"])

    def test_local_toml_overrides_mode_and_can_be_removed(self):
        import config

        original_path = config.LOCAL_CONFIG_PATH
        original_manager = config._LOCAL_MANAGER
        original_settings = deepcopy(config._SETTINGS)
        original_exports = {
            "global": deepcopy(config.GLOBAL_SETTINGS),
            "primary": deepcopy(config.PRIMARY_MODES),
            "subflow": deepcopy(config.SUBFLOW_CONFIGS),
            "base": deepcopy(config.BASE_STAGE_LEVELS),
            "game": deepcopy(config.GAME_CONFIGS),
            "stage": deepcopy(config.STAGE_CONFIGS),
        }
        try:
            with tempfile.TemporaryDirectory() as directory:
                local_path = Path(directory) / "local.toml"
                local_path.write_text(
                    "[primary_modes.dungeon]\nbless_mode = 'exp'\n",
                    encoding="utf-8",
                )
                config.LOCAL_CONFIG_PATH = local_path
                config._LOCAL_MANAGER = None

                self.assertTrue(config.refresh_runtime_config())
                self.assertEqual(config.get_runtime_game_config("dungeon")["bless_mode"], "exp")

                local_path.unlink()
                self.assertTrue(config.refresh_runtime_config())
                self.assertEqual(config.get_runtime_game_config("dungeon")["bless_mode"], "combat")
        finally:
            config.LOCAL_CONFIG_PATH = original_path
            config._LOCAL_MANAGER = original_manager
            config._SETTINGS = original_settings
            config._replace_mapping(config.GLOBAL_SETTINGS, original_exports["global"])
            config._replace_mapping(config.PRIMARY_MODES, original_exports["primary"])
            config._replace_mapping(config.SUBFLOW_CONFIGS, original_exports["subflow"])
            config._replace_mapping(config.BASE_STAGE_LEVELS, original_exports["base"])
            config._replace_mapping(config.GAME_CONFIGS, original_exports["game"])
            config._replace_mapping(config.STAGE_CONFIGS, original_exports["stage"])
