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
        """測試：Step 1 點擊寶箱建築 ➔ Step 2 點擊免費寶箱 ➔ Step 3 確認彈窗 ➔ Step 4 退出並記錄完成"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        def fake_match(img, template, threshold=0.75, **kwargs):
            if kwargs.get("quiet"):
                return (None, 0.0)
            if template == "goback_town.png":
                return (None, 0.0)
            if template == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 300), 0.88)
            if template == "town_building/red_dot.png":
                # 在 INIT 階段有紅點
                return ((200, 380), 0.85)
            if template == "town_building/mysterious_treasure/free_treasure.png":
                return ((400, 400), 0.92)
            if template == "free.png":
                return ((400, 500), 0.90)
            if template == "common/confirm.png":
                return ((400, 550), 0.85)
            if template == "common/quit.png":
                return ((100, 100), 0.80)
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True):
            # Step 1: INIT ➔ 發現建築與紅點 ➔ 點擊進入 ➔ CLICK_FREE_CHEST
            res1 = self.handler.handle(mock_img, rect)
            self.assertTrue(res1)
            self.assertEqual(self.handler.step_phase, "CLICK_FREE_CHEST")

            # Step 2: CLICK_FREE_CHEST ➔ WAITING_CONFIRM
            self.handler.last_action_time = 0.0
            res2 = self.handler.handle(mock_img, rect)
            self.assertTrue(res2)
            self.assertEqual(self.handler.step_phase, "WAITING_CONFIRM")

            # Step 3: WAITING_CONFIRM ➔ WAITING_QUIT
            self.handler.last_action_time = 0.0
            res3 = self.handler.handle(mock_img, rect)
            self.assertTrue(res3)
            self.assertEqual(self.handler.step_phase, "WAITING_QUIT")

            # Step 4: WAITING_QUIT ➔ 點擊 quit 退出建築 ➔ VERIFY_EXIT
            self.handler.last_action_time = 0.0
            res4 = self.handler.handle(mock_img, rect)
            self.assertTrue(res4)
            self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

            # Step 5: VERIFY_EXIT ➔ 模擬退回城鎮後紅點已消除 (沒檢查到紅點)
            def fake_match_verified(img, template, threshold=0.75, **kwargs):
                if template == "town_building/mysterious_treasure/mysterious_treasure.png":
                    return ((200, 300), 0.88)
                # 紅點已消失
                return (None, 0.0)

            self.mock_machine.matcher.match.side_effect = fake_match_verified
            self.handler.last_action_time = 0.0
            res5 = self.handler.handle(mock_img, rect)
            self.assertTrue(res5)
            self.mock_daily_manager.record_subflow_completed.assert_called_with("chest")
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_verify_exit_with_red_dot_still_present(self):
        """測試：退出後再次檢查紅點 (有檢查到紅點 ➔ 判定未完成領取，不呼叫 record_subflow_completed)"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler.step_phase = "VERIFY_EXIT"

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 300), 0.88)
            if template == "town_building/red_dot.png":
                return ((200, 380), 0.85)  # 仍然有紅點！
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        with patch("os.path.exists", return_value=True):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            # 斷言：絕對不得標記完成！
            self.mock_daily_manager.record_subflow_completed.assert_not_called()
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_init_precheck_skips_when_no_red_dot(self):
        """測試：進入前預檢 (INIT 階段發現建築無紅點 ➔ 判定今日已領過，直接標記完成並跳過)"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler.step_phase = "INIT"

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "town_building/mysterious_treasure/mysterious_treasure.png":
                return ((200, 300), 0.88)
            # 無紅點
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        with patch("os.path.exists", return_value=True):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            self.mock_daily_manager.record_subflow_completed.assert_called_with("chest")
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()
            # 斷言未點擊建築
            self.mock_machine.mouse.click.assert_not_called()

    def test_handler_pops_subflow_when_chest_not_found(self):
        """測試：當連續 5 輪未發現寶箱建築時，彈出下一個任務（絕不標記完成）"""
        mock_img = MagicMock()
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        self.mock_machine.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            for _ in range(4):
                self.handler.handle(mock_img, rect)
                self.handler.last_action_time = 0.0
            res_last = self.handler.handle(mock_img, rect)

        self.assertTrue(res_last)
        # 斷言：找不到建築時，絕對不可標記完成！
        self.mock_daily_manager.record_subflow_completed.assert_not_called()
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

    def test_click_free_chest_scale_passing_and_coordinates(self):
        """測試：CLICK_FREE_CHEST 正確傳遞 screen_scale 進行局部 free.png 匹配並計算正確點擊座標"""
        mock_img = MagicMock()
        mock_img.shape = (793, 1536, 3)
        rect = {"left": 0, "top": 0, "width": 1536, "height": 793}
        self.handler.step_phase = "CLICK_FREE_CHEST"

        recorded_scales = []
        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == "town_building/mysterious_treasure/free_treasure.png":
                return ((556, 405), 0.96)
            if template == "free.png":
                recorded_scales.append(kwargs.get("scale"))
                return ((209, 333), 0.93)
            return (None, 0.0)

        self.mock_machine.matcher._compute_auto_scale.return_value = 0.8
        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True), \
             patch("cv2.imread", return_value=MagicMock(shape=(477, 537, 3))):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            self.assertIn(0.8, recorded_scales)
            self.mock_machine.click_and_wait_until_gone.assert_called_once()
            args, _ = self.mock_machine.click_and_wait_until_gone.call_args
            self.assertEqual(args[0], "free.png")
            self.assertEqual(args[1], 551)
            self.assertEqual(args[2], 548)

if __name__ == "__main__":
    unittest.main()

