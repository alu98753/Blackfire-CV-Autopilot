import unittest
import time
import os
from unittest.mock import MagicMock, patch
import numpy as np

from states.state_machine import GameStateMachine
from states.login_flow import handle_global_login, _wait_for_town


class TestBehaviorLoginFlow(unittest.TestCase):
    """
    登入流程與超時重開處置單元測試套件
    """

    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("states.exceptions.subflows.game_relaunch.GameRelaunchSubflow")
    @patch("states.login_flow.GameRelaunchSubflow")
    @patch("os.path.exists", return_value=True)
    @patch("time.sleep")
    def test_login_timeout_triggers_relaunch(self, mock_sleep, mock_exists, mock_relaunch1, mock_relaunch2):
        """
        [測試 1] 驗證當點擊登入後，連續 35 秒未能進入城鎮 (door.png 未出現)，
        _wait_for_town 必須拒絕假性登入成功，直接呼叫 GameRelaunchSubflow 殺進程重開！
        """
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.capturer.get_window_rect.return_value = self.rect
        self.capturer.capture.return_value = dummy_img

        # 模擬 match 永遠無法匹配到任何城鎮或彈窗特徵
        self.matcher.match.return_value = (None, 0.0)

        # 模擬 time.time()：每次調用自動前進 10 秒，第二次迴圈時時間即可自然達到 40 秒並超過 35 秒門檻
        t_state = [1000.0]

        def mock_time():
            t_state[0] += 10.0
            return t_state[0]

        with patch("time.time", side_effect=mock_time):
            res = _wait_for_town(self.machine, self.rect)

        # 斷言：_wait_for_town 應傳回 False (拒絕假成功)
        self.assertFalse(res)

        # 斷言：GameRelaunchSubflow 實例之 execute 必須被精確呼叫一次
        mock_execute = mock_relaunch1.return_value.execute
        mock_execute.assert_called_once()
        self.assertEqual(mock_execute.call_args[1]["reason"], "login_timeout_failed")

    @patch("states.login_flow._wait_for_town", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_handle_global_login_success_resets_stuck_count(self, mock_exists, mock_wait_town):
        """
        [測試 2] 驗證當成功偵測到 login.png 且 _wait_for_town 回傳 True 時，
        handle_global_login 回傳 True 並重置 consecutive_stuck_count。
        """
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.machine.consecutive_stuck_count = 3
        self.matcher.match.return_value = ((500, 500), 0.90)

        res = handle_global_login(self.machine, dummy_img, self.rect)

        self.assertTrue(res)
        self.assertEqual(self.machine.consecutive_stuck_count, 0)
        mock_wait_town.assert_called_once()


if __name__ == "__main__":
    unittest.main()
