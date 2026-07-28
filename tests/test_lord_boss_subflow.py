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
        os.environ["DEBUG_PAUSE_BOSS"] = "0"

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
        self.state_machine.original_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.stamina_retreat_start_time = time.time()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        
        handler = LordBossHandler(self.state_machine)
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)

    @patch('os.path.exists')
    def test_lord_boss_priority_selection(self, mock_exists):
        """測試：高優先權鎖定測試 (古代惡靈 lord_spectre: 7200s 應優先於 育母蜘蛛 lord_spider: 3600s)"""
        mock_exists.return_value = True
        stage_cfg = GAME_CONFIGS["stage"].copy()
        self.state_machine.primary_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.50)
        self.state_machine.matcher.match.side_effect = lambda img, temp, **kw: ((100, 100), 0.9)
        
        handler = LordBossHandler(self.state_machine)
        handler.has_reset_to_left = True
        
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)
        # 斷言：發起戰鬥時鎖定的目標必須是高優先權 Boss (lord_spectre: 7200s)
        self.assertEqual(self.state_machine.current_lord_boss_key, "lord_spectre")

    def test_update_boss_cooldown_in_daily_manager(self):
        """測試：DailyManager.update_boss_cooldown 依據剩餘秒數即時修復時間戳"""
        self.daily_manager.update_boss_cooldown("lord_spider", 1800.0)
        ok, reason = self.daily_manager.is_boss_available("lord_spider")
        self.assertFalse(ok)
        self.assertIn("冷卻中", reason)

    @patch('states.handlers.lord_boss.LordBossHandler._check_card_cooldown_ocr')
    @patch('os.path.exists')
    def test_pre_click_cooldown_ocr_intercept(self, mock_exists, mock_ocr):
        """測試：點擊前若經 OCR 判定冷卻中，跳過點擊並自動更新 DailyManager，繼續檢查下一個可用 Boss"""
        mock_exists.return_value = True
        # 模擬第一個 Boss (lord_spectre) 在點擊前經 OCR 判讀為冷卻中 (剩餘 1800 秒)
        mock_ocr.side_effect = lambda img, pos, *args, **kwargs: (1800.0, "00:30:00") if pos == (100, 100) else (None, None)
        
        stage_cfg = GAME_CONFIGS["stage"].copy()
        self.state_machine.primary_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.50)

        def fake_match(img, temp, **kw):
            if temp == "load/lord_spectre.png":
                return ((100, 100), 0.90)
            if temp == "load/lord_spider.png":
                return ((200, 200), 0.90)
            if temp == "stages/start.png":
                return ((300, 300), 0.90)
            if temp in ["battle/battle_features_1.png", "battle/battle_features_2.png", "common/auto.png"]:
                return ((400, 400), 0.90)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = fake_match
        handler = LordBossHandler(self.state_machine)
        handler.has_reset_to_left = True
        
        # 執行 handle，預期 lord_spectre 被 pre-click OCR 攔截跳過，選擇 lord_spider 進入戰鬥
        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        self.assertEqual(self.state_machine.current_lord_boss_key, "lord_spider")
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_BATTLE)

    # ------------------------------------------------------------------
    # 3. 防死鎖與假進戰場驗證退場測試 (Deadlock Prevention & Fallback)
    # ------------------------------------------------------------------
    def test_mark_boss_completed_in_daily_manager(self):
        """測試：DailyManager.mark_boss_completed 可將特定 Boss 標記為今日已打滿 (completed_today = True)"""
        self.daily_manager.mark_boss_completed("lord_spider")
        spider_info = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        self.assertTrue(spider_info["completed_today"])
        self.assertEqual(spider_info["today_count"], 5)
        avail = self.daily_manager.get_available_lord_bosses()
        self.assertNotIn("lord_spider", avail)

    @patch('states.handlers.lord_boss.LordBossHandler._check_card_cooldown_ocr')
    @patch('os.path.exists')
    def test_lord_boss_handler_battle_verification_failed_and_quit(self, mock_exists, mock_ocr):
        """測試：點擊開始戰鬥後 2.5 秒未比對到戰鬥特徵，且 start.png 依然存在時，自動點擊 quit 離場並標記 DailyManager 完成"""
        mock_exists.return_value = True
        mock_ocr.return_value = (None, None)

        stage_cfg = GAME_CONFIGS["stage"].copy()
        self.state_machine.primary_config = stage_cfg
        self.state_machine.config = GAME_CONFIGS["lord_boss"].copy()
        self.state_machine.current_state = self.state_machine.STATE_LORD_BOSS
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, False, 0.95, 0.50)

        def fake_match(img, temp, **kw):
            if temp == "load/lord_spider.png":
                return ((100, 100), 0.90)
            if temp == "stages/start.png":
                return ((300, 300), 0.90)
            if temp == "common/quit.png":
                return ((500, 500), 0.90)
            return (None, 0.0)

        self.state_machine.matcher.match.side_effect = fake_match
        handler = LordBossHandler(self.state_machine)
        handler.has_reset_to_left = True

        handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        # 斷言：點擊 quit 後狀態轉移至 NAVIGATING，且 lord_spider 已標記為今日完成
        spider_info = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        self.assertTrue(spider_info["completed_today"])

    def test_battle_handler_5s_timeout_fallback_marks_boss_completed(self):
        """測試：當 BATTLE 狀態觸發 5 秒防卡死退場且存有 current_lord_boss_key 時，自動補償將該 Boss 標記為完成」"""
        from states.handlers.battle import BattleHandler
        self.state_machine.current_state = self.state_machine.STATE_BATTLE
        self.state_machine.current_lord_boss_key = "lord_spider"

        self.state_machine.matcher.match.return_value = (None, 0.0)
        battle_handler = BattleHandler(self.state_machine)
        battle_handler.non_battle_feature_start_time = time.time() - 6.0  # 模擬超時 6 秒

        battle_handler.handle(None, {"left": 0, "top": 0, "width": 1000, "height": 800})
        # 斷言：5 秒防卡死觸發，current_lord_boss_key 被清空且 DailyManager 的 lord_spider 已標記完成
        self.assertIsNone(self.state_machine.current_lord_boss_key)
        spider_info = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        self.assertTrue(spider_info["completed_today"])

if __name__ == '__main__':
    unittest.main()
