import os
import json
import unittest
from unittest.mock import MagicMock
from utils.quest_mapper import QuestMapper, TaskNode
from utils.quest_scheduler import QuestScheduler
from utils.daily_manager import DailyManager, DEFAULT_DAILY_STATUS
from states.state_machine import GameStateMachine

class TestQuestStateMachineIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data_quest")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_json_path = os.path.join(self.test_dir, "test_daily_status.json")
        
        # 準備模擬數據
        sample_status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
        sample_status["subflows"]["bulletin_board"]["accepted_quests"] = [
            "清除樹人",
            "清除史萊姆",
            "史萊姆王的毀滅",
            "擊殺首領"
        ]
        with open(self.test_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_status, f, ensure_ascii=False, indent=2)

        self.daily_mgr = DailyManager(data_dir=self.test_dir, status_file="test_daily_status.json")

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_factory_and_summary_print(self):
        """驗證 from_daily_status 工廠方法與控制台印出機制"""
        accepted = self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"]
        scheduler = QuestScheduler.from_daily_status(accepted)
        self.assertEqual(len(scheduler.tasks), 4)
        
        pending = scheduler.get_pending_tasks()
        self.assertEqual(len(pending), 4)

    def test_load_quest_scheduler_from_daily_manager(self):
        """驗證 DailyManager 載入 QuestScheduler"""
        scheduler = self.daily_mgr.load_quest_scheduler()
        self.assertIsNotNone(scheduler)
        self.assertEqual(len(scheduler.tasks), 4)

    def test_task_piggybacking_record_kill_event(self):
        """驗證事件廣播同步更新多個相關任務 (Piggybacking)"""
        scheduler = self.daily_mgr.load_quest_scheduler()
        
        # 模擬擊殺史萊姆王 (同時滿足史萊姆王的毀滅與通用首領擊殺)
        scheduler.record_kill_event(enemy_name="史萊姆王", is_boss=True, dungeon_index=0)
        
        tasks_map = {t.quest_title: t for t in scheduler.tasks}
        self.assertTrue(tasks_map["史萊姆王的毀滅"].is_completed)
        self.assertTrue(tasks_map["擊殺首領"].is_completed)

    def test_remove_accepted_quest_from_json(self):
        """驗證 completed 任務從 daily_status.json 的 accepted_quests 中成功移除"""
        self.assertTrue("清除樹人" in self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"])
        
        removed = self.daily_mgr.remove_accepted_quest("清除樹人")
        self.assertTrue(removed)
        
        # 重新開啟驗證持久化檔案
        with open(self.test_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("清除樹人", data["subflows"]["bulletin_board"]["accepted_quests"])

    def test_state_machine_attach_and_advance(self):
        """驗證 GameStateMachine 掛載 QuestScheduler 與目標推進"""
        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)
        self.assertEqual(sm.quest_scheduler, scheduler)

        # 模擬完成全部任務
        for t in scheduler.tasks:
            t.completed_count = t.target_count

    def test_unknown_quest_recording(self):
        """驗證未定義/無法映射的懸賞任務會被自動記錄至 unknown_quests 陣列"""
        self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"].append("未知神秘任務_XYZ")
        scheduler = self.daily_mgr.load_quest_scheduler()

        # 斷言：未定義任務不加入主執行佇列
        task_titles = [t.quest_title for t in scheduler.tasks]
        self.assertNotIn("未知神秘任務_XYZ", task_titles)

    def test_unknown_quests_persistence_and_daily_reset_preservation(self):
        """驗證 unknown_quests 僅會增量 append (且去重)，並在 08:05 跨日重置時絕不清空"""
        self.daily_mgr.record_unknown_quest("未知任務_A")
        self.daily_mgr.record_unknown_quest("未知任務_B")
        self.daily_mgr.record_unknown_quest("未知任務_A")  # 再次寫入，測試去重/不重複增加

        bb = self.daily_mgr.status["subflows"]["bulletin_board"]
        self.assertEqual(bb["unknown_quests"], ["未知任務_A", "未知任務_B"])

        # 模擬跨日 08:05 重置
        self.daily_mgr.check_and_reset_daily(force=True)

        # 重新從硬碟讀取 json 狀態檔案
        with open(self.test_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        loaded_unknowns = data["subflows"]["bulletin_board"].get("unknown_quests", [])
        self.assertEqual(loaded_unknowns, ["未知任務_A", "未知任務_B"])
        self.assertIn("未知任務_A", loaded_unknowns)
        self.assertIn("未知任務_B", loaded_unknowns)

if __name__ == "__main__":
    unittest.main()


