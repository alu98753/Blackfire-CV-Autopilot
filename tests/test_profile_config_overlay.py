import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from config import (
    get_defaults_config,
    get_profile_config_path,
    set_active_profile,
    get_active_profile,
    refresh_runtime_config,
    GAME_CONFIGS,
    PRIMARY_MODES,
    SUBFLOW_CONFIGS
)


class TestProfileConfigOverlay(unittest.TestCase):
    def setUp(self):
        self.test_user_data_dir = Path(tempfile.mkdtemp())
        self.sandbox_dir = self.test_user_data_dir / "sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.native_dir = self.test_user_data_dir / "native"
        self.native_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # 切回 native
        with patch.object(config, "USER_DATA_DIR", Path("user_data")):
            set_active_profile("native")
        if self.test_user_data_dir.exists():
            shutil.rmtree(self.test_user_data_dir, ignore_errors=True)

    def test_profile_config_overlay_and_inheritance(self):
        """驗證：沙盒專屬 config.toml 僅覆蓋特定欄位，其餘欄位完美繼承 defaults.toml"""
        sandbox_toml_content = """
[subflow_configs.jewelry_workshop]
enabled = false

[primary_modes.daily]
tier4_stage_level = 4
tier4_sub_stage = "first"
"""
        (self.sandbox_dir / "config.toml").write_text(sandbox_toml_content, encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            # 1. 切換至沙盒 Profile
            set_active_profile("sandbox")
            self.assertEqual(get_active_profile(), "sandbox")
            
            # 2. 驗證覆蓋的屬性
            self.assertFalse(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])
            self.assertEqual(PRIMARY_MODES["daily"]["tier4_stage_level"], 4)
            self.assertEqual(PRIMARY_MODES["daily"]["tier4_sub_stage"], "first")

            # 3. 驗證繼承的屬性 (defaults.toml 中未被覆蓋的設定依舊維持)
            self.assertEqual(PRIMARY_MODES["daily"]["type"], "mix")
            self.assertTrue("bulletin_board" in SUBFLOW_CONFIGS)

            # 4. 切換回 native Profile (無 override，還原 defaults.toml)
            set_active_profile("native")
            self.assertEqual(get_active_profile(), "native")
            self.assertTrue(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])
            self.assertEqual(PRIMARY_MODES["daily"]["tier4_stage_level"], 6)

    def test_profile_hot_reload_when_config_changed(self):
        """驗證：當 Profile 的 config.toml 修改時，refresh_runtime_config 能即時熱加載"""
        config_path = self.sandbox_dir / "config.toml"
        config_path.write_text("""
[subflow_configs.jewelry_workshop]
enabled = false
""", encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            self.assertFalse(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])

            # 模擬使用者在掛機中修改了 config.toml 重新開啟珠寶工廠
            config_path.write_text("""
[subflow_configs.jewelry_workshop]
enabled = true
""", encoding="utf-8")
            
            reloaded = refresh_runtime_config()
            self.assertTrue(reloaded)
            self.assertTrue(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])


if __name__ == "__main__":
    unittest.main()
