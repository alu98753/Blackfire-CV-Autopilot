import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.exceptions.watchdog import ExceptionWatchdog
from states.state_machine import GameStateMachine

class TestWatchdogCollectOnlyExemption(unittest.TestCase):
    def setUp(self):
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)
        self.watchdog = ExceptionWatchdog(self.state_machine)

    def test_watchdog_exempts_collect_only_state(self):
        """
        [COLLECT_ONLY 待機豁免斷言] 驗證當狀態為 STATE_COLLECT_ONLY 時，
        在動態 CD 逾時門檻內 (如 7200 秒 CD + 60 秒緩衝)，Watchdog.check() 恆回傳 False。
        """
        self.state_machine.config = {"diamond_cd": 7200.0, "bread_cd": 7200.0}
        self.state_machine.current_state = self.state_machine.STATE_COLLECT_ONLY
        self.state_machine.last_state_change = time.time() - 3600.0

        triggered = self.watchdog.check(screen_img=None)
        self.assertFalse(triggered)
        self.assertIsNone(self.state_machine.stashed_state)

    def test_watchdog_active_during_bread_and_diamond_collection(self):
        """
        [子流程狀態恢復 30s 監視斷言] 驗證當轉移至 STATE_BREAD_COLLECTION 或 STATE_DIAMOND_COLLECTION 時，
        若停留超過 30s 逾時，Watchdog 恢復監控並回傳 True 發起救援。
        """
        for st in [self.state_machine.STATE_BREAD_COLLECTION, self.state_machine.STATE_DIAMOND_COLLECTION]:
            self.state_machine.current_state = st
            self.state_machine.last_state_change = time.time() - 35.0

            mock_handler = MagicMock()
            mock_handler.subflows_map = {}
            self.state_machine.handlers[self.state_machine.STATE_POPUP_RECOVERY] = mock_handler

            with patch('states.exceptions.watchdog.safe_match', return_value=(None, 0.0)):
                triggered = self.watchdog.check(screen_img=None)

            self.assertTrue(triggered)
            self.assertEqual(self.state_machine.stashed_state, st)

            # 重置測試狀態
            self.state_machine.stashed_state = None

    def test_watchdog_active_during_navigation_and_battle(self):
        """
        [冷卻 Resume 狀態恢復 30s/90s 監視斷言] 驗證 Resume 切回 NAVIGATING (>30s) 或 BATTLE (>90s) 時，
        Watchdog 恢復嚴格逾時監控並回傳 True 發起救援。
        """
        # 1. NAVIGATING > 90s
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.last_state_change = time.time() - 95.0

        mock_handler = MagicMock()
        mock_handler.subflows_map = {}
        self.state_machine.handlers[self.state_machine.STATE_POPUP_RECOVERY] = mock_handler

        with patch('states.exceptions.watchdog.safe_match', return_value=(None, 0.0)):
            triggered_nav = self.watchdog.check(screen_img=None)

        self.assertTrue(triggered_nav)
        self.assertEqual(self.state_machine.stashed_state, self.state_machine.STATE_NAVIGATING)

        # 2. BATTLE > 90s
        self.state_machine.stashed_state = None
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.last_state_change = time.time() - 95.0

        with patch('states.exceptions.watchdog.safe_match', return_value=(None, 0.0)):
            triggered_battle = self.watchdog.check(screen_img=None)

        self.assertTrue(triggered_battle)
        self.assertEqual(self.state_machine.stashed_state, self.state_machine.STATE_BATTLE)

if __name__ == '__main__':
    unittest.main()
