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
    def test_bulletin_board_full_accept_and_quit_flow(self, mock_exists):
        """
        測試懸賞告示牌完整流程：
        1. 城鎮點擊告示牌 ➔ WAIT_BOARD_OPEN
        2. 看見 quit.png ➔ CHECK_RESET
        3. 發現 reset.png ➔ 點擊重置 ➔ PROCESS_ACCEPT_QUESTS
        4. FIND_TOP_TASK (發現 task.png 於 X=100, Y=100) ➔ 抓標題 ➔ 點擊任務列 ➔ CLICK_ACCEPT_BTN
        5. CLICK_ACCEPT_BTN ➔ 發現 accept_task.png ➔ 點擊接受 ➔ CLICK_CONFIRM_POPUP
        6. CLICK_CONFIRM_POPUP ➔ 點擊 confirm.png ➔ 返回 FIND_TOP_TASK
        7. 再次 FIND_TOP_TASK (已無 task.png) ➔ 轉移至 EXIT_BOARD
        8. EXIT_BOARD 點擊 quit.png ➔ ALL_DONE_EXITING
        9. ALL_DONE_EXITING 寫入 DailyManager accepted_quests 欄位並切換佇列
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        self.state_machine.need_bulletin_board = True
        self.state_machine.town_subflow_queue = []

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()

        # Step 1: 城鎮中點擊告示牌
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

        # Step 2: 等待看到 quit.png
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
        self.assertEqual(handler.step_phase, "PROCESS_ACCEPT_QUESTS")
        self.assertEqual(handler.accept_sub_phase, "FIND_TOP_TASK")

        # Step 4: 發現 task.png -> 點擊首列任務
        handler.last_action_time = 0.0
        self.mock_matcher.match_all.return_value = [(100, 100, 0.90)]
        self.mock_mouse.click.reset_mock()

        # Mock OCR reader
        mock_ocr = MagicMock()
        mock_ocr._ocr_crop.return_value = "清除野豬"
        handler.ocr_extractor = mock_ocr

        handler.handle()
        self.mock_mouse.click.assert_called_once_with(100, 100)
        self.assertEqual(handler.accept_sub_phase, "CLICK_ACCEPT_BTN")
        self.assertIn("清除野豬", handler.accepted_quest_titles)

        # Step 5: 點擊 accept_task.png
        handler.last_action_time = 0.0
        def fake_match_step5(img, name, **kw):
            if name == "town_building/bulletin_board/accept_task.png":
                return ((600, 500), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step5
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(600, 500)
        self.assertEqual(handler.accept_sub_phase, "CLICK_CONFIRM_POPUP")

        # Step 6: 點擊 confirm.png
        handler.last_action_time = 0.0
        def fake_match_step6(img, name, **kw):
            if name == "common/confirm.png":
                return ((400, 400), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step6
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(400, 400)
        self.assertEqual(handler.accept_sub_phase, "FIND_TOP_TASK")

        # Step 7: 已無 task.png ➔ 轉移至 EXIT_BOARD
        handler.last_action_time = 0.0
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (None, 0.0)
        self.mock_matcher.match_all.return_value = []
        handler.handle()
        self.assertEqual(handler.step_phase, "EXIT_BOARD")

        # Step 8: EXIT_BOARD 點擊 quit.png
        handler.last_action_time = 0.0
        def fake_match_step8(img, name, **kw):
            if name == "common/quit.png":
                return ((700, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step8
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(700, 100)
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        # Step 9: 完成離場寫入 DailyManager
        handler.last_action_time = 0.0
        handler.handle()
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with(
            "bulletin_board", extra_data={"accepted_quests": ["清除野豬"]}
        )

    @patch('os.path.exists')
    def test_bulletin_board_skip_reset_when_no_reset_btn(self, mock_exists):
        """
        邊界測試 1：無 reset.png 時自動跳過重置，直接進入任務接取階段。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()
        handler.step_phase = "CHECK_RESET"

        # 模擬找不到 reset.png
        self.mock_matcher.match.return_value = (None, 0.0)
        handler.handle()
        self.assertEqual(handler.step_phase, "PROCESS_ACCEPT_QUESTS")

    @patch('os.path.exists')
    def test_bulletin_board_lobby_goback_town(self, mock_exists):
        """
        邊界測試 2：若處於大廳畫面 (發現 goback_town.png)，先點擊返回城鎮。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()

        # 模擬大廳畫面 (Goback_town.png 存在)
        def fake_match_goback(img, name, **kw):
            if name == "goback_town.png":
                return ((50, 50), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_goback
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(50, 50)
        # 應維持在 INIT 階段並等待回到城鎮
        self.assertEqual(handler.step_phase, "INIT")

if __name__ == "__main__":
    unittest.main()
