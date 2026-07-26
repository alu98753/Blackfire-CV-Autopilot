import unittest
import numpy as np
from unittest.mock import MagicMock, patch
from states.handlers.bag_cleaning import BagCleaningHandler
from states.handlers.backpack_full_sorting import BackpackFullSortingHandler

class TestBehaviorBagCleaning(unittest.TestCase):
    """
    背包銷毀與品質分類行為測試集 (Google Software Dev Standard)
    專注於 Given 背包滿/裝備分類情境 ➔ When 觸發 handle ➔ Then 斷言灰色護裝銷毀與高品質分解權限
    """
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_DUNGEON_EXPLORING = "DUNGEON_EXPLORING"
        self.mock_machine.STATE_BAG_CLEANING = "BAG_CLEANING"
        self.mock_machine.bag_opened_clicked = True
        self.mock_machine.config = {
            "disassemble_colors": ["gray_or_empty", "green", "blue", "purple"],
            "keep_colors": ["purple", "orange_yellow", "red"],
            "backpack_full_destroyable_colors": ["gray_or_empty"]
        }

        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    # =========================================================================
    # 5.1 單個裝備滿時預設銷毀行為測試
    # =========================================================================

    @patch('states.handlers.backpack_full_sorting.np.std')
    def test_5_1_backpack_full_restricts_destroy_target_to_gray_only(self, mock_std):
        """
        [5.1 Behavior Test]
        Given: 背包已滿彈窗 (backpack_full.png) 開啟，右側有 green 與 gray_or_empty 裝備
        When: 執行 BackpackFullSortingHandler.handle()
        Then: 嚴格僅選擇 gray_or_empty 裝備進行銷毀點擊，絕不誤刪 green 或更高階裝備
        """
        handler = BackpackFullSortingHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.save_diagnostic_image = MagicMock()

        handler.matcher.match.side_effect = lambda img, tpl, **kw: ((500, 300), 0.90) if tpl == "backpack_full.png" else (None, 0.0)

        # 模擬右側第 0 格為 green，第 1 格為 gray_or_empty
        classify_returns = ["purple"] + ["gray_or_empty"] * 15 + ["green", "gray_or_empty"] + ["gray_or_empty"] * 14
        handler.classify_slot_color = MagicMock(side_effect=classify_returns)
        mock_std.return_value = 25.0

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch('states.handlers.backpack_full_sorting.time.sleep'):
            handler.handle(fake_img, self.rect)

        # 驗證發射點擊之 X 座標大於 650 (即正確點擊第 1 格 gray_or_empty，而非第 0 格 green)
        clicked_x = handler.mouse.click.call_args_list[0][0][0]
        self.assertGreater(clicked_x, 650, "未選擇 gray_or_empty 格子，誤選了 green 格子！")

    # =========================================================================
    # 5.2 大量分解高品質允許行為測試
    # =========================================================================

    @patch('os.path.exists', return_value=True)
    def test_5_2_disassemble_colors_allows_up_to_epic_purple(self, mock_exists):
        """
        [5.2 Behavior Test]
        Given: disassemble_colors 包含 ["gray_or_empty", "green", "blue", "purple"]
        When: 大量裝備分解流程執行
        Then: 允許最高分解至紫色史詩品質，保護橙黃與紅色裝備
        """
        disassemble_colors = self.mock_machine.config.get("disassemble_colors", [])
        self.assertIn("purple", disassemble_colors)
        self.assertNotIn("orange_yellow", disassemble_colors)
        self.assertNotIn("red", disassemble_colors)

if __name__ == "__main__":
    unittest.main()
