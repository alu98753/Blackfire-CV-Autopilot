import unittest
from unittest.mock import patch, MagicMock
import os
import sys

from config import GAME_CONFIGS
from main import setup_stage_config, setup_dungeon_config, setup_mode_config, check_mode_templates

class TestMainConfig(unittest.TestCase):

    def test_toml_config_preserves_integer_cooldown_indices(self):
        self.assertEqual(GAME_CONFIGS["dungeon"]["cooldown_map"][1], 300.0)

    @patch('os.path.exists')
    @patch('builtins.input', return_value="")
    def test_setup_stage_config_default(self, mock_input, mock_exists):
        """測試 setup_stage_config 預設選擇 (第 6 關魔王關)"""
        mock_exists.return_value = True
        config = GAME_CONFIGS["stage"].copy()
        
        setup_stage_config(config)
        
        self.assertEqual(config["stage_target"], "stages/first_stage.png")
        self.assertEqual(config["stage_entry"], "stages/level6_ice_cave.png")
        self.assertIn("stages/first_stage.png", config["navigation_path"])

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

    def test_setup_equipment_config_and_normalize_config(self):
        """測試 normalize_config 能夠在任何模式下補充完整的 disassemble_colors 與 keep_colors"""
        from main import setup_equipment_config
        from config import normalize_config, GAME_CONFIGS
        
        cfg_collect = GAME_CONFIGS["collect_only"].copy()
        setup_equipment_config(cfg_collect)
        cfg_collect = normalize_config(cfg_collect)
        self.assertEqual(cfg_collect["keep_colors"], ["purple", "orange_yellow", "red"])
        self.assertEqual(cfg_collect["disassemble_colors"], ["gray_or_empty", "green", "blue"])

        cfg_daily = GAME_CONFIGS["daily"].copy()
        cfg_daily = normalize_config(cfg_daily)
        self.assertEqual(cfg_daily["keep_colors"], ["purple", "orange_yellow", "red"])
        self.assertEqual(cfg_daily["disassemble_colors"], ["gray_or_empty", "green", "blue"])

    @patch('os.path.exists')
    @patch('builtins.input', side_effect=["5", "1", "1", "1", "6", "1"])
    def test_setup_mode_config_daily_default(self, mock_input, mock_exists):
        """測試 setup_mode_config 在 daily 模式下啟用 stage farming (地下城 5 冰雪洞窟 + 允許打怪 + 冰凍峽谷 6-1 關卡)"""
        mock_exists.return_value = True
        mock_args = MagicMock()
        mock_args.subflow = None
        mock_args.mode = "daily"
        mock_args.backend = True
        mock_args.blessmode = None
        mock_args.enable_lord_boss = None
        mock_args.enable_dungeon = None
        mock_args.enable_stage_farming = None
        mock_args.enable_town_daily = None

        config = setup_mode_config(mock_args)
        self.assertFalse(config["greedy_dungeon"])
        self.assertIn("dungeons/Ice_entry.png", config["navigation_path"])
        self.assertTrue(config["enable_stage_farming"])
        self.assertEqual(config["stage_entry"], "stages/level6_ice_cave.png")
        self.assertEqual(config["stage_target"], "stages/first_stage.png")
        self.assertEqual(config["bless_mode"], "combat")

    @patch('os.path.exists')
    @patch('builtins.input', side_effect=["1", "2", "2", "2"])
    def test_setup_mode_config_daily_no_stage_farming(self, mock_input, mock_exists):
        """測試 setup_mode_config 在 daily 模式下選擇不打怪 (地下城 1 黏糊糊石窟 + 祝福 2 生命 + 關閉打怪，免選普通關卡)"""
        mock_exists.return_value = True
        mock_args = MagicMock()
        mock_args.subflow = None
        mock_args.mode = "daily"
        mock_args.backend = True
        mock_args.blessmode = None
        mock_args.enable_lord_boss = None
        mock_args.enable_dungeon = None
        mock_args.enable_stage_farming = None
        mock_args.enable_town_daily = None

        config = setup_mode_config(mock_args)
        self.assertFalse(config["greedy_dungeon"])
        self.assertIn("dungeons/Slime_entry.png", config["navigation_path"])
        self.assertFalse(config["enable_stage_farming"])
        self.assertEqual(config["bless_mode"], "life")

    @patch('os.path.exists')
    @patch('builtins.input', side_effect=["1", "2", "1", "1", "1", "4"])
    def test_setup_mode_config_daily_custom(self, mock_input, mock_exists):
        """測試 setup_mode_config 在 daily 模式下自訂選擇 (地下城 1 黏糊糊石窟 + 關卡 1 蒼穹平原魔王關 + 祝福 2 生命)"""
        mock_exists.return_value = True
        mock_args = MagicMock()
        mock_args.subflow = None
        mock_args.mode = "daily"
        mock_args.backend = True
        mock_args.blessmode = None
        mock_args.enable_lord_boss = None
        mock_args.enable_dungeon = None
        mock_args.enable_stage_farming = None
        mock_args.enable_town_daily = None

        config = setup_mode_config(mock_args)
        self.assertFalse(config["greedy_dungeon"])
        self.assertIn("dungeons/Slime_entry.png", config["navigation_path"])
        self.assertTrue(config["enable_stage_farming"])
        self.assertEqual(config["stage_entry"], "stages/level1_sky_plains.png")
        self.assertEqual(config["stage_target"], "stages/level1_final.png")
        self.assertEqual(config["bless_mode"], "life")

if __name__ == "__main__":
    unittest.main()
