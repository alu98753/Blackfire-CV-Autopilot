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

    def test_user_reported_typos_normalization(self):
        """
        驗證用戶回報的真實 EasyOCR 錯別字自動清洗與正名對齊。
        """
        from utils.quest_mapper import normalize_quest_title
        self.assertEqual(normalize_quest_title("史萊姆王的致滅"), "史萊姆王的毀滅")
        self.assertEqual(normalize_quest_title("消滅蛛王與蛛俊"), "消滅蛛王與蛛後")
        self.assertEqual(normalize_quest_title("蛛后之死"), "蛛後之死")
        self.assertEqual(normalize_quest_title("擎殺直領"), "擊殺首領")
        node_boss = self.mapper.parse_quest("擎殺直領")
        self.assertEqual(node_boss.mode_type, "ignored")
        self.assertEqual(normalize_quest_title("討伐忠魔"), "討伐惡魔")
        node_demon = self.mapper.parse_quest("討伐忠魔")
        self.assertEqual(node_demon.mode_type, "stage")
        self.assertEqual(node_demon.stage_level, 6)
        self.assertEqual(node_demon.sub_stage, "six")
        self.assertIn("--mode stage --stage 6 --sub six", node_demon.to_cli_args())
        self.assertEqual(normalize_quest_title("清除樹入"), "清除樹人")
        self.assertEqual(normalize_quest_title("害山詛咒"), "雪山詛咒")
        node_snow = self.mapper.parse_quest("害山詛咒")
        self.assertEqual(node_snow.mode_type, "ignored")

    def test_missing_quest_rules_json_raises_value_error(self):
        """
        [防呆斷言] 驗證當 config/quest_rules.json 不存在或 JSON 損壞時，
        QuestMapper 初始化或載入必須顯式拋出 ValueError。
        """
        fake_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "non_existent_rules.json")
        with self.assertRaises(ValueError):
            QuestMapper(rules_file=fake_path)

    def test_dynamic_hot_reload_from_quest_rules_json(self):
        """
        [熱重載測試] 驗證當在運行過程中修改 config/quest_rules.json 檔期內容時，
        QuestMapper 能秒級感知並重載新規則，無需重新啟動程式。
        """
        test_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch", "test_hot_reload_rules.json")
        os.makedirs(os.path.dirname(test_json), exist_ok=True)
        import json, time

        initial_data = {
            "deterministic_quests": ["清除骷髏"],
            "banner_verify_quests": [],
            "ignored_quests": [],
            "typo_groups": {},
            "dungeon_rules": [{"pattern": "(清除骷髏)", "dungeon_index": 3, "policy": "deterministic_count"}],
            "stage_rules": []
        }
        with open(test_json, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False)

        mapper = QuestMapper(rules_file=test_json)
        self.assertIsNotNone(mapper.parse_quest("清除骷髏"))
        self.assertIsNone(mapper.parse_quest("火焰龍王"))

        time.sleep(0.01)
        initial_data["deterministic_quests"].append("火焰龍王")
        initial_data["dungeon_rules"].append({"pattern": "(火焰龍王)", "dungeon_index": 0, "policy": "deterministic_count"})
        with open(test_json, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False)

        node = mapper.parse_quest("火焰龍王")
        self.assertIsNotNone(node)
        self.assertEqual(node.mode_type, "dungeon")
        self.assertEqual(node.dungeon_index, 0)

        if os.path.exists(test_json):
            os.remove(test_json)

    def test_exact_full_name_match_prevent_unknown_false_positive(self):
        """
        驗證全新未知任務 (如 '龍騎士的毀滅'、'瘋狂鬼魂') 不會因為部分關鍵字重疊而被誤判，
        必須 100% 傳回 None 並精確觸發 unknown_quests 上報。
        """
        # 1. '龍騎士的毀滅' 雖然帶有 '的毀滅'，但不完全等於已知任務，應回傳 None
        node_dragon = self.mapper.parse_quest("龍騎士的毀滅")
        self.assertIsNone(node_dragon)

        # 2. '瘋狂鬼魂' 雖然帶有 '鬼魂'，但不完全等於已知任務，應回傳 None
        node_ghost = self.mapper.parse_quest("瘋狂鬼魂")
        self.assertIsNone(node_ghost)

    def test_ocr_noisy_title_completion_does_not_misspill_other_quests(self):
        """
        [Regression Test] 驗證當佇列中同時存在 '清除史萊姆' 與 '史萊姆王的毀滅' 時，
        從彈窗 OCR 讀取到帶噪訊字串 '史萊姆王的毀滅玉3t' 能精確對齊核銷 '史萊姆王的毀滅'，
        且絕對不會誤扣或標記完成 '清除史萊姆'。
        """
        node1 = self.mapper.parse_quest("清除史萊姆")
        node2 = self.mapper.parse_quest("史萊姆王的毀滅")

        self.scheduler.add_task(node1)
        self.scheduler.add_task(node2)

        # 模擬彈窗 OCR 辨識出帶有尾巴噪訊的字串 '史萊姆王的毀滅玉3t'
        matched_title = self.scheduler.record_task_complete("史萊姆王的毀滅玉3t")

        # 1. 斷言匹配到的標題必須是 '史萊姆王的毀滅'
        self.assertEqual(matched_title, "史萊姆王的毀滅")

        # 2. 斷言 '史萊姆王的毀滅' 已標記為完成 (10/10)
        self.assertTrue(node2.is_completed)

        # 3. 斷言 '清除史萊姆' 絕不能被誤扣/誤標記完成 (0/10)
        self.assertFalse(node1.is_completed)
        self.assertEqual(node1.completed_count, 0)

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

        # 3. 圖片 3: 擊殺首領 (已視為 IGNORED 顯式跳過任務)
        node3 = self.mapper.parse_quest("擊殺首領", "各種強大的首領在附近地區活動...", "擊殺: 首領 x 5")
        self.assertEqual(node3.mode_type, "ignored")

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
        # 1. 載入 4 個任務
        quests = [
            ("史萊姆王的毀滅", "黏糊糊的石窟...", "擊殺: [史萊姆王] x 1"),
            ("清除骷髏", "骷髏在戰場上...", "擊殺: 骷髏 x 10"),
            ("擊敗冰元素", "冰元素棲息在...", "擊殺: 冰元素 x 10"),
            ("清除野豬", "野豬在肆意...", "擊殺: 野豬 x 10"),
        ]
        for title, desc, req in quests:
            node = self.mapper.parse_quest(title, desc, req)
            self.scheduler.add_task(node)

        self.assertEqual(len(self.scheduler.get_pending_tasks()), 4)

        # 2. 第一次取得啟動指令 ➔ 應優先傳回地下城 1 (史萊姆王)
        cmd1, msg1 = self.scheduler.get_next_action_config()
        self.assertIn("--mode dungeon --dungeon 1", cmd1)
        print(f"\n[動態排程 step 1] 指令: {cmd1} | 說明: {msg1}")

        # 3. 模擬通關地下城 1
        self.scheduler.record_kill_event(enemy_name="史萊姆王", is_boss=True, dungeon_index=0, kill_count=1)

        # 斷言：史萊姆王的毀滅屬於 POLICY_BANNER_VERIFY，record_kill_event 絕不自動加算進度！
        slime_task = [t for t in self.scheduler.tasks if t.quest_title == "史萊姆王的毀滅"][0]
        self.assertFalse(slime_task.is_completed)

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

        self.scheduler.record_kill_event(enemy_name="野豬", stage_level=1, sub_stage="final", kill_count=10)

        # 所有任務皆完成
        pending_after = self.scheduler.get_pending_tasks()
        self.assertEqual(len(pending_after), 0)

    def test_similar_quest_titles_no_mis_matching(self):
        """
        [Regression Bug Fix 測試] 驗證當佇列中同時存在相似名稱任務 (如 '清除樹人' 與 '清除蛙人' 相似度 0.75) 時，
        辨識到 '清除蛙人' 必須 100% 精確匹配 '清除蛙人'，絕不能因早出現在列表而被 '清除樹人' 攔截。
        """
        from utils.quest_scheduler import QuestScheduler
        scheduler = QuestScheduler()
        node_tree = self.mapper.parse_quest("清除樹人")
        node_frog = self.mapper.parse_quest("清除蛙人")

        scheduler.add_task(node_tree)
        scheduler.add_task(node_frog)

        matched_title = scheduler.record_task_complete("清除蛙人田玉[2")

        self.assertEqual(matched_title, "清除蛙人")
        self.assertTrue(node_frog.is_completed)
        self.assertFalse(node_tree.is_completed)

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
            "冰雪洞窟的暴君",  # BANNER_VERIFY, dungeon 4
            "破除森林的枷鎖",  # BANNER_VERIFY, dungeon 2
            "史萊姆王的毀滅",  # BANNER_VERIFY, dungeon 0
            "清除蛙人",       # DETERMINISTIC, stage 5
            "清除沙蟲",       # DETERMINISTIC, stage 4
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

    def test_all_stage_quest_templates_exist_on_disk(self):
        """
        [防呆門禁測試] 驗證全關卡懸賞任務 (包含沙蟲 Level 4、蛙人 Level 5、野豬 Level 1)
        轉換產出的 stage_entry 圖片檔案 100% 存在於硬碟 templates/ 資料夾中，防範無效檔名退守。
        """
        import os
        for quest in ["清除沙蟲", "清除蛙人", "清除骷髏", "清除史萊姆", "清除樹人"]:
            node = self.mapper.parse_quest(quest)
            cfg = node.to_config_dict()
            if "stage_entry" in cfg:
                entry_path = os.path.join("templates", cfg["stage_entry"])
                self.assertTrue(
                    os.path.exists(entry_path),
                    f"任務 [{quest}] 映射的 stage_entry 圖片檔案不存在: {entry_path}"
                )
                self.assertIn("navigation_path", cfg)
                self.assertIn(cfg["stage_entry"], cfg["navigation_path"])

    def test_from_daily_status_applies_four_tier_sorting(self):
        """
        [防呆門禁測試] 驗證由亂序的 accepted_quests (包含沙蟲 L4, 森林枷鎖, 蛙人 L5)
        經由 from_daily_status 建立的 QuestScheduler 會自動進行四階梯排序：
        1. 破除森林的枷鎖 (Dungeon 3) ➔ 2. 清除蛙人 (Stage 5) ➔ 3. 清除沙蟲 (Stage 4)
        """
        unordered_input = ["清除沙蟲", "破除森林的枷鎖", "清除蛙人"]
        scheduler = QuestScheduler.from_daily_status(unordered_input)
        titles_in_queue = [t.quest_title for t in scheduler.tasks]
        self.assertEqual(titles_in_queue, ["破除森林的枷鎖", "清除蛙人", "清除沙蟲"])

    def test_stage_target_image_existence_and_dynamic_mapping(self):
        """
        [動態圖片對應測試] 驗證『清除沙蟲』(Level 4 middle) 能精確映射至 level4_middle.png，且圖片在 templates 下實體存在！
        """
        import os
        node_sandworm = self.mapper.parse_quest("清除沙蟲")
        self.assertIsNotNone(node_sandworm)
        
        cfg = node_sandworm.to_config_dict()
        # 斷言 stage_target 為 stages/level4_middle.png (絕非找不到的 middle_stage.png)
        self.assertEqual(cfg["stage_target"], "stages/level4_middle.png")
        
        # 斷言實體圖檔存在
        full_path = os.path.join("templates", cfg["stage_target"])
        self.assertTrue(os.path.exists(full_path), f"圖檔不存在: {full_path}")
        
        # 斷言導航路徑最後一個圖標為 level4_middle.png
        self.assertEqual(cfg["navigation_path"][-1], "stages/level4_middle.png")

    def test_task_node_to_cli_args_and_summary_output(self):
        """
        [CLI 指令生成測試] 驗證 TaskNode.to_cli_args 能精確產出 CLI 啟動命令，並能在 summary 中成功格式化輸出！
        """
        node_sandworm = self.mapper.parse_quest("清除沙蟲")
        cli_sandworm = node_sandworm.to_cli_args()
        self.assertIn("--mode stage", cli_sandworm)
        self.assertIn("--stage 4", cli_sandworm)
        self.assertIn("--sub middle", cli_sandworm)

        node_dungeon = self.mapper.parse_quest("破除森林的枷鎖")
        cli_dungeon = node_dungeon.to_cli_args()
        self.assertIn("--mode dungeon", cli_dungeon)
        self.assertIn("--dungeon 3", cli_dungeon)

        # 驗證排程器 print_task_summary 不拋出例外
        scheduler = QuestScheduler()
        scheduler.add_task(node_sandworm)
        scheduler.add_task(node_dungeon)
        scheduler.print_task_summary()

    def test_equipment_quality_preferences_propagation(self):
        """
        [品質偏好傳承測試] 驗證在 GameStateMachine 動態切換懸賞關卡時，
        使用者選擇的 keep_colors 與 disassemble_colors 能被 100% 精確繼承傳承！
        """
        from unittest.mock import MagicMock
        from states.state_machine import GameStateMachine

        capturer = MagicMock()
        matcher = MagicMock()
        mouse = MagicMock()
        sm = GameStateMachine(capturer=capturer, matcher=matcher, mouse=mouse)
        
        # 模擬使用者在 main.py 輸入的偏好：紫色及以上保留，藍色及以下分解
        user_config = {
            "name": "每日懸賞任務",
            "type": "daily",
            "keep_colors": ["purple", "orange_yellow", "red"],
            "disassemble_colors": ["gray_or_empty", "green", "blue"]
        }
        sm.config = user_config

        # 模擬切換懸賞任務 (至清除沙蟲 Stage 4 middle)
        node_sandworm = self.mapper.parse_quest("清除沙蟲")
        scheduler = QuestScheduler()
        scheduler.add_task(node_sandworm)
        sm.attach_quest_scheduler(scheduler)

        # 觸發動態切換
        sm.check_and_advance_quest_target()

        # 斷言切換後的 sm.config 依然 100% 保存著使用者的品質偏好！
        self.assertEqual(sm.config["keep_colors"], ["purple", "orange_yellow", "red"])
        self.assertEqual(sm.config["disassemble_colors"], ["gray_or_empty", "green", "blue"])

    def test_update_bulletin_board_quests_filters_unknown_and_ignored(self):
        """
        [未知/忽略任務隔離測試] 驗證當告示牌掃描到未知任務 (完全未知任務_XYZ) 與忽略任務 (獵金之蟲) 時，
        update_bulletin_board_quests 能精確將未知任務上報至 unknown_quests，剔除忽略任務，並只留有效懸賞至 accepted_quests！
        """
        import tempfile, shutil
        from utils.daily_manager import DailyManager
        tmp_dir = tempfile.mkdtemp()
        try:
            daily_mgr = DailyManager(data_dir=tmp_dir, status_file="test_status.json")
            raw_scanned = ["清除骷髏", "完全未知任務_XYZ", "獵金之蟲"]
            res = daily_mgr.update_bulletin_board_quests(raw_scanned)
            
            # 斷言 accepted_quests 僅含有效任務 "清除骷髏"
            self.assertEqual(res, ["清除骷髏"])
            
            # 斷言 unknown_quests 精確包含 "完全未知任務_XYZ"，且不含 "獵金之蟲"
            bb = daily_mgr.status["subflows"]["bulletin_board"]
            unknowns = bb.get("unknown_quests", [])
            self.assertIn("完全未知任務_XYZ", unknowns)
            self.assertNotIn("獵金之蟲", unknowns)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_toad_and_void_walker_quest_mapping(self):
        """
        [清除蛤蟆與虛空行者的審判測試]
        1. 驗證 '清除蛤蟆' 能精確映射至 幽暗沼澤 (Level 5) 第六小關 (six)。
        2. 驗證 EasyOCR 錯字 '虛f行者昀番判' 能自動正名為 '虛空行者的審判' 並解析為 mode_type == 'ignored'。
        """
        node_toad = self.mapper.parse_quest("清除蛤蟆")
        self.assertIsNotNone(node_toad)
        self.assertEqual(node_toad.mode_type, "stage")
        self.assertEqual(node_toad.stage_level, 5)
        self.assertEqual(node_toad.sub_stage, "six")

        from utils.quest_mapper import normalize_quest_title
        norm_void = normalize_quest_title("虛f行者昀番判")
        self.assertEqual(norm_void, "虛空行者的審判")
        
        node_void = self.mapper.parse_quest(norm_void)
        self.assertIsNotNone(node_void)
        self.assertEqual(node_void.mode_type, "ignored")

    def test_is_current_task_batch_completed_when_higher_priority_cooldown_expires(self):
        """
        [懸賞離場 bug 防護測試]
        當低優先度任務 (清除蛤蟆 Stage 5) 進度到達 8/10 (batch滿4) 時，
        即使高優先度任務 (破除森林的枷鎖 Dungeon 3) 冷卻剛好到期，
        is_current_task_batch_completed 依然必須正確針對【當前執行的任務】回傳 True！
        """
        now = 1000.0
        scheduler = QuestScheduler.from_daily_status(["破除森林的枷鎖", "清除蛤蟆"])
        toad_node = [t for t in scheduler.tasks if t.quest_title == "清除蛤蟆"][0]
        toad_node.completed_count = 8  # 8 % 4 == 0 滿批次
        
        # 1. 當 Dungeon 3 也在冷卻中時
        cd_map_active = {2: now + 100.0} # Dungeon 3 index 2
        stage5_cfg = toad_node.to_config_dict()
        
        # 2. 當 Dungeon 3 冷卻剛好結束 (now = 1101.0)
        now_after_cd = 1101.0
        
        # 當傳入 current_config 時，必須精確判斷當前任務 (toad_node) 已滿 8 次 (True)
        res_current = scheduler.is_current_task_batch_completed(
            dungeon_cooldowns=cd_map_active, 
            now_ts=now_after_cd,
            current_config=stage5_cfg
        )
        self.assertTrue(res_current, "當前任務已滿 8 次，應正確判定批次完成！")

    def test_has_higher_priority_task_ready(self):
        """
        [高優先度搶佔測試]
        當前正執行關卡任務 (清除蛤蟆 Stage 5，進度 5/10 未滿批次)，
        若高優先度地下城任務 (破除森林的枷鎖 Dungeon 3) 冷卻結束，
        has_higher_priority_task_ready 應回傳 True，提示戰鬥結算應立即離場切換任務！
        """
        now = 1000.0
        scheduler = QuestScheduler.from_daily_status(["破除森林的枷鎖", "清除蛤蟆"])
        toad_node = [t for t in scheduler.tasks if t.quest_title == "清除蛤蟆"][0]
        toad_node.completed_count = 5  # 5/10 未滿批次
        
        stage5_cfg = toad_node.to_config_dict()
        cd_map = {2: now + 100.0} # Dungeon 3 (index 2) 在冷卻中
        
        # 當冷卻未結束 (now = 1050.0) ➔ 無更高優先度任務就緒 ➔ False
        self.assertFalse(
            scheduler.has_higher_priority_task_ready(current_config=stage5_cfg, dungeon_cooldowns=cd_map, now_ts=1050.0)
        )
        
        # 當冷卻結束 (now = 1101.0) ➔ Dungeon 3 已經就緒 ➔ True
        self.assertTrue(
            scheduler.has_higher_priority_task_ready(current_config=stage5_cfg, dungeon_cooldowns=cd_map, now_ts=1101.0)
        )

    def test_task_node_to_config_dict_stage_and_dungeon_enables_farming(self):
        """
        [關卡與地下城懸賞配置轉換測試]
        驗證 TaskNode 轉換為 config 字典時：
        - 關卡任務 (stage) 必具備 enable_stage_farming=True
        - 地下城任務 (dungeon) 必具備 enable_dungeon=True
        - 所有全域規範化開關皆齊全有效
        """
        node_ice = self.mapper.parse_quest("擊敗冰元素")
        self.assertIsNotNone(node_ice)
        stage_cfg = node_ice.to_config_dict()
        self.assertTrue(stage_cfg.get("enable_stage_farming", False), "關卡懸賞任務必須自動啟用 enable_stage_farming")
        self.assertEqual(stage_cfg.get("type"), "stage")

        node_dungeon = self.mapper.parse_quest("史萊姆王的毀滅")
        self.assertIsNotNone(node_dungeon)
        dungeon_cfg = node_dungeon.to_config_dict()
        self.assertTrue(dungeon_cfg.get("enable_dungeon", False), "地下城懸賞任務必須自動啟用 enable_dungeon")
        self.assertEqual(dungeon_cfg.get("type"), "dungeon")


if __name__ == "__main__":
    unittest.main()




