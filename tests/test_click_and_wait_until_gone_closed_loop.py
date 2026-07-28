import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.state_machine import GameStateMachine
from states.handlers.base import BaseStateHandler
from states.handlers.blood_altar import BloodAltarHandler
from states.handlers.result import ResultHandler

class TestClickAndWaitUntilGoneClosedLoop(unittest.TestCase):
    def setUp(self):
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)
        self.base_handler = BaseStateHandler(self.state_machine)

    def test_click_and_wait_until_gone_successful_disappearance(self):
        """
        [閉環消失斷言 1: 正常消失]
        發起點擊後，持續輪詢比對畫面，當按鈕圖案真正從畫面上 None (消失) 才解鎖返回。
        """
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 模擬 capture 次數：
        # 第 1 幀：按鈕仍在 (500, 500)
        # 第 2 幀：按鈕消失 (None)
        poll_count = 0
        def mock_match(fresh_img, template_name, **kwargs):
            nonlocal poll_count
            poll_count += 1
            if poll_count == 1:
                return (500, 500), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            self.base_handler.click_and_wait_until_gone(
                "common/quit.png", 500, 500, rect, timeout=4.0, check_interval=0.1, post_delay=0.0
            )

        # 斷言 1: 初次發起點擊 (500, 500)
        self.state_machine.mouse.click.assert_called_with(500, 500)
        # 斷言 2: 輪詢到 None 即刻解鎖（共輪詢 2 次）
        self.assertEqual(poll_count, 2)

    def test_click_and_wait_until_gone_triggers_reclick_if_not_disappeared(self):
        """
        [閉環消失斷言 2: 重試補點擊]
        若點擊後超過 retry_interval 按鈕仍未消失，對當前座標發起自動補點擊 (Re-click)。
        """
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        # 模擬 5 幀比對皆存在 (500, 500)
        self.state_machine.matcher.match.return_value = ((500, 500), 0.90)

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            self.base_handler.click_and_wait_until_gone(
                "receive_daily.png", 500, 500, rect, timeout=2.5, retry_interval=1.0, check_interval=0.2, post_delay=0.0
            )

        # 斷言: 當按鈕長久未消失時，觸發至少 2 次以上的補點擊 (Initial click + Re-clicks)
        self.assertGreaterEqual(self.state_machine.mouse.click.call_count, 2)

    def test_blood_altar_uses_click_and_wait_until_gone_for_receive_daily(self):
        """
        [組件實施斷言 3: 血之祭壇領血]
        驗證 BloodAltarHandler 點擊 receive_daily_btn 採用 click_and_wait_until_gone 閉環。
        """
        handler = BloodAltarHandler(self.state_machine)
        handler.step_phase = "RECEIVE_TAB_OPEN"
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        def mock_match(img, template, **kwargs):
            if template == "town_building/Blood_Altar/receive_daily.png":
                return (500, 400), 0.85
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match
        handler.click_and_wait_until_gone = MagicMock()

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言: 顯式呼叫 click_and_wait_until_gone 並傳入 receive_daily_btn
        handler.click_and_wait_until_gone.assert_called_once()
        self.assertEqual(handler.step_phase, "HANDLING_RECEIVE_POPUPS")

    def test_result_handler_uses_click_and_wait_until_gone_for_continue_and_exit(self):
        """
        [組件實施斷言 4: 戰鬥結算離場與繼續]
        驗證 ResultHandler 在點擊 common/continue.png 或 exit_btn 時，採用 click_and_wait_until_gone 閉環確認消失才推進。
        """
        handler = ResultHandler(self.state_machine)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        def mock_match(img, template, **kwargs):
            if template == "common/continue.png":
                return (700, 600), 0.95
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match
        handler.click_and_wait_until_gone = MagicMock()

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言: 結算點擊採用 click_and_wait_until_gone 閉環確認消失
        handler.click_and_wait_until_gone.assert_called_once()

if __name__ == '__main__':
    unittest.main()
