"""Tests for Daily mode dungeon toggle (enable/disable) and profile persistence."""

import unittest
from unittest.mock import MagicMock, patch
import argparse

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
    @patch('builtins.input', side_effect=["5", "1", "2"])
    def test_dungeon_standalone_mode_does_not_allow_disable(self, mock_input, mock_persist):
        """[純地下城模式隔離測試] 驗證在非 daily 模式 (allow_disable=False) 下不允許停用"""
        config = {
            "_config_mode_key": "dungeon",
            "enable_dungeon": True,
            "tier4_dungeon_index": 4,
        }
        args = argparse.Namespace(mode="dungeon", blessmode=None)

        res = setup_dungeon_config(config, args, interactive=True, allow_disable=False)

        self.assertTrue(res.get("enable_dungeon", True))
        self.assertEqual(res["tier4_dungeon_index"], 5)


if __name__ == "__main__":
    unittest.main()
