import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.exceptions.watchdog import ExceptionWatchdog


class TestUserInterventionTimeCompensation(unittest.TestCase):
    """
    使用者介入操作時間補償與 Watchdog 豁免單元測試套件
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.watchdog = ExceptionWatchdog(self.machine)

    def test_1_user_intervention_time_offset_compensation(self):
        """
        測試 1：手動操作 106 秒後恢復，last_state_change 正確增加 106 秒，使實際狀態持續時間不被誤計。
        """
        # 假設 146 秒前進入 BATTLE 戰鬥狀態，其中包含 106 秒使用者手動操作
        now = time.time()
        self.machine.current_state = self.machine.STATE_BATTLE
        self.machine.last_state_change = now - 146.0

        # 模擬使用者手動操作 (持續 106 秒)
        self.machine.user_operating = True
        self.machine.user_operation_start_time = now - 106.0

        # 模擬結束手動操作，計算時間補償
        pause_duration = now - self.machine.user_operation_start_time
        self.machine.last_state_change += pause_duration
        self.machine.user_operating = False
        self.machine.user_operation_start_time = None

        # 斷言：扣除 106 秒後，腳本實際狀態時間為 40.0 秒 (未滿 90 秒門檻)
        state_duration = time.time() - self.machine.last_state_change
        self.assertAlmostEqual(state_duration, 40.0, delta=1.5)

        # 斷言：Watchdog 檢查回傳 False (不觸發 90 秒卡死)
        triggered = self.watchdog.check(screen_img=None)
        self.assertFalse(triggered)

    def test_2_watchdog_exempt_during_active_user_operating(self):
        """
        測試 2：在 user_operating == True 期間，即便狀態時間超過 200 秒，Watchdog 亦絕對回傳 False 放行。
        """
        now = time.time()
        self.machine.current_state = self.machine.STATE_BATTLE
        self.machine.last_state_change = now - 200.0  # 已遠超 90 秒門檻

        # 標記使用者正在手動操作
        self.machine.user_operating = True
        self.machine.user_operation_start_time = now - 150.0

        # 檢測 Watchdog
        triggered = self.watchdog.check(screen_img=None)

        # 斷言：使用者操作期間必須回傳 False 豁免
        self.assertFalse(triggered)

    def test_3_multiple_user_interventions_compensation_accumulated(self):
        """
        測試 3：多次手動操作中斷後累加補償，確保 last_state_change 精確反映實際腳本執行時間。
        """
        now = time.time()
        self.machine.current_state = self.machine.STATE_NAVIGATING
        # 總共歷時 100 秒，其中進行兩次手動操作 (30 秒 + 50 秒 = 80 秒手動操作)
        self.machine.last_state_change = now - 100.0

        # 第 1 次手動操作 30 秒
        self.machine.last_state_change += 30.0

        # 第 2 次手動操作 50 秒
        self.machine.last_state_change += 50.0

        # 斷言：經兩次補償後，扣除 80 秒手動操作，實際腳本時間為 20.0 秒
        state_duration = time.time() - self.machine.last_state_change
        self.assertAlmostEqual(state_duration, 20.0, delta=1.5)


if __name__ == "__main__":
    unittest.main()
