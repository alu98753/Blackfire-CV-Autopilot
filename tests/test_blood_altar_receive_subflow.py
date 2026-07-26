import unittest
from unittest.mock import MagicMock, patch
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS


class TestBloodAltarReceiveSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_matcher = MagicMock()

        self.state_machine = GameStateMachine(
            capturer=self.mock_capturer,
            mouse=self.mock_mouse,
            matcher=self.mock_matcher
        )

        self.mock_daily_manager = MagicMock()
        self.state_machine.daily_manager = self.mock_daily_manager

    @patch('os.path.exists')
    def test_blood_altar_full_receive_subflow(self, mock_exists):
        """測試：完整每日領血流程 (ENTERED_BUILDING ➔ 點擊 receive_entry.png ➔ RECEIVE_TAB_OPEN ➔ 點擊 receive_daily.png ➔ HANDLING_RECEIVE_POPUPS ➔ 點擊 confirm.png ➔ SACRIFICE_MENU_OPEN)"""
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        self.state_machine.need_blood_altar = True

        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.has_claimed_daily = False
        self.mock_daily_manager.is_subflow_completed.return_value = False

        # Step 1: 在建築內點擊 receive_entry.png 領血頁籤
        handler.step_phase = "ENTERED_BUILDING"
        handler.last_action_time = 0.0

        def fake_match_step1(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/receive_entry.png":
                return ((300, 400), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.assertEqual(handler.step_phase, "RECEIVE_TAB_OPEN")

        # Step 2: 在 RECEIVE_TAB_OPEN 點擊 receive_daily.png 每日領血按鈕
        handler.last_action_time = 0.0

        def fake_match_step2(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/receive_daily.png":
                return ((400, 500), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        handler.handle()
        self.assertTrue(handler.has_claimed_daily)
        self.assertEqual(handler.step_phase, "HANDLING_RECEIVE_POPUPS")

        # Step 3: 在 HANDLING_RECEIVE_POPUPS 點擊 common/confirm.png 領取確認彈窗
        handler.last_action_time = 0.0

        def fake_match_step3(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "common/confirm.png":
                return ((450, 550), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step3
        handler.handle()

        # Step 4: 彈窗關閉後看見 Sacrifice.png 獻祭選單按鈕 ➔ 轉入 SACRIFICE_MENU_OPEN
        handler.last_action_time = 0.0

        def fake_match_step4(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/Sacrifice.png":
                return ((700, 700), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step4
        handler.handle()
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")


if __name__ == "__main__":
    unittest.main()
