import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import StateMachineLogicTestCase


class TestStateTransitionStateMachine(StateMachineLogicTestCase):

    def test_blood_altar_mode_initialization(self):
        """
        測試血之祭壇模式初始化與配置結構。
        """
        from config import GAME_CONFIGS
        cfg = GAME_CONFIGS["blood_altar"].copy()
        self.assertEqual(cfg["type"], "blood_altar")
        self.assertIn("sacrifice_settings", cfg)
        for key in ["gray", "green", "blue", "purple"]:
            self.assertIn(key, cfg["sacrifice_settings"])

    @patch('os.path.exists')
    def test_detect_state_jewelry_workshop_mode_forces_jewelry_workshop_state(self, mock_exists):
        """
        測試當模式為 jewelry_workshop 且在城鎮大門 (common/door.png 可見) 時：
        detect_current_state() 會正確轉移至 STATE_JEWELRY_WORKSHOP 狀態，不會誤入 NAVIGATING 或 LOBBY！
        """
        from config import GAME_CONFIGS
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["jewelry_workshop"].copy()
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN
        self.state_machine.need_diamond_collection = True

        def mock_match(img, name, **kw):
            if name in ["common/door.png", "town_building/Jewelry_workshop/Jewelry_workshop.png"]:
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        self.state_machine.need_jewelry_workshop = True
        self.state_machine.detect_current_state(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_JEWELRY_WORKSHOP)

    @patch('os.path.exists')
    def test_detect_state_blood_altar_mode_forces_blood_altar_state(self, mock_exists):
        """
        測試當需要血之祭壇且在城鎮大門時：
        detect_current_state() 會正確轉移至 STATE_BLOOD_ALTAR 狀態！
        """
        from config import GAME_CONFIGS
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.need_blood_altar = True
        self.state_machine.current_state = self.state_machine.STATE_UNKNOWN

        def mock_match(img, name, **kw):
            if name in ["common/door.png", "town_building/Blood_Altar/Blood_Altar.png"]:
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match
        import numpy as np
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = self.mock_capturer.get_window_rect()

        self.state_machine.detect_current_state(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BLOOD_ALTAR)

    @patch('os.path.exists')
    @patch('states.handlers.battle.time.sleep')
    def test_battle_handler_result_button_threshold(self, mock_sleep, mock_exists):
        """
        測試 BattleHandler 結算按鈕門檻為 0.80：
        - 若圖案殘影相似度為 0.7694 (< 0.80)，has_battle_feature 為 False，滿 5 秒觸發重設為 STATE_UNKNOWN。
        - 若圖案相似度為 0.85 (>= 0.80)，觸發點擊並跳轉至 STATE_RESULT。
        """
        from config import GAME_CONFIGS
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.battle_start_time = time.time() - 10.0 # 避開前 8 秒保護期

        handler = self.state_machine.handlers[self.state_machine.STATE_BATTLE]
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        # 1. 情境 A：結算圖案相似度為 0.7694 (< 0.80) 且無其他戰鬥特徵
        def mock_match_low(img, name, threshold=0.8, **kw):
            conf = 0.7694 if name in ["common/continue.png", "stages/retry.png"] else 0.0
            return ((100, 100), conf) if conf >= threshold else (None, conf)

        self.mock_matcher.match.side_effect = mock_match_low
        handler.non_battle_feature_start_time = time.time() - 5.1 # 已滿 5.1 秒未偵測到合格特徵

        handler.handle(fake_img, rect)
        # 應成功判定意外退出並轉移至 UNKNOWN
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

        # 2. 情境 B：真實結算圖案相似度為 0.85 (>= 0.80)
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        handler.non_battle_feature_start_time = None
        def mock_match_high(img, name, threshold=0.8, **kw):
            conf = 0.85 if name == "common/continue.png" else 0.0
            return ((100, 100), conf) if conf >= threshold else (None, conf)

        self.mock_matcher.match.side_effect = mock_match_high
        handler.handle(fake_img, rect)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_RESULT)


if __name__ == "__main__":
    unittest.main()
