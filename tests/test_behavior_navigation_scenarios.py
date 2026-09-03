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


class TestNavigationScenarios(BehavioralScenarioTestCase):

    @patch('os.path.exists')
    def test_navigation_priority_and_safety_lock(self, mock_exists):
        """
        [行為場景 1] 鑽石與體力領取優先權與安全保護行為：
        Given: 鑽石與體力定時器同時到期，且畫面上可見返回城鎮按鈕。
        When: 執行狀態機決策。
        Then:
          1. 應優先執行鑽石流程 (而非體力流程)。
          2. 返回城鎮後開啟鑽石視窗。
          3. 進入視窗後，視窗安全保護機制應鎖定，只比對鑽石免費領取按鈕或關閉按鈕，忽視可能出現在背景的鑽石圖標，點選免費按鈕。
          4. 二次確認領取後關閉視窗，清除鑽石需求，並開始體力領取。
        """
        # Arrange
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True
        self.state_machine.need_diamond_collection = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        mock_exists.return_value = True
        
        # Act & Assert Step 1: 在 UNKNOWN 看到 goback_town.png，轉移至 NAVIGATING
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((100, 800), 0.9) if name == "goback_town.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # Step 2: 點選 goback_town.png 返回城鎮大廳
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(100, 800)
        
        # Step 3: 偵測 diamond.png 開啟鑽石領取視窗
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((200, 200), 0.9) if name == "diamond.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(200, 200)
        
        # Step 4: 進入鑽石視窗 (畫面上存在 common/quit.png)，只比對 free.png (安全鎖定)
        # 即使此時背景可能有一張 diamond.png，在安全保護下亦不會去點擊它
        def match_side_effect_dia_window(img, name, threshold):
            # 模擬視窗內退出按鈕可見
            if name == "common/quit.png":
                return ((500, 500), 0.9)
            # 偵測到免費按鈕
            if name == "free.png":
                return ((300, 300), 0.9)
            # 如果嘗試去點擊大廳入口，回傳 None 阻止
            if name == "diamond.png":
                return ((200, 200), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_dia_window
        self.state_machine.step()
        # 必須是點擊免費鑽石 (300, 300)，而不是重複點擊大廳入口 (200, 200)
        self.mock_mouse.click.assert_called_with(300, 300)
        
        # Step 5: 點選確認領取
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(400, 400)
        self.assertTrue(self.state_machine.diamond_collected_this_run)
        
        # Step 6: 點擊退出按鈕，結束鑽石領取，第一步應點擊但尚未重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "common/quit.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 500)
        self.assertTrue(self.state_machine.need_diamond_collection)
        
        # 模擬退出按鈕消失，第二步完成重置
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (None, 0.0)
        self.state_machine.step()
        self.assertFalse(self.state_machine.need_diamond_collection)
        self.assertFalse(self.state_machine.diamond_collected_this_run)
        
        # Step 7: 自動切換到體力領取流程 (尋找並點擊 common/bread.png)
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((600, 600), 0.9) if name == "common/bread.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(600, 600)
        self.assertTrue(self.state_machine.need_bread_collection)

    @patch('os.path.exists')
    @patch('time.time')
    def test_stage_navigation_path_with_scrolling(self, mock_time, mock_exists):
        """
        [行為場景 18] 關卡模式下的尋路與滑動向下滾動尋找魔王關：
        Given: 狀態機處於 NAVIGATING 狀態。
        When & Then:
          1. 畫面看到 common/select_stage.png ➔ 應點擊該按鈕。
          2. 畫面看到 stages/level2_barren_rocks.png ➔ 應點擊進入第二關。
          3. 畫面看到 stages/level2_entry1.png，但未看見 stages/level2_final.png ➔ 應執行 mouse.scroll 往下滾動，而不進行點擊。
          4. 畫面同時看到 stages/level2_entry1.png 和 stages/level2_final.png ➔ 應優先點擊 stages/level2_final.png，不執行滾動。
        """
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.config["navigation_path"] = [
            "common/door.png",
            "exit_battle.png",
            "common/select_stage.png",
            "stages/level2_barren_rocks.png",
            "stages/stage_label.png",
            "stages/level2_final.png"
        ]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True
        mock_time.return_value = 1000.0
        # 步驟 0: 畫面看到 common/door.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((50, 50), 0.9) if name == "common/door.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(50, 50)

        # 步驟 1: 畫面看到 common/select_stage.png
        # The frame after clicking the town door must prove that ENTER_LOBBY
        # reached its postcondition before the legacy route may continue.
        def match_lobby_stage_selection(img, name, threshold):
            if name == "common/select_stage.png":
                return (150, 150), 0.9
            if name == "goback_town.png":
                return (100, 800), 0.9
            return None, 0.0

        self.mock_matcher.match.side_effect = match_lobby_stage_selection
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(150, 150)
        
        # 步驟 2: 畫面看到 stages/level2_barren_rocks.png
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((250, 250), 0.9) if name == "stages/level2_barren_rocks.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(250, 90)
        
        # 步驟 3: 畫面看到 stages/stage_label.png，但沒有 stages/level2_final.png ➔ 滾動
        # 設定模擬時間
        mock_time.return_value = 1000.0
        self.state_machine.last_stage_scroll_time = 0.0
        
        def match_side_effect_step3(img, name, threshold):
            if name == "stages/stage_label.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_step3
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.drag.reset_mock()
        
        # 模擬魔王關卡已經缺失 2.0 秒，使等待緩衝期已過
        self.state_machine.__setattr__("missing_time_stages/level2_final.png", time.time() - 2.0)

        self.state_machine.step()
        
        # 應調用 drag 拖曳滑動，且不應該點擊
        self.mock_mouse.click.assert_not_called()
        # 拖曳的點應在視窗中心點： rect=(0,0,1920,1080) ➔ 中心為 (960, 540)
        # drag 帶入 start_x=960, start_y=640, end_x=960, end_y=440
        self.mock_mouse.drag.assert_called_with(960, 640, 960, 440)
        self.assertEqual(self.state_machine.last_stage_scroll_time, 1000.0)
        
        # 步驟 4: 畫面同時出現 stages/stage_label.png 和 stages/level2_final.png ➔ 直接點擊 final.png
        def match_side_effect_step4(img, name, threshold):
            if name == "stages/stage_label.png":
                return ((100, 100), 0.9)
            elif name == "stages/level2_final.png":
                return ((350, 350), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_step4
        self.mock_mouse.click.reset_mock()
        self.mock_mouse.drag.reset_mock()
        
        self.state_machine.step()
        
        # 應直接點擊魔王關，不調用拖曳
        self.mock_mouse.click.assert_called_with(350, 350)
        self.mock_mouse.drag.assert_not_called()

    @patch('os.path.exists')
    def test_level_island_click_y_offset(self, mock_exists):
        """
        [行為場景 21] 尋路狀態下關卡小島按鈕 Y 軸向上偏置點擊：
        Given: 狀態機處於 NAVIGATING 狀態。
        When: 畫面中匹配到 stages/level3_ancient_forest.png，其座標為 (500, 600)。
        Then: 點擊的 Y 軸座標應向上偏置減去 160 像素，點擊座標應為 (500, 440)。
        """
        # 手動設置 config 的 navigation_path 包含該關卡小島
        self.state_machine.config = {
            "type": "stage",
            "navigation_path": ["stages/level3_ancient_forest.png"],
            "lobby_start_btn": "stages/start.png"
        }
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True

        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 600), 0.9) if name == "stages/level3_ancient_forest.png" else (None, 0.0)
        )
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(500, 440)

    @patch('os.path.exists')
    def test_navigation_prioritize_lobby_check(self, mock_exists):
        """
        [行為場景 22] 尋路狀態下大廳開始按鈕優先攔截：
        Given: 狀態機處於 NAVIGATING 狀態。
        When: 畫面同時出現大廳開始按鈕 stages/start.png 與小島按鈕 stages/level3_ancient_forest.png。
        Then: 狀態機應優先偵測到大廳開始按鈕，將狀態轉移至 LOBBY，且不觸發小島點擊。
        """
        self.state_machine.config = {
            "type": "stage",
            "navigation_path": ["stages/level3_ancient_forest.png"],
            "lobby_start_btn": "stages/start.png"
        }
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        mock_exists.return_value = True

        def match_side_effect(img, name, threshold):
            if name == "stages/start.png":
                return ((800, 800), 0.9)
            elif name == "stages/level3_ancient_forest.png":
                return ((500, 600), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)
        self.mock_mouse.click.assert_not_called()

    @patch('os.path.exists')
    def test_navigation_in_town_after_diamond_collection_ignores_false_stage_matches(self, mock_exists):
        """
        測試領完鑽石回到城鎮 (TOWN) 時：
        即使背景圖像雜訊導致 stage_templates (如 level4_desert_ruins) 低信心度誤判 (0.603)，
        由於在城鎮 (common/door.png 可見)，不得判定為關卡介面已開啟 (stage_select_open 應強制為 False)，
        亦不可執行滑動，必須點擊 common/door.png 進入大廳！
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        
        def mock_match(img, name, **kw):
            if name == "common/door.png":
                return ((76, 751), 0.9521)
            elif name == "diamond.png":
                return ((1115, 83), 0.9750)
            elif name == "stages/level4_desert_ruins.png":
                return ((194, 795), 0.6030) # 低信心度誤判
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = mock_match
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.mock_mouse.drag.reset_mock()
        self.mock_mouse.click.reset_mock()
        
        self.state_machine.step()
        
        # 斷言：絕不可執行向左/向右拖曳滑動！
        self.mock_mouse.drag.assert_not_called()
        # 斷言：必須點擊 common/door.png (76, 751) 進入大廳！
        self.mock_mouse.click.assert_called_once_with(76, 751)


if __name__ == "__main__":
    unittest.main()
