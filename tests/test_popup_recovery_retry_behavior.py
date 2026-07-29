import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.exceptions.handler import UnexpectedPopupRecoveryHandler
from states.exceptions.watchdog import ExceptionWatchdog
from states.handlers.battle import BattleHandler


class TestPopupRecoveryRetryBehavior(unittest.TestCase):
    """
    驗證 1st Watchdog 逾時不殺進程、PopupRecovery 重試失敗回復原狀態，
    以及 BattleHandler 在戰鬥中呼叫 notify_ui_progress 之單元測試。
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.machine.config = {"name": "測試模式", "type": "dungeon"}
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("states.exceptions.subflows.GameRelaunchSubflow.execute")
    def test_1_first_watchdog_timeout_popup_recovery_max_retries_restores_state(self, mock_relaunch):
        """
        測試 1：第 1 次 Watchdog 逾時進入 POPUP_RECOVERY，連續 5 次未偵測到彈窗時，
        應發起 restore_stashed_state() 恢復原狀態，絕不直接發起 GameRelaunchSubflow 殺進程。
        """
        self.machine.current_state = self.machine.STATE_BATTLE
        self.machine.stash_current_state(reason="test_timeout")
        self.machine.current_state = self.machine.STATE_POPUP_RECOVERY
        self.machine.exception_watchdog.consecutive_stuck_count = 1

        handler = UnexpectedPopupRecoveryHandler(self.machine)
        handler.subflows_map = {}  # 模擬無相符彈窗 Subflow

        with patch("states.exceptions.handler.GenericAntiStuckSubflow.can_handle", return_value=False):
            for _ in range(4):
                handler.handle(self.fake_img, self.rect)
                mock_relaunch.assert_not_called()
                self.assertEqual(self.machine.current_state, self.machine.STATE_POPUP_RECOVERY)

            # 第 5 次嘗試（達到 max_retries=5）
            handler.handle(self.fake_img, self.rect)
            # 斷言：絕不呼叫 GameRelaunchSubflow
            mock_relaunch.assert_not_called()
            # 斷言：應回復原暫存狀態 STATE_BATTLE
            self.assertEqual(self.machine.current_state, self.machine.STATE_BATTLE)

    @patch("os.path.exists", return_value=True)
    def test_2_battle_handler_notifies_ui_progress_when_auto_visible(self, mock_exists):
        """
        測試 2：BattleHandler 偵測到 auto.png 等戰鬥進行中特徵時，應主動呼叫 notify_ui_progress() 重置 Watchdog 計時器。
        """
        handler = BattleHandler(self.machine)
        self.machine.current_state = self.machine.STATE_BATTLE
        self.machine.last_state_change = time.time() - 50.0

        # 模擬比對 auto.png 成功
        self.mock_matcher.match.side_effect = lambda img, tpl, threshold=0.7, quiet=True: ((100, 100), 0.95) if tpl == "common/auto.png" else (None, 0.0)

        with patch.object(self.machine, "notify_ui_progress") as mock_notify:
            handler.handle(self.fake_img, self.rect)
            mock_notify.assert_called()


if __name__ == "__main__":
    unittest.main()
