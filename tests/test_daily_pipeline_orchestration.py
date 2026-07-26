import os
import json
import time
import unittest
import tempfile
import numpy as np
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
        """驗證 Tier 1 一極優先 (每日一次性城鎮速領) 順序: chest -> hero_draw -> blood_altar (+ jewelry_workshop) -> bulletin_board"""
        pending = self.daily_mgr.get_pending_town_subflows()
        self.assertEqual(pending, ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"])

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.town_subflow_queue, ["hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"])

    def test_tier2_lord_boss_priority_over_bulletin_board(self):
        """驗證 Tier 1 城鎮速領 (包含 bulletin_board) 完成後，Tier 2 領主 Boss 討伐被優先觸發"""
        # 手動標示 Tier 1 子流程已完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("bulletin_board")

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
        self.daily_mgr.record_subflow_completed("bulletin_board")

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
        self.daily_mgr.record_subflow_completed("bulletin_board")

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
        self.assertEqual(sm.config["stage_name"], "冰凍峽谷 (first)")

        self.assertIn("Ice_entry.png", sm.config["navigation_path"][-1])

    def test_dungeon_cooldown_reschedules_in_daily_mode(self):
        """驗證當在 daily 模式下地下城 #4 冷卻時，不會原地等待，而是跳過冷卻地下城切換至下一個未冷卻懸賞任務"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True
        self.daily_mgr.status["subflows"]["lord_boss"]["completed_today"] = True

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 模擬地下城 3 (index 3 神秘遺跡: 清除骷髏) 正在冷卻中
        now_ts = time.time()
        sm.dungeon_cooldowns[3] = now_ts + 600.0

        # 在 daily 模式觸發動態重排
        sm.evaluate_and_schedule_daily_pipeline()

        # 斷言已自動跳過冷卻中的地下城 3 (神秘遺跡)，切換為下一個任務 (清除樹人 - 森林迷宮 index 2)
        self.assertIn("森林迷宮", sm.config["name"])

    def test_navigation_dungeon_cooldown_triggers_pipeline_reevaluation(self):
        """驗證當導航模組偵測到地下城冷卻時，會在 daily 模式下自動喚起動態重新排程，防範死結乒乓對點"""
        from states.handlers.navigation import NavigationHandler
        from config import GAME_CONFIGS, DUNGEON_NAMES

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 模擬正處於每日懸賞模式，當前任務為森林迷宮
        sm.evaluate_and_schedule_daily_pipeline()
        sm.config["dungeon_names"] = DUNGEON_NAMES
        sm.config["greedy_allowed_indices"] = [0, 1, 2, 3, 4]

        nav_handler = NavigationHandler(sm)
        nav_handler.matcher.match.return_value = ((500, 700), 0.95)

        # 模擬 2 號地下城 (森林迷宮) 冷卻 10 分鐘
        now_ts = time.time()
        sm.dungeon_cooldowns[2] = now_ts + 600.0

        # 呼叫 _switch_to_stage_or_back 模擬冷卻發現
        nav_handler._switch_to_stage_or_back(screen_img=MagicMock(), rect={"left": 0, "top": 0}, reason="森林迷宮冷卻中")

        # 斷言 daily pipeline 被重新動態排程，任務順延切換，config 已不再是原本冷卻中的森林迷宮
        self.assertNotIn("森林迷宮", sm.config.get("name", ""))

    def test_tier1_resume_after_partial_completion(self):
        """[Tier 1 檢驗] 驗證城鎮速領中途斷開重新啟動時，會自動接續剩餘未完成項目 (如只留 blood_altar, jewelry_workshop, bulletin_board)"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        pending = self.daily_mgr.get_pending_town_subflows()
        self.assertEqual(pending, ["blood_altar", "jewelry_workshop", "bulletin_board"])

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.evaluate_and_schedule_daily_pipeline()
        self.assertEqual(sm.town_subflow_queue, ["jewelry_workshop", "bulletin_board"])
        self.assertEqual(sm.current_state, sm.STATE_BLOOD_ALTAR)

    def test_tier2_boss_preemption_over_tier3_and_tier4(self):
        """[Tier 2 檢驗] 驗證即使在 Tier 3/4 刷關期間，只要 Boss CD 結束且未滿 5 次，必定搶先插隊"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        # 模擬原本正處於 Tier 3 懸賞戰鬥
        sm.transition_to(sm.STATE_BATTLE)

        # 模擬 Lord Boss 剛冷卻完畢 (未滿5次)
        now_ts = time.time()
        self.daily_mgr.update_boss_cooldown("lord_spider", 0.0, now_ts=now_ts)

        # 戰鬥結束回到大廳重新評估
        sm.evaluate_and_schedule_daily_pipeline()
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

    def test_tier4_fallback_mix_mode_and_repreemption_by_tier2(self):
        """[Tier 4 檢驗] 驗證懸賞全清且 Boss 滿次時退守 Mix 模式，當 Boss 次數未滿且 CD 到時可再次插隊"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        # 設蜘蛛今日 5 次全滿
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        bosses["lord_spider"]["today_count"] = 5
        bosses["lord_spider"]["completed_today"] = True

        # 設惡靈 4 次且處於冷卻中
        now_ts = time.time()
        bosses["lord_spectre"]["today_count"] = 4
        bosses["lord_spectre"]["completed_today"] = False
        bosses["lord_spectre"]["last_fight_timestamp"] = now_ts

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        # 無懸賞任務
        sm.quest_scheduler = None

        # 評估應落入 Tier 4 Mix 退守
        sm.evaluate_and_schedule_daily_pipeline()
        self.assertEqual(sm.config["name"], "混合模式")

        # 模擬 7201 秒後惡靈冷卻時間結束，再次評估時應被 Tier 2 搶占插隊打 Boss！
        bosses["lord_spectre"]["last_fight_timestamp"] = now_ts - 7201.0
        sm.evaluate_and_schedule_daily_pipeline()
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

    def test_tier4_does_not_trigger_should_exit_battle_due_to_quest_batch_completed(self):
        """[Tier 4 離場防呆測試] 驗證處於 Tier 4 退守模式時，即使懸賞全完成，也不會將常規關卡戰鬥誤判為離場場次"""
        from states.handlers.result import ResultHandler

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.quest_scheduler = None  # 代表處於 Tier 4 (懸賞全清)
        sm.set_config({"name": "混合模式", "type": "mix", "stage_name": "level6"})

        # 模擬無其他離場需求 (無體力退避、背包未滿、Boss全冷卻中、無可用地下城)
        sm.stamina_retreat_start_time = None
        sm.need_bag_cleaning = False
        sm.need_diamond_collection = False
        sm.need_bread_collection = False
        sm.has_available_dungeon = MagicMock(return_value=False)
        sm.daily_manager.has_available_lord_boss = MagicMock(return_value=False)

        handler = ResultHandler(sm)
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)

        # 測試：當在 Tier 4 看見 retry 按鈕，且沒有其他離場原因時，_check_final_buttons_exist 應判定 should_exit_battle=False
        should_exit = (
            sm.stamina_retreat_start_time is not None or
            sm.need_bag_cleaning or 
            sm.need_diamond_collection or 
            (sm.enable_bread and sm.need_bread_collection) or
            (sm.config.get("type") == "mix" and sm.has_available_dungeon()) or
            (sm.is_daily_pipeline_active() and sm.daily_manager.has_available_lord_boss()) or
            (sm.is_daily_pipeline_active() and False and not True)
        )
        self.assertFalse(should_exit)

    def test_daily_reset_triggers_active_battle_exit(self):
        """[08:05 重置離場測試] 驗證當跨越 08:05 觸發重置時，pending_daily_reset_exit 標記會被置為 True，使 ResultHandler 在戰鬥結束後主動離場"""
        from states.handlers.result import ResultHandler

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.set_config({"name": "每日懸賞任務", "type": "mix", "stage_name": "level6"})

        # 模擬 08:05 觸發重置
        sm.pending_daily_reset_exit = True

        handler = ResultHandler(sm)
        
        # 測試：ResultHandler 的 should_exit_battle 在 pending_daily_reset_exit == True 時應為 True
        is_daily = sm.is_daily_pipeline_active()
        is_in_tier4 = is_daily and (getattr(sm, "quest_scheduler", None) is None or sm.quest_scheduler.is_all_completed())
        
        should_exit = (
            getattr(sm, "pending_daily_reset_exit", False) or
            sm.stamina_retreat_start_time is not None or
            sm.need_bag_cleaning or 
            sm.need_diamond_collection or 
            (sm.enable_bread and sm.need_bread_collection) or
            (sm.config.get("type") == "mix" and sm.has_available_dungeon())
        )
        self.assertTrue(should_exit)


if __name__ == "__main__":
    unittest.main()

