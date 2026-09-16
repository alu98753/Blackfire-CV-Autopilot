"""Behavior integration tests for Dungeon 8 (巨龍巢穴 / 巨龍之巢) and bounty quest."""

import unittest
from utils.dungeon_catalog import DungeonCatalog
from utils.quest_mapper import QuestMapper, TaskNode
from utils.quest_scheduler import QuestScheduler


class TestDungeon8Integration(unittest.TestCase):
    """Behavior tests for Dungeon 8 catalog, quest mapping, and scheduling."""

    def setUp(self):
        self.mapper = QuestMapper()

    def test_dungeon8_catalog_properties(self):
        """驗證地下城目錄中第 8 關 (巨龍巢穴) 的名稱、圖檔與導航路徑解析"""
        self.assertEqual(DungeonCatalog.get_name(8), "巨龍巢穴")
        self.assertEqual(DungeonCatalog.get_entry_template(8), "dungeons/dragon_lair.png")
        self.assertTrue(DungeonCatalog.is_valid_index(8))

        nav_path = ["common/door.png", "dungeons/dungeon.png", "dungeons/dragon_lair.png"]
        self.assertEqual(DungeonCatalog.resolve_index_from_nav_path(nav_path), 8)

    def test_dragon_lair_quest_resolution(self):
        """驗證「巨龍之巢」與「巨龍巢穴」正確映射為第 8 關地下城任務與 banner_verify_only 策略"""
        for title in ["巨龍之巢", "巨龍巢穴"]:
            node = self.mapper.parse_quest(title)
            self.assertIsNotNone(node, f"Failed to parse {title}")
            self.assertEqual(node.mode_type, "dungeon")
            self.assertEqual(node.dungeon_index, 8)
            self.assertEqual(node.counting_policy, "banner_verify_only")
            self.assertEqual(node.target_count, 20)

            cfg = node.to_config_dict()
            self.assertEqual(cfg["navigation_path"], ["common/door.png", "dungeons/dungeon.png", "dungeons/dragon_lair.png"])
            self.assertEqual(cfg["tier4_dungeon_index"], 8)

    def test_dungeon8_cooldown_reporting(self):
        """驗證第 8 關冷卻時間格式化報告與就緒狀態"""
        now = 1000.0
        cds = {8: now + 2400.0}  # 40 分鐘冷卻 (2400 秒)
        report = DungeonCatalog.format_cooldown_report(cds, target_indices=[8], now_ts=now)
        self.assertFalse(report.has_available)
        self.assertEqual(report.available_indices, [])
        self.assertIn("[巨龍巢穴]: 冷卻中 (40 分 0 秒)", report.summary_str)

        cds_ready = {8: 0.0}
        report_ready = DungeonCatalog.format_cooldown_report(cds_ready, target_indices=[8], now_ts=now)
        self.assertTrue(report_ready.has_available)
        self.assertEqual(report_ready.available_indices, [8])
        self.assertIn("[巨龍巢穴]: 就緒 (可打)", report_ready.summary_str)

    def test_quest_scheduler_prioritizes_dungeon8(self):
        """驗證懸賞任務排程器：地下城優先於普通關卡排定"""
        raw_list = ["討伐惡魔", "巨龍之巢", "清除野豬"]
        bounty_cfg = {"max_stage": 8, "max_dungeon": 8}
        scheduler = QuestScheduler.from_daily_status(raw_list, bounty_config=bounty_cfg)

        scheduled_titles = [t.quest_title for t in scheduler.tasks]
        self.assertIn("巨龍之巢", scheduled_titles)
        self.assertIn("討伐惡魔", scheduled_titles)
        self.assertIn("清除野豬", scheduled_titles)

        next_node, _ = scheduler.get_next_action_node()
        self.assertIsNotNone(next_node)
        self.assertEqual(next_node.quest_title, "巨龍之巢")
        self.assertEqual(next_node.mode_type, "dungeon")
        self.assertEqual(next_node.dungeon_index, 8)


if __name__ == "__main__":
    unittest.main()
