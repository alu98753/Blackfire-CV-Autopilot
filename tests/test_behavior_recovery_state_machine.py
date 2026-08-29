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


class TestRecoveryStateMachine(StateMachineLogicTestCase):

    @patch('os.path.exists')
    def test_defeat_restart_flow(self, mock_exists):
        """
        測試戰鬥中戰敗並重新開始的完整流轉邏輯：
        1. 處於 BATTLE 狀態下，偵測到戰敗大圖 defeat.png ➔ 轉移至 RESULT
        2. 進入 RESULT 狀態後，再次匹配 defeat.png。此時：
           - 模擬 defeat_retry.png 匹配失敗 (None)
           - 模擬 stages/retry.png 匹配失敗 (None)
           - 預期：應使用防禦性相對座標 (defeat_center_x - 140, defeat_center_y + 250) 執行點擊
           - 點擊後，狀態回到 BATTLE，run_count 累加
        3. 另一個情況：在 RESULT 狀態下且戰敗：
           - 模擬 defeat_retry.png 匹配成功 (pos)
           - 預期：直接點擊該按鈕座標，狀態回到 BATTLE
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.run_count = 0
        
        mock_exists.return_value = True
        self.mock_capturer.get_window_rect.return_value = {"left": 100, "top": 100, "width": 1920, "height": 1080}
        
        # 1. 在 BATTLE 狀態，看見 defeat.png ➔ 轉移至 RESULT
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((500, 500), 0.9) if name == "defeat.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_RESULT)
        
        # 2. 在 RESULT 狀態下，匹配失敗按鈕 ➔ 觸發相對座標備份點擊 (X=100+500-140=460, Y=100+500+250=850)
        # 模擬 match：只有 defeat.png 匹配成功，其餘 None
        def match_side_effect_fallback(img, name, threshold):
            if name == "defeat.png":
                return ((500, 500), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_fallback
        self.state_machine.step()
        
        # 斷言：點擊相對座標 (460, 850)，且轉移為 LOADING，且次數為 1
        self.mock_mouse.click.assert_called_with(460, 850)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)
        self.assertEqual(self.state_machine.run_count, 1)
        
        # 模擬進入戰鬥，看見 auto.png ➔ 轉移為 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        
        # 3. 再來一次，測試能成功匹配 defeat_retry.png
        self.state_machine.current_state = self.state_machine.STATE_RESULT
        self.state_machine.last_result_retry_click_time = 0.0
        self.state_machine.defeat_count = 0
        
        def match_side_effect_success(img, name, threshold):
            if name == "defeat.png":
                return ((500, 500), 0.9)
            if name == "defeat_retry.png":
                return ((400, 800), 0.9)
            return (None, 0.0)
            
        self.mock_matcher.match.side_effect = match_side_effect_success
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        # 斷言：應點擊匹配到的按鈕座標 (100+400=500, 100+800=900)，且轉移為 LOADING
        self.mock_mouse.click.assert_called_with(500, 900)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)
        self.assertEqual(self.state_machine.run_count, 2)

        # 模擬再次進入戰鬥，看見 auto.png ➔ 轉移為 BATTLE
        self.mock_matcher.match.side_effect = lambda img, name, threshold: (
            ((400, 400), 0.9) if name == "common/auto.png" else (None, 0.0)
        )
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

    @patch('os.path.exists')
    def test_stuck_protection_flow(self, mock_exists):
        """
        測試防卡死監控流程：
        1. 在 NAVIGATING 狀態下，若連續 15 幀狀態未轉移，則判定為卡死。
        2. 分支 A: 找到 confirm.png ➔ 點擊該確認按鈕以清除阻礙，保持原本狀態。
        3. 分支 B: 找不到任何確認按鈕 ➔ 強制轉移至 STATE_UNKNOWN 重新定位。
        """
        mock_exists.return_value = True
        
        # 準備
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_NAVIGATING
        self.state_machine.consecutive_stuck_count = 0
        self.mock_capturer.capture.return_value = MagicMock()
        
        # 模擬 match，前 14 次不觸發卡死
        self.mock_matcher.match.return_value = (None, 0.0)
        
        for _ in range(14):
            self.state_machine.step()
            
        self.assertEqual(self.state_machine.consecutive_stuck_count, 14)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 測試分支 A: 卡住逾時發起暫存並由 GenericAntiStuckSubflow 點擊匹配 confirm.png
        self.state_machine.last_state_change = time.time() - 95.0
        
        def match_confirm(img, name, threshold=0.75, quiet=True):
            if "common/confirm.png" in name:
                return ((800, 400), 0.9)
            return None, 0.0
        self.mock_matcher.match.side_effect = match_confirm
        self.mock_mouse.click.reset_mock()
        
        # 1. 執行 step 觸發 Watchdog 暫存
        with patch("os.path.exists", return_value=True):
            self.state_machine.step()
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_POPUP_RECOVERY)
            
            # 2. 下一步由 UnexpectedPopupRecoveryHandler 調度 GenericAntiStuckSubflow
            self.state_machine.step()
            self.mock_mouse.click.assert_called_with(800, 400)
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        
        # 測試分支 B: 找不到任何確認按鈕且達到最大重試次數
        self.state_machine.last_state_change = time.time() - 31.0
        self.mock_matcher.match.side_effect = lambda img, name, threshold=0.75, quiet=True: (None, 0.0)
        self.mock_mouse.click.reset_mock()
        
        with patch("os.path.exists", return_value=True):
            self.state_machine.step()  # 進入 POPUP_RECOVERY
            popup_handler = self.state_machine.handlers[self.state_machine.STATE_POPUP_RECOVERY]
            popup_handler.max_retries = 1
            self.state_machine.step()  # 發起 Fallback 退避
            self.mock_mouse.click.assert_not_called()
            self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)

    @patch('os.path.exists')
    def test_login_page_detection_with_confirm_btn(self, mock_exists):
        """
        測試全域登入功能（包含確認按鈕）：
        若有 login_confirm.png，應精確定位並點選按鈕。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        mock_exists.side_effect = lambda path: True
        
        # 模擬比對結果：login.png 位於中心 (500, 500), login_confirm.png 位於 (970, 783)
        self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kwargs: (
            ((500, 500), 0.95) if name == "login/login.png" else (
                ((970, 783), 0.92) if name == "login/login_confirm.png" else (
                    ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
                )
            )
        )
        
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        self.mock_mouse.click.assert_called_once_with(970, 783)

    @patch('os.path.exists')
    def test_login_page_detection_with_fallback_offset(self, mock_exists):
        """
        測試全域登入功能（無確認按鈕，使用相對偏移量）：
        若無 login_confirm.png，應基於 login.png 中心算出的偏移量進行點選。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.mock_capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        mock_exists.side_effect = lambda path: "login_confirm.png" not in path.replace("\\", "/")
        
        # 模擬比對結果：login.png 位於中心 (500, 500)
        self.mock_matcher.match.side_effect = lambda img, name, threshold=None, **kwargs: (
            ((500, 500), 0.95) if name == "login/login.png" else (
                ((100, 100), 0.9) if name == "common/door.png" else (None, 0.0)
            )
        )
        
        self.mock_mouse.click.reset_mock()
        self.state_machine.step()
        
        # 計算偏移量：dx = -3, dy = 253 (因為 mock 視窗高度為 1080, scale_y = 1.0)
        # click_x = 500 - 3 = 497
        # click_y = 500 + 253 = 753
        self.mock_mouse.click.assert_called_once_with(497, 753)

    @patch('os.path.exists')
    def test_loading_state_flow(self, mock_exists):
        """
        測試過渡加載狀態 (STATE_LOADING) 的運作流程：
        1. 看到戰鬥特徵 ➔ 進入 BATTLE。
        2. 超時過長 ➔ 重置為 UNKNOWN。
        3. 跳出體力不足 ➔ 觸發退避。
        """
        self.state_machine.config = GAME_CONFIGS["stage"]
        self.state_machine.current_state = self.state_machine.STATE_LOADING
        self.state_machine.loading_start_time = time.time()
        mock_exists.return_value = True

        # 情況 1: 沒有戰鬥特徵，且未超時 ➔ 繼續等待
        self.mock_matcher.match.return_value = (None, 0.0)
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_LOADING)

        # 情況 2: 超時 (設定啟動時間在 20 秒前) ➔ 重置為 UNKNOWN
        self.state_machine.loading_start_time = time.time() - 20.0
        self.state_machine.step()
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

        # 情況 3: 跳出體力不足 ➔ 觸發退避 (全域攔截)
        self.state_machine.current_state = self.state_machine.STATE_LOADING
        self.state_machine.loading_start_time = time.time()
        
        # 模擬看見 no_bread.png
        def match_no_bread(img, name, threshold=None, brightness_threshold=None):
            if name == "no_bread/no_bread.png":
                return (500, 500), 0.9
            if name == "goback_town.png":
                return (100, 100), 0.9
            return None, 0.0
        self.mock_matcher.match.side_effect = match_no_bread
        self.state_machine.step()
        
        # 應觸發退避並變為 COLLECT_ONLY
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    @patch('os.path.exists')
    @patch('states.handlers.battle.time.sleep')
    def test_battle_handler_user_resumed_lobby_detection(self, mock_sleep, mock_exists):
        """
        測試手動介入恢復時的大廳按鈕 (門檻 0.90) 檢測與標記重置：
        - just_resumed_from_user == True 且大廳按鈕相似度 0.92 >= 0.90 ➔ 標記重置為 False，切換至 STATE_UNKNOWN。
        - just_resumed_from_user == True 但大廳按鈕相似度 0.85 < 0.90 ➔ 標記重置為 False，維持 BATTLE。
        """
        from config import GAME_CONFIGS
        mock_exists.return_value = True
        self.state_machine.config = GAME_CONFIGS["stage"].copy()
        self.state_machine.current_state = self.state_machine.STATE_BATTLE

        handler = self.state_machine.handlers[self.state_machine.STATE_BATTLE]
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 800, "height": 600}

        # 1. 情境 A：標記為 True 且畫面上看見大廳按鈕 (0.92 >= 0.90)
        self.state_machine.just_resumed_from_user = True
        def mock_match_lobby_high(img, name, threshold=0.9, **kw):
            conf = 0.92 if name == "common/door.png" else 0.0
            return ((100, 100), conf) if conf >= threshold else (None, conf)

        self.mock_matcher.match.side_effect = mock_match_lobby_high
        handler.handle(fake_img, rect)

        # 斷言標記被重置為 False 且狀態切換為 UNKNOWN
        self.assertFalse(self.state_machine.just_resumed_from_user)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_UNKNOWN)

        # 2. 情境 B：標記為 True 但大廳按鈕為 0.85 (< 0.90)，畫面仍有戰鬥特徵 auto.png (0.90)
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.just_resumed_from_user = True
        def mock_match_lobby_low(img, name, threshold=0.9, **kw):
            conf = 0.90 if name == "common/auto.png" else (0.85 if name == "common/door.png" else 0.0)
            return ((200, 200), conf) if conf >= threshold else (None, conf)

        self.mock_matcher.match.side_effect = mock_match_lobby_low
        handler.handle(fake_img, rect)

        # 斷言標記被重置為 False 且狀態維持在 BATTLE
        self.assertFalse(self.state_machine.just_resumed_from_user)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)


if __name__ == "__main__":
    unittest.main()
