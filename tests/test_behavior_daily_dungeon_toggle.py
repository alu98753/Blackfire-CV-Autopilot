"""Tests for Daily mode dungeon toggle (enable/disable) and profile persistence."""

import unittest
from unittest.mock import MagicMock, patch
import argparse
from pathlib import Path

from cli.dungeon_setup import setup_dungeon_config
from cli.mode_setup import setup_mode_config


class TestDailyDungeonToggle(unittest.TestCase):
    """Behavior tests for Daily mode dungeon toggle and persistence."""

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', return_value="8")
    def test_daily_dungeon_selection_disable_option_8(self, mock_input, mock_persist):
        """[選單 8 停用測試] 驗證在 daily 模式下選擇 8 時，停用地下城並寫回 profile，且不提示祝福/退避問答"""
        config = {
            "_config_mode_key": "daily",
            "enable_dungeon": True,
            "tier4_dungeon_index": 5,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config, args, interactive=True, allow_disable=True)

        self.assertFalse(res["enable_dungeon"])
        mock_persist.assert_called_once_with(config, {"enable_dungeon": False})
        # 僅消耗 1 次 input (直接 early return，不問祝福與自動返回)
        self.assertEqual(mock_input.call_count, 1)

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', side_effect=["6", "1", "2"])
    def test_daily_dungeon_selection_re_enable_from_disabled(self, mock_input, mock_persist):
        """[由停用切換為啟用測試] 驗證在已停用狀態下選擇 6 (冰雪洞窟) 可恢復啟用並回寫 profile"""
        config = {
            "_config_mode_key": "daily",
            "enable_dungeon": False,
            "tier4_dungeon_index": 4,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config, args, interactive=True, allow_disable=True)

        self.assertTrue(res["enable_dungeon"])
        self.assertEqual(res["tier4_dungeon_index"], 6)
        self.assertTrue(mock_persist.called)
        last_updates = mock_persist.call_args[0][1]
        self.assertTrue(last_updates.get("enable_dungeon"))

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', return_value="")
    def test_daily_dungeon_selection_default_is_8_when_disabled(self, mock_input, mock_persist):
        """[停用狀態 Enter 沿用測試] 驗證當 TOML 已為停用時，預設選擇為 8，Enter 保持停用且不重複寫回"""
        config = {
            "_config_mode_key": "daily",
            "enable_dungeon": False,
            "tier4_dungeon_index": 5,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config, args, interactive=True, allow_disable=True)

        self.assertFalse(res["enable_dungeon"])
        # 原本就是 False，選擇 8 不應重複調用 persist
        mock_persist.assert_not_called()
        self.assertEqual(mock_input.call_count, 1)

    @patch('cli.mode_setup.setup_daily_tier4_config')
    @patch('cli.mode_setup.setup_dungeon_config')
    def test_daily_cli_no_dungeon_bypasses_setup(self, mock_setup_dungeon, mock_setup_tier4):
        """[CLI 參數停用測試] 驗證傳入 --no-dungeon (args.enable_dungeon=False) 時直接跳過地下城選單"""
        args = argparse.Namespace(
            mode="daily",
            subflow=None,
            backend=False,
            blessmode=None,
            enable_lord_boss=None,
            enable_dungeon=False,
            enable_stage_farming=None,
            enable_town_daily=None,
        )

        cfg = setup_mode_config(args)

        self.assertFalse(cfg["enable_dungeon"])
        mock_setup_dungeon.assert_not_called()
        mock_setup_tier4.assert_called_once()

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', side_effect=["7", "135", "1", "2"])
    def test_daily_dungeon_selection_greedy_custom_subset_persists(self, mock_input, mock_persist):
        """[貪婪自訂子集測試] 驗證選擇 7 並輸入 135 時，啟用地下城、設定 greedy_allowed_indices=[1, 3, 5] 並回寫 profile"""
        config_dict = {
            "_config_mode_key": "daily",
            "enable_dungeon": False,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "greedy_allowed_indices": [1, 2, 3, 4, 5, 6],
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        self.assertTrue(res["enable_dungeon"])
        self.assertTrue(res["greedy_dungeon"])
        self.assertEqual(res["greedy_allowed_indices"], [1, 3, 5])
        self.assertTrue(mock_persist.called)
        last_updates = mock_persist.call_args[0][1]
        self.assertTrue(last_updates.get("enable_dungeon"))
        self.assertTrue(last_updates.get("greedy_dungeon"))
        self.assertEqual(last_updates.get("greedy_allowed_indices"), [1, 3, 5])

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', side_effect=["7", "", "1", "2"])
    def test_daily_dungeon_selection_greedy_default_all_persists(self, mock_input, mock_persist):
        """[貪婪預設全部測試] 驗證選擇 7 並直接 Enter 時，預設打全部 1~6 關並回寫 profile"""
        config_dict = {
            "_config_mode_key": "daily",
            "enable_dungeon": False,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "greedy_allowed_indices": [1, 2, 3, 4, 5, 6],
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        self.assertTrue(res["enable_dungeon"])
        self.assertTrue(res["greedy_dungeon"])
        self.assertEqual(res["greedy_allowed_indices"], [1, 2, 3, 4, 5, 6])
        self.assertTrue(mock_persist.called)
        last_updates = mock_persist.call_args[0][1]
        self.assertTrue(last_updates.get("enable_dungeon"))
        self.assertTrue(last_updates.get("greedy_dungeon"))

    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', side_effect=["3", "1", "2"])
    def test_daily_dungeon_selection_single_dungeon_persists_specific_index(self, mock_input, mock_persist):
        """[單一地下城測試] 驗證選擇 3 (森林迷宮) 時，設定 index=3、greedy=False，並回寫 profile"""
        config_dict = {
            "_config_mode_key": "daily",
            "enable_dungeon": True,
            "greedy_dungeon": True,
            "tier4_dungeon_index": 6,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        res = setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        self.assertTrue(res["enable_dungeon"])
        self.assertFalse(res["greedy_dungeon"])
        self.assertEqual(res["tier4_dungeon_index"], 3)
        self.assertEqual(res["name"], "地下城 - 森林迷宮")
        self.assertTrue(mock_persist.called)
        last_updates = mock_persist.call_args[0][1]
        self.assertFalse(last_updates.get("greedy_dungeon"))
        self.assertEqual(last_updates.get("tier4_dungeon_index"), 3)

    @patch('builtins.input', side_effect=["5", "1", "2"])
    def test_dungeon_standalone_mode_does_not_allow_disable(self, mock_input):
        """[純地下城模式隔離測試] 驗證在非 daily 模式 (allow_disable=False) 下不允許停用"""
        config_dict = {
            "_config_mode_key": "dungeon",
            "enable_dungeon": True,
            "tier4_dungeon_index": 4,
        }
        args = argparse.Namespace(mode="dungeon", blessmode=None)

        res = setup_dungeon_config(config_dict, args, interactive=True, allow_disable=False)

        self.assertTrue(res.get("enable_dungeon", True))
        self.assertEqual(res["tier4_dungeon_index"], 5)


class TestDailyDungeonProfileFilePersistence(unittest.TestCase):
    """端到端驗證：CLI 選擇後的配置真實寫入 user_data/<profile>/config.toml 且內容精確。"""

    def setUp(self):
        import tempfile, shutil
        import config as cfg_module
        self.cfg_module = cfg_module
        self.temp_dir = Path(tempfile.mkdtemp())
        self.profile_name = "test_user"
        (self.temp_dir / self.profile_name).mkdir(parents=True, exist_ok=True)
        self.user_data_patcher = patch.object(cfg_module, "USER_DATA_DIR", self.temp_dir)
        self.user_data_patcher.start()
        cfg_module.set_active_profile(self.profile_name)

    def tearDown(self):
        self.cfg_module.set_active_profile("native")
        self.user_data_patcher.stop()
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _read_profile_toml(self):
        import tomllib
        profile_toml_path = self.temp_dir / self.profile_name / "config.toml"
        self.assertTrue(profile_toml_path.exists(), f"Profile TOML 不存在: {profile_toml_path}")
        with profile_toml_path.open("rb") as f:
            return tomllib.load(f)

    @patch('builtins.input', return_value="8")
    def test_option_8_writes_enable_dungeon_false_to_profile_toml(self, _mock_input):
        """[真實寫檔測試 - 選項 8] 選擇 8 時，真實寫入 [primary_modes.daily] enable_dungeon = false"""
        config_dict = {
            "_config_mode_key": "daily",
            "type": "mix",
            "enable_dungeon": True,
            "tier4_dungeon_index": 6,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        data = self._read_profile_toml()
        daily_cfg = data.get("primary_modes", {}).get("daily", {})
        self.assertIn("enable_dungeon", daily_cfg)
        self.assertFalse(daily_cfg["enable_dungeon"])

    @patch('builtins.input', side_effect=["6", "1", "2"])
    def test_option_6_writes_single_dungeon_to_profile_toml(self, _mock_input):
        """[真實寫檔測試 - 選項 6] 選擇單一地下城時，真實寫入 enable_dungeon = true 與 tier4_dungeon_index = 6"""
        config_dict = {
            "_config_mode_key": "daily",
            "type": "mix",
            "enable_dungeon": False,
            "greedy_dungeon": True,
            "tier4_dungeon_index": 2,
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        data = self._read_profile_toml()
        daily_cfg = data.get("primary_modes", {}).get("daily", {})
        self.assertTrue(daily_cfg.get("enable_dungeon"))
        self.assertFalse(daily_cfg.get("greedy_dungeon"))
        self.assertEqual(daily_cfg.get("tier4_dungeon_index"), 6)

    @patch('builtins.input', side_effect=["7", "135", "1", "2"])
    def test_option_7_writes_greedy_subset_to_profile_toml(self, _mock_input):
        """[真實寫檔測試 - 選項 7] 選擇貪婪並輸入 135 時，真實寫入 greedy_dungeon = true 與 greedy_allowed_indices = [1, 3, 5]"""
        config_dict = {
            "_config_mode_key": "daily",
            "type": "mix",
            "enable_dungeon": False,
            "greedy_dungeon": False,
            "tier4_dungeon_index": 6,
            "greedy_allowed_indices": [1, 2, 3, 4, 5, 6],
        }
        args = argparse.Namespace(mode="daily", blessmode=None)

        setup_dungeon_config(config_dict, args, interactive=True, allow_disable=True)

        data = self._read_profile_toml()
        daily_cfg = data.get("primary_modes", {}).get("daily", {})
        self.assertTrue(daily_cfg.get("enable_dungeon"))
        self.assertTrue(daily_cfg.get("greedy_dungeon"))
        self.assertEqual(daily_cfg.get("greedy_allowed_indices"), [1, 3, 5])


if __name__ == "__main__":
    unittest.main()
