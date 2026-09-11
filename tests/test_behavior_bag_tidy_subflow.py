import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time
from states.handlers.bag_tidy import BagTidyHandler
from states.state_machine import GameStateMachine


class TestBehaviorBagTidySubflow(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_machine = MagicMock()
        self.mock_machine.capturer = self.mock_capturer
        self.mock_machine.matcher = self.mock_matcher
        self.mock_machine.mouse = self.mock_mouse
        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.get_window_rect.return_value = self.rect
        self.mock_capturer.capture.return_value = self.fake_img

    def test_bag_tidy_lifecycle_and_postcondition_verification(self):
        """
        [契約 1 驗證] 驗證 BagTidyHandler 完整生命週期：
        1. INIT: 城鎮中點擊開包
        2. WAIT_BAG_OPEN: 偵測到 tidy.png 點擊整理
        3. WAIT_TIDY_SETTLE: 靜置等待渲染後切換至 CLOSE_AND_VERIFY
        4. CLOSE_AND_VERIFY: 閉環確認關閉，驗證 Postcondition (quit/tidy 皆無，door 存在)，成功結案交棒
        """
        handler = BagTidyHandler(self.mock_machine)
        handler.step_phase = "INIT"
        handler.last_action_time = 0.0

        # Step 1: INIT 階段，畫面可見城門與背包入口文字
        def match_init(img, tpl, **kw):
            if tpl == "common/door.png":
                return ((100, 500), 0.90)
            if tpl == "common/bag_text.png":
                return ((750, 550), 0.92)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_init
        handler.handle(self.fake_img, self.rect)
        self.assertEqual(handler.step_phase, "WAIT_BAG_OPEN")
        self.mock_mouse.click.assert_called_once_with(750, 505)

        # Step 2: WAIT_BAG_OPEN 階段，畫面出現 tidy.png
        self.mock_mouse.click.reset_mock()
        handler.last_action_time = 0.0

        def match_wait_open(img, tpl, **kw):
            if tpl == "common/tidy.png":
                return ((700, 480), 0.93)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_wait_open
        handler.handle(self.fake_img, self.rect)
        self.assertEqual(handler.step_phase, "WAIT_TIDY_SETTLE")
        self.mock_mouse.click.assert_called_once_with(700, 480)

        # Step 3: WAIT_TIDY_SETTLE 階段，靜置後偵測到 quit.png
        handler.last_action_time = time.time() - 1.0

        def match_settle(img, tpl, **kw):
            if tpl == "common/quit.png":
                return ((760, 120), 0.91)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_settle
        handler.handle(self.fake_img, self.rect)
        self.assertEqual(handler.step_phase, "CLOSE_AND_VERIFY")

        # Step 4: CLOSE_AND_VERIFY 階段，執行 click_and_wait_until_gone 並驗證 Postcondition
        handler.last_action_time = 0.0
        bag_open_img = np.ones((600, 800, 3), dtype=np.uint8)
        clean_town_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = clean_town_img

        def match_step4(img, tpl, **kw):
            if np.array_equal(img, bag_open_img):
                if tpl == "common/quit.png":
                    return ((760, 120), 0.91)
            elif np.array_equal(img, clean_town_img):
                if tpl == "common/door.png":
                    return ((100, 500), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_step4
        with patch.object(handler, "click_and_wait_until_gone") as mock_wait_gone:
            handler.handle(bag_open_img, self.rect)

            mock_wait_gone.assert_called_once_with("common/quit.png", 760, 120, self.rect, timeout=4.0, threshold=0.80)
            # 斷言結案交棒給狀態機
            self.mock_machine.pop_and_next_town_subflow.assert_called_once()
            self.assertEqual(handler.step_phase, "INIT")

    def test_bag_tidy_aborts_and_does_not_pop_if_postcondition_fails(self):
        """
        [契約 2 驗證] 驗證若退出後背包殘留 (quit.png 仍存在)，絕不提前 pop_and_next_town_subflow
        """
        handler = BagTidyHandler(self.mock_machine)
        handler.step_phase = "CLOSE_AND_VERIFY"
        handler.last_action_time = 0.0

        with patch.object(handler, "click_and_wait_until_gone"):
            # 模擬點擊關閉後畫面依然看得到 quit.png (未消失)
            def match_still_open(img, tpl, **kw):
                if tpl == "common/quit.png":
                    return ((760, 120), 0.91)
                return (None, 0.0)

            self.mock_matcher.match.side_effect = match_still_open
            handler.handle(self.fake_img, self.rect)

            # 斷言絕不交棒
            self.mock_machine.pop_and_next_town_subflow.assert_not_called()
            self.assertEqual(handler.step_phase, "CLOSE_AND_VERIFY")

    def test_bag_tidy_initial_overlay_dismissal(self):
        """
        [契約 3 驗證] 驗證 INIT 階段若存在未知覆蓋層 (有 quit 但無 door)，優先閉環關閉
        """
        handler = BagTidyHandler(self.mock_machine)
        handler.step_phase = "INIT"
        handler.last_action_time = 0.0

        def match_overlay(img, tpl, **kw):
            if tpl == "common/quit.png":
                return ((760, 120), 0.88)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_overlay
        with patch.object(handler, "click_and_wait_until_gone") as mock_wait_gone:
            handler.handle(self.fake_img, self.rect)
            mock_wait_gone.assert_called_once_with("common/quit.png", 760, 120, self.rect, timeout=3.0, threshold=0.80)
            self.assertEqual(handler.step_phase, "INIT")


    def test_trigger_bag_maintenance_chain_includes_bag_tidy_by_default(self):
        """
        [契約 4 驗證] 驗證 GameStateMachine.trigger_bag_maintenance_chain() 預設調度清單包含 bag_tidy
        """
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        machine.current_state = machine.STATE_BAG_CLEANING
        machine.start_subflow_queue = MagicMock()
        machine.transition_to = MagicMock()

        machine.trigger_bag_maintenance_chain()

        # 斷言預設包含 blood_sacrifice, bag_tidy, jewelry_workshop
        machine.start_subflow_queue.assert_called_once_with(["blood_sacrifice", "bag_tidy", "jewelry_workshop"])
        machine.transition_to.assert_called_once_with(machine.STATE_NAVIGATING)


if __name__ == "__main__":
    unittest.main()
