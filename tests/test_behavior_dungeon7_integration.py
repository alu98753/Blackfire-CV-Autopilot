"""Behavior integration tests for Dungeon 7 (獸人地堡) and bounty quest (血角終結者)."""

import unittest
from utils.dungeon_catalog import DungeonCatalog
from utils.quest_mapper import QuestMapper, TaskNode
from utils.quest_scheduler import QuestScheduler


class TestDungeon7Integration(unittest.TestCase):
    """Behavior tests for Dungeon 7 catalog, quest mapping, and scheduling."""

    def setUp(self):
        self.mapper = QuestMapper()

    def test_dungeon7_catalog_properties(self):
        """驗證地下城目錄中第 7 關 (獸人地堡) 的名稱、圖檔與導航路徑解析"""
        self.assertEqual(DungeonCatalog.get_name(7), "獸人地堡")
        self.assertEqual(DungeonCatalog.get_entry_template(7), "dungeons/orc_bunker.png")
        self.assertTrue(DungeonCatalog.is_valid_index(7))

        nav_path = ["common/door.png", "dungeons/dungeon.png", "dungeons/orc_bunker.png"]
        self.assertEqual(DungeonCatalog.resolve_index_from_nav_path(nav_path), 7)

    def test_bloodhorn_terminator_quest_resolution(self):
        """驗證「血角終結者」與「獸人地堡」正確映射為第 7 關地下城任務與 banner_verify_only 策略"""
        node = self.mapper.parse_quest("血角終結者")
        self.assertIsNotNone(node)
        self.assertEqual(node.mode_type, "dungeon")
        self.assertEqual(node.dungeon_index, 7)
        self.assertEqual(node.counting_policy, "banner_verify_only")
        self.assertEqual(node.target_count, 20)

        cfg = node.to_config_dict()
        self.assertEqual(cfg["navigation_path"], ["common/door.png", "dungeons/dungeon.png", "dungeons/orc_bunker.png"])
        self.assertEqual(cfg["tier4_dungeon_index"], 7)

        node_name = self.mapper.parse_quest("獸人地堡")
        self.assertIsNotNone(node_name)
        self.assertEqual(node_name.mode_type, "dungeon")
        self.assertEqual(node_name.dungeon_index, 7)

    def test_dungeon7_cooldown_reporting(self):
        """驗證第 7 關冷卻時間格式化報告與就緒狀態"""
        now = 1000.0
        cds = {7: now + 2100.0}  # 35 分鐘冷卻 (2100 秒)
        report = DungeonCatalog.format_cooldown_report(cds, target_indices=[7], now_ts=now)
        self.assertFalse(report.has_available)
        self.assertEqual(report.available_indices, [])
        self.assertIn("[獸人地堡]: 冷卻中 (35 分 0 秒)", report.summary_str)

        cds_ready = {7: 0.0}
        report_ready = DungeonCatalog.format_cooldown_report(cds_ready, target_indices=[7], now_ts=now)
        self.assertTrue(report_ready.has_available)
        self.assertEqual(report_ready.available_indices, [7])
        self.assertIn("[獸人地堡]: 就緒 (可打)", report_ready.summary_str)

    def test_quest_scheduler_prioritizes_dungeon7(self):
        """驗證懸賞任務排程器：確定性地下城/Boss地下城依照優先順序正確排定"""
        raw_list = ["討伐惡魔", "血角終結者", "清除野豬"]
        bounty_cfg = {"max_stage": 7, "max_dungeon": 7}
        scheduler = QuestScheduler.from_daily_status(raw_list, bounty_config=bounty_cfg)

        scheduled_titles = [t.quest_title for t in scheduler.tasks]
        self.assertIn("血角終結者", scheduled_titles)
        self.assertIn("討伐惡魔", scheduled_titles)
        self.assertIn("清除野豬", scheduled_titles)

        # 驗證首個可執行的 action node
        next_node, _ = scheduler.get_next_action_node()
        self.assertIsNotNone(next_node)
        # 地下城 (血角終結者) 優先於普通關卡 (討伐惡魔 / 清除野豬)
        self.assertEqual(next_node.quest_title, "血角終結者")
        self.assertEqual(next_node.mode_type, "dungeon")
        self.assertEqual(next_node.dungeon_index, 7)


if __name__ == "__main__":
    unittest.main()
