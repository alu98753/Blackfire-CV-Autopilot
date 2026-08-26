import unittest
from unittest.mock import MagicMock, patch
import time

from states.state_machine import GameStateMachine
from utils.keyboard_listener import PauseController

class TestBehaviorPauseResume(unittest.TestCase):
    """
    測試空白鍵暫停/繼續控制、相鄰節奏間隔、背景執行緒與內部計時器補償行為
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

    def test_cadence_interval_success(self):
        """
        測試相鄰節奏間隔小於 1.5 秒時，敲滿 3 次必定成功觸發 (即使總耗時超過 1.2 秒)
        """
        controller = PauseController(capturer=self.mock_capturer, required_taps=3, cadence_timeout_sec=1.5, start_thread=False)

        # 第 1 下 (T = 100.0)
        res1 = controller._on_tap_detected(100.0)
        self.assertFalse(res1)
        self.assertEqual(controller.tap_count, 1)

        # 第 2 下 (T = 100.8，相鄰間隔 0.8s <= 1.5s)
        res2 = controller._on_tap_detected(100.8)
        self.assertFalse(res2)
        self.assertEqual(controller.tap_count, 2)

        # 第 3 下 (T = 101.6，相鄰間隔 0.8s <= 1.5s，總耗時 1.6s)
        res3 = controller._on_tap_detected(101.6)
        self.assertTrue(res3)
        self.assertEqual(controller.tap_count, 0)
        self.assertTrue(controller.check_toggle_triggered())

    def test_cadence_interval_timeout_reset(self):
        """
        測試相鄰節奏間隔超過 1.5 秒時，自動重置計數為第 1 下
        """
        controller = PauseController(capturer=self.mock_capturer, required_taps=3, cadence_timeout_sec=1.5, start_thread=False)

        # 第 1 下 (T = 100.0)
        controller._on_tap_detected(100.0)
        self.assertEqual(controller.tap_count, 1)

        # 超時停頓 1.8 秒後才按第 2 下 (T = 101.8 > 100.0 + 1.5)
        res = controller._on_tap_detected(101.8)
        self.assertFalse(res)
        # 計數應被自動重置為 1 (重新開始第一下)
        self.assertEqual(controller.tap_count, 1)

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetAsyncKeyState")
    def test_background_thread_captures_during_main_thread_blocking(self, mock_get_async_key, mock_get_console, mock_get_fg):
        """
        測試當主執行緒被耗時任務 (如 OCR/子流程) 阻塞時，背景執行緒仍能 100% 捕獲 3 次按鍵
        """
        mock_get_console.return_value = 11111
        mock_get_fg.return_value = 11111
        mock_get_async_key.return_value = 0x0

        # 啟動背景執行緒 (debounce 設為極小)
        controller = PauseController(capturer=self.mock_capturer, required_taps=3, cadence_timeout_sec=1.5, debounce_sec=0.01, start_thread=True)

        try:
            # 模擬使用者在背景敲擊 3 次 (間隔 0.05s)
            for _ in range(3):
                mock_get_async_key.return_value = 0x8000 # 按下
                time.sleep(0.03)
                mock_get_async_key.return_value = 0x0    # 釋放
                time.sleep(0.03)

            # 模擬主執行緒執行耗時任務後回到頂部檢查
            time.sleep(0.05)
            self.assertTrue(controller.check_toggle_triggered())
            # 再次檢查應已被消費
            self.assertFalse(controller.check_toggle_triggered())
        finally:
            controller.stop()

    @patch("ctypes.windll.user32.GetForegroundWindow")
    @patch("ctypes.windll.kernel32.GetConsoleWindow")
    @patch("ctypes.windll.user32.GetAsyncKeyState")
    def test_focus_window_filter(self, mock_get_async_key, mock_get_console, mock_get_fg):
        """
        測試視窗焦點過濾：前景視窗為第三方視窗時被 100% 過濾
        """
        mock_get_console.return_value = 11111
        mock_get_fg.return_value = 99999 # 瀏覽器等非目標視窗
        mock_get_async_key.return_value = 0x8000

        controller = PauseController(capturer=self.mock_capturer, start_thread=False)
        controller._poll_once()

        self.assertEqual(controller.tap_count, 0)
        self.assertFalse(controller.check_toggle_triggered())

if __name__ == "__main__":
    unittest.main()
