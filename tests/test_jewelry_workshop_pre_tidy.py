import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.handlers.jewelry_workshop import JewelryWorkshopHandler


class TestJewelryWorkshopPreTidy(unittest.TestCase):
    """
    珠寶加工廠純進店與場景防護 (Scene Guard / Pure Entry) 單元測試套件
    驗證背包整理已徹底抽離為獨立子流程後，珠寶加工廠的進店行為與自癒能力。
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.need_jewelry_workshop = True
        self.mock_machine.config = {"type": "jewelry_workshop"}

        self.handler = JewelryWorkshopHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("os.path.exists", return_value=True)
    def test_1_pure_entry_when_town_is_clean(self, mock_exists):
        """
        測試 1：處於純淨城鎮 (door 可見，無 quit/tidy 覆蓋層) 時，直接點擊珠寶店建築進入 ENTERED_BUILDING
        """
        def mock_match(screen_img, template_name, **kw):
            if template_name in ["common/door.png", "town_building/Jewelry_workshop/Jewelry_workshop.png"]:
                return ((600, 400), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.sleep"):
            self.handler.handle(self.fake_img, self.rect)

        # 斷言點擊了珠寶加工廠建築，直接進入 ENTERED_BUILDING 階段，絕不點擊背包
        self.assertEqual(self.handler.step_phase, "ENTERED_BUILDING")
        self.handler.mouse.click.assert_called_once_with(600, 400)

    @patch("os.path.exists", return_value=True)
    def test_2_scene_guard_dismisses_residual_overlay(self, mock_exists):
        """
        測試 2：若城鎮殘留彈窗覆蓋層 (quit 可見)，Scene Guard 攔截並關閉覆蓋層，不盲目點擊建築
        """
        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/door.png":
                return ((100, 100), 0.90)
            elif template_name == "common/quit.png":
                return ((900, 100), 0.90)
            elif template_name == "town_building/Jewelry_workshop/Jewelry_workshop.png":
                return ((600, 400), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.sleep"), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言觸發了覆蓋層關閉，且維持在 INIT 階段等待純淨城鎮
            mock_wait.assert_called_once()
            self.assertEqual(self.handler.step_phase, "INIT")

    @patch("os.path.exists", return_value=True)
    def test_3_entered_building_timeout_recovery(self, mock_exists):
        """
        測試 3：若處於 ENTERED_BUILDING 且超過 4 秒畫面依然見到城門 door.png，自動退回 INIT 重新進店
        """
        self.handler.step_phase = "ENTERED_BUILDING"
        self.handler.entered_building_time = 100.0

        def mock_match(screen_img, template_name, **kw):
            if template_name == "common/door.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.time", return_value=105.0), \
             patch("states.handlers.jewelry_workshop.time.sleep"):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言進店逾時 5 秒後仍見城門，自動自癒退回 INIT 重新發起進店
            self.assertEqual(self.handler.step_phase, "INIT")


if __name__ == "__main__":
    unittest.main()

