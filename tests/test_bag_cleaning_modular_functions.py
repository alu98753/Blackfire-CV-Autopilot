import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from states.handlers.bag_cleaning import BagCleaningHandler


class TestBagCleaningModularFunctions(unittest.TestCase):
    """
    BagCleaningHandler 模組化 Function 獨立單元測試套件
    驗證每個拆分出來的成員函數 (open_backpack, tidy_backpack, quit_backpack 等) 均可單獨正確呼叫與運作。
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.STATE_DUNGEON_EXPLORING = "DUNGEON_EXPLORING"
        self.mock_machine.STATE_BAG_CLEANING = "BAG_CLEANING"
        self.mock_machine.config = {"disassemble_colors": ["gray_or_empty", "green"]}

        self.handler = BagCleaningHandler(self.mock_machine)
        self.handler.matcher = MagicMock()
        self.handler.mouse = MagicMock()
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    def test_1_open_backpack_standalone(self):
        """測試獨立呼叫 open_backpack 能正確比對文字並點擊開啟背包"""
        self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((500, 300), 0.95) if tpl == "common/bag_text.png" else (None, 0.0)

        res = self.handler.open_backpack(self.fake_img, self.rect)

        self.assertTrue(res)
        self.assertTrue(self.mock_machine.bag_opened_clicked)
        self.handler.mouse.click.assert_called_once()

    def test_2_enter_mass_disassembly_standalone(self):
        """測試獨立呼叫 enter_mass_disassembly 能正確點擊大量分解按鈕"""
        with patch("os.path.exists", return_value=True):
            self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((600, 400), 0.90) if tpl == "common/Backpack_Disassembly.png" else (None, 0.0)

            res = self.handler.enter_mass_disassembly(self.fake_img, self.rect)

            self.assertTrue(res)
            self.handler.mouse.click.assert_called_once_with(600, 400)

    def test_3_select_all_items_standalone(self):
        """測試獨立呼叫 select_all_items 能正確點擊全選並初始化標記"""
        with patch("os.path.exists", return_value=True):
            self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((400, 700), 0.88) if tpl == "common/select_all.png" else (None, 0.0)

            res = self.handler.select_all_items(self.fake_img, self.rect)

            self.assertTrue(res)
            self.assertTrue(self.mock_machine.bag_select_all_clicked)
            self.assertEqual(self.mock_machine.bag_deselected_slots, set())

    def test_4_execute_disassembly_standalone(self):
        """測試獨立呼叫 execute_disassembly 能正確點擊分解按鈕"""
        with patch("os.path.exists", return_value=True):
            self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((800, 700), 0.85) if tpl == "common/Disassembly.png" else (None, 0.0)

            res = self.handler.execute_disassembly(self.fake_img, self.rect)

            self.assertTrue(res)
            self.assertTrue(self.mock_machine.bag_disassembled)

    def test_5_confirm_popups_standalone(self):
        """測試獨立呼叫 confirm_popups 能正確點擊確認彈窗"""
        self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((700, 500), 0.92) if tpl == "common/confirm.png" else (None, 0.0)

        res = self.handler.confirm_popups(self.fake_img, self.rect)

        self.assertTrue(res)
        self.assertTrue(self.mock_machine.bag_disassembled)

    def test_6_tidy_backpack_standalone(self):
        """測試獨立呼叫 tidy_backpack 能正確點擊整理按鈕"""
        with patch("os.path.exists", return_value=True):
            self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((300, 800), 0.91) if tpl == "common/tidy.png" else (None, 0.0)

            res = self.handler.tidy_backpack(self.fake_img, self.rect)

            self.assertTrue(res)
            self.assertTrue(self.mock_machine.bag_tidied)

    def test_7_quit_backpack_standalone(self):
        """測試獨立呼叫 quit_backpack 能點擊退出按鈕並觸發重置與流水線"""
        with patch("os.path.exists", return_value=True), \
             patch.object(self.handler, "click_and_wait_until_gone") as mock_wait:
            self.handler.matcher.match.side_effect = lambda img, tpl, **kw: ((900, 100), 0.90) if tpl == "common/quit.png" else (None, 0.0)
            self.mock_machine.is_in_dungeon = False
            self.mock_machine.config = {"type": "stage"}

            res = self.handler.quit_backpack(self.fake_img, self.rect)

            self.assertTrue(res)
            mock_wait.assert_called_once()
            self.assertFalse(self.mock_machine.need_bag_cleaning)
            self.mock_machine.trigger_town_subflow_chain.assert_called_once()


if __name__ == "__main__":
    unittest.main()
