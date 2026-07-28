import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time

from states.handlers.jewelry_workshop import JewelryWorkshopHandler


class TestBehaviorJewelryStuck(unittest.TestCase):
    """
    珠寶加工廠出售長途流程與卡死防護行為單元測試套件
    
    測試重點：
    1. 驗證 JewelryWorkshopHandler 在進行有效滑動/點擊/出售商品時，會主動呼叫 machine.notify_ui_progress()，
       刷新 last_state_change，確保長途出售商品不會被 30 秒 Watchdog 誤判卡死。
    2. 驗證當從 Popup Recovery 復原後若畫面上已在城鎮 (common/door.png 可見)，
       JewelryWorkshopHandler 會觸發 Scene Guard 防護攔截，重置狀態並調用 pop_and_next_town_subflow()，
       絕不卡在 exitfromhouse_and_to_town.png 死迴圈中。
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_machine.config = {"type": "jewelry_workshop"}
        self.mock_machine.last_state_change = time.time()
        self.handler = JewelryWorkshopHandler(self.mock_machine)

    def test_jewelry_workshop_calls_notify_ui_progress_on_drag(self):
        """[NotifyProgress] 驗證在商品搜尋與滑動過程，主動呼叫 notify_ui_progress()"""
        dummy_screen = np.zeros((500, 500, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 500, "height": 500}

        self.handler.step_phase = "SELL_MENU_OPEN"
        self.handler.goods_scroll_state = "TOP"

        with patch.object(self.handler, "_get_enabled_goods", return_value=["test_item"]):
            with patch.object(self.handler.matcher, "match", return_value=(None, 0.0)):
                with patch.object(self.handler.mouse, "drag"):
                    with patch("os.path.exists", return_value=True):
                        with patch("time.sleep"):
                            self.handler.handle(dummy_screen, rect)

                            # 斷言 1: 觸發向下拖曳
                            self.assertEqual(self.handler.goods_scroll_state, "SCROLLED_DOWN")
                            # 斷言 2: 呼叫 notify_ui_progress 重置 stuck 狀態
                            self.mock_machine.notify_ui_progress.assert_called()

    def test_jewelry_workshop_scene_guard_when_already_in_town(self):
        """[SceneGuard] 驗證若在 SELL_MENU_OPEN 階段畫面上已看見 common/door.png，自動結算離場"""
        dummy_screen = np.zeros((500, 500, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0}

        self.handler.step_phase = "SELL_MENU_OPEN"

        # Mock matcher 在 SELL_MENU_OPEN 比對到 common/door.png (已在城鎮)
        def mock_match_side_effect(img, tpl, threshold=0.8, **kwargs):
            if tpl == "common/door.png":
                return (100, 100), 0.90
            return None, 0.0

        with patch.object(self.handler.matcher, "match", side_effect=mock_match_side_effect):
            with patch("time.sleep"):
                self.handler.handle(dummy_screen, rect)

                # 斷言 1: step_phase 重置為 INIT
                self.assertEqual(self.handler.step_phase, "INIT")
                # 斷言 2: 自動呼叫 pop_and_next_town_subflow 跳轉下一個任務
                self.mock_machine.pop_and_next_town_subflow.assert_called_once()


if __name__ == "__main__":
    unittest.main()
