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
        測試解析用戶圖片中的 5 個每日懸賞任務條件與指令產生。
        """
        # 1. 圖片 1: 清除骷髏 (現在一對一對應至地下城 #4 神秘遺跡)
        node1 = self.mapper.parse_quest("清除骷髏", "骷髏在戰場上肆虐...", "擊殺: 骷髏 x 10")
        self.assertEqual(node1.mode_type, "dungeon")
        self.assertEqual(node1.dungeon_index, 3)
        self.assertEqual(node1.target_count, 10)
        self.assertIn("--mode dungeon --dungeon 4", node1.to_cli_args())

        # 2. 圖片 2: 擊敗冰元素
        node2 = self.mapper.parse_quest("擊敗冰元素", "冰元素棲息在寒冷地區...", "擊殺: 冰元素 x 10")
        self.assertEqual(node2.mode_type, "stage")
        self.assertEqual(node2.stage_level, 6)
        self.assertEqual(node2.sub_stage, "first")
        self.assertEqual(node2.target_count, 10)
        self.assertIn("--mode stage --stage 6 --sub first", node2.to_cli_args())

        # 3. 圖片 3: 擊殺首領
        node3 = self.mapper.parse_quest("擊殺首領", "各種強大的首領在附近地區活動...", "擊殺: 首領 x 5")
        self.assertEqual(node3.mode_type, "generic_boss")
        self.assertEqual(node3.target_count, 5)

        # 4. 圖片 4: 清除野豬
        node4 = self.mapper.parse_quest("清除野豬", "野豬在肆意橫行...", "擊殺: 野豬 x 10")
        self.assertEqual(node4.mode_type, "stage")
        self.assertEqual(node4.stage_level, 1)
        self.assertEqual(node4.sub_stage, "final")
        self.assertEqual(node4.target_count, 10)
        self.assertIn("--mode stage --stage 1 --sub final", node4.to_cli_args())

        # 5. 圖片 5: 史萊姆王的毀滅
        node5 = self.mapper.parse_quest("史萊姆王的毀滅", "在地下城黏糊糊的石窟最深處...", "擊殺: [史萊姆王] x 1")
        self.assertEqual(node5.mode_type, "dungeon")
        self.assertEqual(node5.dungeon_index, 0)
        self.assertEqual(node5.target_count, 1)
        self.assertIn("--mode dungeon --dungeon 1", node5.to_cli_args())

    def test_dynamic_scheduler_workflow_and_task_piggybacking(self):
        """
        測試 QuestScheduler 的動態 Maintain 流程：
        - 納入 5 個任務。
        - 優先產出地下城專屬指令。
        - 完成地下城史萊姆王時，自動併行更新「擊殺首領」進度 (Piggybacking)！
        - 依序完成所有任務直至 is_all_completed == True。
        """
        # 1. 載入 5 個任務 (史萊姆王放在第一個)
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

        # 3. 模擬通關地下城 1 (黏糊糊的石窟, 擊殺史萊姆王 x 1)
        self.scheduler.record_kill_event(enemy_name="史萊姆王", is_boss=True, dungeon_index=0, kill_count=1)

        # 斷言：史萊姆王任務已完成！且首領任務計數自動增為 1/5 (Task Piggybacking)！
        slime_task = [t for t in self.scheduler.tasks if t.quest_title == "史萊姆王的毀滅"][0]
        boss_task = [t for t in self.scheduler.tasks if t.quest_title == "擊殺首領"][0]
        self.assertTrue(slime_task.is_completed)
        self.assertEqual(boss_task.completed_count, 1)

        # 4. 第二次取得啟動指令 ➔ 應傳回關卡 1 (清除骷髏)
        cmd2, msg2 = self.scheduler.get_next_action_config()
        self.assertIn("--mode stage --stage 1 --sub first", cmd2)
        print(f"[動態排程 step 2] 指令: {cmd2} | 說明: {msg2}")

        # 模擬擊殺 10 隻骷髏完成任務
        self.scheduler.record_kill_event(enemy_name="骷髏", stage_level=1, sub_stage="first", kill_count=10)

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

        # 模擬打野豬魔王關 4 次 (每次算 1 隻野豬與 1 個 Boss)
        for _ in range(4):
            self.scheduler.record_kill_event(enemy_name="野豬", is_boss=True, stage_level=1, sub_stage="final", kill_count=1)

        # 剩餘野豬 6 隻，首領已累積 1(史萊姆) + 4(野豬) = 5 隻！首領任務自動完成！
        self.assertTrue(boss_task.is_completed)

        # 模擬打完剩下的 6 隻野豬
        self.scheduler.record_kill_event(enemy_name="野豬", stage_level=1, sub_stage="final", kill_count=6)

        # 7. 最終斷言：所有懸賞任務 100% 完成！
        self.assertTrue(self.scheduler.is_all_completed())
        cmd_end, msg_end = self.scheduler.get_next_action_config()
        self.assertIsNone(cmd_end)
        self.assertIn("100% 完成", msg_end)
        print(f"[動態排程 最終狀態] {msg_end}")

if __name__ == "__main__":
    unittest.main()
