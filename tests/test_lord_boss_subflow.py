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

class TestLordBossSubflowMatrix(unittest.TestCase):
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
        """測試：初始化時兩個 Boss 均應為可用狀態，且 CD 較大者 (lord_spectre: 7200s) 優先於 (lord_spider: 3600s)"""
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertIn("lord_spider", avail)
        self.assertIn("lord_spectre", avail)
        self.assertTrue(self.daily_manager.has_available_lord_boss())
        self.assertEqual(avail[0], "lord_spectre")
        self.assertEqual(avail[1], "lord_spider")

    def test_lord_boss_cd_and_max_count(self):
        """測試：戰鬥後記錄 timestamp，CD 未過期前判定不可挑戰，過期後自動恢復"""
        self.daily_manager.record_lord_boss_fight("lord_spider")
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertNotIn("lord_spider", avail)
        self.assertIn("lord_spectre", avail)

        spider_status = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        spider_status["last_fight_timestamp"] = time.time() - 3601.0
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertIn("lord_spider", avail)

        spider_status["today_count"] = 5
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertNotIn("lord_spider", avail)

    def test_lord_boss_reset_at_0830(self):
        """測試：跨越 08:30 時，所有 Boss 的今日次數清零"""
        self.daily_manager.record_lord_boss_fight("lord_spider")
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"] = 5
        
        self.daily_manager.status["last_daily_reset_date"] = "2020-01-01"
        self.daily_manager.next_reset_timestamp = time.time() - 10.0
        self.daily_manager.check_and_reset_daily(force=True)
        
        self.assertEqual(self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"], 0)

    # ------------------------------------------------------------------
    # 2. 全模式矩陣回歸測試 (Matrix Tests for Stage/Dungeon/Mix/Retreat)
    # ------------------------------------------------------------------
    def test_lord_boss_return_routing_in_stage_mode(self):
        """測試：在 stage 模式下打完 Boss 佇列全空時，應回復原 stage config 並轉移至 NAVIGATING"""
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"] = 5
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spectre"]["today_count"] = 5
        
        # 設置主模式配置為 stage
        stage_cfg = GAME_CONFIGS["stage"].copy()
        self.state_machine.primary_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        
        handler = LordBossHandler(self.state_machine)
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        # 斷言：狀態轉移為 NAVIGATING 且 config 已恢復為 stage 主配置
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        self.assertEqual(self.state_machine.config["type"], "stage")

    def test_lord_boss_return_routing_in_dungeon_mode(self):
        """測試：在 dungeon 模式下打完 Boss 佇列全空時，應回復原 dungeon config 並轉移至 NAVIGATING"""
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"] = 5
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spectre"]["today_count"] = 5
        
        dungeon_cfg = GAME_CONFIGS["dungeon"].copy()
        self.state_machine.primary_config = dungeon_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        
        handler = LordBossHandler(self.state_machine)
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_NAVIGATING)
        self.assertEqual(self.state_machine.config["type"], "dungeon")

    def test_lord_boss_return_routing_in_stamina_retreat(self):
        """測試：在體力退避期間打完 Boss 佇列全空時，應回復配置並轉移至 COLLECT_ONLY"""
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]["today_count"] = 5
        self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spectre"]["today_count"] = 5
        
        stage_cfg = GAME_CONFIGS["stage"].copy()
        self.state_machine.primary_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        
        handler = LordBossHandler(self.state_machine)
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

if __name__ == '__main__':
    unittest.main()
