import unittest
import time
import os
import json
from unittest.mock import MagicMock, patch
import numpy as np

from states.state_machine import GameStateMachine
from states.exceptions import ExceptionWatchdog
from config import get_exception_features_config, get_critical_exception_templates



class TestBehaviorGlobalWatchdog(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)
        self.watchdog = self.machine.exception_watchdog

    def test_non_battle_stuck_30s_timeout_triggers_stash(self):
        """驗證非戰鬥狀態 (LOBBY) 持續卡住達 30 秒觸發 ExceptionWatchdog 暫存與復原"""
        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.last_state_change = time.time() - 31.0  # 模擬已卡住 31 秒

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        res = self.watchdog.check(dummy_img)

        self.assertTrue(res)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
        self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_LOBBY)

    def test_battle_stuck_90s_timeout_triggers_stash(self):
        """驗證戰鬥狀態 (BATTLE) 未滿 90 秒不觸發，滿 90 秒觸發 ExceptionWatchdog"""
        self.machine.current_state = GameStateMachine.STATE_BATTLE
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        # 80 秒未滿門檻
        self.machine.last_state_change = time.time() - 80.0
        res_80s = self.watchdog.check(dummy_img)
        self.assertFalse(res_80s)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_BATTLE)

        # 91 秒已滿門檻 (1.5 分鐘)
        self.machine.last_state_change = time.time() - 91.0
        res_91s = self.watchdog.check(dummy_img)
        self.assertTrue(res_91s)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
        self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_BATTLE)

    def test_mismatch_critical_template_and_dimming_scan(self):
        """驗證 30 秒低頻率特徵與遮罩衝突攔截 (Mismatch Interceptor)"""
        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.last_state_change = time.time()
        self.watchdog.last_mismatch_check_time = 0.0  # 觸發低頻檢查

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        # 模擬 matcher 命中 exceptions/Raid_Box.png
        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "Raid_Box" in template_name:
                return (100, 100), 0.90
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            res = self.watchdog.check(dummy_img)
            self.assertTrue(res)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
            self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_NAVIGATING)

    def test_hot_reload_and_dynamic_directory_discovery(self):
        """驗證 config/exception_features.json 熱重載與 templates/exceptions/ 動態目錄發現"""
        critical_tpls = get_critical_exception_templates()
        self.assertIn("exceptions/Raid_Box.png", critical_tpls)


if __name__ == "__main__":
    unittest.main()
