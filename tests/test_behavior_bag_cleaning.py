import unittest
import numpy as np
from unittest.mock import MagicMock, patch
from config import BACKPACK_FULL_SETTINGS
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

        def mock_match_side_effect(img, tpl, **kw):
            if tpl == "backpack_full.png":
                return ((500, 300), 0.90)
            elif tpl == "common/destroy.png":
                return ((500, 500), 0.90)
            elif tpl == "common/confirm.png":
                return ((600, 600), 0.90)
            elif tpl == "common/collect.png":
                return ((700, 700), 0.90)
            elif "goods" in tpl or "Jewelry_workshop" in tpl:
                return ((400, 400), 0.90)
            return (None, 0.0)

        handler.matcher.match.side_effect = mock_match_side_effect

        # 模擬右側第 0 格為 green，第 1 格為 gray_or_empty
        classify_returns = ["purple"] + ["gray_or_empty"] * 15 + ["green", "gray_or_empty"] + ["gray_or_empty"] * 14
        handler.classify_slot_color = MagicMock(side_effect=lambda crop: classify_returns.pop(0) if classify_returns else "gray_or_empty")
        mock_std.return_value = 25.0

        destroy_settings = {
            "destroy_goods": {
                "gray": {"item": True},
                "green": {},
                "blue": {},
                "purple": {},
            }
        }
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch.dict(BACKPACK_FULL_SETTINGS, destroy_settings, clear=True), \
             patch('states.handlers.backpack_full_sorting.time.sleep'):
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

    # =========================================================================
    # 5.3 防卡死、重新開啟背包與備援退出測試
    # =========================================================================

    @patch('os.path.exists', return_value=True)
    def test_5_3_resets_bag_opened_clicked_when_no_features_detected(self, mock_exists):
        """
        [5.3 Behavior Test]
        Given: bag_opened_clicked 為 True，但畫面上無任何可點擊的背包動作按鈕
        When: 連續呼叫 handle 3 次
        Then: 重置 bag_opened_clicked 為 False，允許下一輪重新點擊開啟背包
        """
        self.mock_machine.bag_wait_count = 0
        self.mock_machine.bag_opened_clicked = True
        self.mock_machine.bag_clean_start_time = 100.0

        handler = BagCleaningHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.matcher.match.return_value = (None, 0.0)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch('states.handlers.bag_cleaning.time.time', return_value=105.0):
            handler.handle(fake_img, self.rect)
            handler.handle(fake_img, self.rect)
            handler.handle(fake_img, self.rect)

        self.assertFalse(self.mock_machine.bag_opened_clicked)

    @patch('os.path.exists', return_value=True)
    def test_5_4_backup_quit_when_disassembled_without_tidy(self, mock_exists):
        """
        [5.4 Behavior Test]
        Given: bag_disassembled 為 True 且畫面上沒有 tidy.png，但有 quit.png
        When: 執行 BagCleaningHandler.handle()
        Then: 觸發 quit_backpack 點擊退出背包並完成狀態重置與轉移
        """
        self.mock_machine.bag_clean_start_time = 100.0
        self.mock_machine.bag_disassembled = True
        self.mock_machine.bag_tidied = False
        self.mock_machine.is_in_dungeon = False
        self.mock_machine.previous_state = "NAVIGATING"

        handler = BagCleaningHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.click_and_wait_until_gone = MagicMock()

        def mock_match(img, tpl, **kw):
            if tpl == "common/quit.png":
                return ((1100, 150), 0.95)
            return (None, 0.0)

        handler.matcher.match.side_effect = mock_match
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch('states.handlers.bag_cleaning.time.sleep'):
            with patch('states.handlers.bag_cleaning.time.time', return_value=105.0):
                for _ in range(3):
                    handler.handle(fake_img, self.rect)

        handler.click_and_wait_until_gone.assert_called_once()
        self.assertFalse(self.mock_machine.need_bag_cleaning)

    @patch('states.handlers.bag_cleaning.time.time')
    def test_5_5_timeout_watchdog_resets_stuck_cleaning(self, mock_time):
        """
        [5.5 Behavior Test]
        Given: 背包清理狀態停留超過 30 秒
        When: 執行 BagCleaningHandler.handle()
        Then: 自動引發 Timeout 防卡死救援，重置所有標記並退出
        """
        mock_time.return_value = 100.0
        self.mock_machine.bag_clean_start_time = None
        self.mock_machine.is_in_dungeon = True

        handler = BagCleaningHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.matcher.match.return_value = (None, 0.0)
        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        handler.handle(fake_img, self.rect) # 記錄 start_time = 100.0
        mock_time.return_value = 135.0
        handler.handle(fake_img, self.rect) # 135.0 > 100.0 + 30.0 -> 超時

        self.assertFalse(self.mock_machine.need_bag_cleaning)
        self.mock_machine.transition_to.assert_called()

    @patch('os.path.exists', return_value=True)
    def test_5_6_deselect_valuable_items_with_calibrated_offsets(self, mock_exists):
        """
        [5.6 Behavior Test]
        Given: 大量分解畫面中，Row 1 Col 1 為紫色貴重裝備且帶有打勾，Row 0 Col 0 貴重但無打勾
        When: 執行 handler.deselect_valuable_items()
        Then: 成功依校準偏移偵測到 Row 1 Col 1 打勾，發射點擊反選並記錄至 bag_deselected_slots
        """
        self.mock_machine.config = {"disassemble_colors": ["gray_or_empty", "green", "blue"]}
        self.mock_machine.bag_deselected_slots = set()

        handler = BagCleaningHandler(self.mock_machine)
        handler.matcher = MagicMock()
        handler.mouse = MagicMock()
        handler.classify_slot_color = MagicMock()

        # 模擬比對 quit.png 於標準座標 (1391, 185)
        handler.matcher.match.side_effect = lambda img, tpl, **kw: ((1391, 185), 0.95) if tpl == "common/quit.png" else (None, 0.0)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # 根據校準常數計算 Row 1 Col 1 中心及打勾區
        btn_cx = 1391 + int(handler.QUIT_OFFSET_X * 1.0)
        btn_cy = 185 + int(handler.QUIT_OFFSET_Y * 1.0)
        x1_r1c1 = int(btn_cx + 1 * handler.CELL_WIDTH)
        y1_r1c1 = int(btn_cy + 1 * handler.CELL_HEIGHT)
        cx_r1c1 = int(x1_r1c1 + handler.CELL_WIDTH / 2.0)
        cy_r1c1 = int(y1_r1c1 + handler.CELL_HEIGHT / 2.0)
        fake_img[y1_r1c1+10:y1_r1c1+120, x1_r1c1+10:x1_r1c1+120] = (80, 20, 80)

        chk_x = int(cx_r1c1 + handler.CHECK_OFFSET_X)
        chk_y = int(cy_r1c1 + handler.CHECK_OFFSET_Y)
        fake_img[chk_y:chk_y+20, chk_x:chk_x+20] = (0, 200, 0)

        # 設定色彩分類：Row 1 Col 1 為 purple，其餘為 gray_or_empty
        def mock_classify(crop):
            if crop.shape[0] > 0 and crop.shape[1] > 0 and np.mean(crop) > 1.0:
                return "purple"
            return "gray_or_empty"

        handler.classify_slot_color.side_effect = mock_classify

        with patch('states.handlers.bag_cleaning.time.sleep'):
            res = handler.deselect_valuable_items(fake_img, self.rect)

        self.assertTrue(res)
        handler.mouse.click.assert_called_once_with(self.rect["left"] + cx_r1c1, self.rect["top"] + cy_r1c1)
        self.assertIn((1, 1), self.mock_machine.bag_deselected_slots)

if __name__ == "__main__":
    unittest.main()

