import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine


class BehavioralScenarioTestCase(unittest.TestCase):
    def setUp(self):
        # 建立主依賴 Mock 物件
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_mouse.last_action_time = 0.0
        
        # 解決 Mock match 被傳入 check_brightness 或 brightness_threshold 參數時的不相容問題，自動過濾 kwargs
        orig_call = self.mock_matcher.match._mock_call
        def patched_mock_call(*args, **kwargs):
            kwargs.pop('check_brightness', None)
            kwargs.pop('brightness_threshold', None)
            kwargs.pop('quiet', None)
            return orig_call(*args, **kwargs)
        self.mock_matcher.match._mock_call = patched_mock_call
        
        # 預設視窗座標與大小 (1920x1080)
        self.mock_capturer.get_window_rect.return_value = {
            "left": 0, "top": 0, "width": 1920, "height": 1080
        }
        
        # 實例化待測狀態機 (System Under Test)
        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )
        mock_dm = MagicMock()
        mock_dm.is_subflow_completed.return_value = False
        mock_dm.check_and_reset_daily.return_value = False
        self.state_machine.daily_manager = mock_dm

        
        # 初始化定時器變數以隔離實際時間干擾
        self.state_machine.need_diamond_collection = False
        self.state_machine.need_bread_collection = False
        self.state_machine.last_diamond_collection_time = time.time()
        self.state_machine.last_bread_collection_time = time.time()


class StateMachineLogicTestCase(unittest.TestCase):
    def setUp(self):
        # 建立 Mock 物件
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        
        # 解決 Mock match 被傳入 check_brightness 或 brightness_threshold 參數時的不相容問題，自動過濾 kwargs
        orig_call = self.mock_matcher.match._mock_call
        def patched_mock_call(*args, **kwargs):
            kwargs.pop('check_brightness', None)
            kwargs.pop('brightness_threshold', None)
            kwargs.pop('quiet', None)
            return orig_call(*args, **kwargs)
        self.mock_matcher.match._mock_call = patched_mock_call
        
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


class TaskCompletePhaseTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        from states.state_machine import GameStateMachine
        self.state_machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.rect = {"left": 10, "top": 20, "width": 800, "height": 600}

