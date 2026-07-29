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
    珠寶加工廠進場前城鎮背包預先整理 (Pre-Tidy) 單元測試套件
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.need_jewelry_workshop = True
        self.mock_machine.bag_tidied = False
        self.mock_machine.bag_opened_clicked = False
        self.mock_machine.config = {"type": "jewelry_workshop"}

        self.handler = JewelryWorkshopHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()
        self.handler.bag_handler.matcher = self.handler.matcher
        self.handler.bag_handler.mouse = self.handler.mouse
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("os.path.exists", return_value=True)
    def test_1_pre_tidy_open_backpack_first(self, mock_exists):
        """
        測試 1：處於城鎮且 pre_tidy_done = False 時，優先點擊開啟背包 (open_backpack)
        """
        def mock_match(screen_img, template_name, **kw):
            if template_name in ["common/door.png", "town_building/Jewelry_workshop/Jewelry_workshop.png"]:
                return ((100, 100), 0.90)
            elif template_name == "common/bag_text.png":
                return ((500, 200), 0.95)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.sleep"):
            self.handler.handle(self.fake_img, self.rect)

        # 斷言點擊了背包入口，尚未點擊珠寶加工廠建築
        self.assertTrue(self.mock_machine.bag_opened_clicked)
        self.assertEqual(self.handler.step_phase, "INIT")

    @patch("os.path.exists", return_value=True)
    def test_2_pre_tidy_tidy_backpack_second(self, mock_exists):
        """
        測試 2：當背包開啟後，優先點擊整理按鈕 (tidy_backpack)
        """
        self.mock_machine.bag_opened_clicked = True
        self.mock_machine.bag_tidied = False

        def mock_match(screen_img, template_name, **kw):
            if template_name in ["common/door.png", "town_building/Jewelry_workshop/Jewelry_workshop.png"]:
                return ((100, 100), 0.90)
            elif template_name == "common/tidy.png":
                return ((300, 800), 0.92)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.sleep"):
            self.handler.handle(self.fake_img, self.rect)

        # 斷言點擊了整理按鈕，設定 bag_tidied = True
        self.assertTrue(self.mock_machine.bag_tidied)
        self.assertEqual(self.handler.step_phase, "INIT")

    @patch("os.path.exists", return_value=True)
    def test_3_pre_tidy_quit_and_enter_building_finally(self, mock_exists):
        """
        測試 3：當背包整理完畢後，點擊退出關閉背包並標記 pre_tidy_done = True；下一影格點擊珠寶加工廠進入建築。
        """
        self.mock_machine.bag_opened_clicked = True
        self.mock_machine.bag_tidied = True

        def mock_match(screen_img, template_name, **kw):
            if template_name in ["common/door.png", "town_building/Jewelry_workshop/Jewelry_workshop.png"]:
                return ((100, 100), 0.90)
            elif template_name == "common/quit.png":
                return ((900, 100), 0.90)
            return (None, 0.0)

        self.handler.matcher.match.side_effect = mock_match

        with patch("states.handlers.jewelry_workshop.time.sleep"), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait:
            self.handler.handle(self.fake_img, self.rect)

            # 斷言關閉了背包，並設定 pre_tidy_done = True
            mock_wait.assert_called_once()
            self.assertTrue(self.handler.pre_tidy_done)

        # 模擬下一影格 (背包已關閉，pre_tidy_done = True)
        self.mock_machine.bag_opened_clicked = False
        self.mock_machine.bag_tidied = False
        self.handler.last_action_time = 0.0

        with patch("states.handlers.jewelry_workshop.time.sleep"):
            self.handler.handle(self.fake_img, self.rect)

            # 斷言點擊了珠寶加工廠建築，進入 ENTERED_BUILDING 階段
            self.assertEqual(self.handler.step_phase, "ENTERED_BUILDING")


if __name__ == "__main__":
    unittest.main()
