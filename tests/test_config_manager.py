import json
import tempfile
import unittest
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
