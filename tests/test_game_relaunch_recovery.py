import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.exceptions.handler import UnexpectedPopupRecoveryHandler
from states.exceptions.watchdog import ExceptionWatchdog
from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow


class TestGameRelaunchRecovery(unittest.TestCase):
    """
    Watchdog 與 UnexpectedPopupRecoveryHandler 重啟自癒機制 (GameRelaunchSubflow) 單元測試套件
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.machine.config = {"mode": "test"}
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

    @patch("subprocess.run")
    @patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready")
    def test_1_game_relaunch_subflow_execution(self, mock_ensure_ready, mock_subprocess_run):
        """
        測試 1：GameRelaunchSubflow.execute() 能否正確發起 taskkill、呼叫 ensure_game_ready、重置暫存與轉移至 LOGIN_FLOW
        """
        mock_ensure_ready.return_value = True
        self.machine.stashed_state = "NAVIGATING"
        self.machine.stashed_context = {"reason": "test"}
        self.machine.exception_watchdog.consecutive_stuck_count = 2

        subflow = GameRelaunchSubflow()
        res = subflow.execute(self.machine, reason="unit_test_trigger")

        self.assertTrue(res)
        # 驗證執行多重 taskkill 強行關閉進程
        self.assertTrue(mock_subprocess_run.called)
        # 驗證呼叫 Launcher
        mock_ensure_ready.assert_called_once()
        # 驗證清空暫存與轉移至 LOGIN_FLOW
        self.assertIsNone(self.machine.stashed_state)
        self.assertEqual(self.machine.stashed_context, {})
        self.assertEqual(self.machine.exception_watchdog.consecutive_stuck_count, 0)
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)

    @patch.object(GameRelaunchSubflow, "execute", return_value=True)
    def test_2_popup_recovery_handler_max_retries_relaunch(self, mock_relaunch_execute):
        """
        測試 2：UnexpectedPopupRecoveryHandler 嘗試 1~4 次不觸發重啟，第 5 次 (max_retries=5) 自動調用 GameRelaunchSubflow
        """
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 模擬無任何 Subflow 匹配，連刷 4 次 (retry_count 累加至 4)
        with patch.object(self.machine.matcher, "match", return_value=(None, 0.0)):
            for i in range(4):
                handler.handle(self.fake_img, rect)
                mock_relaunch_execute.assert_not_called()
                self.assertEqual(handler.retry_count, i + 1)

            # 第 5 次呼叫 (retry_count 滿 5) 應觸發 GameRelaunchSubflow
            handler.handle(self.fake_img, rect)
            mock_relaunch_execute.assert_called_once()
            self.assertEqual(mock_relaunch_execute.call_args[1]["reason"], "popup_recovery_max_retries_exceeded")

    @patch.object(GameRelaunchSubflow, "execute", return_value=True)
    def test_3_watchdog_consecutive_timeout_relaunch(self, mock_relaunch_execute):
        """
        測試 3：Watchdog 第 1 次逾時走輕量救援 (stash_current_state)，連續第 2 次逾時自動觸發 GameRelaunchSubflow
        """
        watchdog = self.machine.exception_watchdog
        self.machine.current_state = self.machine.STATE_NAVIGATING
        # 模擬時間滿 35 秒逾時
        self.machine.last_state_change = 100.0

        with patch("time.time", return_value=135.5), \
             patch.object(self.machine, "stash_current_state") as mock_stash:
            # 第 1 次逾時：發起輕量救援，不發起重啟
            res1 = watchdog.check(self.fake_img)
            self.assertTrue(res1)
            mock_stash.assert_called_once()
            mock_relaunch_execute.assert_not_called()
            self.assertEqual(watchdog.consecutive_stuck_count, 1)

            # 第 2 次連續逾時 (同一狀態 NAVIGATING)：應發起 GameRelaunchSubflow 重啟
            res2 = watchdog.check(self.fake_img)
            self.assertTrue(res2)
            mock_relaunch_execute.assert_called_once()
            self.assertEqual(watchdog.consecutive_stuck_count, 0)
            self.assertIsNone(watchdog.last_stuck_state)

    def test_4_normal_state_transition_resets_consecutive_stuck_count(self):
        """
        測試 4：正常狀態轉移 (transition_to) 自動將 Watchdog consecutive_stuck_count 清空歸零
        """
        watchdog = self.machine.exception_watchdog
        watchdog.consecutive_stuck_count = 1
        watchdog.last_stuck_state = "NAVIGATING"

        self.machine.transition_to(self.machine.STATE_LOBBY)

        self.assertEqual(watchdog.consecutive_stuck_count, 0)
        self.assertIsNone(watchdog.last_stuck_state)

    @patch("subprocess.run")
    @patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready", return_value=True)
    def test_5_script_pid_exemption_guard(self, mock_ensure_ready, mock_subprocess_run):
        """
        測試 5：驗證當 HWND 恰好返回與當前腳本相同的 PID 時，護欄觸發不進行 PID kill，且絕對不使用 WINDOWTITLE 萬用字元指令
        """
        script_pid = os.getpid()
        subflow = GameRelaunchSubflow()

        with patch("win32gui.FindWindow", return_value=99999), \
             patch("win32process.GetWindowThreadProcessId", return_value=(0, script_pid)):
            subflow.execute(self.machine, reason="pid_guard_test")

            # 斷言：沒有發起 taskkill /f /pid <script_pid>
            for call_item in mock_subprocess_run.call_args_list:
                cmd_str = call_item[0][0]
                self.assertNotIn(f"taskkill /f /pid {script_pid}", cmd_str)
                self.assertNotIn("WINDOWTITLE", cmd_str)


if __name__ == "__main__":
    unittest.main()
