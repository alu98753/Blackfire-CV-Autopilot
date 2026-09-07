"""Behavior tests for Blood Altar exit flow and Foreground Overlay Dismiss Gate."""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from states.state_machine import GameStateMachine
from states.handlers.blood_altar import BloodAltarHandler
from config import GAME_CONFIGS


class TestBehaviorBloodAltarExit(unittest.TestCase):
    """Behavior tests for BloodAltarHandler exit phase (Overlay Dismiss Gate & Scene Navigation)."""

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
        self.state_machine.config = GAME_CONFIGS["blood_altar"].copy()
        self.state_machine.need_blood_altar = True

        self.handler = BloodAltarHandler(self.state_machine)
        self.handler.step_phase = "ALL_DONE_EXITING"
        self.handler.last_action_time = 0.0

        self.dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1280, "height": 720}

    def test_all_done_exiting_prioritizes_cancel_btn_over_exit_btn(self):
        """
        [Overlay Dismiss Gate 門禁測試 1: cancel.png]
        Given: ALL_DONE_EXITING 階段，畫面上同時可見前景取消按鈕 (common/cancel.png) 與背景退出按鈕 (exitfromhouse_and_to_town.png)
        When: 執行 handler.handle()
        Then:
          1. 觸發 click_and_wait_until_gone 點擊並等待 common/cancel.png 消失
          2. 絕不點擊 exitfromhouse_and_to_town.png (防止前景遮罩阻擋導致空點死循環)
        """
        def fake_match(img, template, **kwargs):
            if template == "common/cancel.png":
                return ((731, 622), 0.90)
            if template == "town_building/exitfromhouse_and_to_town.png":
                return ((66, 713), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.handler.click_and_wait_until_gone = MagicMock(return_value=True)

        res = self.handler.handle(self.dummy_img, self.rect)

        self.assertTrue(res)
        # 斷言 1: 優先點擊 cancel.png 啟動閉環
        self.handler.click_and_wait_until_gone.assert_called_once_with(
            "common/cancel.png", 731, 622, self.rect, threshold=0.80
        )
        # 斷言 2: mouse.click 絕不調用背景 exit 座標 (66, 713)
        self.mock_mouse.click.assert_not_called()

    def test_all_done_exiting_prioritizes_quit_btn_over_exit_btn(self):
        """
        [Overlay Dismiss Gate 門禁測試 2: quit.png]
        Given: ALL_DONE_EXITING 階段，畫面上同時可見前景關閉按鈕 (common/quit.png) 與背景退出按鈕 (exitfromhouse_and_to_town.png)
        When: 執行 handler.handle()
        Then: 優先使用 click_and_wait_until_gone 關閉 quit.png，絕不點擊 exitfromhouse_and_to_town.png
        """
        def fake_match(img, template, **kwargs):
            if template == "common/quit.png":
                return ((800, 200), 0.88)
            if template == "town_building/exitfromhouse_and_to_town.png":
                return ((66, 713), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.handler.click_and_wait_until_gone = MagicMock(return_value=True)

        res = self.handler.handle(self.dummy_img, self.rect)

        self.assertTrue(res)
        self.handler.click_and_wait_until_gone.assert_called_once_with(
            "common/quit.png", 800, 200, self.rect, threshold=0.80
        )
        self.mock_mouse.click.assert_not_called()

    def test_all_done_exiting_clicks_exit_btn_when_foreground_is_clean(self):
        """
        [Scene Navigation Edge 導航放行測試]
        Given: ALL_DONE_EXITING 階段，前景已無任何 cancel.png 或 quit.png，僅有 exitfromhouse_and_to_town.png
        When: 執行 handler.handle()
        Then: 放行點擊離開建築按鈕返回城鎮
        """
        def fake_match(img, template, **kwargs):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return ((66, 713), 0.95)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match

        res = self.handler.handle(self.dummy_img, self.rect)

        self.assertTrue(res)
        self.mock_mouse.click.assert_called_once_with(66, 713)

    def test_all_done_exiting_records_completion_when_in_town_without_red_dot(self):
        """
        [Scene Terminal 終態結算測試]
        Given: ALL_DONE_EXITING 階段，畫面已回到城鎮大門 (common/door.png 可見) 且紅點已消除
        When: 執行 handler.handle()
        Then: 記錄完成並調用 pop_and_next_town_subflow()
        """
        def fake_match(img, template, **kwargs):
            if template in ["common/door.png", "town_building/Blood_Altar/Blood_Altar.png"]:
                return ((100, 200), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = fake_match
        self.state_machine.pop_and_next_town_subflow = MagicMock()

        res = self.handler.handle(self.dummy_img, self.rect)

        self.assertTrue(res)
        self.mock_daily_manager.record_subflow_completed.assert_called_once_with("blood_altar")
        self.state_machine.pop_and_next_town_subflow.assert_called_once()
        self.assertFalse(self.state_machine.need_blood_altar)


if __name__ == "__main__":
    unittest.main()
