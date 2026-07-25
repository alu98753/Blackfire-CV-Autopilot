import os
import time
import unittest
from unittest.mock import MagicMock, patch
from states.handlers.chest import ChestHandler
from utils.daily_manager import DailyManager, DEFAULT_DAILY_STATUS

class TestChestSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "name": "神秘寶箱",
            "type": "chest",
            "building_btn": "town_building/mysterious_treasure/mysterious_treasure.png"
        }
        self.mock_machine.capturer = MagicMock()
        self.mock_machine.matcher = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.mock_daily_manager = MagicMock()
        self.mock_machine.daily_manager = self.mock_daily_manager
        
        self.handler = ChestHandler(self.mock_machine)

    def test_handler_return_to_town_when_in_lobby(self):
        """測試：當畫面在大廳 (視角有 goback_town.png) 時，自動點擊返回城鎮"""
        mock_img = MagicMock()
        rect = {"left": 100, "top": 100, "width": 800, "height": 600}
        
        self.mock_machine.matcher.match.side_effect = lambda img, template, threshold=0.8: (
            (50, 50), 0.90) if template == "goback_town.png" else (None, 0.0)

        result = self.handler.handle(mock_img, rect)
        self.assertTrue(result)
        self.mock_machine.mouse.click.assert_called_once_with(150, 150)

    def test_handler_claims_chest_when_found(self):
        """測試：Step 1 點擊寶箱建築 ➔ Step 2 點擊免費寶箱 ➔ Step 3 確認彈窗並記錄完成"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "goback_town.png":
                return (None, 0.0)
            if template == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 300), 0.88)
            if template == "town_building/mysterious_treasure/free_treasure.png":
                return ((400, 500), 0.90)
            if template == "common/confirm.png":
                return ((400, 550), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            # Step 1: INIT ➔ CLICK_FREE_CHEST
            res1 = self.handler.handle(mock_img, rect)
            self.assertTrue(res1)
            self.assertEqual(self.handler.step_phase, "CLICK_FREE_CHEST")

            # Step 2: CLICK_FREE_CHEST ➔ WAITING_CONFIRM
            self.handler.last_action_time = 0.0
            res2 = self.handler.handle(mock_img, rect)
            self.assertTrue(res2)
            self.assertEqual(self.handler.step_phase, "WAITING_CONFIRM")

            # Step 3: WAITING_CONFIRM ➔ Complete
            self.handler.last_action_time = 0.0
            res3 = self.handler.handle(mock_img, rect)
            self.assertTrue(res3)
            self.mock_daily_manager.record_subflow_completed.assert_called_with("chest")
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_handler_pops_subflow_when_chest_not_found(self):
        """測試：當連續 5 輪未發現寶箱建築時，標記完成並呼叫 pop_and_next_town_subflow()"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        self.mock_machine.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            for _ in range(4):
                self.handler.handle(mock_img, rect)
                self.handler.last_action_time = 0.0
            res_last = self.handler.handle(mock_img, rect)

        self.assertTrue(res_last)
        self.mock_daily_manager.record_subflow_completed.assert_called_with("chest")
        self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_daily_manager_chest_completion_and_reset(self):
        """測試：DailyManager 正確記錄 chest 完成狀態並可於 08:30 重置"""
        test_dir = "scratch/test_user_data"
        dm = DailyManager(data_dir=test_dir, status_file="test_chest_daily.json")
        
        self.assertFalse(dm.is_subflow_completed("chest"))
        
        dm.record_subflow_completed("chest")
        self.assertTrue(dm.is_subflow_completed("chest"))

        # 模擬跨越 08:30 重置
        dm.status["last_daily_reset_date"] = "2026-01-01"
        dm.next_reset_timestamp = time.time() - 10
        dm.check_and_reset_daily(force=True)

        self.assertFalse(dm.is_subflow_completed("chest"))

        # 清理測試暫存檔
        if os.path.exists(dm.file_path):
            os.remove(dm.file_path)

if __name__ == "__main__":
    unittest.main()
