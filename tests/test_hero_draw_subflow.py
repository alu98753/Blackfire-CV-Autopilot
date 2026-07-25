import os
import time
import unittest
from unittest.mock import MagicMock, patch
from states.handlers.hero_draw import HeroDrawHandler
from utils.daily_manager import DailyManager

class TestHeroDrawSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "name": "抽英雄",
            "type": "hero_draw",
            "building_btn": "town_building/Tavern/Tavern.png",
            "recruitment_btn": "town_building/Tavern/free_recruitment.png"
        }
        self.mock_machine.capturer = MagicMock()
        self.mock_machine.matcher = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.mock_daily_manager = MagicMock()
        self.mock_machine.daily_manager = self.mock_daily_manager
        
        self.handler = HeroDrawHandler(self.mock_machine)

    def test_handler_return_to_town_when_in_lobby(self):
        """測試：當畫面在大廳 (看得到 goback_town.png) 時，點擊返回城鎮"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        
        self.mock_machine.matcher.match.side_effect = lambda img, template, threshold=0.8: (
            (100, 100), 0.90) if template == "goback_town.png" else (None, 0.0)

        result = self.handler.handle(mock_img, rect)
        self.assertTrue(result)
        self.mock_machine.mouse.click.assert_called_once_with(100, 100)

    def test_handler_starts_already_inside_tavern(self):
        """測試：當一開始就處於酒館內部 (看得到 free_recruitment.png / exitfromhouse_and_to_town.png) 時，自動辨識並切換至 ENTERED_TAVERN"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return ((500, 500), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        res = self.handler.handle(mock_img, rect)
        self.assertTrue(res)
        self.assertEqual(self.handler.step_phase, "ENTERED_TAVERN")

    def test_handler_full_recruitment_flow(self):
        """測試：完整的進入酒館 ➔ 免費招募 ➔ 點擊招募 (RECRUITED.png) ➔ 點擊確認 ➔ 點擊退出 ➔ 寫入 DailyManager"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        def fake_match(img, template, threshold=0.75, *args, **kwargs):
            if template == "town_building/Tavern/Tavern.png":
                return ((200, 200), 0.85)
            if template == "town_building/Tavern/free_recruitment.png":
                return ((300, 300), 0.85)
            if template == "town_building/Tavern/RECRUITED.png":
                return ((350, 350), 0.85)
            if template in ["common/confirm.png", "common/ok.png"]:
                return ((400, 400), 0.85)
            if template in ["common/quit.png", "town_building/exitfromhouse_and_to_town.png"]:
                return ((500, 500), 0.85)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            # 1. Step 1: INIT 點擊 Tavern.png
            res1 = self.handler.handle(mock_img, rect)
            self.assertTrue(res1)
            self.assertEqual(self.handler.step_phase, "ENTERED_TAVERN")
            self.mock_machine.mouse.click.assert_called_with(200, 200)

            # 2. Step 2: ENTERED_TAVERN 點擊 free_recruitment.png
            self.handler.last_action_time = 0.0
            res2 = self.handler.handle(mock_img, rect)
            self.assertTrue(res2)
            self.assertEqual(self.handler.step_phase, "CLICKED_FREE_RECRUITMENT")
            self.mock_machine.mouse.click.assert_called_with(300, 300)

            # 3. Step 3: CLICKED_FREE_RECRUITMENT 點擊 RECRUITED.png (專用「招募」按鈕)
            self.handler.last_action_time = 0.0
            res3 = self.handler.handle(mock_img, rect)
            self.assertTrue(res3)
            self.assertEqual(self.handler.step_phase, "WAITING_CONFIRM")
            self.mock_machine.mouse.click.assert_called_with(350, 350)

            # 4. Step 4: WAITING_CONFIRM 點擊 confirm.png
            self.handler.last_action_time = 0.0
            res4 = self.handler.handle(mock_img, rect)
            self.assertTrue(res4)
            self.assertEqual(self.handler.step_phase, "ALL_DONE_EXITING")

            # 5. Step 5: ALL_DONE_EXITING 點擊 quit.png 退出並彈出下一任務
            self.handler.last_action_time = 0.0
            res5 = self.handler.handle(mock_img, rect)
            self.assertTrue(res5)
            self.mock_daily_manager.record_subflow_completed.assert_called_with("hero_draw")
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_daily_manager_hero_draw_completion_and_reset(self):
        """測試：DailyManager 正確記錄 hero_draw 完成狀態並於 08:05 重置"""
        test_dir = "scratch/test_user_data"
        dm = DailyManager(data_dir=test_dir, status_file="test_hero_draw_daily.json")
        
        self.assertFalse(dm.is_subflow_completed("hero_draw"))
        
        dm.record_subflow_completed("hero_draw")
        self.assertTrue(dm.is_subflow_completed("hero_draw"))

        # 模擬跨越 08:05 重置
        dm.status["last_daily_reset_date"] = "2026-01-01"
        dm.next_reset_timestamp = time.time() - 10
        dm.check_and_reset_daily(force=True)

        self.assertFalse(dm.is_subflow_completed("hero_draw"))

        if os.path.exists(dm.file_path):
            os.remove(dm.file_path)

if __name__ == "__main__":
    unittest.main()
