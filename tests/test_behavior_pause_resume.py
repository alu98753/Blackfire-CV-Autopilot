import unittest
from unittest.mock import MagicMock, patch
import time

from states.state_machine import GameStateMachine
from utils.keyboard_listener import PauseController

class TestBehaviorPauseResume(unittest.TestCase):
    """
    測試空白鍵暫停/繼續控制與內部計時器補償行為
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_capturer.hwnd = 12345
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)

    def test_pause_resume_lifecycle(self):
        """
        測試基本 pause / resume / toggle_pause 狀態機生命週期
        """
        self.assertFalse(self.state_machine.is_paused)
        self.assertIsNone(self.state_machine.pause_start_time)

        # 1. 觸發暫停
        self.state_machine.pause()
        self.assertTrue(self.state_machine.is_paused)
        self.assertIsNotNone(self.state_machine.pause_start_time)

        # 2. 觸發恢復
        duration = self.state_machine.resume()
        self.assertFalse(self.state_machine.is_paused)
        self.assertIsNone(self.state_machine.pause_start_time)
        self.assertTrue(self.state_machine.just_resumed_from_user)
        self.assertGreaterEqual(duration, 0.0)

        # 3. 測試 toggle_pause
        is_paused = self.state_machine.toggle_pause()
        self.assertTrue(is_paused)
        self.assertTrue(self.state_machine.is_paused)

        is_paused = self.state_machine.toggle_pause()
        self.assertFalse(is_paused)
        self.assertFalse(self.state_machine.is_paused)

    def test_internal_timers_compensation_math(self):
        """
        測試內部安全/防卡死計時器的精確數學補償
        """
        self.state_machine.last_state_change = 1000.0
        self.state_machine.battle_start_time = 900.0
        self.state_machine.stashed_context = {"timestamp": 950.0}
        self.state_machine.missing_time_common_door = 800.0

        loading_handler = self.state_machine.handlers.get(self.state_machine.STATE_LOADING)
        if loading_handler:
            loading_handler.loading_start_time = 700.0

        battle_handler = self.state_machine.handlers.get(self.state_machine.STATE_BATTLE)
        if battle_handler:
            battle_handler.non_battle_feature_start_time = 850.0

        # 執行 120 秒補償
        self.state_machine.compensate_internal_timers(120.0)

        self.assertEqual(self.state_machine.last_state_change, 1120.0)
        self.assertEqual(self.state_machine.battle_start_time, 1020.0)
        self.assertEqual(self.state_machine.stashed_context["timestamp"], 1070.0)
        self.assertEqual(self.state_machine.missing_time_common_door, 920.0)

        if loading_handler:
            self.assertEqual(loading_handler.loading_start_time, 820.0)
        if battle_handler:
            self.assertEqual(battle_handler.non_battle_feature_start_time, 970.0)

        self.assertFalse(self.state_machine.user_operating)
        self.assertTrue(self.state_machine.just_resumed_from_user)

    def test_game_cooldowns_not_affected(self):
        """
        【關鍵邊界保護】驗證客觀遊戲數據與冷卻時間絕不被手動暫停補償篡改
        """
        self.state_machine.dungeon_cooldowns = {0: 500.0, 1: 600.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.state_machine.last_bread_collection_time = 700.0
        self.state_machine.last_diamond_collection_time = 800.0

        # 執行 300 秒長暫停補償
        self.state_machine.compensate_internal_timers(300.0)

        # 斷言客觀遊戲冷卻時間完全未受影響
        self.assertEqual(self.state_machine.dungeon_cooldowns[0], 500.0)
        self.assertEqual(self.state_machine.dungeon_cooldowns[1], 600.0)
        self.assertEqual(self.state_machine.last_bread_collection_time, 700.0)
        self.assertEqual(self.state_machine.last_diamond_collection_time, 800.0)

    def test_watchdog_immunity_after_long_pause(self):
        """
        測試暫停超過 90 秒後恢復，Watchdog 絕對不會因停滯誤判為卡死
        """
        now = time.time()
        # 設定為處於 NAVIGATING (長逾時 90s 門檻)，已運行 40s
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.last_state_change = now - 40.0

        # 模擬暫停 120 秒
        self.state_machine.pause()
        self.state_machine.pause_start_time = now - 120.0

        # 恢復
        self.state_machine.resume()

        # 斷言 Watchdog check 不會觸發逾時
        is_stuck = self.state_machine.exception_watchdog.check(None)
        self.assertFalse(is_stuck)

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetAsyncKeyState")
    def test_pause_controller_focus_filtering_and_triple_tap(self, mock_get_async_key, mock_get_console, mock_get_fg):
        """
        測試 PauseController 連按 3 次空白鍵 (Triple-Space) 觸發與視窗焦點過濾機制
        """
        mock_get_console.return_value = 11111 # Console HWND
        controller = PauseController(capturer=self.mock_capturer, required_taps=3, window_sec=0.5, debounce_sec=0.01)

        # 1. 前景視窗為 Console 視窗，第 1 次按 Space -> 尚未滿 3 次，返回 False
        mock_get_fg.return_value = 11111
        mock_get_async_key.return_value = 0x8000
        self.assertFalse(controller.check_toggle_triggered())

        # 釋放按鍵
        time.sleep(0.02)
        mock_get_async_key.return_value = 0x0
        controller.check_toggle_triggered()

        # 第 2 次按 Space -> 尚未滿 3 次，返回 False
        time.sleep(0.02)
        mock_get_async_key.return_value = 0x8000
        self.assertFalse(controller.check_toggle_triggered())

        # 釋放按鍵
        time.sleep(0.02)
        mock_get_async_key.return_value = 0x0
        controller.check_toggle_triggered()

        # 第 3 次按 Space -> 滿 3 次，返回 True
        time.sleep(0.02)
        mock_get_async_key.return_value = 0x8000
        self.assertTrue(controller.check_toggle_triggered())

        # 2. 前景視窗為第三方視窗 (例如瀏覽器 99999)，連敲多次 Space 均被 100% 過濾忽略
        mock_get_async_key.return_value = 0x0
        controller.check_toggle_triggered()
        mock_get_fg.return_value = 99999 # 瀏覽器
        for _ in range(5):
            mock_get_async_key.return_value = 0x8000
            self.assertFalse(controller.check_toggle_triggered())
            mock_get_async_key.return_value = 0x0
            controller.check_toggle_triggered()

if __name__ == "__main__":
    unittest.main()
