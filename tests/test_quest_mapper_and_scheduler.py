import unittest
import os
import sys

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.quest_mapper import QuestMapper, TaskNode
from utils.quest_scheduler import QuestScheduler

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class TestQuestMapperAndScheduler(unittest.TestCase):
    """
    測試懸賞任務解析 (QuestMapper) 與動態排程器 (QuestScheduler)。
    驗證用戶提供的 5 種經典每日懸賞任務情境：
    1. 清除骷髏 (骷髏 x 10)
    2. 擊敗冰元素 (冰元素 x 10)
    3. 擊殺首領 (首領 x 5)
    4. 清除野豬 (野豬 x 10)
    5. 史萊姆王的毀滅 ([史萊姆王] x 1)
    """
    def setUp(self):
        self.mapper = QuestMapper()
        self.scheduler = QuestScheduler()

    def test_parse_five_user_quests(self):
        """
        測試解析用戶圖片中的 5 個每日懸賞任務條件、指令與計數策略 (counting_policy)。
        """
        # 1. 圖片 1: 清除骷髏 (可精確計數)
        node1 = self.mapper.parse_quest("清除骷髏", "骷髏在戰場上肆虐...", "擊殺: 骷髏 x 10")
        self.assertEqual(node1.mode_type, "dungeon")
        self.assertEqual(node1.dungeon_index, 3)
        self.assertEqual(node1.target_count, 10)
        self.assertEqual(node1.counting_policy, TaskNode.POLICY_DETERMINISTIC)
        self.assertIn("--mode dungeon --dungeon 4", node1.to_cli_args())

        # 2. 圖片 2: 擊敗冰元素 (可精確計數)
        node2 = self.mapper.parse_quest("擊敗冰元素", "冰元素棲息在寒冷地區...", "擊殺: 冰元素 x 10")
        self.assertEqual(node2.mode_type, "stage")
        self.assertEqual(node2.stage_level, 6)
        self.assertEqual(node2.sub_stage, "first")
        self.assertEqual(node2.target_count, 10)
        self.assertEqual(node2.counting_policy, TaskNode.POLICY_DETERMINISTIC)
        self.assertIn("--mode stage --stage 6 --sub first", node2.to_cli_args())

        # 3. 圖片 3: 擊殺首領 (預設固定 10 次)
        node3 = self.mapper.parse_quest("擊殺首領", "各種強大的首領在附近地區活動...", "擊殺: 首領 x 5")
        self.assertEqual(node3.mode_type, "generic_boss")
        self.assertEqual(node3.target_count, 10)

        # 4. 圖片 4: 清除野豬 (可精確計數)
        node4 = self.mapper.parse_quest("清除野豬", "野豬在肆意橫行...", "擊殺: 野豬 x 10")
        self.assertEqual(node4.mode_type, "stage")
        self.assertEqual(node4.stage_level, 1)
        self.assertEqual(node4.sub_stage, "final")
        self.assertEqual(node4.target_count, 10)
        self.assertEqual(node4.counting_policy, TaskNode.POLICY_DETERMINISTIC)
        self.assertIn("--mode stage --stage 1 --sub final", node4.to_cli_args())

        # 5. 圖片 5: 史萊姆王的毀滅 (不確定 Boss 任務 -> POLICY_BANNER_VERIFY, 固定 10 次)
        node5 = self.mapper.parse_quest("史萊姆王的毀滅", "在地下城黏糊糊的石窟最深處...", "擊殺: [史萊姆王] x 1")
        self.assertEqual(node5.mode_type, "dungeon")
        self.assertEqual(node5.dungeon_index, 0)
        self.assertEqual(node5.target_count, 10)
        self.assertEqual(node5.counting_policy, TaskNode.POLICY_BANNER_VERIFY)
        self.assertIn("--mode dungeon --dungeon 1", node5.to_cli_args())

        # 6. 不打的任務 (IGNORED_QUESTS): 測試 完成任何地下城 / 敵人剿滅 / 獵金之蟲
        node_ignore1 = self.mapper.parse_quest("完成任何地下城", "", "")
        node_ignore2 = self.mapper.parse_quest("獵金之蟲", "", "")
        self.assertEqual(node_ignore1.mode_type, "ignored")
        self.assertEqual(node_ignore2.mode_type, "ignored")

    def test_dynamic_scheduler_workflow_and_task_piggybacking(self):
        """
        測試 QuestScheduler 的動態 Maintain 流程：
        - 納入 5 個任務。
        - 優先產出地下城專屬指令。
        - 通過 counting_policy 保障：POLICY_BANNER_VERIFY 任務不會被 record_kill_event 誤計數。
        """
        # 1. 載入 5 個任務
        quests = [
            ("史萊姆王的毀滅", "黏糊糊的石窟...", "擊殺: [史萊姆王] x 1"),
            ("清除骷髏", "骷髏在戰場上...", "擊殺: 骷髏 x 10"),
            ("擊敗冰元素", "冰元素棲息在...", "擊殺: 冰元素 x 10"),
            ("擊殺首領", "各種強大的首領...", "擊殺: 首領 x 5"),
            ("清除野豬", "野豬在肆意...", "擊殺: 野豬 x 10"),
        ]
        for title, desc, req in quests:
            node = self.mapper.parse_quest(title, desc, req)
            self.scheduler.add_task(node)

        self.assertEqual(len(self.scheduler.get_pending_tasks()), 5)

        # 2. 第一次取得啟動指令 ➔ 應優先傳回地下城 1 (史萊姆王)
        cmd1, msg1 = self.scheduler.get_next_action_config()
        self.assertIn("--mode dungeon --dungeon 1", cmd1)
        print(f"\n[動態排程 step 1] 指令: {cmd1} | 說明: {msg1}")

        # 3. 模擬通關地下城 1
        self.scheduler.record_kill_event(enemy_name="史萊姆王", is_boss=True, dungeon_index=0, kill_count=1)

        # 斷言：史萊姆王的毀滅屬於 POLICY_BANNER_VERIFY，record_kill_event 絕不自動加算進度！
        slime_task = [t for t in self.scheduler.tasks if t.quest_title == "史萊姆王的毀滅"][0]
        boss_task = [t for t in self.scheduler.tasks if t.quest_title == "擊殺首領"][0]
        self.assertFalse(slime_task.is_completed)
        self.assertEqual(boss_task.completed_count, 1)

        # 模擬彈窗領獎成功核銷史萊姆王任務
        self.scheduler.remove_completed_quest("史萊姆王的毀滅")

        # 4. 第二次取得啟動指令 ➔ 應傳回地下城 4 (神秘遺跡 - 清除骷髏)
        cmd2, msg2 = self.scheduler.get_next_action_config()
        self.assertIn("--mode dungeon --dungeon 4", cmd2)
        print(f"[動態排程 step 2] 指令: {cmd2} | 說明: {msg2}")

        # 模擬打完地下城 4 清除骷髏任務 (DETERMINISTIC_QUESTS 自動加算完成)
        self.scheduler.record_kill_event(enemy_name="骷髏", dungeon_index=3, kill_count=10)

        # 5. 第三次取得啟動指令 ➔ 應傳回關卡 6 第一關 (冰元素)
        cmd3, msg3 = self.scheduler.get_next_action_config()
        self.assertIn("--mode stage --stage 6 --sub first", cmd3)
        print(f"[動態排程 step 3] 指令: {cmd3} | 說明: {msg3}")

        # 模擬擊殺 10 隻冰元素完成任務
        self.scheduler.record_kill_event(enemy_name="冰元素", stage_level=6, sub_stage="first", kill_count=10)

        # 6. 第四次取得啟動指令 ➔ 應傳回關卡 1 魔王關 (野豬)
        cmd4, msg4 = self.scheduler.get_next_action_config()
        self.assertIn("--mode stage --stage 1 --sub final", cmd4)
        print(f"[動態排程 step 4] 指令: {cmd4} | 說明: {msg4}")

        # 模擬打野豬魔王關 9 次 (每次算 1 隻野豬與 1 個 Boss，加算前次史萊姆 1 次共 10 次 Boss)
        for _ in range(9):
            self.scheduler.record_kill_event(enemy_name="野豬", is_boss=True, stage_level=1, sub_stage="final", kill_count=1)

        # 首領已累積 1(史萊姆) + 9(野豬) = 10 隻！首領任務自動完成！
        self.assertTrue(boss_task.is_completed)

        # 模擬打完剩下的 1 隻野豬 (累計 10 隻野豬)
        self.scheduler.record_kill_event(enemy_name="野豬", stage_level=1, sub_stage="final", kill_count=1)


        # 7. 最終斷言：所有懸賞任務 100% 完成！
        self.assertTrue(self.scheduler.is_all_completed())
        cmd_end, msg_end = self.scheduler.get_next_action_config()
        self.assertIsNone(cmd_end)
        self.assertIn("100% 完成", msg_end)
        print(f"[動態排程 最終狀態] {msg_end}")

    def test_quest_sorting_priority(self):
        """
        驗證 QuestMapper.sort_quests 排序演算法：
        - 確定性 (DETERMINISTIC) > 彈窗核銷 (BANNER_VERIFY) > 忽略 (IGNORED).
        - 地下城 (dungeon) > 關卡 (stage).
        - idx / stage_level 大者排前面 (dungeon 3 > 2 > 0; stage 5 > 4).
        """
        unordered_quests = [
            "史萊姆王的毀滅",  # BANNER_VERIFY (dungeon 0)
            "清除沙蟲",       # DETERMINISTIC (stage 4)
            "破除森林的枷鎖",  # BANNER_VERIFY (dungeon 2)
            "清除樹人",       # DETERMINISTIC (dungeon 2)
            "清除蛙人",       # DETERMINISTIC (stage 5)
            "清除骷髏",       # DETERMINISTIC (dungeon 3)
            "清除史萊姆",     # DETERMINISTIC (dungeon 0)
            "敵人剿滅",       # IGNORED
            "冰雪洞窟的暴君",  # BANNER_VERIFY (dungeon 4)
        ]
        sorted_quests = self.mapper.sort_quests(unordered_quests)

        expected_order = [
            "清除骷髏",       # DETERMINISTIC, dungeon 3
            "清除樹人",       # DETERMINISTIC, dungeon 2
            "清除史萊姆",     # DETERMINISTIC, dungeon 0
            "清除蛙人",       # DETERMINISTIC, stage 5
            "清除沙蟲",       # DETERMINISTIC, stage 4
            "冰雪洞窟的暴君",  # BANNER_VERIFY, dungeon 4
            "破除森林的枷鎖",  # BANNER_VERIFY, dungeon 2
            "史萊姆王的毀滅",  # BANNER_VERIFY, dungeon 0
        ]
        self.assertEqual(sorted_quests, expected_order)

    def test_dungeon_cooldown_skipping_and_resumption(self):
        """
        驗證地下城冷卻時動態跳過並順延執行次優先任務，且在冷卻結束後自動恢復最高優先任務。
        - 任務 1: 清除骷髏 (Dungeon 3)
        - 任務 2: 清除樹人 (Dungeon 2)
        - 任務 3: 清除蛙人 (Stage 5)
        """
        import time
        quests = ["清除骷髏", "清除樹人", "清除蛙人"]
        sorted_quests = self.mapper.sort_quests(quests)
        scheduler = QuestScheduler.from_daily_status(sorted_quests)

        now = time.time()
        # 1. 初始狀態無冷卻 ➔ 應選取第 1 優先任務 [清除骷髏] (Dungeon 4, index 3)
        cmd1, msg1 = scheduler.get_next_action_config(dungeon_cooldowns={}, now_ts=now)
        self.assertIn("--dungeon 4", cmd1)

        # 2. 設 Dungeon 3 (神秘遺跡) 冷卻 1800 秒 ➔ 應自動跳過並選取第 2 優先任務 [清除樹人] (Dungeon 3, index 2)
        cd_map_1 = {3: now + 1800.0}
        cmd2, msg2 = scheduler.get_next_action_config(dungeon_cooldowns=cd_map_1, now_ts=now)
        self.assertIn("--dungeon 3", cmd2)

        # 3. 設 Dungeon 3 與 Dungeon 2 皆在冷卻中 ➔ 應自動跳過所有地下城並選取關卡任務 [清除蛙人] (Stage 5)
        cd_map_2 = {3: now + 1800.0, 2: now + 1800.0}
        cmd3, msg3 = scheduler.get_next_action_config(dungeon_cooldowns=cd_map_2, now_ts=now)
        self.assertIn("--mode stage --stage 5", cmd3)

        # 4. 模擬 1801 秒後，Dungeon 3 冷卻結束 ➔ 再次查詢時應自動搶先恢復選取最高優先任務 [清除骷髏] (Dungeon 4)
        cmd4, msg4 = scheduler.get_next_action_config(dungeon_cooldowns=cd_map_1, now_ts=now + 1801.0)
        self.assertIn("--dungeon 4", cmd4)

    def test_task_node_batch_completion_and_max_limit(self):
        """驗證每 4 次戰鬥 (mod 4 == 0) 觸發離場領獎批次，且最多 10 次上限自動 completed"""
        node = self.mapper.parse_quest("清除野豬")
        self.assertFalse(node.is_batch_completed())
        self.assertFalse(node.is_completed)

        node.completed_count = 1
        self.assertFalse(node.is_batch_completed())

        node.completed_count = 4
        self.assertTrue(node.is_batch_completed())
        self.assertFalse(node.is_completed)

        node.completed_count = 5
        self.assertFalse(node.is_batch_completed())

        node.completed_count = 8
        self.assertTrue(node.is_batch_completed())
        self.assertFalse(node.is_completed)

        node.completed_count = 10
        self.assertTrue(node.is_batch_completed())
        self.assertTrue(node.is_completed)


if __name__ == "__main__":
    unittest.main()



