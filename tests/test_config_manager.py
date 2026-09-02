import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from utils.config_manager import ConfigLoadError, JsonConfigManager, TomlConfigManager


class TestJsonConfigManager(unittest.TestCase):
    def test_defaults_validator_keeps_last_good_snapshot_during_partial_save(self):
        import config

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "defaults.toml"
            path.write_text(
                config.DEFAULTS_PATH.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            manager = TomlConfigManager(
                path,
                validator=config._validate_defaults_snapshot,
            )
            valid_snapshot = manager.snapshot()

            path.write_text(
                "config_version = 1\n\n[global]\nmonitor_index = 1\n",
                encoding="utf-8",
            )

            self.assertEqual(manager.snapshot(), valid_snapshot)
            self.assertIsInstance(manager.last_error, ConfigLoadError)

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
        original_manager = config._PROFILE_MANAGER
        original_settings = deepcopy(config._SETTINGS)
        original_exports = {
            "global": deepcopy(config.GLOBAL_SETTINGS),
            "primary": deepcopy(config.PRIMARY_MODES),
            "subflow": deepcopy(config.SUBFLOW_CONFIGS),
            "base": deepcopy(config.BASE_STAGE_LEVELS),
            "game": deepcopy(config.GAME_CONFIGS),
            "stage": deepcopy(config.STAGE_CONFIGS),
        }
        original_profile = config.get_active_profile()
        try:
            with tempfile.TemporaryDirectory() as directory:
                local_path = Path(directory) / "local.toml"
                local_path.write_text(
                    "[primary_modes.dungeon]\nbless_mode = 'exp'\n",
                    encoding="utf-8",
                )
                config.LOCAL_CONFIG_PATH = local_path
                config._ACTIVE_PROFILE = "non_existent_profile_for_test"
                config._PROFILE_MANAGER = None

                self.assertTrue(config.refresh_runtime_config())
                self.assertEqual(config.get_runtime_game_config("dungeon")["bless_mode"], "exp")

                local_path.unlink()
                self.assertTrue(config.refresh_runtime_config())
                self.assertEqual(config.get_runtime_game_config("dungeon")["bless_mode"], "combat")
        finally:
            config._ACTIVE_PROFILE = original_profile
            config.LOCAL_CONFIG_PATH = original_path
            config._PROFILE_MANAGER = original_manager
            config._SETTINGS = original_settings
            config._replace_mapping(config.GLOBAL_SETTINGS, original_exports["global"])
            config._replace_mapping(config.PRIMARY_MODES, original_exports["primary"])
            config._replace_mapping(config.SUBFLOW_CONFIGS, original_exports["subflow"])
            config._replace_mapping(config.BASE_STAGE_LEVELS, original_exports["base"])
            config._replace_mapping(config.GAME_CONFIGS, original_exports["game"])
            config._replace_mapping(config.STAGE_CONFIGS, original_exports["stage"])

    def test_global_monitor_index_and_profile_override(self):
        import config
        from config import get_defaults_config, get_monitor_index, set_active_profile

        # 1. 預設 profile (native) 的 monitor_index 為 1
        set_active_profile("native")
        self.assertEqual(get_monitor_index(), 1)
        self.assertEqual(get_defaults_config()["global"]["monitor_index"], 1)

        # 2. 切換至 sandbox profile，應讀取到 user_data/sandbox/config.toml 中的 monitor_index = 2
        set_active_profile("sandbox")
        self.assertEqual(get_monitor_index(), 2)
        self.assertEqual(get_defaults_config()["global"]["monitor_index"], 2)

        # 3. 還原至 native
        set_active_profile("native")
        self.assertEqual(get_monitor_index(), 1)
