import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import BehavioralScenarioTestCase


class TestCollectionScenarios(BehavioralScenarioTestCase):

    @patch('os.path.exists')
    def test_diamond_cooldown_exit(self, mock_exists):
        """
        [行為場景 2] 鑽石冷卻退出行為：
        Given: 鑽石領取定時器到期，且已進入鑽石領取視窗。
        When: 畫面上無免費領取按鈕 (傳回 None)。
        Then: 程式應識別冷卻狀態，直接點擊退出按鈕退出視窗，且重設鑽石領取需求，防止卡在視窗中。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.need_diamond_collection = True
        self.state_machine.diamond_collected_this_run = False
        self.state_machine.diamond_window_opened = True
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        
        # Act
        def match_side_effect_cooldown(img, name, threshold):
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_cooldown
        self.state_machine.step()
        self.state_machine.step()
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertTrue(self.state_machine.need_diamond_collection)
        
        # 模擬退出按鈕消失，第二步完成重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.need_diamond_collection)

    @patch('os.path.exists')
    @patch('time.time')
    def test_bread_cooldown_exit_defense(self, mock_time, mock_exists):
        """
        [行為場景 12] 領體力冷卻/已滿自動關閉保護行為：
        Given: 體力領取定時器到期，進入 NAVIGATING 狀態領體力。
               畫面上無免費領取按鈕 (collect.png 匹配失敗)，但看見關閉退出按鈕 (common/quit.png)。
        When: 執行狀態機決策。
        Then:
          1. 程式應識別冷卻/已領狀態，點擊退出按鈕 (common/quit.png)。
          2. need_bread_collection 應被設為 False，last_bread_collection_time 應更新，防止無限卡死在視窗內。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.bread_window_opened = True
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        
        # 設定虛擬目前時間為 1000s
        mock_time.return_value = 1000.0
        
        # 模擬 match：quit.png 成功，collect.png 失敗
        def match_side_effect(img, name, threshold):
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        
        # Act 1: 第一次執行，因未嘗試過領取，執行防禦性相對座標點擊 (X = 0+500-208 = 292, Y = 0+500+612 = 1112)
        self.state_machine.step()
        
        # Assert 1
        self.mock_mouse.click.assert_called_with(292, 1112)
        self.assertTrue(self.state_machine.need_bread_collection)
        self.assertTrue(self.state_machine.bread_click_attempted)
        
        # Act 2: 第二次執行，因已嘗試過領取，執行退出體力按鈕點擊，第一步應點擊但尚未重置
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        # Assert 2
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertTrue(self.state_machine.need_bread_collection)
        self.assertTrue(self.state_machine.bread_click_attempted)
        
        # Act 3: 第三次執行，模擬退出按鈕消失，完成退出重置
        self.mock_mouse.click.reset_mock()
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        
        # Assert 3
        self.assertFalse(self.state_machine.need_bread_collection)
        self.assertFalse(self.state_machine.bread_click_attempted)
        self.assertEqual(self.state_machine.last_bread_collection_time, 1000.0)

    @patch('os.path.exists')
    def test_result_exit_battle_click_if_diamond_due(self, mock_exists):
        """
        [行為場景 17-C] 領鑽石時間到時應點擊離開戰鬥按鈕：
        Given: 狀態機處於 RESULT 狀態，且 need_diamond_collection = True。
        When: 執行狀態機決策。
        Then: 程式應點擊 exit_battle.png 退出結算，回大廳準備領鑽石。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_bag_cleaning = False
        self.state_machine.need_diamond_collection = True
        mock_exists.return_value = True
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "exit_battle.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(200, 200)

    @patch('os.path.exists')
    def test_result_exit_battle_click_if_bread_due(self, mock_exists):
        """
        [行為場景 17-D] 領體力時間到時應點擊離開戰鬥按鈕：
        Given: 狀態機處於 RESULT 狀態，enable_bread = True 且 need_bread_collection = True。
        When: 執行狀態機決策。
        Then: 程式應點擊 exit_battle.png 退出結算，回大廳準備領體力。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_bag_cleaning = False
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        mock_exists.return_value = True
        
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "exit_battle.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        
        # Act
        self.state_machine.step()
        
        # Assert
        self.mock_mouse.click.assert_called_with(200, 200)


if __name__ == "__main__":
    unittest.main()
