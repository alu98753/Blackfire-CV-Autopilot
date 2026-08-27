import unittest
import time
import os
from unittest.mock import MagicMock, patch
import numpy as np

from states.state_machine import GameStateMachine
from states.exceptions import ExceptionWatchdog, WheelOfFortuneSubflow, RaidBoxSubflow
from config import get_critical_exception_templates


class TestBehaviorGlobalWatchdog(unittest.TestCase):
    """
    全域 Watchdog 雙重條件 (Dual-Condition) 處置與效能護欄單元測試套件
    """

    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.machine = GameStateMachine(self.capturer, self.matcher, self.mouse)
        self.watchdog = self.machine.exception_watchdog

    def test_non_battle_under_30s_does_not_trigger_or_scan(self):
        """[測試 1] 效能護欄：非戰鬥狀態 (LOBBY) 卡住未滿 30 秒，絕對不觸發，且 0 圖像匹配消耗"""
        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.last_state_change = time.time() - 20.0  # 未滿 30 秒 (僅 20s)

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        # 模擬即使 matcher 回傳專屬圖案，也不應被呼叫
        self.matcher.match.return_value = ((100, 100), 0.99)

        res = self.watchdog.check(dummy_img)

        # 斷言：未滿門檻回傳 False，狀態維持 LOBBY，且 matcher 完全未被呼叫 (0 圖像比對消耗)
        self.assertFalse(res)
        self.assertEqual(self.machine.current_state, GameStateMachine.STATE_LOBBY)
        self.matcher.match.assert_not_called()

    def test_long_subflow_states_under_90s_does_not_trigger_or_scan(self):
        """[測試 2] 效能護欄：戰鬥、探索、背包整理與長城鎮子流程 (共 10 個狀態) 未滿 90 秒，絕對不觸發"""
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.matcher.match.return_value = ((100, 100), 0.99)

        long_states = [
            GameStateMachine.STATE_BATTLE,
            GameStateMachine.STATE_DUNGEON_EXPLORING,
            GameStateMachine.STATE_LORD_BOSS,
            GameStateMachine.STATE_HERO_DRAW,
            GameStateMachine.STATE_BULLETIN_BOARD,
            GameStateMachine.STATE_BLOOD_ALTAR,
            GameStateMachine.STATE_JEWELRY_WORKSHOP,
            GameStateMachine.STATE_CHEST,
            GameStateMachine.STATE_BAG_CLEANING,
            GameStateMachine.STATE_BACKPACK_FULL_SORTING
        ]

        # 逐一驗證 10 個長流程狀態在 85 秒 (未滿 90s) 時均回傳 False，且不觸發 Watchdog
        for st in long_states:
            self.machine.current_state = st
            self.machine.last_state_change = time.time() - 85.0
            self.assertFalse(self.watchdog.check(dummy_img))
            self.assertEqual(self.machine.current_state, st)

        self.matcher.match.assert_not_called()

    @patch("states.exceptions.subflows.game_relaunch.GameRelaunchSubflow.execute", return_value=True)
    def test_collect_only_window_lost_triggers_relaunch(self, mock_relaunch_execute):
        """[測試 7] COLLECT_ONLY 待機中，當視窗崩潰消失 (rect is None) 時，立即觸發 GameRelaunchSubflow 重啟"""
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.machine.current_state = GameStateMachine.STATE_COLLECT_ONLY
        self.capturer.get_window_rect.return_value = None

        res = self.watchdog.check(dummy_img)

        self.assertTrue(res)
        mock_relaunch_execute.assert_called_once()
        self.assertEqual(mock_relaunch_execute.call_args[1]["reason"], "collect_only_window_lost")

    @patch("states.exceptions.subflows.game_relaunch.GameRelaunchSubflow.execute", return_value=True)
    def test_collect_only_dynamic_cooldown_timeout_triggers_relaunch(self, mock_relaunch_execute):
        """[測試 8] COLLECT_ONLY 待機中，當滯留超時 (超過 max(diamond_cd, bread_cd) + 60s 緩衝) 時，自動觸發 GameRelaunchSubflow 重啟"""
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.machine.current_state = GameStateMachine.STATE_COLLECT_ONLY
        self.capturer.get_window_rect.return_value = {"left": 0, "top": 0, "width": 1920, "height": 1080}
        self.machine.config = {"diamond_cd": 300.0, "bread_cd": 300.0}

        # 1. 待機 300 秒 (未滿 360 秒門檻)，放行不觸發
        self.machine.last_state_change = time.time() - 300.0
        self.assertFalse(self.watchdog.check(dummy_img))
        mock_relaunch_execute.assert_not_called()

        # 2. 待機 365 秒 (超過 360 秒門檻)，觸發重啟
        self.machine.last_state_change = time.time() - 365.0
        res = self.watchdog.check(dummy_img)

        self.assertTrue(res)
        mock_relaunch_execute.assert_called_once()
        self.assertEqual(mock_relaunch_execute.call_args[1]["reason"], "collect_only_cooldown_timeout_exceeded")

    def test_timeout_30s_with_matched_specific_subflow_template(self):
        """[測試 3] 雙重條件：滿 90 秒 + 掃描命中 Wheel_of_Fortune.png 專屬 Subflow 圖案"""
        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        self.machine.last_state_change = time.time() - 95.0  # 卡住達 95 秒 (滿 90s)

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        def mock_match(screen_img, template_name, threshold=0.75, quiet=True):
            if "Wheel_of_Fortune" in template_name:
                return (200, 150), 0.95
            return None, 0.0

        self.matcher.match.side_effect = mock_match

        with patch("os.path.exists", return_value=True):
            res = self.watchdog.check(dummy_img)

            self.assertTrue(res)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
            self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_NAVIGATING)

            # 斷言正確認出並指派 WheelOfFortuneSubflow 給 popup_handler
            popup_handler = self.machine.handlers[GameStateMachine.STATE_POPUP_RECOVERY]
            self.assertIsNotNone(popup_handler.active_subflow)
            self.assertEqual(popup_handler.active_subflow.name, "wheel_of_fortune_subflow")

    def test_timeout_30s_without_matched_subflow_template_prepares_generic_anti_stuck(self):
        """[測試 4] 雙重條件：滿 30 秒 + 無任何專屬圖案命中 ➔ active_subflow 為 None，準備走優先級 2 通用防卡死兜底"""
        self.machine.current_state = GameStateMachine.STATE_LOBBY
        self.machine.last_state_change = time.time() - 31.0  # 卡住達 31 秒 (滿 30s)

        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            res = self.watchdog.check(dummy_img)

            self.assertTrue(res)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
            self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_LOBBY)

            # 斷言 active_subflow 為 None (PopupRecovery 內部將自動跳至優先級 2 GenericAntiStuckSubflow)
            popup_handler = self.machine.handlers[GameStateMachine.STATE_POPUP_RECOVERY]
            self.assertIsNone(popup_handler.active_subflow)

    def test_battle_stuck_91s_timeout_triggers_stash(self):
        """[測試 5] 雙重條件：戰鬥 (BATTLE) 滿 91 秒 (1.5 分鐘) 觸發 ExceptionWatchdog 暫存」"""
        self.machine.current_state = GameStateMachine.STATE_BATTLE
        self.machine.last_state_change = time.time() - 91.0
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            res = self.watchdog.check(dummy_img)

            self.assertTrue(res)
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_POPUP_RECOVERY)
            self.assertEqual(self.machine.stashed_state, GameStateMachine.STATE_BATTLE)

    def test_hot_reload_and_dynamic_directory_discovery(self):
        """[測試 6] 驗證 config/exception_features.json 熱重載與 templates/exceptions/ 動態目錄發現"""
        critical_tpls = get_critical_exception_templates()
        self.assertIn("exceptions/Raid_Box.png", critical_tpls)
        self.assertIn("exceptions/Wheel_of_Fortune.png", critical_tpls)

    @patch("states.exceptions.subflows.game_relaunch.GameRelaunchSubflow.execute", return_value=True)
    def test_restore_stashed_state_preserves_watchdog_memory_and_second_timeout_relaunch(self, mock_relaunch):
        """[測試 9] 驗證 restore_stashed_state 恢復暫存時享有全新寬限期，唯有再次逾時滿 90s 才觸發 GameRelaunchSubflow"""
        self.machine.current_state = GameStateMachine.STATE_NAVIGATING
        original_ts = time.time() - 95.0
        self.machine.last_state_change = original_ts
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.matcher.match.return_value = (None, 0.0)

        with patch("os.path.exists", return_value=True):
            # 第 1 次逾時：觸發暫存，進入 POPUP_RECOVERY
            self.watchdog.check(dummy_img)
            self.assertEqual(self.watchdog.consecutive_stuck_count, 1)
            self.assertEqual(self.watchdog.last_stuck_state, GameStateMachine.STATE_NAVIGATING)

            # 模擬彈窗處理完成，恢復原狀態
            self.machine.restore_stashed_state()

            # 斷言 1：恢復後的狀態維持 NAVIGATING，保留卡死次數 1，但 last_state_change 獲賦予全新寬限期
            self.assertEqual(self.machine.current_state, GameStateMachine.STATE_NAVIGATING)
            self.assertEqual(self.watchdog.consecutive_stuck_count, 1)
            self.assertEqual(self.watchdog.last_stuck_state, GameStateMachine.STATE_NAVIGATING)
            self.assertGreater(self.machine.last_state_change, original_ts)
            self.assertAlmostEqual(self.machine.last_state_change, time.time(), delta=1.0)

            # 斷言 2：復原後的第一幀 (未滿 90s)，Watchdog 必須放行 (回傳 False)，絕不誤殺
            res_immediate = self.watchdog.check(dummy_img)
            self.assertFalse(res_immediate)
            mock_relaunch.assert_not_called()

            # 斷言 3：若原狀態「再次卡住超過 90 秒」，才判定連續 2 次逾時並調用 GameRelaunchSubflow
            self.machine.last_state_change = time.time() - 95.0
            res_second_timeout = self.watchdog.check(dummy_img)
            self.assertTrue(res_second_timeout)
            mock_relaunch.assert_called_once()
            self.assertIn("watchdog_consecutive_timeout", mock_relaunch.call_args[1]["reason"])


if __name__ == "__main__":
    unittest.main()
