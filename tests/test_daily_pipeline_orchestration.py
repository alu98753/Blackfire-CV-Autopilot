import os
import json
import time
import unittest
import tempfile
from unittest.mock import MagicMock
from utils.daily_manager import DailyManager, DEFAULT_DAILY_STATUS
from states.state_machine import GameStateMachine
from utils.quest_scheduler import QuestScheduler

class TestDailyPipelineOrchestration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_json_path = os.path.join(self.test_dir, "test_daily_status.json")
        sample_status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
        sample_status["subflows"]["bulletin_board"]["accepted_quests"] = [
            "清除樹人",
            "清除史萊姆",
            "史萊姆王的毀滅"
        ]
        with open(self.test_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_status, f, ensure_ascii=False, indent=2)

        self.daily_mgr = DailyManager(data_dir=self.test_dir, status_file="test_daily_status.json")

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tier1_town_subflows_priority_order(self):
        """驗證 Tier 1 一極優先 (每日一次性城鎮速領) 順序: chest -> hero_draw -> blood_altar (+ jewelry_workshop)"""
        pending = self.daily_mgr.get_pending_town_subflows()
        self.assertEqual(pending, ["chest", "hero_draw", "blood_altar", "jewelry_workshop"])

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.town_subflow_queue, ["hero_draw", "blood_altar", "jewelry_workshop"])

    def test_tier2_lord_boss_priority_over_bulletin_board(self):
        """驗證 Tier 2 領主 Boss 討伐優先級大於 bulletin_board 懸賞告示牌"""
        # 手動標示 Tier 1 子流程已完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")

        # 斷言 Tier 1 已空
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), [])

        # 斷言尚有可用 Lord Boss (預設狀態蜘蛛與惡靈皆為 0/5，冷卻滿)
        self.assertTrue(self.daily_mgr.has_available_lord_boss())

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 觸發大流水線調度
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        # 斷言優先發起 lord_boss 流水線並切換至 STATE_LORD_BOSS
        self.assertEqual(sm.town_subflow_queue, [])
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

    def test_lord_boss_preemptive_interruption_during_quests(self):
        """驗證當懸賞戰鬥完成後，若 Lord Boss 冷卻結束，會立刻搶先插隊執行 lord_boss"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 模擬 Lord Boss 剛剛冷卻完成
        now_ts = time.time()
        self.daily_mgr.update_boss_cooldown("lord_spider", 0.0, now_ts=now_ts)

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)


    def test_tier4_fallback_mix_mode_when_all_daily_completed(self):
        """驗證當速領、Boss (已滿5次) 與 8 個懸賞全完成時，退守 mix 模式 (冰雪洞窟 + 關卡 6-1)"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")

        # 手動將 Boss 次數填滿
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True
        self.daily_mgr.status["subflows"]["lord_boss"]["completed_today"] = True

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 將懸賞任務全數完成
        for t in scheduler.tasks:
            t.completed_count = t.target_count

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled)
        self.assertIsNone(sm.quest_scheduler)
        self.assertEqual(sm.config["type"], "mix")
        self.assertEqual(sm.config["stage_name"], "冰雪洞窟 (first)")
        self.assertIn("Ice_entry.png", sm.config["navigation_path"][-1])


if __name__ == "__main__":
    unittest.main()
