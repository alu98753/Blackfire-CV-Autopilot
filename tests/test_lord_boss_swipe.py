import unittest
import numpy as np
import os
import time
from unittest.mock import MagicMock, patch
from states.handlers.lord_boss import LordBossHandler
from config import GAME_CONFIGS

class TestLordBossSwipeLogic(unittest.TestCase):
    """
    專門測試 LordBossHandler 重用卡片導航器後的行為：
    1. 首次進入選關介面 (Lord_entry_after) 時，發動 reset_to_left 復位拖曳。
    2. 畫面上看到 Boss 卡片且無冷卻木牌時進行點擊選擇。
    3. 畫面上未見 Boss 卡片時發動 swipe_left_page 翻頁。
    """

    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_daily = MagicMock()

        self.mock_machine.mouse = self.mock_mouse
        self.mock_machine.capturer = self.mock_capturer
        self.mock_machine.matcher = self.mock_matcher
        self.mock_machine.daily_manager = self.mock_daily

        self.mock_matcher.match.return_value = (None, 0.0)
        # 標記 Lord_entry_after 頁籤已開啟
        self.mock_matcher.match_mutually_exclusive_tabs.return_value = (True, False, (0, 0), 0.95)

        # Boss selection is a GameStateMachine policy: handlers must not read
        # DailyManager availability directly, otherwise profile selection is
        # bypassed.
        self.mock_machine.get_available_selected_lord_bosses.return_value = ["lila_spider", "ancient_spirit"]

        self.mock_machine.config = GAME_CONFIGS.get("lord_boss", {}).copy()
        self.mock_machine.config["bosses"] = {
            "lila_spider": {"name": "育母蜘蛛麗拉西亞", "template": "load/spider.png"},
            "ancient_spirit": {"name": "古代惡靈", "template": "load/spirit.png"}
        }

        self.handler = LordBossHandler(self.mock_machine)
        self.handler.mouse = self.mock_mouse
        self.handler.matcher = self.mock_matcher

        self.rect = {"left": 100, "top": 50, "width": 1000, "height": 800}

    @patch("states.handlers.lord_boss.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    def test_lord_boss_first_entry_resets_to_left(self, mock_exists, mock_detect_cd):
        """[Lord Boss 滑動測試 1] 首次進入選關介面，優先發動拉至最左側 (reset_to_left)"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        # 第一次呼叫 handle：第一個 Boss 未出現，執行向右拖曳拉回第 1 次
        self.handler.handle(screen_img, self.rect)
        self.mock_mouse.drag.assert_called_once_with(300, 450, 900, 450)
        self.assertEqual(self.handler.reset_swipe_count, 1)
        self.assertFalse(self.handler.has_reset_to_left)

        # 第二次呼叫 handle：第一個 Boss 成功匹配出現，判定回到起點，確立 has_reset_to_left = True
        def mock_match_first(screen, templ, threshold=0.78, **kwargs):
            if "spider" in templ:
                return (200, 300), 0.90
            return None, 0.0

        self.mock_matcher.match.side_effect = mock_match_first
        self.handler.handle(screen_img, self.rect)
        self.assertTrue(self.handler.has_reset_to_left)

    @patch("states.handlers.lord_boss.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    def test_lord_boss_visible_card_clicks_direct(self, mock_exists, mock_detect_cd):
        """[Lord Boss 滑動測試 2] 復位後於畫面上看見可用 Boss 卡片，點擊選擇"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        self.handler.has_reset_to_left = True  # 已復位

        def mock_match(screen, templ, threshold=0.78, **kwargs):
            if "spider" in templ:
                return (200, 300), 0.90
            return None, 0.0

        self.mock_matcher.match.side_effect = mock_match

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.handler.handle(screen_img, self.rect)

        # 點擊座標 100+200=300, 50+300=350
        self.mock_mouse.click.assert_called_with(300, 350)
        self.assertEqual(self.handler.current_target_boss, "lila_spider")

    @patch("states.handlers.lord_boss.detect_cooldown_sign_and_time")
    @patch("os.path.exists")
    def test_lord_boss_no_card_swipes_left_to_next_page(self, mock_exists, mock_detect_cd):
        """[Lord Boss 滑動測試 3] 復位後畫面上未發現可用 Boss，發動向左滑動翻頁"""
        mock_exists.return_value = True
        mock_detect_cd.return_value = (False, None, "")

        self.handler.has_reset_to_left = True  # 已復位
        self.mock_matcher.match.return_value = (None, 0.0)  # 無卡片在畫面上

        screen_img = np.zeros((800, 1000, 3), dtype=np.uint8)
        self.handler.handle(screen_img, self.rect)

        # 驗證發動向左滑動: 100 + 600 = 700 -> 100 + 400 = 500, duration=0.8, inertia=False
        self.mock_mouse.drag.assert_called_once_with(700, 450, 500, 450, duration=0.8, inertia=False)

if __name__ == "__main__":
    unittest.main()
