import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.daily_manager import DailyManager
from states.state_machine import GameStateMachine
from states.handlers.lord_boss import LordBossHandler
from config import GAME_CONFIGS

class TestLordBossSubflow(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.status_file = os.path.join(self.test_dir, "daily_status.json")
        self.daily_manager = DailyManager(status_file=self.status_file)
        
        mock_capturer = MagicMock()
        mock_matcher = MagicMock()
        mock_mouse = MagicMock()
        self.state_machine = GameStateMachine(capturer=mock_capturer, matcher=mock_matcher, mouse=mock_mouse)
        self.state_machine.daily_manager = self.daily_manager

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. DailyManager 首領討伐 CD 與計數測試
    # ------------------------------------------------------------------
    def test_lord_boss_initial_state(self):
        """測試：初始化時兩個 Boss 均應為可用狀態"""
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertIn("lord_spider", avail)
        self.assertIn("lord_spectre", avail)
        self.assertTrue(self.daily_manager.has_available_lord_boss())

    def test_lord_boss_cd_and_max_count(self):
        """測試：戰鬥後記錄 timestamp，CD 未過期前判定不可挑戰，過期後自動恢復"""
        # 1. 育母蜘蛛 (lord_spider) 打一次 (CD 3600s)
        self.daily_manager.record_lord_boss_fight("lord_spider")
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertNotIn("lord_spider", avail)
        self.assertIn("lord_spectre", avail)

        # 2. 模擬過了 3601 秒，蜘蛛應恢復可用
        spider_status = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        spider_status["last_fight_timestamp"] = time.time() - 3601.0
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertIn("lord_spider", avail)

        # 3. 測試 5 次上限：當 today_count >= 5，就算 CD 過期也不再可用
        spider_status["today_count"] = 5
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertNotIn("lord_spider", avail)

    def test_lord_boss_reset_at_0830(self):
        """測試：跨越 08:30 時，所有 Boss 的今日次數清零"""
        self.daily_manager.record_lord_boss_fight("lord_spider")
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"] = 5
        
        # 模擬上一輪為昨天 2020-01-01
        self.daily_manager.status["last_daily_reset_date"] = "2020-01-01"
        self.daily_manager.check_and_reset_daily()
        
        # 次數應清零
        self.assertEqual(self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"], 0)

    # ------------------------------------------------------------------
    # 2. LordBossHandler UI 點擊與頁籤比對測試
    # ------------------------------------------------------------------
    @patch('os.path.exists')
    def test_lord_boss_handler_flow(self, mock_exists):
        """測試：LordBossHandler 入口頁籤開啟、選 Boss 與點擊 start 進入戰鬥"""
        mock_exists.return_value = True
        handler = LordBossHandler(self.state_machine)
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        
        # 模擬 1：尚未開啟 Lord_entry_after 頁籤，比對到 door.png 與 Lord_entry.png
        def mock_match_exclusive(screen_img, template_a, template_b, margin=0.02, threshold=0.70):
            # template_a = load/Lord_entry_after.png, template_b = load/Lord_entry.png
            return False, (None, 0.0) # Lord_entry_after 未開啟
            
        handler.match_mutually_exclusive_tabs = mock_match_exclusive
        
        def mock_match(img, name, *args, **kwargs):
            if name == "load/Lord_entry.png":
                return ((200, 200), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match
        
        # 執行第 1 步：點擊 Lord_entry.png
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.state_machine.mouse.click.assert_called_with(200, 200)

        # 模擬 2：頁籤已開啟 (Lord_entry_after)，進行選擇 Boss 點擊
        def mock_match_exclusive_opened(screen_img, template_a, template_b, margin=0.02, threshold=0.70):
            return True, ((200, 200), 0.95)
        handler.match_mutually_exclusive_tabs = mock_match_exclusive_opened

        def mock_match_boss(img, name, *args, **kwargs):
            if name == "load/lord_spider.png":
                return ((300, 300), 0.9)
            elif name == "stages/start.png":
                return ((400, 400), 0.9)
            return (None, 0.0)
        self.state_machine.matcher.match.side_effect = mock_match_boss

        # 執行第 2 步：點擊 start.png 發起戰鬥並轉移至 STATE_BATTLE
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

if __name__ == '__main__':
    unittest.main()
