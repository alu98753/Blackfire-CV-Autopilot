import time
import unittest

from utils.dungeon_catalog import DungeonCatalog, DungeonCooldownReport


class TestDungeonCatalog(unittest.TestCase):
    def test_get_name_valid_1_based(self):
        self.assertEqual(DungeonCatalog.get_name(1), "黏糊糊的石窟")
        self.assertEqual(DungeonCatalog.get_name(2), "幽影地穴")
        self.assertEqual(DungeonCatalog.get_name(3), "森林迷宮")
        self.assertEqual(DungeonCatalog.get_name(4), "神秘遺跡")
        self.assertEqual(DungeonCatalog.get_name(5), "幽暗監獄")
        self.assertEqual(DungeonCatalog.get_name(6), "冰雪洞窟")

    def test_get_name_out_of_bounds_fallback(self):
        self.assertEqual(DungeonCatalog.get_name(0), "地下城")
        self.assertEqual(DungeonCatalog.get_name(7), "地下城")
        self.assertEqual(DungeonCatalog.get_name(-1), "地下城")
        self.assertEqual(DungeonCatalog.get_name(None, default="未知"), "未知")
        self.assertEqual(DungeonCatalog.get_name("invalid", default="未知"), "未知")

    def test_get_entry_template_valid_and_fallback(self):
        self.assertEqual(DungeonCatalog.get_entry_template(1), "dungeons/Slime_entry.png")
        self.assertEqual(DungeonCatalog.get_entry_template(6), "dungeons/Ice_entry.png")
        self.assertEqual(DungeonCatalog.get_entry_template(0), "dungeons/Ice_entry.png")
        self.assertEqual(DungeonCatalog.get_entry_template(7), "dungeons/Ice_entry.png")
        self.assertEqual(DungeonCatalog.get_entry_template(None), "dungeons/Ice_entry.png")

    def test_resolve_index_from_nav_path(self):
        path1 = ["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]
        self.assertEqual(DungeonCatalog.resolve_index_from_nav_path(path1), 1)

        path6 = ["common/door.png", "dungeons/dungeon.png", "dungeons/Ice_entry.png"]
        self.assertEqual(DungeonCatalog.resolve_index_from_nav_path(path6), 6)

        path_empty = []
        self.assertIsNone(DungeonCatalog.resolve_index_from_nav_path(path_empty))

        path_other = ["stages/first_stage.png"]
        self.assertIsNone(DungeonCatalog.resolve_index_from_nav_path(path_other))

    def test_is_valid_index(self):
        self.assertTrue(DungeonCatalog.is_valid_index(1))
        self.assertTrue(DungeonCatalog.is_valid_index(6))
        self.assertFalse(DungeonCatalog.is_valid_index(0))
        self.assertFalse(DungeonCatalog.is_valid_index(7))
        self.assertFalse(DungeonCatalog.is_valid_index("1"))
        self.assertFalse(DungeonCatalog.is_valid_index(None))

    def test_build_default_cooldowns(self):
        cds = DungeonCatalog.build_default_cooldowns()
        self.assertEqual(list(cds.keys()), [1, 2, 3, 4, 5, 6])
        self.assertTrue(all(v == 0.0 for v in cds.values()))

    def test_format_cooldown_report_all_ready(self):
        cds = {i: 0.0 for i in range(1, 7)}
        report = DungeonCatalog.format_cooldown_report(cds, target_indices=[1, 2, 3, 4, 5, 6])
        self.assertIsInstance(report, DungeonCooldownReport)
        self.assertTrue(report.has_available)
        self.assertEqual(len(report.available_names), 6)
        self.assertEqual(report.available_indices, [1, 2, 3, 4, 5, 6])
        self.assertIn("[黏糊糊的石窟]: 就緒 (可打)", report.summary_str)
        self.assertIn("[冰雪洞窟]: 就緒 (可打)", report.summary_str)

    def test_format_cooldown_report_mixed_and_infinite(self):
        now = 1000.0
        cds = {
            1: now + 300.0,      # 冷卻中 5 分鐘
            2: float("inf"),     # 永久不可打
            3: 0.0,              # 就緒
            4: now + 120.0,      # 冷卻中 2 分鐘
            5: 0.0,              # 就緒
            6: now + 60.0,       # 冷卻中 1 分鐘 (最短)
        }
        report = DungeonCatalog.format_cooldown_report(cds, target_indices=[1, 2, 3, 4, 5, 6], now_ts=now)
        self.assertTrue(report.has_available)
        self.assertEqual(report.available_names, ["森林迷宮", "幽暗監獄"])
        self.assertEqual(report.available_indices, [3, 5])
        self.assertIn("[黏糊糊的石窟]: 冷卻中 (5 分 0 秒)", report.summary_str)
        self.assertIn("[幽影地穴]: 永久不可打", report.summary_str)
        self.assertIn("[森林迷宮]: 就緒 (可打)", report.summary_str)
        self.assertEqual(report.min_remaining_seconds, 60.0)

    def test_format_cooldown_report_ignores_invalid_indices_safely(self):
        # 測試即使傳入包含 0 或 99 的異常索引，絕不崩潰
        report = DungeonCatalog.format_cooldown_report({}, target_indices=[0, 1, 99])
        self.assertEqual(report.available_names, ["黏糊糊的石窟"])
        self.assertEqual(report.available_indices, [1])


if __name__ == "__main__":
    unittest.main()
