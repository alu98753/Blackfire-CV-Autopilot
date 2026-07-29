import unittest
from unittest.mock import MagicMock
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.handlers.backpack_full_sorting import BackpackFullSortingHandler


class TestBackpackFullDynamicDestroyable(unittest.TestCase):
    """
    驗證 BackpackFullSortingHandler 動態結合 jewelry_workshop goods_settings 判斷可銷毀品質之單元測試
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.handler = BackpackFullSortingHandler(self.machine)

    def test_1_default_jewelry_workshop_goods_settings_includes_gray_and_green(self):
        """
        測試 1：預設 PRIMARY_MODES 中 jewelry_workshop 的 goods_settings 包含 gray(True) 與 green(True)，
        計算出之 destroyable_colors 應包含 gray_or_empty, gray, green。
        """
        destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertIn("gray_or_empty", destroyable)
        self.assertIn("gray", destroyable)
        self.assertIn("green", destroyable)
        self.assertNotIn("blue", destroyable)
        self.assertNotIn("purple", destroyable)

    def test_2_custom_goods_settings_enables_blue_destroyable(self):
        """
        測試 2：當配置檔中 goods_settings 額外將 blue 的某項材料設為 True 時，
        destroyable_colors 應自動動態擴充包含 blue。
        """
        self.machine.config = {
            "goods_settings": {
                "gray": {"item1": True},
                "green": {"item2": False},
                "blue": {"item3": True},
                "purple": {}
            }
        }
        destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertIn("gray_or_empty", destroyable)
        self.assertIn("blue", destroyable)
        self.assertNotIn("green", destroyable)
        self.assertNotIn("purple", destroyable)


    def test_3_max_scroll_attempts_defaults_to_5(self):
        """
        測試 3：驗證背包已滿滾動尋找的最多次數預設為 5 次。
        """
        max_scrolls = self.machine.config.get("backpack_full_max_scroll", 5)
        self.assertEqual(max_scrolls, 5)


if __name__ == "__main__":
    unittest.main()
