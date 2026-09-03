import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import config
from config import (
    get_defaults_config,
    get_profile_config_path,
    set_active_profile,
    get_active_profile,
    refresh_runtime_config,
    get_runtime_game_config,
    GAME_CONFIGS,
    PRIMARY_MODES,
    SUBFLOW_CONFIGS,
    BACKPACK_FULL_SETTINGS,
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

    def test_sell_and_destroy_goods_are_independent_per_profile(self):
        sandbox_config = """
[subflow_configs.jewelry_workshop.sell_goods.gray]
Warcraft_Fang = true

[backpack_full.destroy_goods.gray]
Warcraft_Fang = false
"""
        native_config = """
[subflow_configs.jewelry_workshop.sell_goods.gray]
Warcraft_Fang = false

[backpack_full.destroy_goods.gray]
Warcraft_Fang = true
"""
        (self.sandbox_dir / "config.toml").write_text(
            sandbox_config, encoding="utf-8"
        )
        (self.native_dir / "config.toml").write_text(
            native_config, encoding="utf-8"
        )

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            self.assertTrue(
                SUBFLOW_CONFIGS["jewelry_workshop"]["sell_goods"]["gray"]["Warcraft_Fang"]
            )
            self.assertFalse(
                BACKPACK_FULL_SETTINGS["destroy_goods"]["gray"]["Warcraft_Fang"]
            )

            set_active_profile("native")
            self.assertFalse(
                SUBFLOW_CONFIGS["jewelry_workshop"]["sell_goods"]["gray"]["Warcraft_Fang"]
            )
            self.assertTrue(
                BACKPACK_FULL_SETTINGS["destroy_goods"]["gray"]["Warcraft_Fang"]
            )

    def test_legacy_jewelry_goods_settings_overrides_sell_goods(self):
        legacy_config = """
[subflow_configs.jewelry_workshop.goods_settings.gray]
Warcraft_Fang = true
"""
        (self.sandbox_dir / "config.toml").write_text(
            legacy_config, encoding="utf-8"
        )

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            workshop = SUBFLOW_CONFIGS["jewelry_workshop"]
            self.assertTrue(workshop["sell_goods"]["gray"]["Warcraft_Fang"])
            self.assertNotIn("goods_settings", workshop)

    def test_sandbox_profile_reload_syncs_running_daily_mode(self):
        """A running daily machine must consume changed sandbox Profile values."""
        from states.state_machine import GameStateMachine

        config_path = self.sandbox_dir / "config.toml"
        config_path.write_text("""
[primary_modes.daily]
bless_mode = "combat"
auto_bread = true
auto_diamond = true
""", encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            initial = get_runtime_game_config("daily")
            machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock(), preload_ocr=False)
            machine.config = initial.copy()
            machine.primary_config = initial.copy()
            machine.bread_collection_available = True
            machine.enable_bread = True
            machine.need_bread_collection = True
            machine.need_diamond_collection = True
            machine.enable_runtime_config_refresh("daily", initial)

            config_path.write_text("""
[primary_modes.daily]
bless_mode = "life"
auto_bread = false
auto_diamond = false
""", encoding="utf-8")

            self.assertTrue(machine.refresh_config_at_safe_point())
            self.assertEqual(machine.config["bless_mode"], "life")
            self.assertFalse(machine.enable_bread)
            self.assertFalse(machine.need_bread_collection)
            self.assertFalse(machine.need_diamond_collection)

    def test_sandbox_boss_targets_apply_to_stage_mode(self):
        config_path = self.sandbox_dir / "config.toml"
        config_path.write_text("""
[defaults.activities]
lord_boss_targets = ["lord_spider"]
""", encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            self.assertEqual(GAME_CONFIGS["stage"]["lord_boss_targets"], ["lord_spider"])

    def test_vision_thresholds_overlay_and_get_template_threshold(self):
        """驗證：vision 比對門檻與 template_thresholds 的讀取、繼承與 get_template_threshold 運作"""
        from config import (
            DEFAULT_THRESHOLD,
            SUB_STAGE_THRESHOLD,
            EXIT_BATTLE_THRESHOLD,
            ENTRY_THRESHOLD,
            get_template_threshold
        )
        # 1. 預設 defaults.toml 讀取
        self.assertEqual(DEFAULT_THRESHOLD, 0.80)
        self.assertEqual(SUB_STAGE_THRESHOLD, 0.93)
        self.assertEqual(EXIT_BATTLE_THRESHOLD, 0.88)
        self.assertEqual(ENTRY_THRESHOLD, 0.60)
        self.assertEqual(get_template_threshold("stages/six_stage.png"), 0.93)
        self.assertEqual(get_template_threshold("stages/first_stage.png"), 0.90)
        self.assertEqual(get_template_threshold("stages/final_boss_stage.png"), 0.93)
        self.assertEqual(get_template_threshold("common/door.png"), 0.80)
        self.assertEqual(get_template_threshold("common/door.png", default=0.60), 0.60)

        # 2. 測試 Profile 自訂覆蓋特定模板門檻
        sandbox_toml_content = """
[vision]
sub_stage_threshold = 0.94

[vision.template_thresholds]
"stages/six_stage.png" = 0.96
"stages/first_stage.png" = 0.92
"""
        (self.sandbox_dir / "config.toml").write_text(sandbox_toml_content, encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            self.assertEqual(get_template_threshold("stages/six_stage.png"), 0.96)
            self.assertEqual(get_template_threshold("stages/first_stage.png"), 0.92)
            self.assertEqual(get_template_threshold("stages/level6_final.png"), 0.94)

            # 切回 native
            set_active_profile("native")
            self.assertEqual(get_template_threshold("stages/six_stage.png"), 0.93)
            self.assertEqual(get_template_threshold("stages/first_stage.png"), 0.90)

    def test_update_profile_config_writes_and_reloads(self):
        """驗證：update_profile_config 寫入 user_data/<profile>/config.toml 並即時熱重載生效"""
        from config import update_profile_config
        # 初始狀態：先將 sandbox 的珠寶店設為關閉
        (self.sandbox_dir / "config.toml").write_text("""
[subflow_configs.jewelry_workshop]
enabled = false
""", encoding="utf-8")

        with patch.object(config, "USER_DATA_DIR", self.test_user_data_dir):
            set_active_profile("sandbox")
            self.assertFalse(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])

            # 呼叫 update_profile_config 啟用珠寶店並設定 Tier 4 退守為 Level 4
            update_profile_config("sandbox", {
                "subflow_configs": {
                    "jewelry_workshop": {"enabled": True}
                },
                "primary_modes": {
                    "daily": {
                        "tier4_stage_level": 4,
                        "tier4_sub_stage": "final"
                    }
                }
            })

            # 驗證即時熱重載生效
            self.assertTrue(SUBFLOW_CONFIGS["jewelry_workshop"]["enabled"])
            self.assertEqual(PRIMARY_MODES["daily"]["tier4_stage_level"], 4)
            self.assertEqual(PRIMARY_MODES["daily"]["tier4_sub_stage"], "final")

            # 驗證實體檔案存在且內容正確
            saved_content = (self.sandbox_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn("tier4_stage_level = 4", saved_content)
            self.assertIn('tier4_sub_stage = "final"', saved_content)


if __name__ == "__main__":
    unittest.main()
