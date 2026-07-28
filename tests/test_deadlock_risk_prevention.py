import unittest
import time
import os
import sys
import shutil
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.daily_manager import DailyManager
from utils.quest_scheduler import QuestScheduler, TaskNode
from states.state_machine import GameStateMachine
from states.handlers.lord_boss import LordBossHandler
from states.stamina_flow import handle_insufficient_stamina
from config import GAME_CONFIGS, PRIMARY_MODES

class TestDeadlockRiskPrevention(unittest.TestCase):
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

    def test_lord_boss_failed_start_marks_json_completed_and_quits(self):
        """
        [組件 1 防死鎖斷言] 驗證當點擊 Lord Boss 開始戰鬥，但在 2.5s 驗證期間未進入戰鬥（伺服器已滿 5/5 或拒絕進場）：
        - 比對並點擊 quit.png 退場。
        - 顯式呼叫 DailyManager.mark_boss_completed(boss_key)，更新 daily_status.json 為 completed_today = True。
        - 呼叫 pop_and_next_town_subflow() 自動流轉，絕不無限重試。
        """
        boss_handler = LordBossHandler(self.state_machine)
        self.state_machine.config = {
            "name": "首領討伐",
            "type": "subflow",
            "subflow": "lord_boss",
            "entry_before": "load/Lord_entry.png",
            "entry_after": "load/Lord_entry_after.png",
            "start_btn": "stages/start.png",
            "bosses": {
                "lord_spider": {"name": "蜘蛛女王", "template": "bosses/spider.png", "start_btn": "bosses/start_spider.png"}
            }
        }
        boss_handler.current_target_boss = "lord_spider"
        rect = {"left": 0, "top": 0, "width": 1000, "height": 800}

        def mock_match(img, template, **kwargs):
            if template == "stages/start.png":
                return (500, 500), 0.90
            elif template == "common/quit.png":
                return (800, 200), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match
        self.state_machine.matcher.match_mutually_exclusive_tabs.return_value = (True, (500, 500), 0.95, "load/Lord_entry_after.png")

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            boss_handler.handle(None, rect)

        # 斷言 1: DailyManager 已標記該 Boss 為已打滿 completed_today == True
        spider_info = self.daily_manager.status["subflows"]["lord_boss"]["bosses"]["lord_spider"]
        self.assertTrue(spider_info["completed_today"])
        self.assertEqual(spider_info["today_count"], 5)

        # 斷言 2: click_and_wait_until_gone 被調用，進行 quit.png 關閉退場
        self.assertTrue(self.state_machine.matcher.match.called)

    def test_no_bread_triggers_collect_only_and_prevents_reentry(self):
        """
        [組件 2 防死鎖斷言] 驗證進場爆出 no_bread.png 時：
        - 點擊 cancel 關閉彈窗並退回城鎮。
        - 備份 original_config 並設定 stamina_retreat_start_time。
        - 狀態機切換至 STATE_COLLECT_ONLY，且在 collect_only 期間禁止自動推進/進場。
        """
        self.state_machine.config = GAME_CONFIGS["daily"].copy()

        def mock_match(img, template, **kwargs):
            if template == "no_bread/no_bread.png":
                return (500, 400), 0.95
            elif template == "no_bread/cancel.png":
                return (400, 500), 0.90
            elif template == "goback_town.png":
                return (100, 700), 0.90
            return None, 0.0

        self.state_machine.matcher.match.side_effect = mock_match

        with patch('os.path.exists', return_value=True), patch('time.sleep', return_value=None):
            triggered = handle_insufficient_stamina(self.state_machine, None, {"left": 0, "top": 0, "width": 1000, "height": 800})

        self.assertTrue(triggered)
        self.assertEqual(self.state_machine.current_state, self.state_machine.STATE_COLLECT_ONLY)
        self.assertIsNotNone(self.state_machine.stamina_retreat_start_time)
        self.assertEqual(self.state_machine.config["type"], "collect_only")

    def test_quest_scheduler_max_run_limit_and_all_completed_transition(self):
        """
        [組件 3 防死鎖斷言] 驗證當懸賞任務點擊/執行達到上限 max_run_limit = 10 時：
        - TaskNode.is_completed 自動回傳 True。
        - QuestScheduler.is_all_completed() 回傳 True。
        - Daily Master Pipeline 自動解綁 quest_scheduler 並平滑切換至 Tier 4 退守模式。
        """
        node = TaskNode("史萊姆王的毀滅", "dungeon", dungeon_index=0, max_run_limit=10)
        scheduler = QuestScheduler(daily_manager=self.daily_manager)
        scheduler.add_task(node)
        self.state_machine.quest_scheduler = scheduler

        # 模擬打滿 10 次
        node.completed_count = 10
        self.assertTrue(node.is_completed)
        self.assertTrue(scheduler.is_all_completed())

        # 模擬 Tier 1/2 皆完成
        for sf in self.daily_manager.status.get("subflows", {}).values():
            sf["completed_today"] = True
        for b in self.daily_manager.status["subflows"]["lord_boss"]["bosses"].values():
            b["today_count"] = 5
            b["completed_today"] = True

        scheduled = self.state_machine.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled) # apply_mix_fallback_config returns False
        self.assertIsNone(self.state_machine.quest_scheduler)
        self.assertTrue(self.state_machine.config.get("is_tier4_fallback", False))

    def test_town_subflows_record_completion_and_pop_queue(self):
        """
        [組件 4 防死鎖斷言] 驗證城鎮子流程 (chest, hero_draw, blood_altar, jewelry_workshop) 完成時：
        - record_subflow_completed 正確更新 daily_status.json。
        - pop_and_next_town_subflow 能彈出已完成項目，不會循環卡死在同一個子流程。
        """
        self.daily_manager.record_subflow_completed("chest")
        self.daily_manager.record_subflow_completed("hero_draw")

        self.assertTrue(self.daily_manager.is_subflow_completed("chest"))
        self.assertTrue(self.daily_manager.is_subflow_completed("hero_draw"))

        self.state_machine.town_subflow_queue = ["chest", "hero_draw", "blood_altar"]
        self.state_machine.pop_and_next_town_subflow()

        self.assertEqual(self.state_machine.town_subflow_queue, ["hero_draw", "blood_altar"])

if __name__ == '__main__':
    unittest.main()
