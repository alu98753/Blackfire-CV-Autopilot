import os
import time
import unittest
import numpy as np
from unittest.mock import MagicMock, patch
from states.handlers.chest import (
    ChestHandler,
    CHEST_DEFER_SECONDS,
    CHEST_BUILDING_TEMPLATE,
    CHEST_DIALOG_TEMPLATE,
    CHEST_FREE_BTN_TEMPLATE,
    CHEST_CONFIRM_TEMPLATES,
    CHEST_QUIT_TEMPLATES,
    CHEST_GOBACK_TOWN_TEMPLATE,
)
from utils.daily_manager import DailyManager


class TestChestSubflow(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {
            "name": "神秘寶箱",
            "type": "chest",
            "building_btn": CHEST_BUILDING_TEMPLATE,
        }
        self.mock_machine.capturer = MagicMock()
        self.mock_machine.matcher = MagicMock()
        self.mock_machine.mouse = MagicMock()
        self.mock_machine.is_dev_subflow_run = False
        self.mock_daily_manager = MagicMock()
        self.mock_machine.daily_manager = self.mock_daily_manager
        
        # 防止單元測試將全黑 dummy 矩陣寫入真實 scratch/debug 磁碟檔案
        patcher = patch("states.debug.visualizer.DebugVisualizer.draw_detection")
        self.mock_draw_detection = patcher.start()
        self.addCleanup(patcher.stop)

        self.handler = ChestHandler(self.mock_machine)

    def test_handler_return_to_town_when_in_lobby(self):
        """測試：當畫面在大廳 (視角有 goback_town.png) 時，自動點擊返回城鎮"""
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 100, "top": 100, "width": 800, "height": 600}
        
        self.mock_machine.matcher.match.side_effect = lambda img, template, threshold=0.8: (
            (50, 50), 0.90) if template == CHEST_GOBACK_TOWN_TEMPLATE else (None, 0.0)

        result = self.handler.handle(mock_img, rect)
        self.assertTrue(result)
        self.mock_machine.mouse.click.assert_called_once_with(150, 150)

    def test_handler_claims_chest_full_pipeline(self):
        """
        測試完整神秘寶箱領取管線：
        Step 1 (INIT，有紅點) ➔ Step 2 (CLICK_FREE_CHEST，點擊 free.png)
        ➔ Step 3 (WAITING_CONFIRM，點擊 confirm.png)
        ➔ Step 4 (VERIFY_CLAIM_SUCCESS，free.png 消失，確認完成)
        ➔ Step 5 (WAITING_QUIT，點擊 quit.png)
        ➔ Step 6 (VERIFY_EXIT，回到城鎮切換下一任務)
        """
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        def fake_match(img, template, threshold=0.75, **kwargs):
            if kwargs.get("quiet"):
                return (None, 0.0)
            if template == CHEST_GOBACK_TOWN_TEMPLATE:
                return (None, 0.0)
            if template == CHEST_BUILDING_TEMPLATE:
                return ((200, 300), 0.88)
            if template == "town_building/red_dot.png":
                return ((200, 380), 0.85)
            if template == CHEST_DIALOG_TEMPLATE:
                return ((400, 400), 0.92)
            if template == CHEST_FREE_BTN_TEMPLATE:
                # 在 CLICK_FREE_CHEST 階段存在
                return ((400, 500), 0.90)
            if template in CHEST_CONFIRM_TEMPLATES:
                return ((400, 550), 0.85)
            if template in CHEST_QUIT_TEMPLATES:
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

            # Step 3: WAITING_CONFIRM ➔ VERIFY_CLAIM_SUCCESS
            self.handler.last_action_time = 0.0
            res3 = self.handler.handle(mock_img, rect)
            self.assertTrue(res3)
            self.assertEqual(self.handler.step_phase, "VERIFY_CLAIM_SUCCESS")

            # Step 4: VERIFY_CLAIM_SUCCESS ➔ 模擬 free.png 已消失 (Postcondition 成立)
            def fake_match_verified(img, template, threshold=0.75, **kwargs):
                if template == CHEST_GOBACK_TOWN_TEMPLATE:
                    return (None, 0.0)
                if template == CHEST_FREE_BTN_TEMPLATE:
                    return (None, 0.0)  # free 按鈕消失！
                if template == "common/quit.png":
                    return ((100, 100), 0.80)
                return (None, 0.0)

            self.mock_machine.matcher.match.side_effect = fake_match_verified
            self.handler.last_action_time = 0.0
            res4 = self.handler.handle(mock_img, rect)
            self.assertTrue(res4)
            self.assertEqual(self.handler.step_phase, "WAITING_QUIT")
            self.mock_daily_manager.record_subflow_completed.assert_called_with("chest")

            # Step 5: WAITING_QUIT ➔ 點擊 quit 退出建築 ➔ VERIFY_EXIT
            self.handler.last_action_time = 0.0
            res5 = self.handler.handle(mock_img, rect)
            self.assertTrue(res5)
            self.assertEqual(self.handler.step_phase, "VERIFY_EXIT")

            # Step 6: VERIFY_EXIT ➔ 回到城鎮，切換下一個子流程
            def fake_match_town(img, template, threshold=0.75, **kwargs):
                if template == CHEST_BUILDING_TEMPLATE:
                    return ((200, 300), 0.88)
                return (None, 0.0)

            self.mock_machine.matcher.match.side_effect = fake_match_town
            self.handler.last_action_time = 0.0
            res6 = self.handler.handle(mock_img, rect)
            self.assertTrue(res6)
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()

    def test_init_precheck_defers_when_no_red_dot(self):
        """
        測試：進入前預檢 (INIT 階段發現建築無紅點)
        - 斷言：必須調用 defer_subflow("chest", 180) 暫緩冷卻！
        - 關鍵防護：絕對不得呼叫 record_subflow_completed！
        """
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler.step_phase = "INIT"

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == CHEST_BUILDING_TEMPLATE:
                return ((200, 300), 0.88)
            # 無紅點
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        with patch("os.path.exists", return_value=True):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            # 斷言：必須暫緩退避，嚴禁誤標記完成
            self.mock_daily_manager.defer_subflow.assert_called_once_with("chest", CHEST_DEFER_SECONDS)
            self.mock_daily_manager.record_subflow_completed.assert_not_called()
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()
            # 斷言未點擊建築
            self.mock_machine.mouse.click.assert_not_called()

    def test_claim_failed_when_free_button_persists_triggers_defer(self):
        """
        測試：領取後 Postcondition 失敗
        - 情境：點擊確認彈窗後進入 VERIFY_CLAIM_SUCCESS，但連續檢測 free.png 依然存在 (點擊未生效)。
        - 斷言：判定失敗，觸發 defer_subflow("chest", 180)，絕對不得標記完成。
        """
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler.step_phase = "VERIFY_CLAIM_SUCCESS"

        def fake_match(img, template, threshold=0.70, **kwargs):
            if template == CHEST_FREE_BTN_TEMPLATE:
                return ((400, 500), 0.88)  # free.png 仍然存在！
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        with patch("os.path.exists", return_value=True):
            # 模擬連續 3 次檢測失敗
            for _ in range(2):
                self.handler.handle(mock_img, rect)
                self.handler.last_action_time = 0.0
            res = self.handler.handle(mock_img, rect)

            self.assertTrue(res)
            self.assertEqual(self.handler.step_phase, "WAITING_QUIT")
            self.mock_daily_manager.defer_subflow.assert_called_once_with("chest", CHEST_DEFER_SECONDS)
            self.mock_daily_manager.record_subflow_completed.assert_not_called()

    def test_handler_pops_subflow_when_chest_not_found(self):
        """連續找不到已驗證過的入口時必須 defer，不能靜默遺失任務。"""
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        self.mock_machine.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            for _ in range(4):
                self.handler.handle(mock_img, rect)
                self.handler.last_action_time = 0.0
            res_last = self.handler.handle(mock_img, rect)

        self.assertTrue(res_last)
        self.mock_daily_manager.record_subflow_completed.assert_not_called()
        self.mock_daily_manager.defer_subflow.assert_called_once_with(
            "chest", CHEST_DEFER_SECONDS
        )
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

    def test_click_free_chest_uses_exact_free_coordinates(self):
        """測試：CLICK_FREE_CHEST 採用卡片底部 30% Scoped ROI 精確比對 free.png，無猜測 fallback 座標"""
        mock_img = np.zeros((793, 1536, 3), dtype=np.uint8)
        rect = {"left": 10, "top": 20, "width": 1536, "height": 793}
        self.handler.step_phase = "CLICK_FREE_CHEST"

        captured_crops = []
        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == CHEST_DIALOG_TEMPLATE:
                return ((500, 400), 0.96)
            if template == CHEST_FREE_BTN_TEMPLATE:
                captured_crops.append(img.shape)
                # 模擬在底部 30% ROI 內匹配到 (200, 75)
                return ((200, 75), 0.93)
            return (None, 0.0)

        self.mock_machine.matcher._compute_auto_scale.return_value = 1.0
        self.mock_machine.matcher.match.side_effect = fake_match

        with patch("os.path.exists", return_value=True), \
             patch("cv2.imread", return_value=np.zeros((350, 400, 3), dtype=np.uint8)):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            self.mock_machine.click_and_wait_until_gone.assert_called_once()
            args, _ = self.mock_machine.click_and_wait_until_gone.call_args
            # target template 必須是 free.png
            self.assertEqual(args[0], CHEST_FREE_BTN_TEMPLATE)
            # 斷言搜尋區域是底部 30% (高度 350 - int(350*0.7) = 105)
            self.assertTrue(any(shape[0] == 105 for shape in captured_crops))
            # x = left(10) + x1(300) + pos_sub_free_x(200) = 510
            # y = top(20) + y1(225) + btn_roi_y_start(245) + pos_sub_free_y(75) = 565
            self.assertEqual(args[1], 510)
            self.assertEqual(args[2], 565)


    def test_init_dev_mode_forces_entry_when_no_red_dot(self):
        """測試：Dev 測試模式下 (is_dev_subflow_run=True)，即使無紅點也強制點擊進入建築"""
        mock_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler.step_phase = "INIT"
        self.mock_machine.is_dev_subflow_run = True

        def fake_match(img, template, threshold=0.75, **kwargs):
            if template == CHEST_BUILDING_TEMPLATE:
                return ((200, 300), 0.88)
            # 無紅點
            return (None, 0.0)

        self.mock_machine.matcher.match.side_effect = fake_match
        with patch("os.path.exists", return_value=True):
            res = self.handler.handle(mock_img, rect)
            self.assertTrue(res)
            # 斷言：Dev 模式強制進入，轉入 CLICK_FREE_CHEST，且不得 defer
            self.assertEqual(self.handler.step_phase, "CLICK_FREE_CHEST")
            self.mock_daily_manager.defer_subflow.assert_not_called()
            self.mock_machine.mouse.click.assert_called_once_with(200, 300)


if __name__ == "__main__":
    unittest.main()
