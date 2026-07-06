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
        self.state_machine.need_diamond_collection = False
        self.state_machine.last_diamond_collection_time = time.time()

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
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. NAVIGATING 狀態下：
        # - 看到 door.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
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
    def test_dungeon_skill_event_and_descend_flow(self, mock_exists):
        """
        測試地下城模式技能事件與下樓流程：
        點擊技能事件 ➔ 點擊選擇 ➔ 點擊確認/OK ➔ 點擊退出 ➔ 點擊下樓 ➔ 點擊下樓確認。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        
        mock_exists.return_value = True
        
        # 1. 看到 skill_event.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((150, 150), 0.9) if name == "dungeons/skill_event.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(150, 150)
        
        # 2. 看到 choose.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((250, 250), 0.9) if name == "dungeons/choose.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(250, 250)
        
        # 3. 看到 common/ok.png ➔ 點擊確認
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((350, 350), 0.9) if name == "common/ok.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(350, 350)
        
        # 4. 看到 quit.png ➔ 點擊退出
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((450, 450), 0.9) if name == "dungeons/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(450, 450)
        
        # 5. 看到 gungeon_godown.png ➔ 點擊下樓
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((550, 550), 0.9) if name == "dungeons/gungeon_godown.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(550, 550)
        
        # 6. 看到 gungeon_godown_confirm.png ➔ 點擊確認下樓
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((650, 650), 0.9) if name == "dungeons/gungeon_godown_confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(650, 650)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 7. 手動將下樓點擊時間推前 7 秒，模擬冷卻時間屆滿後，重設本層記憶
        self.assertTrue(self.state_machine.skill_selected_this_floor)
        self.state_machine.last_godown_click_time -= 7.0
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.skill_selected_this_floor)

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

    @patch('os.path.exists')
    def test_dungeon_battle_backpack_full_cleaning_flow(self, mock_exists):
        """
        測試地下城模式下，在 BATTLE 戰鬥結束/結算時偵測到背包滿 ➔ 轉移至 EXPLORING ➔ 攔截進入 BAG_CLEANING。
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        
        mock_exists.return_value = True
        
        # 1. 戰鬥中/結算時看到背包已滿 bagfull_quit.png ➔ 點擊並標記 need_bag_cleaning，並轉移至 EXPLORING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((150, 150), 0.9) if name == "common/bagfull_quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(150, 150)
        self.assertTrue(self.state_machine.need_bag_cleaning)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_DUNGEON_EXPLORING)
        
        # 2. 進入 EXPLORING 後，在下一幀因為 need_bag_cleaning 標記，應被 ExploreHandler 攔截轉移至 BAG_CLEANING
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BAG_CLEANING)

    @patch('os.path.exists')
    def test_global_task_complete_and_confirm_interception(self, mock_exists):
        """
        測試全域彈窗攔截器：
        1. 看到 task_complete.png ➔ 點擊「領取獎勵」(相對 Y+281 的座標)
        2. 在大廳狀態下看到確認/OK 彈窗 ➔ 自動點選確認關閉
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        
        # 模擬擷取視窗大小 (1920x1080)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 task_complete.png 位於中心 (960, 540)
        # 預計點擊 Claim Rewards 按鈕中心: X=960, Y=540+281 = 821
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 540), 0.9) if name == "task_complete.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(960, 821)
        
        # 2. 點擊完領取獎勵後，畫面彈出 confirm.png
        # 此時在大廳狀態，通用確認攔截器應點選確認關閉
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 600), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(960, 600)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

    @patch('os.path.exists')
    def test_global_backpack_full_interception(self, mock_exists):
        """
        測試全域背包滿攔截器新邏輯：
        1. 看到 backpack_full.png ➔ 狀態切換至 STATE_BACKPACK_FULL_SORTING
        2. 在 STATE_BACKPACK_FULL_SORTING 狀態下，若左側無貴重物品 ➔ 點擊右上角關閉 (1540, 240) 且返回 STATE_UNKNOWN
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 全域偵測到 backpack_full.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 540), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BACKPACK_FULL_SORTING)
        
        # 2. 執行 BackpackFullSortingHandler，由於為空畫面 (無貴重物品)，應直接點擊關閉並回到 STATE_UNKNOWN
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 540), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(1540, 240)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

    @patch('os.path.exists')
    def test_backpack_full_sorting_and_destroy_flow(self, mock_exists):
        """
        測試背包滿自適應分選與銷毀流：
        左側 Col 0, Row 0 有一個黃金/橘黃物品。
        右側 Col 0, Row 0 有一個綠色物品。
        1. 看到 backpack_full.png ➔ 狀態切換至 STATE_BACKPACK_FULL_SORTING
        2. 執行 BackpackFullSortingHandler，應定位到綠色物品並點擊 ➔ 點擊 destroy.png ➔ 點擊 confirm.png ➔ 點擊左側貴重物品 ➔ 完成本次分選。
        """
        import numpy as np
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 backpack_full.png 進入狀態
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((960, 540), 0.9) if name == "backpack_full.png" else (None, 0.0)
        )
        self.state_machine.step()
        
        # 2. 準備實體 numpy 圖像，畫上指定邊框顏色以供分選
        test_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        # 左側 Col 0, Row 0: 黃金邊框 (BGR = [0, 200, 200])
        test_img[180+10:180+20, 27+10:27+98] = [0, 200, 200]
        test_img[180+88:180+98, 27+10:27+98] = [0, 200, 200]
        test_img[180+10:180+98, 27+10:27+20] = [0, 200, 200]
        test_img[180+10:180+98, 27+88:27+98] = [0, 200, 200]
        
        # 右側 Col 0, Row 0: 綠色邊框 (BGR = [0, 200, 0])
        # 我們也在中間給一些起伏，使 std 較大，避免被當成純黑空格
        test_img[180+10:180+20, 627+10:627+98] = [0, 200, 0]
        test_img[180+88:180+98, 627+10:627+98] = [0, 200, 0]
        test_img[180+10:180+98, 627+10:627+20] = [0, 200, 0]
        test_img[180+10:180+98, 627+88:627+98] = [0, 200, 0]
        test_img[180+50:180+60, 627+50:627+60] = [50, 50, 50]
        
        self.mock_capturer.capture.return_value = test_img
        
        # 模擬 match 結果
        def match_side_effect(img, name, threshold):
            if name == "backpack_full.png":
                return ((960, 540), 0.9)
            elif name == "common/destroy.png":
                return ((500, 500), 0.9) # 銷毀按鈕
            elif name == "common/confirm.png":
                return ((600, 600), 0.9) # 銷毀確認按鈕
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        
        # 執行 step，觸發 BackpackFullSortingHandler
        self.state_machine.step()
        
        # 驗證最後一個被點選的是左側貴重物品，證明整個鏈式分選流程成功執行
        self.mock_mouse.click.assert_called_with(81, 234)

    @patch('os.path.exists')
    def test_global_diamond_collection_flow(self, mock_exists):
        """
        測試自動領取鑽石流程以及當體力與鑽石計時器同時到期時的優先順序 (先領鑽石，再領體力)：
        1. 看到 goback_town.png ➔ 狀態轉移至 NAVIGATING
        2. 在 NAVIGATING 狀態下看到 goback_town.png ➔ 點點返回大廳
        3. 看到 diamond.png ➔ 點點打開鑽石領取畫面
        4. 看到 diamond_free.png ➔ 點點領取免費鑽石
        5. 看到 confirm.png ➔ 點點確認並標記 diamond_collected_this_run
        6. 看到 quit_bread.png ➔ 關閉鑽石畫面，結束鑽石流程，並開始體力流程
        7. 看到 common/bread.png ➔ 開始點點進入領體力
        """
        self.state_machine.config = GAME_CONFIGS["dungeon_slime"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.need_diamond_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測 goback_town.png ➔ 轉移狀態 (不點擊)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 2. 進入 NAVIGATING 後 ➔ 點擊 goback_town.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 800)
        
        # 3. 看到 diamond.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "diamond.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # 4. 看到 diamond_free.png ➔ 點擊
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((300, 300), 0.9) if name == "diamond_free.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(300, 300)
        
        # 5. 看到 confirm.png ➔ 點擊確認，並標記 diamond_collected_this_run
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertTrue(self.state_machine.diamond_collected_this_run)
        
        # 6. 看到退出按鈕 ➔ 關閉鑽石，重置 need_diamond_collection 為 False，開始體力流程
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/quit_bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertFalse(self.state_machine.need_diamond_collection)
        self.assertFalse(self.state_machine.diamond_collected_this_run)
        
        # 7. 下一幀應自動啟動體力領取流程 (尋找 bread.png 並點擊)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        self.assertTrue(self.state_machine.need_bread_collection)

if __name__ == "__main__":
    unittest.main()
