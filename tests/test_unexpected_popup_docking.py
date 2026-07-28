import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.state_machine import GameStateMachine
from states.exceptions.watchdog import ExceptionWatchdog
from states.exceptions.handler import UnexpectedPopupRecoveryHandler
from states.exceptions.subflows import WheelOfFortuneSubflow, RaidBoxSubflow, GenericAntiStuckSubflow

class TestUnexpectedPopupDocking(unittest.TestCase):
    def setUp(self):
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)
        self.watchdog = ExceptionWatchdog(self.state_machine)
        self.popup_handler = UnexpectedPopupRecoveryHandler(self.state_machine)
        self.state_machine.handlers[self.state_machine.STATE_POPUP_RECOVERY] = self.popup_handler

    def test_wheel_of_fortune_popup_detection_and_recovery(self):
        """
        [全螢幕彈窗對接斷言 1: 幸運輪盤]
        當幸運輪盤 Wheel_of_Fortune.png 蓋住畫面時，
        PopupRecovery 優先級 1 命中 WheelOfFortuneSubflow，點擊 quit.png 並恢復暫存狀態。
        """
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.stash_current_state("test_wheel")

        # 模擬比對到 exceptions/Wheel_of_Fortune.png 與 common/quit.png
        def mock_match(img, template, **kwargs):
            if template in ["exceptions/Wheel_of_Fortune.png", "Wheel_of_Fortune.png"]:
                return (100, 100), 0.90
            elif template == "common/quit.png":
                return (800, 150), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True), patch('cv2.imread', return_value=MagicMock(shape=(600, 800, 3))):
            self.popup_handler.handle(None, rect)

        # 斷言 1: 成功發起點擊
        self.state_machine.mouse.click.assert_called()
        # 斷言 2: 中央統一將狀態復原回原暫存狀態 (STATE_NAVIGATING)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        self.assertIsNone(self.state_machine.stashed_state)

    def test_raid_box_popup_detection_and_recovery(self):
        """
        [全螢幕彈窗對接斷言 2: 掃蕩/懸賞寶箱]
        當掃蕩寶箱 Raid_Box.png 蓋住畫面時，
        PopupRecovery 優先級 1 命中 RaidBoxSubflow，點擊 cancel.png 並恢復暫存狀態。
        """
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.stash_current_state("test_raid_box")

        # 模擬比對到 exceptions/Raid_Box.png 與 exceptions/cancel.png
        def mock_match(img, template, **kwargs):
            if template in ["exceptions/Raid_Box.png", "Raid_Box.png"]:
                return (100, 100), 0.90
            elif template == "exceptions/cancel.png":
                return (500, 500), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True):
            self.popup_handler.handle(None, rect)

        # 斷言 1: 成功點擊取消關閉按鈕
        self.state_machine.mouse.click.assert_called()
        # 斷言 2: 恢復原暫存狀態 (STATE_BATTLE)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

    def test_generic_anti_stuck_fallback_recovery(self):
        """
        [全螢幕彈窗對接斷言 3: 無專屬圖案時觸發優先級 2 通用防卡死]
        當畫面上無專屬 Subflow 圖案時，自動觸發 GenericAntiStuckSubflow 點擊全域按鈕。
        """
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        self.state_machine.stash_current_state("test_generic")

        # 模擬專屬圖案接 None，但通用 exceptions/cancel.png 匹配成功
        def mock_match(img, template, **kwargs):
            if template in ["exceptions/Wheel_of_Fortune.png", "exceptions/Raid_Box.png"]:
                return None, 0.0
            elif template == "exceptions/cancel.png":
                return (500, 500), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True):
            self.popup_handler.handle(None, rect)

        # 斷言: 觸發通用防卡死點擊並復原狀態 (STATE_LOBBY)
        self.state_machine.mouse.click.assert_called()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

    def test_watchdog_stashes_state_and_triggers_popup_recovery_on_timeout(self):
        """
        [全螢幕彈窗對接斷言 4: Watchdog 逾時自動觸發]
        當處於 NAVIGATING 逾時 > 30s 時，Watchdog 自動暫存原狀態並轉移至 STATE_POPUP_RECOVERY。
        """
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.last_state_change = time.time() - 35.0

        with patch('states.exceptions.watchdog.safe_match', return_value=(None, 0.0)):
            triggered = self.watchdog.check(None)

        # 斷言: 觸發救援、暫存原狀態、狀態轉移至 STATE_POPUP_RECOVERY
        self.assertTrue(triggered)
        self.assertEqual(self.state_machine.stashed_state, self.state_machine.STATE_NAVIGATING)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_POPUP_RECOVERY)

if __name__ == '__main__':
    unittest.main()
