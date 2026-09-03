import os
import json
import time
import tempfile
import unittest
from unittest.mock import patch

from config import (
    get_bounty_quest_config,
    get_defaults_config,
    set_active_profile,
)
from utils.quest_mapper import QuestMapper, TaskNode, is_quest_allowed
from utils.quest_scheduler import QuestScheduler
from utils.daily_manager import DailyManager


class TestBountyQuestFiltering(unittest.TestCase):
    """
    測試懸賞任務 [bounty_quests] 獨立配置與動態篩選機制。
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mapper = QuestMapper()

    def tearDown(self):
        self.temp_dir.cleanup()
        set_active_profile("native")

    def test_defaults_toml_bounty_quests_config(self):
        """驗證 config/defaults.toml 正確配置全域預設 max_stage=6, max_dungeon=5"""
        defaults = get_defaults_config()
        self.assertIn("bounty_quests", defaults)
        bounty_cfg = defaults["bounty_quests"]
        self.assertEqual(bounty_cfg["max_stage"], 6)
        self.assertEqual(bounty_cfg["max_dungeon"], 5)

    def test_profile_bounty_quests_overlay(self):
        """驗證 sandbox 與 native profile 取得獨立的 [bounty_quests] 配置"""
        sandbox_cfg = get_bounty_quest_config("sandbox")
        self.assertEqual(sandbox_cfg["max_stage"], 4)
        self.assertEqual(sandbox_cfg["max_dungeon"], 4)

        native_cfg = get_bounty_quest_config("native")
        self.assertEqual(native_cfg["max_stage"], 6)
        self.assertEqual(native_cfg["max_dungeon"], 5)

        set_active_profile("sandbox")
        self.assertEqual(get_bounty_quest_config(), {"max_stage": 4, "max_dungeon": 4})

        set_active_profile("native")
        self.assertEqual(get_bounty_quest_config(), {"max_stage": 6, "max_dungeon": 5})

    def test_is_quest_allowed_predicate(self):
        """驗證 is_quest_allowed 純函式對關卡與地下城上限的邊界判定"""
        bounty_cfg = {"max_stage": 4, "max_dungeon": 4}

        # 普通關卡測試 (Stage 1~4 允許，Stage 5~6 拒絕)
        node_stage1 = self.mapper.parse_quest("清除野豬")  # Stage 1
        node_stage4 = self.mapper.parse_quest("清除沙蟲")  # Stage 4
        node_stage5 = self.mapper.parse_quest("清除蛙人")  # Stage 5
        node_stage6 = self.mapper.parse_quest("討伐惡魔")  # Stage 6

        self.assertTrue(is_quest_allowed(node_stage1, bounty_cfg))
        self.assertTrue(is_quest_allowed(node_stage4, bounty_cfg))
        self.assertFalse(is_quest_allowed(node_stage5, bounty_cfg))
        self.assertFalse(is_quest_allowed(node_stage6, bounty_cfg))

        # 地下城測試 (Dungeon 0~4 允許，Dungeon 5 拒絕)
        node_dungeon0 = self.mapper.parse_quest("史萊姆王的毀滅")  # Dungeon 0
        node_dungeon3 = self.mapper.parse_quest("破除遺跡的詛咒")  # Dungeon 3
        node_dungeon4 = self.mapper.parse_quest("終結獄炎統治")    # Dungeon 4
        node_dungeon5 = self.mapper.parse_quest("冰雪洞窟的暴君")  # Dungeon 5

        self.assertTrue(is_quest_allowed(node_dungeon0, bounty_cfg))
        self.assertTrue(is_quest_allowed(node_dungeon3, bounty_cfg))
        self.assertTrue(is_quest_allowed(node_dungeon4, bounty_cfg))
        self.assertFalse(is_quest_allowed(node_dungeon5, bounty_cfg))

        # 忽略任務與空節點
        node_ignored = self.mapper.parse_quest("獵金之蟲")
        self.assertFalse(is_quest_allowed(node_ignored, bounty_cfg))
        self.assertFalse(is_quest_allowed(None, bounty_cfg))

    def test_quest_mapper_sort_quests_filters_with_bounty_config(self):
        """驗證 QuestMapper.sort_quests 傳入 bounty_config 時自動剔除超標任務"""
        raw_list = ["討伐惡魔", "冰雪洞窟的暴君", "清除沙蟲", "破除遺跡的詛咒", "清除野豬"]
        bounty_cfg = {"max_stage": 4, "max_dungeon": 4}

        sorted_filtered = self.mapper.sort_quests(raw_list, bounty_config=bounty_cfg)
        # 討伐惡魔 (Stage 6) 與 冰雪洞窟的暴君 (Dungeon 5) 必須被過濾
        self.assertNotIn("討伐惡魔", sorted_filtered)
        self.assertNotIn("冰雪洞窟的暴君", sorted_filtered)
        self.assertIn("破除遺跡的詛咒", sorted_filtered)
        self.assertIn("清除沙蟲", sorted_filtered)
        self.assertIn("清除野豬", sorted_filtered)

    def test_quest_scheduler_from_daily_status_with_bounty_config(self):
        """驗證 QuestScheduler.from_daily_status 只會排入能力上限內的任務"""
        raw_list = ["討伐惡魔", "冰雪洞窟的暴君", "清除沙蟲", "破除遺跡的詛咒"]
        bounty_cfg = {"max_stage": 4, "max_dungeon": 4}

        scheduler = QuestScheduler.from_daily_status(raw_list, bounty_config=bounty_cfg)
        scheduled_titles = [t.quest_title for t in scheduler.tasks]

        self.assertEqual(scheduled_titles, ["破除遺跡的詛咒", "清除沙蟲"])
        self.assertNotIn("討伐惡魔", scheduled_titles)
        self.assertNotIn("冰雪洞窟的暴君", scheduled_titles)

        # 驗證 get_next_action_node 取得的是首個合法任務 (破除遺跡的詛咒)
        next_task, msg = scheduler.get_next_action_node()
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.quest_title, "破除遺跡的詛咒")

    def test_daily_manager_update_bulletin_board_quests_filtering(self):
        """驗證 DailyManager 在接取任務後清洗 accepted_quests，杜絕超標任務寫入存檔"""
        status_file = os.path.join(self.temp_dir.name, "daily_status.json")
        manager = DailyManager(status_file=status_file, profile="sandbox")

        today_new = ["討伐惡魔", "清除沙蟲", "冰雪洞窟的暴君", "清除野豬"]
        with patch("config.get_bounty_quest_config", return_value={"max_stage": 4, "max_dungeon": 4}):
            result = manager.update_bulletin_board_quests(today_new)

        self.assertNotIn("討伐惡魔", result)
        self.assertNotIn("冰雪洞窟的暴君", result)
        self.assertIn("清除沙蟲", result)
        self.assertIn("清除野豬", result)

        # 驗證持久化 JSON 中也僅存合法任務
        saved_quests = manager.status["subflows"]["bulletin_board"]["accepted_quests"]
        self.assertEqual(saved_quests, result)

    def test_daily_manager_reload_status_if_modified_detects_manual_edit(self):
        """驗證當使用者手動修改 daily_status.json 時，reload_status_if_modified 正確重載最新內容"""
        status_file = os.path.join(self.temp_dir.name, "daily_status.json")
        manager = DailyManager(status_file=status_file, profile="sandbox")
        manager.status["subflows"]["bulletin_board"]["accepted_quests"] = ["清除野豬"]
        manager.save_status()

        # 模擬使用者在外部 (例如 VS Code) 手動修改 JSON 內容
        time.sleep(0.05)  # 確保 mtime 往前推進
        with open(status_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        disk_data["subflows"]["bulletin_board"]["accepted_quests"] = ["清除沙蟲", "破除遺跡的詛咒"]
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(disk_data, f, ensure_ascii=False, indent=2)

        # 呼叫 reload_status_if_modified
        reloaded = manager.reload_status_if_modified()
        self.assertTrue(reloaded)
        self.assertEqual(
            manager.status["subflows"]["bulletin_board"]["accepted_quests"],
            ["破除遺跡的詛咒", "清除沙蟲"]
        )


if __name__ == "__main__":
    unittest.main()
