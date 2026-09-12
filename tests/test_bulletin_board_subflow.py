import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
from states.handlers.bulletin_board import BulletinBoardHandler
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

from utils.town_building_detector import BuildingCheckResult

class TestBulletinBoardSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_daily_manager = MagicMock()

        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.mock_capturer.capture.return_value = np.zeros((600, 800, 3), dtype=np.uint8)

        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse
        )
        self.state_machine.daily_manager = self.mock_daily_manager

    @patch('utils.town_building_detector.detect_building_with_red_dot')
    @patch('os.path.exists')
    def test_bulletin_board_full_accept_and_quit_flow(self, mock_exists, mock_detect_red_dot):
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
        mock_detect_red_dot.side_effect = [
            BuildingCheckResult(found_building=True, has_red_dot=True),
            BuildingCheckResult(found_building=True, has_red_dot=False)
        ]
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
            elif name == "town_building/red_dot.png":
                return ((150, 230), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(150, 150)
        self.assertEqual(handler.step_phase, "WAIT_BOARD_OPEN")

        # Step 2: 等待看到 quit.png 與告示牌特徵
        handler.last_action_time = 0.0
        def fake_match_step2(img, name, **kw):
            if name in ["common/quit.png", "town_building/bulletin_board/reset.png"]:
                return ((700, 100), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.assertEqual(handler.step_phase, "CHECK_RESET")

        # Step 3: 檢查重置 (看見 reset.png ➔ 點擊重置)
        handler.last_action_time = 0.0
        def fake_match_step3(img, name, **kw):
            if name == "town_building/bulletin_board/reset.png":
                return ((500, 500), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step3
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(500, 500)
        self.assertEqual(handler.step_phase, "CHECK_RESET")

        # 模擬重置點擊已過 3.1 秒 (大於 3.0 秒渲染等待)
        handler.last_reset_click_time = time.time() - 3.2
        handler.last_action_time = 0.0
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (None, 0.0)
        handler.handle()
        self.assertEqual(handler.step_phase, "PROCESS_ACCEPT_QUESTS")
        self.assertEqual(handler.accept_sub_phase, "FIND_TOP_TASK")

        # Step 4: 發現 task.png -> 點擊首列任務與右半邊 accept_task.png
        handler.last_action_time = 0.0
        self.mock_matcher.match_all.return_value = [(100, 100, 0.90)]
        def fake_match_step4(img, name, **kw):
            if name == "town_building/bulletin_board/accept_task.png":
                return ((600, 500), 0.90)
            return (None, 0.0)
        self.mock_matcher.match.side_effect = fake_match_step4
        self.mock_mouse.click.reset_mock()

        # Mock OCR reader
        mock_ocr = MagicMock()
        mock_ocr.extract_quest_title_at.return_value = "清除野豬"
        handler.ocr_extractor = mock_ocr

        handler.handle()
        self.mock_mouse.click.assert_any_call(100, 100)
        self.mock_mouse.click.assert_any_call(600, 500)
        self.assertEqual(handler.accept_sub_phase, "CLICK_CONFIRM_POPUP")
        self.assertIn("清除野豬", handler.accepted_quest_titles)

        # Step 6: 點擊確認彈窗 confirm.png ➔ 轉移至 WAIT_TASK_ACCEPT_DISMISS
        handler.last_action_time = 0.0
        def fake_match_step6(img, name, **kw):
            if name == "common/confirm.png":
                return ((400, 300), 0.92)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step6
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(400, 300)
        self.assertEqual(handler.accept_sub_phase, "WAIT_TASK_ACCEPT_DISMISS")

        # Step 6.5: WAIT_TASK_ACCEPT_DISMISS 屏障：橫幅存在時必須等待，絕不調用 match_all
        handler.last_action_time = 0.0
        def fake_match_banner_present(img, name, **kw):
            if name == "town_building/bulletin_board/task_accept.png":
                return ((400, 200), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_banner_present
        self.mock_matcher.match_all.reset_mock()
        handler.handle()
        self.assertEqual(handler.accept_sub_phase, "WAIT_TASK_ACCEPT_DISMISS")
        self.mock_matcher.match_all.assert_not_called()

        # Once the banner disappears, the following tick can scan normally.
        handler.last_action_time = 0.0
        self.mock_matcher.match.side_effect = lambda img, name, **kw: (None, 0.0)
        handler.handle()
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

        # Step 9: 完成離場寫入 DailyManager (檢驗紅點已消除)
        handler.last_action_time = 0.0
        def fake_match_step9(img, name, **kw):
            if name == "town_building/bulletin_board/bulletin_board.png":
                return ((150, 150), 0.88)
            # 紅點已消除
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step9
        handler.handle()
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with(
            "bulletin_board", extra_data={"accepted_quests": ["清除野豬"]}
        )

    def test_confirmed_accept_banner_dismissal_refreshes_watchdog_progress(self):
        """A completed acceptance, not the preceding clicks, grants the 90s watchdog lease."""
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        self.state_machine.last_state_change = time.time() - 91.0
        original_notify = self.state_machine.notify_ui_progress
        self.state_machine.notify_ui_progress = MagicMock(wraps=original_notify)
        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.step_phase = "PROCESS_ACCEPT_QUESTS"
        handler.accept_sub_phase = "WAIT_TASK_ACCEPT_DISMISS"
        handler.last_action_time = 0.0
        screen = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        # A still-visible banner is only waiting, so it must not reset the watchdog.
        self.mock_matcher.match.return_value = ((400, 200), 0.90)
        handler.handle(screen, rect)
        self.state_machine.notify_ui_progress.assert_not_called()

        # Its disappearance confirms the game finished accepting one task.
        handler.last_action_time = 0.0
        self.mock_matcher.match.return_value = (None, 0.0)
        handler.handle(screen, rect)

        self.state_machine.notify_ui_progress.assert_called_once()
        self.assertEqual(handler.accept_sub_phase, "FIND_TOP_TASK")
        self.assertFalse(self.state_machine.exception_watchdog.check(MagicMock()))

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

    @patch('os.path.exists')
    def test_bulletin_board_task_already_full_intercept(self, mock_exists):
        """
        邊界測試 3：點擊接受後偵測到任務已滿 (task_already_full.png) 彈窗，
        點擊 CONFIRM、寫入 DailyManager 並轉移至 EXIT_BOARD 準備 QUIT 離場。
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD

        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.reset_state()
        handler.step_phase = "PROCESS_ACCEPT_QUESTS"
        handler.accepted_quest_titles = ["任務1", "任務2"]

        def fake_match_full(img, name, **kw):
            if name == "town_building/bulletin_board/task_already_full.png":
                return ((400, 300), 0.90)
            if name == "common/confirm.png":
                return ((400, 400), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_full
        handler.handle()

        # 斷言點擊了 confirm 按鈕 (400, 400) 並轉移至 EXIT_BOARD 離場
        self.mock_mouse.click.assert_called_once_with(400, 400)
        self.assertEqual(handler.step_phase, "EXIT_BOARD")

    @patch('utils.town_building_detector.detect_building_with_red_dot')
    @patch('os.path.exists', return_value=True)
    def test_bulletin_board_exit_with_red_dot_still_present(self, mock_exists, mock_detect_red_dot):
        """測試：退出後在城鎮再次檢查紅點 (有檢查到紅點 ➔ 判定未完成接取，不標記 completed_today)"""
        mock_detect_red_dot.return_value = BuildingCheckResult(found_building=True, has_red_dot=True)
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.step_phase = "ALL_DONE_EXITING"
        handler.last_action_time = 0.0

        def fake_match(img, name, **kw):
            if name in ["common/door.png", "town_building/bulletin_board/bulletin_board.png"]:
                return ((150, 150), 0.88)
            if name == "town_building/red_dot.png":
                return ((150, 230), 0.85)  # 仍然有紅點！
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        handler.handle()

        self.mock_daily_manager.record_subflow_completed.assert_not_called()

    @patch('os.path.exists', return_value=True)
    def test_bulletin_board_init_skips_when_no_red_dot(self, mock_exists):
        """測試：進入前預檢 (INIT 發現告示牌下方無紅點 ➔ 判定所有任務已接取，直接標記完成並跳過)"""
        self.state_machine.config = GAME_CONFIGS["bulletin_board"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BULLETIN_BOARD
        handler = self.state_machine.handlers[self.state_machine.STATE_BULLETIN_BOARD]
        handler.step_phase = "INIT"
        handler.last_action_time = 0.0

        def fake_match(img, name, **kw):
            if name == "common/door.png":
                return ((100, 200), 0.9)
            if name == "town_building/bulletin_board/bulletin_board.png":
                return ((150, 150), 0.88)
            # 無紅點
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        handler.handle()

        self.mock_daily_manager.record_subflow_completed.assert_called_once_with(
            "bulletin_board", extra_data={"accepted_quests": []}
        )
        self.mock_mouse.click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
