import unittest
from unittest.mock import MagicMock, patch
from states.state_machine import GameStateMachine
from config import GAME_CONFIGS


class TestBloodAltarSacrificeSubflow(unittest.TestCase):
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
    def test_blood_altar_full_sacrifice_subflow(self, mock_exists):
        """測試：完整獻祭流程 (今日已領血 ➔ 切換 SACRIFICE_MENU_OPEN ➔ 選擇血水與獻祭 ➔ 連續 3 幀無血水 ➔ ALL_DONE_EXITING ➔ 退出城鎮)"""
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BLOOD_ALTAR
        self.state_machine.need_blood_altar = True

        handler = self.state_machine.handlers[self.state_machine.STATE_BLOOD_ALTAR]
        handler.has_claimed_daily = True  # 今日已領血
        self.mock_daily_manager.is_subflow_completed.return_value = True

        # Step 1: 在建築內識別到 Sacrifice.png ➔ 點擊轉入 SACRIFICE_MENU_OPEN
        handler.step_phase = "ENTERED_BUILDING"
        handler.last_action_time = 0.0

        def fake_match_step1(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/Blood_Altar/Sacrifice.png":
                return ((700, 750), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step1
        handler.handle()
        self.assertEqual(handler.step_phase, "SACRIFICE_MENU_OPEN")

        # Step 2: 在 SACRIFICE_MENU_OPEN 獻祭灰血水
        handler.last_action_time = 0.0
        has_sacrificed = [False]

        def fake_match_step2(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if not has_sacrificed[0] and name == "town_building/Blood_Altar/gray_blood.png":
                return ((300, 300), 0.85)
            if not has_sacrificed[0] and name == "town_building/sell_max.png":
                return ((400, 400), 0.85)
            if not has_sacrificed[0] and name == "town_building/Blood_Altar/alter.png":
                return ((500, 500), 0.85)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step2
        handler.handle()
        has_sacrificed[0] = True

        # Step 3: 連續 3 幀無血水 ➔ 切換至 ALL_DONE_EXITING
        for _ in range(3):
            handler.last_action_time = 0.0
            handler.handle()

        self.assertEqual(handler.step_phase, "ALL_DONE_EXITING")

        # Step 4: 點擊 exitfromhouse_and_to_town.png 退出離場
        handler.last_action_time = 0.0

        def fake_match_step4(img, name, **kw):
            if kw.get("quiet"):
                return (None, 0.0)
            if name == "town_building/exitfromhouse_and_to_town.png":
                return ((50, 50), 0.9)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match_step4
        handler.handle()

        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("blood_altar")


if __name__ == "__main__":
    unittest.main()
