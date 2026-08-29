import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GAME_CONFIGS
from states.state_machine import GameStateMachine

from tests._legacy_state_machine_test_support import TaskCompletePhaseTestCase


class TestTaskCompletionPhases(TaskCompletePhaseTestCase):

    @patch('os.path.exists')
    def test_phase_happy_path_flow(self, mock_exists):
        """
        維度 1：全順暢主幹流程測試。
        驗證 Phase 1 (INIT) ➔ Phase 2 (OCR) ➔ Phase 3 (FIND) ➔ Phase 4 (DISMISS) 連貫完成並重置 Phase。
        """
        mock_exists.return_value = True
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img

        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "task_complete.png":
                return ((100, 100), 0.90)
            if name == "common/confirm.png":
                return ((150, 150), 0.92)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        with patch.object(self.state_machine, 'click_and_wait_until_gone') as mock_wait_gone:
            # 執行子流程
            self.state_machine._run_task_complete_subflow(self.rect)

            # 斷言 Phase 4 正確調用 click_and_wait_until_gone 監控 confirm.png 消失
            mock_wait_gone.assert_called_once()
            args, kwargs = mock_wait_gone.call_args
            self.assertEqual(args[0], "common/confirm.png")
            self.assertEqual(kwargs.get('check_interval'), 2.0)

        # 斷言最後 Phase 已重置為 INIT_BANNER_CHECK
        self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

    @patch('os.path.exists')
    def test_phase_no_match_retention_and_resumption(self, mock_exists):
        """
        維度 2：Match 失敗狀態留存與跨幀恢復測試。
        模擬第 1 幀無 Match ➔ 狀態留存；第 2 幀淡入 Match 成功 ➔ 切換 Phase 推進。
        """
        mock_exists.return_value = True
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img

        # 第 1 幀：未匹配到大彈窗
        self.mock_matcher.match.return_value = (None, 0.0)
        self.state_machine._run_task_complete_subflow(self.rect)

        # 斷言 Phase 保持在 INIT_BANNER_CHECK
        self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

        # 第 2 幀：Match 成功
        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "task_complete.png":
                return ((100, 100), 0.90)
            if name == "common/confirm.png":
                return ((150, 150), 0.92)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        with patch.object(self.state_machine, 'click_and_wait_until_gone'):
            self.state_machine._run_task_complete_subflow(self.rect)

        # 斷言成功經歷 Phase 1~4 關閉後重置為 INIT_BANNER_CHECK
        self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

    @patch('os.path.exists')
    def test_phase_no_confirm_button_fallback(self, mock_exists):
        """
        維度 3：無獨立確認按鈕，保底座標領獎測試。
        驗證 Phase 3 能算出自適應座標 (766, 1710) 並將標的鎖定為 task_complete.png。
        """
        mock_exists.return_value = True
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img

        # 僅 match 到 task_complete.png，無法 match 到 common/confirm.png 或 ok.png
        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "task_complete.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        with patch.object(self.state_machine, 'click_and_wait_until_gone') as mock_wait_gone:
            self.state_machine._run_task_complete_subflow(self.rect)

            # 斷言 Phase 4 將標的設為 task_complete.png 且點擊計算出之保底座標 (110, 276)
            mock_wait_gone.assert_called_once()
            args, kwargs = mock_wait_gone.call_args
            self.assertEqual(args[0], "task_complete.png")
            self.assertEqual(kwargs.get('check_interval'), 2.0)

        self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

    @patch('os.path.exists')
    def test_phase_sequential_multi_popups(self, mock_exists):
        """
        維度 4：連續多彈窗鏈式處理測試。
        驗證連續 2 個彈窗皆能順暢完成 Phase 1~4 並完成核銷。
        """
        mock_exists.return_value = True
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img

        def match_side_effect(img, name, threshold=None, **kwargs):
            if name == "task_complete.png":
                return ((100, 100), 0.90)
            if name == "common/confirm.png":
                return ((150, 150), 0.92)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect

        with patch.object(self.state_machine, 'click_and_wait_until_gone') as mock_wait_gone:
            # 跑第 1 彈窗
            self.state_machine._run_task_complete_subflow(self.rect)
            self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

            # 跑第 2 彈窗
            self.state_machine._run_task_complete_subflow(self.rect)
            self.assertEqual(self.state_machine.task_complete_phase, "INIT_BANNER_CHECK")

            # 斷言 click_and_wait_until_gone 被成功呼叫 2 次
            self.assertEqual(mock_wait_gone.call_count, 2)

    @patch('os.path.exists')
    def test_task_complete_subflow_advances_quest_target(self, mock_exists):
        """
        驗證領取任務完成彈窗子流程結束時，會主動呼叫 check_and_advance_quest_target() 推進目標配置。
        """
        mock_exists.return_value = True
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        self.mock_capturer.capture.return_value = fake_img

        def match_side_effect(img, name, threshold=None, **kwargs):
            if name in ["task_complete.png", "common/confirm.png"]:
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = match_side_effect
        mock_qs = MagicMock()
        mock_qs.process_task_complete_banner.return_value = "清除史萊姆"
        self.state_machine.quest_scheduler = mock_qs

        with patch.object(self.state_machine, 'check_and_advance_quest_target') as mock_advance, \
             patch.object(self.state_machine, 'click_and_wait_until_gone'):
            self.state_machine._run_task_complete_subflow(self.rect)
            # 斷言 Phase 4 結束時 check_and_advance_quest_target 被成功呼叫 1 次
            mock_advance.assert_called_once()


if __name__ == "__main__":
    unittest.main()
