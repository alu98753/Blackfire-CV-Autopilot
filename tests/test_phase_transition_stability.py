import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.state_machine import GameStateMachine
from states.handlers.blood_altar import BloodAltarHandler
from states.handlers.hero_draw import HeroDrawHandler
from states.handlers.jewelry_workshop import JewelryWorkshopHandler
from states.handlers.chest import ChestHandler
from states.handlers.bulletin_board import BulletinBoardHandler

class TestPhaseTransitionStability(unittest.TestCase):
    def setUp(self):
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)

    def test_blood_altar_init_phase_remains_init_until_building_ui_stable(self):
        """
        [過早切換狀態防護斷言 1: 血之祭壇]
        驗證點擊 Blood_Altar.png 建築物時，狀態仍保持在 INIT 階段；
        直到畫面上穩定比對到內部 UI 特徵 (exitfromhouse_and_to_town.png) 才切換至 ENTERED_BUILDING 階段。
        """
        handler = BloodAltarHandler(self.state_machine)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.config = {"type": "blood_altar"}
        self.state_machine.need_blood_altar = True

        # 幀 1: 僅辨識到城鎮建築 Blood_Altar.png，未看到建築內部 exitfromhouse_and_to_town.png
        def mock_match_frame1(img, template, **kwargs):
            if template == "town_building/Blood_Altar/Blood_Altar.png":
                return (500, 500), 0.85
            elif template == "common/door.png":
                return (100, 700), 0.85
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match_frame1
        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言 1: 點擊建築後，step_phase 依然為 INIT 階段（等待畫面渲染穩定）
        self.assertEqual(handler.step_phase, "INIT")
        self.state_machine.mouse.click.assert_called_once()

        # 幀 2: 畫面渲染完成，成功比對到 exitfromhouse_and_to_town.png
        def mock_match_frame2(img, template, **kwargs):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return (900, 100), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match_frame2
        handler.last_action_time = 0.0 # 繞過冷卻

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言 2: 比對到內部 UI 特徵後，才轉移至 ENTERED_BUILDING 階段
        self.assertEqual(handler.step_phase, "ENTERED_BUILDING")

    def test_hero_draw_init_phase_uses_click_and_wait_until_gone(self):
        """
        [過早切換狀態防護斷言 2: 抽英雄酒館]
        驗證點擊酒館建築 Tavern.png 時，採用 click_and_wait_until_gone 閉環確認建築圖片消失，
        確認入場後才轉移至 ENTERED_TAVERN 階段。
        """
        handler = HeroDrawHandler(self.state_machine)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.config = {"type": "hero_draw"}
        self.state_machine.need_hero_draw = True

        def mock_match(img, template, **kwargs):
            if template == "town_building/Tavern/Tavern.png":
                return (500, 500), 0.85
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match
        self.state_machine.click_and_wait_until_gone = MagicMock()

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言: 使用 click_and_wait_until_gone 閉環確認 Tavern.png 消失後切換至 ENTERED_TAVERN
        self.state_machine.click_and_wait_until_gone.assert_called_once()
        self.assertEqual(handler.step_phase, "ENTERED_TAVERN")

    def test_jewelry_workshop_entered_building_verifies_ui_elements(self):
        """
        [過早切換狀態防護斷言 3: 珠寶加工廠]
        驗證珠寶加工廠必須穩定比對到 sell_out.png 與 exitfromhouse_and_to_town.png 或 sell_btn 頁籤才切換至 SELL_MENU_OPEN。
        """
        handler = JewelryWorkshopHandler(self.state_machine)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.config = {"type": "jewelry_workshop"}
        self.state_machine.need_jewelry_workshop = True

        # 比對到內部 UI 特徵
        def mock_match(img, template, **kwargs):
            if template == "town_building/sell_out.png":
                return (400, 400), 0.85
            elif template == "town_building/exitfromhouse_and_to_town.png":
                return (900, 100), 0.85
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言: 比對到內部 UI 特徵後才切換至 SELL_MENU_OPEN
        self.assertEqual(handler.step_phase, "SELL_MENU_OPEN")

    def test_chest_click_free_chest_phase_verifies_treasure_window_template(self):
        """
        [過早切換狀態防護斷言 4: 神秘寶箱]
        驗證神秘寶箱在 CLICK_FREE_CHEST 階段，必須驗證 free_treasure.png 大彈窗登場後才執行點擊。
        """
        handler = ChestHandler(self.state_machine)
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}
        self.state_machine.config = {"type": "chest"}
        self.state_machine.need_chest = True
        handler.step_phase = "CLICK_FREE_CHEST"

        def mock_match(img, template, **kwargs):
            if template == "town_building/mysterious_treasure/free_treasure.png":
                return (500, 500), 0.85
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            handler.handle(None, rect)

        # 斷言: 成功識別 free_treasure.png 並轉移至 WAITING_CONFIRM
        self.assertEqual(handler.step_phase, "WAITING_CONFIRM")

if __name__ == '__main__':
    unittest.main()
