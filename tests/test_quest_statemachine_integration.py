import os
import json
import unittest
import numpy as np
from unittest.mock import MagicMock
from utils.quest_mapper import QuestMapper, TaskNode
from utils.quest_scheduler import QuestScheduler
from utils.daily_manager import DailyManager, DEFAULT_DAILY_STATUS
from states.state_machine import GameStateMachine

from config import QUEST_TARGET_COUNT, PRIMARY_MODES

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
            "擊敗冰元素"
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
        
        # 模擬擊殺次數 (同時滿足史萊姆王的毀滅與確定性關卡擊敗冰元素)
        scheduler.record_kill_event(enemy_name="冰元素", stage_level=6, sub_stage="first", kill_count=QUEST_TARGET_COUNT)
        
        tasks_map = {t.quest_title: t for t in scheduler.tasks}
        # 史萊姆王的毀滅 屬於 BANNER_VERIFY_QUESTS，record_kill_event 絕不自動加算進度
        self.assertFalse(tasks_map["史萊姆王的毀滅"].is_completed)
        # 確定性任務自動加算完成
        self.assertTrue(tasks_map["擊敗冰元素"].is_completed)


    def test_remove_accepted_quest_from_json(self):
        """驗證 completed 任務從 daily_status.json 的 accepted_quests 中成功移除"""
        self.assertTrue("清除樹人" in self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"])
        
        removed = self.daily_mgr.remove_accepted_quest("清除樹人")
        self.assertTrue(removed)
        
        # 重新開啟驗證持久化檔案
        with open(self.test_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("清除樹人", data["subflows"]["bulletin_board"]["accepted_quests"])

    def test_ocr_noisy_title_cleaning(self):
        """[三者測試 1: 能否正確清洗] 驗證帶有錯別字、尾巴雜訊與符號的 OCR 任務名稱能被正確清洗對齊"""
        from utils.quest_mapper import normalize_quest_title
        
        # 測試 1: 帶尾巴雜字與符號 '清除蛙人玉[2' -> '清除蛙人'
        self.assertEqual(normalize_quest_title("清除蛙人玉[2"), "清除蛙人")
        
        # 測試 2: 帶底線與數字 '史萊姆王的毀滅_123' -> '史萊姆王的毀滅'
        self.assertEqual(normalize_quest_title("史萊姆王的毀滅_123"), "史萊姆王的毀滅")
        
        # 測試 3: 錯別字替換 '野瀦' -> '野豬'，並對齊全名
        self.assertEqual(normalize_quest_title("清除野瀦"), "清除野豬")

    def test_ocr_noisy_title_matching(self):
        """[三者測試 2: 能否正確匹配] 驗證傳入帶雜訊的 OCR 辨識結果能正確匹配 TaskNode 並回傳清洗後的標準標題"""
        self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"] = ["清除蛙人", "清除沙蟲"]
        self.daily_mgr.save_status()
        scheduler = self.daily_mgr.load_quest_scheduler()
        
        # 傳入帶雜訊的 OCR 標題 '清除蛙人玉[2'
        matched_title = scheduler.record_task_complete("清除蛙人玉[2")
        
        # 斷言：成功匹配並回傳乾淨的標準標題 '清除蛙人'
        self.assertEqual(matched_title, "清除蛙人")
        
        # 斷言：對應的 TaskNode 已被標記為完成
        frog_task = next(t for t in scheduler.tasks if t.quest_title == "清除蛙人")
        self.assertTrue(frog_task.is_completed)

    def test_ocr_noisy_title_deletion_and_persistence(self):
        """[三者測試 3: 能否正確刪除] 驗證傳入帶雜訊標題或呼叫 process_task_complete_banner 能正確將任務從 daily_status.json 移除並寫回硬碟"""
        # 在 accepted_quests 中預先塞入包含 "清除蛙人" 的狀態
        self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"] = ["清除蛙人", "清除沙蟲"]
        self.daily_mgr.save_status()
        
        scheduler = self.daily_mgr.load_quest_scheduler()
        
        # 模擬傳入帶雜訊的 OCR 標題進行刪除
        matched_title = scheduler.record_task_complete("清除蛙人玉[2")
        clean_title = matched_title if matched_title else "清除蛙人"
        
        removed = self.daily_mgr.remove_accepted_quest(clean_title)
        self.assertTrue(removed)
        
        # 重新讀取硬碟檔，確認 "清除蛙人" 已從 JSON 硬碟檔中徹底被剔除！
        with open(self.test_json_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
            
        remaining_quests = disk_data["subflows"]["bulletin_board"]["accepted_quests"]
        self.assertNotIn("清除蛙人", remaining_quests)
        self.assertIn("清除沙蟲", remaining_quests)

    def test_dungeon_quest_always_prioritized_over_stage_quest(self):
        """[排序優先級測試] 驗證地下城懸賞任務 (即使為 banner_verify_only) 100% 優先於普通關卡任務 (即使為 deterministic)"""
        from utils.quest_mapper import QuestMapper
        mapper = QuestMapper()
        
        # 傳入：關卡任務 (清除沙蟲, deterministic) 與 地下城任務 (破除森林的枷鎖, banner_verify)
        quests = ["清除沙蟲", "破除森林的枷鎖"]
        sorted_quests = mapper.sort_quests(quests)
        
        # 斷言：地下城任務 '破除森林的枷鎖' 必須排在第 1 位！
        self.assertEqual(sorted_quests[0], "破除森林的枷鎖")
        self.assertEqual(sorted_quests[1], "清除沙蟲")

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

    def test_typo_normalization_in_creation_and_completion(self):
        """驗證 OCR 錯別字 (如 野瀦 ➔ 野豬, 毀減 ➔ 毀滅, 肇敗 ➔ 擊敗) 在建立任務與完成標記/剔除中均 100% 有效"""
        # 1. 測試建立任務階段 (parse_quest 包含錯別字)
        mapper = QuestMapper()
        node_boar = mapper.parse_quest("清除野瀦")  # OCR 誤判 '野瀦'
        self.assertIsNotNone(node_boar)
        self.assertEqual(node_boar.stage_level, 1)
        self.assertEqual(node_boar.sub_stage, "final")

        node_slime = mapper.parse_quest("史萊姆王的毀減")  # OCR 誤判 '毀減'
        self.assertIsNotNone(node_slime)
        self.assertEqual(node_slime.mode_type, "dungeon")
        self.assertEqual(node_slime.dungeon_index, 0)

        # 2. 測試完成任務階段 (record_task_complete 包含錯別字)
        scheduler = QuestScheduler()
        scheduler.add_task(TaskNode("擊敗冰元素", "stage", target_count=10, stage_level=6, sub_stage="first"))
        scheduler.add_task(TaskNode("清除野豬", "stage", target_count=10, stage_level=1, sub_stage="final"))

        # 傳入包含錯別字的 OCR 文字 '肇敗冰元奏'
        matched1 = scheduler.record_task_complete("肇敗冰元奏")
        self.assertTrue(matched1)
        self.assertTrue(scheduler.tasks[0].is_completed)

        # 3. 測試 JSON 剔除階段 (remove_accepted_quest 包含錯別字)
        self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"] = ["史萊姆王的毀滅", "清除野豬"]
        self.daily_mgr.save_status()

        # 使用包含錯別字的 '史萊姆王的毀減' 進行剔除
        removed = self.daily_mgr.remove_accepted_quest("史萊姆王的毀減")
        self.assertTrue(removed)
        self.assertNotIn("史萊姆王的毀滅", self.daily_mgr.status["subflows"]["bulletin_board"]["accepted_quests"])

    def test_new_one_to_one_quest_mapping_rules(self):
        """驗證最新一對一懸賞任務映射規則與禁用項目"""
        mapper = QuestMapper()

        # 1. 沙蟲 -> Level 4 middle
        node_worm = mapper.parse_quest("清除沙蟲")
        self.assertIsNotNone(node_worm)
        self.assertEqual(node_worm.stage_level, 4)
        self.assertEqual(node_worm.sub_stage, "middle")

        # 2. 地下城規則對照
        # 完成任何地下城 -> ignored (不執行)
        self.assertEqual(mapper.parse_quest("完成任何地下城").mode_type, "ignored")
        
        entries = PRIMARY_MODES["dungeon"]["dungeon_entries"]
        slime_idx = entries.index("dungeons/Slime_entry.png")
        forest_idx = entries.index("dungeons/Forest_entry.png")
        ruins_idx = entries.index("dungeons/Ruins_entry.png")
        ice_idx = entries.index("dungeons/Ice_entry.png")

        # 冰雪洞窟的暴君 -> 冰雪洞窟
        self.assertEqual(mapper.parse_quest("冰雪洞窟的暴君").dungeon_index, ice_idx)

        # 史萊姆王 -> 史萊姆
        self.assertEqual(mapper.parse_quest("史萊姆王的毀滅").dungeon_index, slime_idx)
        # 史萊姆 -> 史萊姆
        self.assertEqual(mapper.parse_quest("清除史萊姆").dungeon_index, slime_idx)
        # 破除森林的枷鎖 -> 森林迷宮
        self.assertEqual(mapper.parse_quest("破除森林的枷鎖").dungeon_index, forest_idx)
        # 樹人 -> 森林迷宮
        self.assertEqual(mapper.parse_quest("清除樹人").dungeon_index, forest_idx)
        # 骷髏 -> 神秘遺跡
        self.assertEqual(mapper.parse_quest("清除骷髏").dungeon_index, ruins_idx)

        # 3. 不要做 / 顯式跳過項目 -> 回傳 mode_type == "ignored"，不上報 unknown_quests
        node_ignored1 = mapper.parse_quest("敵人剿滅")
        self.assertIsNotNone(node_ignored1)
        self.assertEqual(node_ignored1.mode_type, "ignored")

        node_ignored2 = mapper.parse_quest("獵金之蟲")
        self.assertIsNotNone(node_ignored2)
        self.assertEqual(node_ignored2.mode_type, "ignored")

        # 4. 驗證 record_unknown_quest 不會將 ignored 任務記錄至 unknown_quests
        self.daily_mgr.record_unknown_quest("敵人剿滅")
        self.daily_mgr.record_unknown_quest("獵金之蟲")
        bb = self.daily_mgr.status["subflows"]["bulletin_board"]
        self.assertNotIn("敵人剿滅", bb.get("unknown_quests", []))
        self.assertNotIn("獵金之蟲", bb.get("unknown_quests", []))

    def test_all_quests_completed_transitions_to_mix(self):
        """驗證當所有每日懸賞任務完成時，狀態機自動解鎖 QuestScheduler 並切換至預設 mix 模式配置 (冰雪洞窟 + 關卡 6-1)"""
        # 手動標示 Tier 1 速領與 Tier 2 Boss 已完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()

        sm.attach_quest_scheduler(scheduler)

        # 手動將所有任務設為 completed
        for t in scheduler.tasks:
            t.completed_count = t.target_count
            self.daily_mgr.remove_accepted_quest(t.quest_title)

        res = sm.check_and_advance_quest_target()
        self.assertIsNone(res)
        self.assertIsNone(sm.quest_scheduler)
        
        # 測試由 evaluate_and_schedule_daily_pipeline 統一將配置切換至動態/預設 Tier 4 Mix 模式
        sm.evaluate_and_schedule_daily_pipeline()
        self.assertEqual(sm.config["type"], "mix")
        self.assertEqual(sm.config["stage_name"], "冰凍峽谷 (first)")

    def test_result_handler_batch_exit_on_fourth_run(self):
        """驗證當普通關卡任務 (batch_size=4) 戰鬥勝利至第 4 場時，ResultHandler 自動累加 completed_count 並觸發批次離場」"""
        from states.handlers.result import ResultHandler
        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.matcher.match.return_value = (None, 0.0)
        scheduler = QuestScheduler.from_daily_status(["擊敗冰元素"])
        sm.attach_quest_scheduler(scheduler)
        sm.backend_mode = "daily"
        sm.check_and_advance_quest_target()

        handler = ResultHandler(sm)
        fake_img = np.zeros((600, 800, 3), dtype=np.uint8)

        # 前 3 場勝利通關
        for run in range(1, 4):
            handler.reset_state()
            handler.handle(fake_img, {"left": 0, "top": 0, "width": 800, "height": 600})

        current_task = scheduler.get_next_action_node()[0]
        self.assertEqual(current_task.completed_count, 3)
        self.assertFalse(scheduler.is_current_task_batch_completed())

        # 第 4 場勝利通關
        handler.reset_state()
        handler.handle(fake_img, {"left": 0, "top": 0, "width": 800, "height": 600})
        self.assertEqual(current_task.completed_count, 4)
        self.assertTrue(scheduler.is_current_task_batch_completed())


if __name__ == "__main__":
    unittest.main()




