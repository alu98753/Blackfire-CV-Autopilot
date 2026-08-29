import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import StateMachineLogicTestCase


class TestTaskCompletionStateMachine(StateMachineLogicTestCase):

    @patch('os.path.exists')
    def test_global_task_complete_and_confirm_interception(self, mock_exists):
        """
        測試全域彈窗攔截器：
        1. 看到 task_complete.png ➔ 轉交 _run_task_complete_subflow 進行 OCR 與核銷
        2. 在大廳狀態下看到確認/OK 彈窗 ➔ 自動點選確認關閉
        """
        self.state_machine.config = GAME_CONFIGS["dungeon"]
        self.state_machine.enable_bread = False
        self.state_machine.need_bread_collection = False
        self.state_machine.current_state = self.state_machine.STATE_LOBBY
        
        mock_exists.return_value = True
        
        # 模擬擷取視窗大小 (1920x1080)
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        
        # 1. 偵測到 task_complete.png 位於中心 (960, 540)，應調用 _run_task_complete_subflow
        with patch.object(self.state_machine, '_run_task_complete_subflow') as mock_subflow:
            self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kw: (
                ((960, 540), 0.9) if name == "task_complete.png" else (None, 0.0)
            )
            self.state_machine.step()
            mock_subflow.assert_called_once()
        
        # 2. 點擊完領取獎勵後，畫面彈出 confirm.png
        # 此時在大廳狀態，通用確認攔截器應點選確認關閉
        self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kw: (
            ((960, 600), 0.9) if name == "common/confirm.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.mock_mouse.click.assert_called_with(960, 600)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOBBY)

    @patch('states.state_machine.os.path.exists')
    def test_run_task_complete_subflow_success(self, mock_exists):
        """
        測試任務完成彈窗領取獎勵子流程成功跑完的狀態：
        1. 看到 common/confirm.png ➔ 點選並結束子流程
        """
        mock_exists.return_value = True
        
        # 模擬 matcher.match 尋找到 task_complete.png 與 confirm.png 隨後消失
        confirm_matched = [False]
        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "task_complete.png":
                if not confirm_matched[0]:
                    return ((100, 100), 0.90)
                return (None, 0.0)
            if name == "common/confirm.png":
                if not confirm_matched[0]:
                    confirm_matched[0] = True
                    return ((150, 150), 0.92)
                return (None, 0.0)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect
        
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        
        # 以 patch 縮短 subflow 的 sleep 時間以加快測試速度
        with patch('states.state_machine.time.sleep') as mock_sleep:
            self.state_machine._run_task_complete_subflow(rect)
            
        # 驗證是否點擊了確認按鈕，且座標加上 rect["left"] / rect["top"]
        self.mock_mouse.click.assert_called_once_with(160, 170)  # 10 + 150, 20 + 150

    @patch('os.path.exists')
    def test_multiple_task_complete_popups_sequential_handling(self, mock_exists):
        """
        測試連續多個任務完成彈窗 (例如完成 2 個任務) 被連貫點擊確認清理完畢
        """
        mock_exists.return_value = True

        popups_cleared = 0
        def match_side_effect(img, name, threshold=None, **kwargs):
            nonlocal popups_cleared
            if name == "task_complete.png":
                if popups_cleared < 2:
                    return ((100, 100), 0.90)
                return (None, 0.0)
            if name == "common/confirm.png":
                if popups_cleared < 2:
                    popups_cleared += 1
                    return ((150, 150), 0.92)
                return (None, 0.0)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect
        rect = {"left": 10, "top": 20, "width": 800, "height": 600}

        with patch.object(self.state_machine, 'click_and_wait_until_gone') as mock_wait_gone:
            self.state_machine._run_task_complete_subflow(rect)
            mock_wait_gone.assert_called_once()

    @patch('os.path.exists')
    def test_task_complete_subflow_waits_2s_loop_until_no_confirm(self, mock_exists):
        """驗證 Phase 4 以 2.0s 為間隔匹配直至沒有 confirm/ok 彈窗才回到原本流程"""
        mock_exists.return_value = True
        self.state_machine.task_complete_phase = "CLICK_DISMISS_LOOP"
        self.state_machine._subflow_click_target = (160, 170, "common/confirm.png")

        rect = {"left": 10, "top": 20, "width": 800, "height": 600}

        with patch.object(self.state_machine, 'click_and_wait_until_gone') as mock_wait_gone:
            with patch('states.state_machine.time.sleep'):
                self.state_machine._run_task_complete_subflow(rect)

        # 斷言點擊並等待消失 API 被呼叫，且包含 check_interval=2.0
        mock_wait_gone.assert_called_once()
        _, kwargs = mock_wait_gone.call_args
        self.assertEqual(kwargs.get('check_interval'), 2.0, "未將 check_interval 設定為 2.0 秒！")
        self.assertEqual(kwargs.get('retry_interval'), 2.0, "未將 retry_interval 設定為 2.0 秒！")


if __name__ == "__main__":
    unittest.main()
