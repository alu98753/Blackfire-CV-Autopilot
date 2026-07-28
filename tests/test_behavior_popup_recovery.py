import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2

from states.state_machine import GameStateMachine
from states.handlers.popup_recovery import (
    UnexpectedPopupRecoveryHandler,
    BaseExceptionSubflow,
    GenericCancelSubflow,
    RaidBoxSubflow
)


class DummySubflow(BaseExceptionSubflow):
    name = "dummy_test_subflow"

    def __init__(self, can_handle_return=True, execute_return=True):
        self.can_handle_return = can_handle_return
        self.execute_return = execute_return
        self.can_handle_called = False
        self.execute_called = False

    def can_handle(self, screen_img, matcher, detector=None) -> bool:
        self.can_handle_called = True
        return self.can_handle_return

    def execute(self, screen_img, machine, rect) -> bool:
        self.execute_called = True
        return self.execute_return


class TestBehaviorPopupRecovery(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)

    def test_state_stashing_and_restoration(self):
        """驗證 GameStateMachine 之狀態暫存 (stash) 與恢復 (restore) 契約"""
        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.task_complete_phase = "NAV_PHASE_1"

        # 1. 執行暫存
        self.machine.stash_current_state(reason="test_misclick")
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
        self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_NAVIGATING)
        self.assertEqual(self.machine.stashed_context["reason"], "test_misclick")

        # 2. 執行恢復
        res = self.machine.restore_stashed_state()
        self.assertTrue(res)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_NAVIGATING)
        self.assertIsNone(self.machine.stashed_state)
        self.assertEqual(self.machine.stashed_context, {})

    def test_dimming_overlay_analysis(self):
        """驗證 UnexpectedPopupRecoveryHandler 之圖像明暗度分析邏輯"""
        handler = UnexpectedPopupRecoveryHandler(self.machine)

        # 建立模擬中央亮、四周暗的遮罩圖像 (100x100 BGR)
        img = np.zeros((100, 100, 3), dtype=np.uint8) + 30  # 背景偏暗 (30)
        img[20:80, 20:80] = 200                             # 中央亮區域 (200)

        dim_info = handler.analyze_dimming_overlay(img)
        self.assertTrue(dim_info["is_dimmed"])
        self.assertGreater(dim_info["center_brightness"], dim_info["border_brightness"])

    def test_custom_subflow_registration_and_execution(self):
        """驗證 Subflow 註冊容器與執行流轉架構"""
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        dummy_subflow = DummySubflow(can_handle_return=True, execute_return=True)
        handler.register_subflow(dummy_subflow)

        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.stash_current_state(reason="test_trigger")

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        # 執行 handler
        handler.handle(dummy_img, rect)

        self.assertTrue(dummy_subflow.can_handle_called)
        self.assertTrue(dummy_subflow.execute_called)
        # 執行完成後應自動觸發 restore_stashed_state，回復至 STATE_NAVIGATING
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_NAVIGATING)

    def test_fallback_when_max_retries_exceeded(self):
        """驗證當無相符 Subflow 且超過 max_retries 時發起 Fallback 降級處理"""
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        # 清空預設 subflow 模擬完全無相符情況
        handler.subflows = []
        handler.max_retries = 3

        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.stash_current_state(reason="unhandled_popup")

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8) + 150 # 非遮罩普通畫面
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        with patch("os.path.exists", return_value=False):
            for _ in range(3):
                handler.handle(dummy_img, rect)

        # 超過 3 次應觸發 Fallback 恢復暫存狀態
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)


if __name__ == "__main__":
    unittest.main()
