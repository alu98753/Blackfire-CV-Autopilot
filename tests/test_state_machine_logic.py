import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestStateMachineLogic(unittest.TestCase):
    def setUp(self):
        # 建立 Mock 物件
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        
        # 模擬視窗大小
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "right": 800, "bottom": 600}
        self.mock_capturer.capture.return_value = MagicMock() # 傳回假的圖片物件
        
        # 實例化狀態機
        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )

    @patch('os.path.exists')
    def test_stage_mode_bread_collection_flow(self, mock_exists):
        """
        測試普通關卡模式：啟動 -> 領體力流程 -> 大廳 -> 戰鬥。
        """
        # 設定為關卡配置，啟用領體力
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        # 模擬所有需要的範本檔案都存在
        mock_exists.return_value = True
        
        # 1. 初始狀態為 UNKNOWN。全域掃描看到 door.png ➔ 應轉移至 NAVIGATING 領體力
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "dungeons/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. NAVIGATING 狀態下：
        # - 看到 door.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "dungeons/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 100)
        self.assertTrue(self.state_machine.need_bread_collection)
        
        # - 看到 bread.png ➔ 點擊打開體力視窗
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # - 看到 bread_collection.png ➔ 點擊領取
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "common/bread_collection.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)

        # - 看到 common/confirm.png ➔ 點擊確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((350, 350), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(350, 350)
        
        # - 看到 quit_bread.png ➔ 點擊退出，結束領取體力流程
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/quit_bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertFalse(self.state_machine.need_bread_collection)
        
        # 3. 領完體力後，NAVIGATING 尋路結束，看到大廳的 stages/start.png ➔ 應轉移至 LOBBY
        # 注意：我們需要先讓尋路因 clicked_any == False 轉移至 LOBBY
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)
        
        # 4. LOBBY 狀態下：看到大廳 stages/start.png ➔ 點擊並轉移至 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "stages/start.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

    @patch('os.path.exists')
    def test_dungeon_slime_explore_and_battle_flow(self, mock_exists):
        """
        測試史萊姆地下城模式：探索事件 -> 遇怪 -> 戰鬥 -> 結算 -> 繼續探索。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        
        # 1. EXPLORING 狀態下：看到開寶箱 Treasure.png ➔ 點擊處理
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "dungeons/Treasure.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 2. EXPLORING 狀態下：看到戰鬥房入口 dungeon_fight.png ➔ 點擊進入
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((700, 700), 0.9) if name == "dungeons/dungeon_fight.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(700, 700)
        # 點擊入口時不應轉移狀態，仍保持在 EXPLORING (等待選祝福)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 3. 進入準備畫面後：看到選擇祝福 choice_bless.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 200), 0.9) if name == "dungeons/choice_bless.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(800, 200)
        
        # 4. 戰鬥真正開打後：偵測到 common/auto.png ➔ 轉移至 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 100), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        
        # 5. BATTLE 狀態下：看到 common/auto.png ➔ 點擊啟用
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 100), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(800, 100)
        
        # 6. 戰鬥結束：看到結算 continue1.png ➔ 點擊並轉回 EXPLORING
        # 注意：dungeon_battle_results 只比對 continue1/2
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((900, 500), 0.9) if name == "common/continue1.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(900, 500)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)

    @patch('os.path.exists')
    def test_backpack_full_cleaning_flow(self, mock_exists):
        """
        測試背包已滿自動清理流程：戰鬥結算偵測到背包滿 ➔ 設定標記 ➔ 回大廳進入 BAG_CLEANING ➔ 執行清理步驟 ➔ 回大廳。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        
        mock_exists.return_value = True
        
        # 1. 在結算畫面看到背包已滿 bagfull_quit.png ➔ 點擊並標記 need_bag_cleaning
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/bagfull_quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 100)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        
        # 2. 隨後看到結算確認 confirm.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # 3. 畫面回到大廳，看到 stages/start.png。此時因為 need_bag_cleaning 標記，大廳處理器應轉移至 LOBBY 再轉至 BAG_CLEANING 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "stages/start.png" else (None, 0.0)
        )
        self.state_machine.step()  # 轉移 RESULT -> LOBBY
        self.state_machine.step()  # LobbyHandler 攔截轉移 LOBBY -> BAG_CLEANING
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)
        
        # 4. BAG_CLEANING 狀態下順序點擊：
        # - 看到 common/bag.png ➔ 點擊打開背包
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/bag.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        
        # - 看到 common/Backpack_Disassembly.png ➔ 點擊進入大量分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/Backpack_Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        
        # - 看到 common/select_all.png ➔ 點擊全選
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/select_all.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        
        # - 看到 common/Disassembly.png ➔ 點擊分解
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((700, 700), 0.9) if name == "common/Disassembly.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(700, 700)
        
        # - 看到確認彈窗 common/confirm.png ➔ 點擊確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((800, 800), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(800, 800)
        
        # - 看到整理按鈕 common/tidy.png ➔ 點擊整理並設定標記 bag_tidied
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((900, 900), 0.9) if name == "common/tidy.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(900, 900)
        self.assertTrue(self.state_machine.bag_tidied)
        
        # - 當 bag_tidied 為 True 時，偵測 quit 按鈕 (dungeons/quit.png) ➔ 點擊退出，結束清理並恢復 LOBBY 狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((1000, 1000), 0.9) if name == "dungeons/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1000, 1000)
        
        self.assertFalse(self.state_machine.need_bag_cleaning)
        self.assertFalse(self.state_machine.bag_tidied)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

if __name__ == "__main__":
    unittest.main()
