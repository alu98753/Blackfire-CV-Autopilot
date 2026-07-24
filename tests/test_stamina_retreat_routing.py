import os
import sys
import time
import unittest
from unittest.mock import MagicMock

# 將專案根目錄加入 Python 搜尋路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.state_machine import GameStateMachine
from states.handlers.bread_collection import BreadCollectionHandler
from states.handlers.lobby import LobbyHandler
from states.handlers.result import ResultHandler
from states.handlers.explore import ExploreHandler
from config import GAME_CONFIGS

class TestStaminaRetreatRouting(unittest.TestCase):
    def setUp(self):
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(mock_capturer, mock_matcher, mock_mouse)
        self.state_machine.config = GAME_CONFIGS["stage"].copy()

    # ------------------------------------------------------------------
    # 1. BreadCollectionHandler 測試
    # ------------------------------------------------------------------
    def test_bread_collection_exit_in_retreat_mode(self):
        """測試：當處於體力退避期間時，領體力完成應返回 STATE_COLLECT_ONLY"""
        handler = BreadCollectionHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BREAD_COLLECTION
        
        self.state_machine.bread_window_opened = True
        self.state_machine.bread_collected_this_run = True
        
        # Mock match 對所有按鈕回傳 None (代表退出按鈕已消失)
        self.state_machine.matcher.match.return_value = (None, 0.0)
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    def test_bread_collection_exit_in_normal_mode(self):
        """測試：當處於正常期間時，領體力完成應返回 STATE_NAVIGATING"""
        handler = BreadCollectionHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BREAD_COLLECTION
        
        self.state_machine.bread_window_opened = True
        self.state_machine.bread_collected_this_run = True
        
        self.state_machine.matcher.match.return_value = (None, 0.0)
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    # ------------------------------------------------------------------
    # 2. LobbyHandler 測試
    # ------------------------------------------------------------------
    def test_lobby_routing_in_retreat_mode(self):
        """測試：當處於體力退避期間時，大廳無按鈕或領取完畢應返回 STATE_COLLECT_ONLY"""
        handler = LobbyHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        self.state_machine.matcher.match.return_value = (None, 0.0)
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    def test_lobby_routing_in_normal_mode(self):
        """測試：當處於正常期間時，大廳無戰鬥按鈕退回尋路應轉移至 STATE_NAVIGATING"""
        handler = LobbyHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        self.state_machine.matcher.match.return_value = (None, 0.0)
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    # ------------------------------------------------------------------
    # 3. ResultHandler 測試
    # ------------------------------------------------------------------
    def test_result_exit_in_retreat_mode(self):
        """測試：當處於體力退避期間時，結算完成應轉移至 STATE_COLLECT_ONLY"""
        handler = ResultHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        
        # 模擬已經在結算畫面並準備點擊 exit_battle.png 退出戰鬥
        self.state_machine.result_detected_feature = "exit_battle.png"
        
        def mock_match(img, name, *args, **kwargs):
            if name == "exit_battle.png":
                return ((100, 100), 0.95)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    def test_result_exit_in_normal_mode(self):
        """測試：當處於正常期間時，結算完成應轉移至 STATE_NAVIGATING"""
        handler = ResultHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.need_diamond_collection = True
        self.state_machine.result_detected_feature = "exit_battle.png"
        
        def mock_match(img, name, *args, **kwargs):
            if name == "exit_battle.png":
                return ((100, 100), 0.95)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    # ------------------------------------------------------------------
    # 4. ExploreHandler 測試
    # ------------------------------------------------------------------
    def test_explore_exit_in_retreat_mode(self):
        """測試：當處於體力退避期間時，探索退出應轉移至 STATE_COLLECT_ONLY"""
        handler = ExploreHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.config["explore_priorities"] = []
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        handler.no_explore_match_count = 5  # 達到 6 次無匹配觸發 fallback
        
        def mock_match(img, name, threshold=0.8):
            if name == "goback_town.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    def test_explore_exit_in_normal_mode(self):
        """測試：當處於正常期間時，探索退出應轉移至 STATE_NAVIGATING"""
        handler = ExploreHandler(self.state_machine)
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.config["explore_priorities"] = []
        self.state_machine.current_state = self.state_machine.STATE_DUNGEON_EXPLORING
        handler.no_explore_match_count = 5
        
        def mock_match(img, name, threshold=0.8):
            if name == "goback_town.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    # ------------------------------------------------------------------
    # 5. state_machine 全域掃描測試
    # ------------------------------------------------------------------
    def test_detect_state_routing_in_retreat_mode(self):
        """測試：當處於體力退避期間時，全域掃描辨識到城鎮圖標應返回 STATE_COLLECT_ONLY"""
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.config = GAME_CONFIGS["collect_only"].copy()
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        def mock_match(img, name, threshold=0.8):
            if name == "common/door.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    def test_detect_state_routing_in_normal_mode(self):
        """測試：當處於正常期間時，全域掃描辨識到城鎮圖標應返回 STATE_NAVIGATING"""
        self.state_machine.stamina_retreat_start_time = None
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        
        def mock_match(img, name, threshold=0.8):
            if name == "common/door.png":
                return ((100, 100), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

if __name__ == "__main__":
    unittest.main()
