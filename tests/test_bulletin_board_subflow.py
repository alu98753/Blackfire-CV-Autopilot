import unittest
from unittest.mock import MagicMock, patch
import time
from states.handlers.bulletin_board import BulletinBoardHandler
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestBulletinBoardSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_daily_manager = MagicMock()

        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.mock_capturer.capture.return_value = MagicMock()

        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )
        self.state_machine.daily_manager = self.mock_daily_manager

    @patch('os.path.exists')
    def test_bulletin_board_reset_and_quit_flow(self, mock_exists):
        """
        測試懸賞告示牌流程（有重置按鈕時）：
        1. 城鎮點擊告示牌 ➔ 轉移至 WAIT_BOARD_OPEN
        2. 等待看到 common/quit.png ➔ 轉移至 CHECK_RESET
        3. 發現 reset.png ➔ 點擊重置 ➔ 轉移至 EXIT_BOARD
        4. 點擊 common/quit.png ➔ 轉移至 ALL_DONE_EXITING
        5. 完成離場 ➔ 寫入 DailyManager 並切換佇列
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        self.state_machine.need_bulletin_board = True
        self.state_machine.town_subflow_queue = []

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()

        # Step 1: 城鎮中點擊告示牌 (對左上 1/4 區域匹配)
        def fake_match_step1(img, name, **kw):
            if name == "common/door.png":
                return ((100, 200), 0.9)
            elif name == "town_building/bulletin_board/bulletin_board.png":
                return ((150, 150), 0.88)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(150, 150)
        self.assertEqual(handler.step_phase, "WAIT_BOARD_OPEN")

        # Step 2: 等待看到 quit.png，確認進入告示牌介面
        handler.last_action_time = 0.0
        def fake_match_step2(img, name, **kw):
            if name == "common/quit.png":
                return ((700, 100), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.assertEqual(handler.step_phase, "CHECK_RESET")

        # Step 3: 點擊 reset.png 重置按鈕
        handler.last_action_time = 0.0
        def fake_match_step3(img, name, **kw):
            if name == "town_building/bulletin_board/reset.png":
                return ((300, 300), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step3
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(300, 300)
        self.assertEqual(handler.step_phase, "EXIT_BOARD")

        # Step 4: 點擊 quit.png 退出告示牌
        handler.last_action_time = 0.0
        def fake_match_step4(img, name, **kw):
            if name == "common/quit.png":
                return ((700, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step4
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(700, 100)
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        # Step 5: 完成離場寫入 DailyManager
        handler.last_action_time = 0.0
        handler.handle()
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("bulletin_board")

    @patch('os.path.exists')
    def test_bulletin_board_no_reset_skip_flow(self, mock_exists):
        """
        測試懸賞告示牌流程（無重置按鈕時自動跳過重置步驟）：
        1. 已看見 common/quit.png ➔ 進入 CHECK_RESET
        2. 未發現 reset.png ➔ 自動跳過 ➔ 轉移至 EXIT_BOARD
        3. 點擊 common/quit.png 離場 ➔ 轉移至 ALL_DONE_EXITING
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        self.state_machine.need_bulletin_board = True
        self.state_machine.town_subflow_queue = []

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.step_phase = "CHECK_RESET"
        handler.last_action_time = 0.0

        # 無 reset.png 只有 quit.png
        def fake_match_no_reset(img, name, **kw):
            if name == "common/quit.png":
                return ((700, 100), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_no_reset
        handler.handle()
        self.assertEqual(handler.step_phase, "EXIT_BOARD")

        # 點擊 quit.png 退出
        handler.last_action_time = 0.0
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(700, 100)
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

if __name__ == "__main__":
    unittest.main()
