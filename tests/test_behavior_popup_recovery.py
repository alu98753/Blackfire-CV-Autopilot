import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2

from states.state_machine import GameStateMachine
from states.exceptions import (
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

    def execute(self, screen_img, mouse, rect, matcher=None) -> bool:
        self.execute_called = True
        return self.execute_return


class TestBehaviorPopupRecovery(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)

    def test_custom_subflow_registration_and_execution(self):
        """驗證動態註冊自訂 Exception Subflow 並優先完成觸發處置與狀態復原"""
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        dummy_subflow = DummySubflow(can_handle_return=True, execute_return=True)
        handler.register_subflow(dummy_subflow)

        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.stash_current_state(reason="test_trigger")

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        handler.handle(dummy_img, rect)

        self.assertTrue(dummy_subflow.can_handle_called)
        self.assertTrue(dummy_subflow.execute_called)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_NAVIGATING)

    def test_unhandled_popup_triggers_max_retries_fallback(self):
        """驗證當所有 Subflow 均無法處置時，達到 max_retries 後發起 Fallback 降級復原"""
        handler = UnexpectedPopupRecoveryHandler(self.machine)
        handler.max_retries = 3

        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.stash_current_state(reason="unhandled_popup")

        dummy_img = np.ones((100, 100, 3), dtype=np.uint8) * 150
        rect = {"left": 0, "top": 0, "width": 100, "height": 100}

        # 模擬比對均失敗
        self.matcher.match.return_value = (None, 0.0)

        for _ in range(3):
            handler.handle(dummy_img, rect)

        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)

    def test_raid_box_scoped_cancel_recovery_and_stage_resumption(self):
        """
        驗證打 Stage 關卡點擊 start.png 前點錯彈出 Raid_Box 時的修復流程：
        0. 暫存狀態 (STATE_LOBBY)
        1. 配對 Raid_Box.png 取得 ROI
        2. 僅於 Raid_Box ROI 內部配對 cancel.png 並發起點擊
        3. 復原原狀態 (STATE_LOBBY)
        4. 復原後 LobbyHandler 重新成功辨識到 stages/start.png 並推進至 STATE_LOADING
        """
        from states.handlers.lobby import LobbyHandler
        from states.exceptions import RaidBoxSubflow

        handler = UnexpectedPopupRecoveryHandler(self.machine)
        lobby_handler = LobbyHandler(self.machine)
        self.machine.config = {"type": "stage", "lobby_start_btn": "stages/start.png"}

        # 0. 先存狀態
        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.stash_current_state(reason="stage_misclick_raid_box")
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)

        dummy_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        # 模擬 matcher 行為：
        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "Raid_Box" in template_name:
                return (500, 300), 0.95
            elif "cancel" in template_name:
                return (100, 300), 0.90
            elif "start.png" in template_name:
                return (900, 800), 0.92
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            # 執行 PopupRecoveryHandler
            handler.handle(dummy_screen, rect)

            # 斷言：發起點擊 cancel.png 的絕對座標 (500+100=600, 300+300=600)
            self.mouse.click.assert_called_with(600, 600)

            # 3. 斷言狀態已自動復原至 STATE_LOBBY
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)

            # 4. 復原後下一次迴圈由 LobbyHandler 接手，成功辨識到 stages/start.png 進入 STATE_LOADING
            self.mouse.click.reset_mock()
            lobby_handler.handle(dummy_screen, rect)

            self.mouse.click.assert_called_with(900, 800)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOADING)

    def test_context_preservation_and_stash_lock(self):
        """驗證 Context 數據深拷貝備份/還原，以及 Stash Lock 防護二次暫存不覆蓋原狀態"""
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
