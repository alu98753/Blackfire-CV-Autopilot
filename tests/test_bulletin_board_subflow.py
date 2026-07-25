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
    def test_bulletin_board_phase1_flow(self, mock_exists):
        """
        測試懸賞告示牌 (bulletin_board) 第一階段流程：
        1. 城鎮中 (door.png, bulletin_board.png) ➔ 於螢幕左上 1/4 區域精確匹配並點擊告示牌
        2. 進入告示牌畫面 ➔ 匹配並點擊 reset.png
        3. 完成階段 ➔ 記錄 DailyManager bulletin_board 已完成並消費佇列
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        self.state_machine.need_bulletin_board = True
        self.state_machine.town_subflow_queue = []

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()

        # Step 1: 城鎮點擊告示牌 (對左上 1/4 區域匹配)
        def fake_match_step1(img, name, **kw):
            if name == "common/door.png":
                return ((100, 200), 0.9)
            elif name == "town_building/bulletin_board/bulletin_board.png":
                return ((150, 150), 0.88)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(150, 150)
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

        # Step 2: 點擊 reset.png 重置按鈕
        handler.last_action_time = 0.0
        def fake_match_step2(img, name, **kw):
            if name == "town_building/bulletin_board/reset.png":
                return ((300, 300), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(300, 300)
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        # Step 3: 進入 ALL_DONE_EXITING ➔ 紀錄 DailyManager 完成並切換佇列
        handler.last_action_time = 0.0
        handler.handle()
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("bulletin_board")

if __name__ == "__main__":
    unittest.main()
