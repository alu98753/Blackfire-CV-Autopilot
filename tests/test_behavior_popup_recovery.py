import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from states.state_machine import GameStateMachine
from states.exceptions import (
    UnexpectedPopupRecoveryHandler,
    BaseExceptionSubflow,
    RaidBoxSubflow,
    GenericAntiStuckSubflow
)


class TestBehaviorPopupRecovery(unittest.TestCase):
    """
    分階段雙層優先級彈窗復原與 Subflow 單元測試套件 (Staged 2-Priority Unit Tests)
    """

    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)
        self.handler = UnexpectedPopupRecoveryHandler(self.machine)

    # -------------------------------------------------------------------------
    # 階段 1：RaidBoxSubflow 專屬獨立單元測試
    # -------------------------------------------------------------------------
    def test_raid_box_subflow_can_handle_and_execute(self):
        """[階段 1] 驗證 RaidBoxSubflow 獨立點擊與 Scoped ROI 運算"""
        subflow = RaidBoxSubflow()
        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 100, "top": 50, "width": 1920, "height": 1080}

        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "Raid_Box" in template_name:
                return (400, 200), 0.95
            elif "cancel" in template_name:
                return (50, 150), 0.90
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            # 1. 斷言 can_handle 傳回 True
            self.assertTrue(subflow.can_handle(dummy_screen, self.matcher))

            # 2. 執行 execute，斷言點擊絕對座標 (100+400+50=550, 50+200+150=400)
            res = subflow.execute(dummy_screen, self.mouse, rect, self.matcher)
            self.assertTrue(res)
            self.mouse.click.assert_called_with(550, 400)

    # -------------------------------------------------------------------------
    # 階段 2：GenericAntiStuckSubflow 專屬獨立單元測試
    # -------------------------------------------------------------------------
    def test_generic_anti_stuck_subflow_can_handle_and_execute(self):
        """[階段 2] 驗證 GenericAntiStuckSubflow 獨立點擊全域按鈕"""
        subflow = GenericAntiStuckSubflow()
        dummy_screen = np.zeros((100, 100, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "common/quit.png" in template_name:
                return (50, 50), 0.90
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            self.assertTrue(subflow.can_handle(dummy_screen, self.matcher))

            res = subflow.execute(dummy_screen, self.mouse, rect, self.matcher)
            self.assertTrue(res)
            self.mouse.click.assert_called_with(50, 50)

    # -------------------------------------------------------------------------
    # 階段 3：雙層優先級分階段調度測試 (Staged Priority Dispatch Tests)
    # -------------------------------------------------------------------------
    def test_priority_level_1_overrides_priority_level_2(self):
        """[階段 3-A] 驗證當同時存在 Raid_Box 與全域 quit.png 時，必定【優先級 1 優先】觸發 RaidBoxSubflow"""
        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.stash_current_state(reason="dual_popup_test")

        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 模擬畫面同時有 Raid_Box.png 與 common/quit.png
        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "Raid_Box" in template_name:
                return (500, 300), 0.95
            elif "cancel" in template_name:
                return (100, 300), 0.90
            elif "common/quit.png" in template_name:
                return (1000, 200), 0.98
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(dummy_screen, rect)

            # 斷言：點擊的是 RaidBoxSubflow 的 cancel.png (500+100=600, 300+300=600)，而不是 quit.png (1000, 200)
            self.mouse.click.assert_called_with(600, 600)
            self.assertEqual(self.handler.active_subflow, None)  # 處置完畢後已清空 active
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)

    def test_priority_level_2_fallback_when_no_level_1_match(self):
        """[階段 3-B] 驗證完全【無優先級 1 專屬圖案】時，自動觸發【優先級 2 通用防卡死】點擊 common/confirm.png"""
        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.stash_current_state(reason="anti_stuck_fallback_test")

        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 模擬畫面無 Raid_Box，但有 common/confirm.png
        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "common/confirm.png" in template_name:
                return (800, 600), 0.92
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            self.handler.handle(dummy_screen, rect)

            # 斷言：發起優先級 2 的通用防卡死點擊 (800, 600)
            self.mouse.click.assert_called_with(800, 600)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_NAVIGATING)

    def test_unhandled_popup_triggers_max_retries_fallback(self):
        """[階段 3-C] 驗證當優先級 1 與 2 均無法匹配時，達到 max_retries 後發起 Fallback 降級復原"""
        self.handler.max_retries = 3

        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.stash_current_state(reason="unhandled_popup")

        dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 150
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        # 模擬所有圖片匹配均失敗
        self.matcher.match.return_value = (None, 0.0)

        for _ in range(3):
            self.handler.handle(dummy_img, rect)

        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)

    def test_context_preservation_and_stash_lock(self):
        """[階段 3-D] 驗證 Context 數據深拷貝備份/還原，以及 Stash Lock 防護二次暫存不覆蓋原狀態"""
        # 1. 初始設定業務狀態與 Context
        self.machine.current_state = GameStateMachine.STATE_DUNGEON_EXPLORING
        self.machine.context = {"dungeon_id": 4, "step_index": 2, "target_name": "Ghost_entry"}

        # 2. 第一次暫存 (stash)
        self.machine.stash_current_state(reason="first_stash")
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
        self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_DUNGEON_EXPLORING)

        # 3. 嘗試二次暫存 (Stash Lock 生效，業務狀態不被覆蓋為 POPUP_RECOVERY)
        self.machine.stash_current_state(reason="second_stash_attempt")
        self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_DUNGEON_EXPLORING)

        # 4. 變更當前 context (模擬彈窗過程中數據變動)
        self.machine.context = {"temporary": "garbage"}

        # 5. 發起還原 (restore)
        self.machine.restore_stashed_state()

        # 6. 斷言業務狀態與 Context 100% 完美復原
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_DUNGEON_EXPLORING)
        self.assertEqual(self.machine.context["dungeon_id"], 4)
        self.assertEqual(self.machine.context["step_index"], 2)
        self.assertEqual(self.machine.context["target_name"], "Ghost_entry")


if __name__ == "__main__":
    unittest.main()
