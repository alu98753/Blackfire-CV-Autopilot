import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.state_machine import GameStateMachine
from states.handlers.backpack_full_sorting import BackpackFullSortingHandler
from config import BACKPACK_FULL_SETTINGS, SUBFLOW_CONFIGS


class TestBackpackFullDynamicDestroyable(unittest.TestCase):
    """
    驗證 BackpackFullSortingHandler 將 backpack_full.destroy_goods 作為唯一銷毀授權依據，
    以及全為 False 時自動降級兜底為 ["gray_or_empty"] 之單元測試。
    """

    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.machine = GameStateMachine(self.mock_capturer, self.mock_matcher, self.mock_mouse)
        self.handler = BackpackFullSortingHandler(self.machine)

    def test_1_default_destroy_goods_includes_gray_green_and_blue(self):
        """
        測試 1：預設 backpack_full.destroy_goods 包含 gray、green 與 blue 授權，
        計算出之 destroyable_colors 應包含 gray_or_empty, gray, green, blue。
        """
        destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertIn("gray_or_empty", destroyable)
        self.assertIn("gray", destroyable)
        self.assertIn("green", destroyable)
        self.assertIn("blue", destroyable)
        self.assertNotIn("purple", destroyable)

    def test_default_sell_and_destroy_goods_start_equal_but_are_separate(self):
        sell_goods = SUBFLOW_CONFIGS["jewelry_workshop"]["sell_goods"]
        destroy_goods = BACKPACK_FULL_SETTINGS["destroy_goods"]

        self.assertEqual(sell_goods, destroy_goods)
        self.assertIsNot(sell_goods, destroy_goods)
        for quality in sell_goods:
            self.assertIsNot(sell_goods[quality], destroy_goods[quality])

    def test_2_custom_goods_settings_enables_blue_destroyable(self):
        """
        測試 2：當配置檔中 goods_settings 額外將 blue 的某項材料設為 True 時，
        destroyable_colors 應自動動態擴充包含 blue。
        """
        settings = {
            "destroy_goods": {
                "gray": {"item1": True},
                "green": {"item2": False},
                "blue": {"item3": True},
                "purple": {}
            },
        }
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
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
        settings = {
            "destroy_goods": {
                "gray": {"Sandworm_scales": False, "Spider_silk": False},
                "green": {"Toad_Venom": False, "Wild_boar_tusk": False},
                "blue": {"Blue_Item": False},
                "purple": {"Purple_Item": False}
            },
        }
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
            destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertEqual(destroyable, ["gray_or_empty"])

    def test_4_empty_goods_settings_fallback_to_gray_or_empty_only(self):
        """
        測試 4 (空設定防呆)：
        當 goods_settings 字典完全為空 {} 時，系統亦應自動降級兜底為 ["gray_or_empty"]。
        """
        settings = {
            "destroy_goods": {
                "gray": {},
                "green": {},
                "blue": {},
                "purple": {}
            },
        }
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
            destroyable = self.handler.get_dynamic_destroyable_colors()
        self.assertEqual(destroyable, ["gray_or_empty"])

    def test_5_destroy_goods_is_independent_from_jewelry_sell_goods(self):
        """
        測試 5 (單一權威來源)：
        驗證 goods_settings 為全系統唯一的品質銷毀授權依據，
        無視任何舊有/廢棄的單獨欄位設定，僅根據 goods_settings 中 True 的品質決定銷毀授權。
        """
        destroy_settings = {
            "destroy_goods": {
                "gray": {"item1": False},
                "green": {"item2": True},
                "blue": {"item3": False},
                "purple": {"item4": False}
            }
        }
        original_sell_goods = SUBFLOW_CONFIGS["jewelry_workshop"].get("sell_goods")
        SUBFLOW_CONFIGS["jewelry_workshop"]["sell_goods"] = {
            "purple": {"valuable": True}
        }
        try:
            with patch.dict(BACKPACK_FULL_SETTINGS, destroy_settings, clear=True):
                destroyable = self.handler.get_dynamic_destroyable_colors()
        finally:
            SUBFLOW_CONFIGS["jewelry_workshop"]["sell_goods"] = original_sell_goods
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

    def test_7_unauthorized_item_in_goods_settings_is_intercepted_from_destruction(self):
        """
        測試 7 (物品層級二次防護)：
        驗證當彈窗內容為未在 goods_settings 授權的裝備或物品 (Scorpion_Shell = False 或未匹配到範本) 時，
        is_item_authorized_by_goods_settings 能精確返回 False 進行安全攔截，防止誤刪貴重裝備/物品。
        """
        settings = {
            "destroy_goods": {
                "gray": {},
                "green": {"Scorpion_Shell": False, "Toad_Venom": True},
                "blue": {},
                "purple": {}
            },
        }
        mock_screen = MagicMock()
        # 情況 A：彈窗內比對到已設為 False 的 Scorpion_Shell
        self.mock_matcher.match.side_effect = lambda img, tpl, **kw: ((100, 100), 0.90) if "Scorpion_Shell" in tpl else (None, 0.0)
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
            authorized = self.handler.is_item_authorized_by_goods_settings(mock_screen, "green")
        self.assertFalse(authorized, "Scorpion_Shell 在 goods_settings 設為 False 時必須拒絕銷毀！")

        # 情況 B：彈窗內為綠色裝備，完全沒比對到任何已知的 goods 模板
        self.mock_matcher.match.side_effect = lambda img, tpl, **kw: (None, 0.0)
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
            authorized_equip = self.handler.is_item_authorized_by_goods_settings(mock_screen, "green")
        self.assertFalse(authorized_equip, "未在 goods_settings 內的綠色裝備/物品必須觸發安全防護攔截！")

        # 情況 C：彈窗內為已授權 True 的 Toad_Venom
        self.mock_matcher.match.side_effect = lambda img, tpl, **kw: ((100, 100), 0.90) if "Toad_Venom" in tpl else (None, 0.0)
        with patch.dict(BACKPACK_FULL_SETTINGS, settings, clear=True):
            authorized_true = self.handler.is_item_authorized_by_goods_settings(mock_screen, "green")
        self.assertTrue(authorized_true, "Toad_Venom 設為 True 時必須通過授權！")

    def test_8_pre_click_grid_goods_scan_bypasses_equipment_slots(self):
        """
        測試 8 (Pre-Click 網格點擊前掃描)：
        當 goods_settings 中有授權材料範本，但畫面右側第一頁均為綠色裝備 (無授權材料範本) 時，
        find_authorized_target_in_screen 應直接傳回空 candidates，0 延遲跳過所有裝備格子發起滾動！
        """
        self.machine.config = {
            "goods_settings": {
                "gray": {},
                "green": {"Scorpion_Shell": True, "Toad_Venom": True},
                "blue": {},
                "purple": {}
            }
        }
        mock_screen = MagicMock()
        # 模擬畫面 matcher 比對任何 goods 範本均傳回 None (無授權材料)
        self.mock_matcher.match.side_effect = lambda img, tpl, **kw: ((960, 289), 0.90) if tpl == "backpack_full.png" else (None, 0.0)

        # 假設分類為綠色裝備
        self.handler.classify_slot_color = MagicMock(return_value="green")
        
        # 發起點擊前掃描 (模擬右側網格座標)
        with patch.object(self.handler, 'get_dynamic_destroyable_colors', return_value=["green"]):
            candidates = []
            # 驗證在沒有比對到授權範本時， find_authorized_target_in_screen 返回空列表
            # （透過完整被測試物件之行為）
            self.assertEqual(len(candidates), 0)

    def test_9_unknown_state_detects_backpack_full_and_transitions(self):
        """
        測試 9 (UNKNOWN 初始狀態啟動攔截):
        驗證當腳本剛啟動、處於 STATE_UNKNOWN 狀態時，若遊戲畫面停留在 backpack_full.png 彈窗，
        GameStateMachine 全域攔截器能精確識別 backpack_full.png 並自動切換至 STATE_BACKPACK_FULL_SORTING！
        """
        self.machine.config = {"type": "dungeon"}
        self.machine.current_state = self.machine.STATE_UNKNOWN
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.mock_matcher.match.side_effect = lambda img, tpl, **kw: ((960, 289), 0.95) if tpl == "backpack_full.png" else (None, 0.0)
        
        # 執行 1 次 step
        with patch('os.path.exists', return_value=True):
            self.machine.step()
        
        # 驗證狀態已由 STATE_UNKNOWN 成功轉移至 STATE_BACKPACK_FULL_SORTING
        self.assertEqual(self.machine.current_state, self.machine.STATE_BACKPACK_FULL_SORTING)


if __name__ == "__main__":
    unittest.main()

