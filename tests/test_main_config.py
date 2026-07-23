import unittest
from unittest.mock import patch, MagicMock
import os
import sys

from config import GAME_CONFIGS
from main import setup_stage_config, setup_dungeon_config, check_mode_templates

class TestMainConfig(unittest.TestCase):

    @patch('os.path.exists')
    @patch('builtins.input', return_value="")
    def test_setup_stage_config_default(self, mock_input, mock_exists):
        """測試 setup_stage_config 預設選擇 (第 6 關魔王關)"""
        mock_exists.return_value = True
        config = GAME_CONFIGS["stage"].copy()
        
        setup_stage_config(config)
        
        self.assertEqual(config["stage_target"], "stages/level6_final.png")
        self.assertEqual(config["stage_entry"], "stages/level6_ice_cave.png")
        self.assertIn("stages/level6_final.png", config["navigation_path"])

    @patch('os.path.exists')
    @patch('builtins.input', side_effect=["1", "4"])
    def test_setup_stage_config_level1_final(self, mock_input, mock_exists):
        """測試 setup_stage_config 自訂選擇第 1 關魔王關"""
        mock_exists.return_value = True
        config = GAME_CONFIGS["stage"].copy()
        
        setup_stage_config(config)
        
        self.assertEqual(config["stage_target"], "stages/level1_final.png")
        self.assertEqual(config["stage_entry"], "stages/level1_sky_plains.png")
        self.assertIn("stages/level1_final.png", config["navigation_path"])

    @patch('os.path.exists')
    @patch('builtins.input', side_effect=["6", "135", "1"])
    def test_setup_dungeon_config_greedy_custom(self, mock_input, mock_exists):
        """測試 setup_dungeon_config 自訂貪婪挑選 [1, 3, 5] 關卡與戰鬥祝福"""
        mock_exists.return_value = True
        config = GAME_CONFIGS["dungeon"].copy()
        mock_args = MagicMock()
        mock_args.blessmode = None
        
        setup_dungeon_config(config, mock_args)
        
        self.assertTrue(config["greedy_dungeon"])
        self.assertEqual(config["greedy_allowed_indices"], [0, 2, 4])
        self.assertEqual(config["bless_mode"], "combat")

    @patch('os.path.exists')
    def test_check_mode_templates(self, mock_exists):
        """測試 check_mode_templates 缺圖與完整性檢測"""
        config = GAME_CONFIGS["stage"].copy()
        config["navigation_path"] = ["common/door.png", "exit_battle.png"]
        config["lobby_start_btn"] = "stages/start.png"
        
        # 情況 1: 所有圖檔皆存在
        mock_exists.return_value = True
        missing = check_mode_templates(config)
        self.assertEqual(missing, [])

        # 情況 2: 部分圖檔遺失
        def mock_exists_side_effect(path):
            if "stages/retry.png" in path:
                return False
            return True
        mock_exists.side_effect = mock_exists_side_effect
        missing = check_mode_templates(config)
        self.assertIn("stages/retry.png", missing)

    @patch('builtins.input', side_effect=["2", "3"])
    def test_setup_equipment_config_collect_only_and_bag_clean(self, mock_input):
        """測試 setup_equipment_config 在 collect_only 跳過選單，而 bag_clean 進行選單設定"""
        from main import setup_equipment_config
        
        cfg_collect = GAME_CONFIGS["collect_only"].copy()
        setup_equipment_config(cfg_collect)
        self.assertEqual(cfg_collect["keep_colors"], [])
        self.assertEqual(cfg_collect["disassemble_colors"], [])

        cfg_bag = GAME_CONFIGS["bag_clean"].copy()
        setup_equipment_config(cfg_bag)
        self.assertEqual(cfg_bag["keep_colors"], ["blue", "purple", "orange_yellow", "red"])
        self.assertEqual(cfg_bag["disassemble_colors"], ["gray_or_empty", "green", "blue"])

if __name__ == "__main__":
    unittest.main()
