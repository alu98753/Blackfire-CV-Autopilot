import unittest
from unittest.mock import MagicMock
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.handlers.backpack_full_sorting import BackpackFullSortingHandler


class TestBackpackFullDynamicDestroyable(unittest.TestCase):
    """
    驗證 BackpackFullSortingHandler 將 goods_settings 作為全系統唯一品質銷毀授權依據，
    以及全為 False 時自動降級兜底為 ["gray_or_empty"] 之單元測試。
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.handler = BackpackFullSortingHandler(self.machine)

    def test_1_default_jewelry_workshop_goods_settings_includes_gray_and_green(self):
        """
        測試 1：預設 SUBFLOW_CONFIGS 中 jewelry_workshop 的 goods_settings 包含 gray(True) 與 green(True)，
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

    def test_3_all_goods_settings_false_fallback_to_gray_or_empty_only(self):
        """
        測試 3 (安全防呆兜底)：
        當 goods_settings 完全沒有開啟任何品質（全部項目的 Boolean 皆為 False），
        系統應自動降級兜底為只允許 ["gray_or_empty"]，確保機制永遠安全不卡死。
        """
        self.machine.config = {
            "goods_settings": {
                "gray": {"Sandworm_scales": False, "Spider_silk": False},
                "green": {"Toad_Venom": False, "Wild_boar_tusk": False},
                "blue": {"Blue_Item": False},
                "purple": {"Purple_Item": False}
            }
        }
        destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertEqual(destroyable, ["gray_or_empty"])

    def test_4_empty_goods_settings_fallback_to_gray_or_empty_only(self):
        """
        測試 4 (空設定防呆)：
        當 goods_settings 字典完全為空 {} 時，系統亦應自動降級兜底為 ["gray_or_empty"]。
        """
        self.machine.config = {
            "goods_settings": {
                "gray": {},
                "green": {},
                "blue": {},
                "purple": {}
            }
        }
        destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertEqual(destroyable, ["gray_or_empty"])

    def test_5_goods_settings_is_sole_source_of_truth(self):
        """
        測試 5 (單一權威來源)：
        驗證 goods_settings 為全系統唯一的品質銷毀授權依據，
        無視任何舊有/廢棄的單獨欄位設定，僅根據 goods_settings 中 True 的品質決定銷毀授權。
        """
        self.machine.config = {
            "goods_settings": {
                "gray": {"item1": False},
                "green": {"item2": True},
                "blue": {"item3": False},
                "purple": {"item4": False}
            },
            # 即使嘗試寫入舊有的單獨設定欄位，系統亦不採納
            "backpack_full_destroyable_colors": ["purple", "red"]
        }
        destroyable = self.handler.get_dynamic_destroyable_colors()
        # 僅有 green 為 True，故結果應嚴格為 ["green"]
        self.assertEqual(destroyable, ["green"])
        self.assertNotIn("purple", destroyable)
        self.assertNotIn("red", destroyable)

    def test_6_max_scroll_attempts_defaults_to_5(self):
        """
        測試 6：驗證背包已滿滾動尋找的最多次數預設為 5 次。
        """
        max_scrolls = self.machine.config.get("backpack_full_max_scroll", 5)
        self.assertEqual(max_scrolls, 5)


if __name__ == "__main__":
    unittest.main()
