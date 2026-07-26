import unittest
from unittest.mock import MagicMock, patch
import time
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS

class TestBloodAltarReceive(unittest.TestCase):
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
        self.mock_daily_manager.is_subflow_completed.return_value = False
        self.state_machine.daily_manager = self.mock_daily_manager


    @patch('os.path.exists')
    def test_blood_altar_receive_daily_full_flow(self, mock_exists):
        """
        測試血之祭壇「每日領血」完整流程：
        1. 城鎮 (Blood_Altar.png) ➔ 點擊進入建築
        2. 建築內 ➔ 點擊 receive_entry.png 進入領血頁籤
        3. 領血頁籤 ➔ 點擊 receive_daily.png
        4. 彈窗關閉 (confirm.png -> ok.png) ➔ 轉至 ALL_DONE_EXITING
        5. 離場 (exitfromhouse_and_to_town.png) ➔ 點擊返回城鎮，記錄 DailyManager 並消費佇列
        """
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        self.state_machine.need_blood_altar = True
        self.state_machine.town_subflow_queue = []

        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.reset_state()

        # Step 1: 城鎮點擊祭壇建築
        def fake_match_step1(img, name, **kw):
            if name == "common/door.png":
                return ((100, 200), 0.9)
            elif name == "town_building/Blood_Altar/Blood_Altar.png":
                return ((550, 688), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(550, 688)
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

        # Step 2: 點擊 receive_entry.png 切換至領血頁籤
        handler.last_action_time = 0.0
        def fake_match_step2(img, name, **kw):
            if name == "town_building/Blood_Altar/receive_entry.png":
                return ((300, 400), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.mock_mouse.click.assert_called_once_with(300, 400)
        self.assertEqual(handler.step_phase, "RECEIVE_TAB_OPEN")

        # Step 3: 點擊 receive_daily.png 領取血水
        handler.last_action_time = 0.0
        def fake_match_step3(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/receive_daily.png":
                return ((400, 500), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step3
        self.mock_mouse.click.reset_mock()
        handler.handle()
        self.assertTrue(handler.has_claimed_daily)
        self.assertEqual(handler.step_phase, "HANDLING_RECEIVE_POPUPS")

        # Step 4: 點擊 common/confirm.png 關閉領取獎勵彈窗
        handler.last_action_time = 0.0
        def fake_match_step4(img, name, **kw):
            if name == "common/confirm.png":
                return ((400, 550), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step4
        self.mock_mouse.click.reset_mock()
        handler.handle()

        # Step 5: 彈窗已關閉，看見 exitfromhouse_and_to_town.png ➔ 進入 ALL_DONE_EXITING 階段
        handler.last_action_time = 0.0
        def fake_match_step5(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((50, 50), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step5
        handler.handle()
        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        # Step 6: 點擊 exitfromhouse_and_to_town.png 離開建築返回城鎮
        handler.last_action_time = 0.0
        self.mock_mouse.click.reset_mock()
        handler.handle()

        # 斷言：DailyManager 已上記錄完成，且 need_blood_altar 被重置為 False
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("blood_altar")
        self.assertFalse(self.state_machine.need_blood_altar)

if __name__ == "__main__":
    unittest.main()
