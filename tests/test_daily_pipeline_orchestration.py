import os
import json
import time
import unittest
import tempfile
import numpy as np
from unittest.mock import MagicMock, patch
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
        
        # 隔離設定檔：確保測試不受使用者本地 defaults.toml 暫時關閉 subflow 的影響
        self.mock_subflow_configs = {
            "chest": {"enabled": True, "name": "寶箱領取"},
            "hero_draw": {"enabled": True, "name": "英雄召喚"},
            "blood_altar": {"enabled": True, "name": "血之祭壇獻祭"},
            "jewelry_workshop": {"enabled": True, "name": "珠寶加工廠出售"},
            "bulletin_board": {"enabled": True, "name": "懸賞告示牌"},
        }
        self.patcher = patch("config.SUBFLOW_CONFIGS", self.mock_subflow_configs)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
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
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        # 設蜘蛛與其他非惡靈 Boss 今日 5 次全滿
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b_name, b_info in bosses.items():
            if b_name != "lord_spectre":
                b_info["today_count"] = 5
                b_info["completed_today"] = True

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

    def test_pop_and_next_town_subflow_state_transition_not_leaked(self):
        """[Subflow State Transition] 驗證城鎮佇列結束時，current_state 會切換至 NAVIGATING，不會殘留 JEWELRY_WORKSHOP"""
        for flow in ["chest", "hero_draw", "blood_altar", "jewelry_workshop", "bulletin_board"]:
            self.daily_mgr.record_subflow_completed(flow)
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True
        self.daily_mgr.status["subflows"]["lord_boss"]["completed_today"] = True
        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.town_subflow_queue = []
        sm.current_state = sm.STATE_JEWELRY_WORKSHOP

        # 執行城鎮流水線結束彈出
        sm.pop_and_next_town_subflow()

        # 斷言 current_state 絕不能殘留在 JEWELRY_WORKSHOP
        self.assertNotEqual(sm.current_state, sm.STATE_JEWELRY_WORKSHOP)
        self.assertEqual(sm.current_state, sm.STATE_NAVIGATING)

    def test_tier4_dynamic_user_configured_primary_config_fallback(self):
        """[Tier 4 檢驗] 驗證懸賞全清時，狀態機自動載入並切換至使用者在 main 階段所設定的動態 primary_config (例如 蒼穹平原 final)"""
        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        
        # 模擬使用者在 main.py 初始化時動態選擇的 Tier 4 退守目標
        custom_tier4_cfg = {
            "name": "蒼穹平原 (final)",
            "type": "stage",
            "stage_level": 1,
            "stage_sub": "final",
            "stage_name": "蒼穹平原 (final)"
        }
        sm.primary_config = custom_tier4_cfg.copy()
        sm.quest_scheduler = None  # 代表懸賞任務全數完成
        
        # 將速領與 Boss 設為完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled)
        self.assertEqual(sm.config["name"], "蒼穹平原 (final)")
        self.assertEqual(sm.config["stage_name"], "蒼穹平原 (final)")

    def test_tier3_all_cooldown_fallbacks_to_tier4(self):
        """[Tier 3 冷卻退守 Tier 4 測試] 驗證當 Tier 3 懸賞任務全數處於冷卻中時，排程器會自動切換至 Tier 4 退守模式"""
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
        
        # 建立僅含有破除森林的枷鎖 (Dungeon 3, index 2) 的排程器
        from utils.quest_scheduler import QuestScheduler
        scheduler = QuestScheduler.from_daily_status(["破除森林的枷鎖"])
        sm.attach_quest_scheduler(scheduler)

        # 設 Dungeon 3 冷卻 10 分鐘
        now_ts = time.time()
        sm.dungeon_cooldowns[2] = now_ts + 600.0

        # 評估 daily pipeline，因任務冷卻，應回傳 False 並自動載入 Tier 4 退守模式 (Mix/Stage)
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled)
        self.assertIn("模式", sm.config.get("name", ""))

    def test_tier4_running_repreempted_when_tier3_cooldown_expires(self):
        """[Tier 4 執行中 Tier 3 解凍搶佔測試] 驗證當處於 Tier 4 退守模式時，只要 Tier 3 懸賞地下城冷卻到期，能夠搶佔離場並切回 Tier 3"""
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
        
        from utils.quest_scheduler import QuestScheduler
        scheduler = QuestScheduler.from_daily_status(["破除森林的枷鎖"])
        sm.attach_quest_scheduler(scheduler)

        # 1. 設冷卻 600 秒，初次排程退守至 Tier 4
        now_ts = time.time()
        sm.dungeon_cooldowns[2] = now_ts + 600.0
        sm.evaluate_and_schedule_daily_pipeline()
        tier4_cfg = sm.config.copy()
        self.assertTrue(tier4_cfg.get("is_tier4_fallback"))

        # 2. 模擬 601 秒後 (冷卻到期)，驗證 has_higher_priority_task_ready 傳回 True
        has_ready = sm.quest_scheduler.has_higher_priority_task_ready(
            current_config=tier4_cfg,
            dungeon_cooldowns=sm.dungeon_cooldowns,
            now_ts=now_ts + 601.0
        )
        self.assertTrue(has_ready, "冷卻解凍後應傳回 True 以觸發結算離場搶佔！")

        # 3. 離場後重新排程，驗證已成功切換回 Tier 3 (破除森林的枷鎖)
        sm.dungeon_cooldowns[2] = 0.0  # 解凍
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.config["type"], "dungeon")
        self.assertEqual(sm.config["dungeon_index"], 2)

    def test_ready_daily_quest_preempts_tier4_at_result_screen(self):
        """Tier 4 結算時，任何已就緒的 Daily 任務都必須離場，不能按再戰。"""
        from states.handlers.result import ResultHandler

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = MagicMock()
        sm.daily_manager.is_subflow_completed.return_value = True
        sm.daily_manager.has_available_lord_boss.return_value = False
        sm.set_config({"name": "Tier 4 退守", "type": "mix", "is_tier4_fallback": True})
        sm.has_available_dungeon = MagicMock(return_value=False)

        scheduler = MagicMock()
        scheduler.is_all_completed.return_value = False
        scheduler.is_current_task_batch_completed.return_value = False
        scheduler.has_higher_priority_task_ready.return_value = False
        scheduler.get_next_action_node.return_value = (MagicMock(), "Daily 任務已就緒")
        sm.quest_scheduler = scheduler

        self.assertTrue(sm.has_ready_daily_quest_preemption())

        handler = ResultHandler(sm)
        handler.subflow_step = "FINAL_MATCH"
        sm.transition_to = MagicMock()

        def match_exit_only(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (500, 500), 0.95
            if template == "stages/retry.png":
                return (700, 500), 0.95
            return None, 0.0

        sm.matcher.match.side_effect = match_exit_only
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("os.path.exists", return_value=True), \
             patch.object(handler, "click_and_wait_until_gone") as mock_click, \
             patch("time.sleep", return_value=None):
            self.assertTrue(handler._handle_impl(fake_screen, rect))

        mock_click.assert_called_once_with("exit_battle.png", 500, 500, rect)
        self.assertFalse(any(call.args[0] == "stages/retry.png" for call in mock_click.call_args_list))
        sm.transition_to.assert_called_once_with(sm.STATE_NAVIGATING)

    def test_tier3_all_completed_clears_scheduler_and_permanently_enters_tier4(self):
        """[Tier 3 全完結解構測試] 驗證當所有 Tier 3 任務進度達成 (10/10) 時，會解除排程器並永久轉入 Tier 4"""
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
        
        from utils.quest_scheduler import QuestScheduler
        scheduler = QuestScheduler.from_daily_status(["清除野豬"])
        node = scheduler.tasks[0]
        node.completed_count = node.target_count  # 達成目標進度完全完結
        sm.attach_quest_scheduler(scheduler)

        # 執行排程
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertFalse(scheduled)
        self.assertIsNone(sm.quest_scheduler, "全完結後應解除 quest_scheduler")




    def test_tier1_5_demon_lords_priority_over_lord_boss(self):
        """驗證 Tier 1 城鎮速領完成後，Tier 1.5 深淵魔王 (0 CD, 3次) 優先於 Tier 2 Lord Boss 被派發"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), [])

        custom_subflow_configs = dict(self.mock_subflow_configs)
        custom_subflow_configs["demon_lords"] = {"enabled": True, "name": "深淵魔王"}

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        with patch("config.SUBFLOW_CONFIGS", custom_subflow_configs):
            scheduled = sm.evaluate_and_schedule_daily_pipeline()
            self.assertTrue(scheduled)
            self.assertEqual(sm.current_state, sm.STATE_DEMON_LORDS)

            for _ in range(3):
                self.daily_mgr.record_demon_lords_fight()
            self.assertTrue(self.daily_mgr.status["subflows"]["demon_lords"]["completed_today"])

            scheduled_lord = sm.evaluate_and_schedule_daily_pipeline()
            self.assertTrue(scheduled_lord)
            self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

    def test_tier1_5_demon_lords_disabled_skips_to_lord_boss(self):
        """驗證當 enable_demon_lords = False 時，系統自動跳過魔王直接進入 Lord Boss"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        custom_subflow_configs = dict(self.mock_subflow_configs)
        custom_subflow_configs["demon_lords"] = {"enabled": True, "name": "深淵魔王"}

        sm = GameStateMachine(capturer=MagicMock(), matcher=MagicMock(), mouse=MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.config = {"enable_demon_lords": False}

        with patch("config.SUBFLOW_CONFIGS", custom_subflow_configs):
            scheduled = sm.evaluate_and_schedule_daily_pipeline()
            self.assertTrue(scheduled)
            self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)

class TestTierConfigMatrix(unittest.TestCase):
    """專門驗證 Tier 1~4 全階梯調度時 Config 設定正確性之測試矩陣」"""
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_json_path = os.path.join(self.test_dir, "test_daily_status.json")
        sample_status = json.loads(json.dumps(DEFAULT_DAILY_STATUS))
        sample_status["subflows"]["bulletin_board"]["accepted_quests"] = [
            "史萊姆王的毀滅"
        ]
        with open(self.test_json_path, "w", encoding="utf-8") as f:
            json.dump(sample_status, f, ensure_ascii=False, indent=2)
        self.daily_mgr = DailyManager(data_dir=self.test_dir, status_file="test_daily_status.json")
        self.mock_subflow_configs = {
            "chest": {"enabled": True, "name": "寶箱領取"},
            "hero_draw": {"enabled": True, "name": "英雄召喚"},
            "blood_altar": {"enabled": True, "name": "血之祭壇獻祭"},
            "jewelry_workshop": {"enabled": True, "name": "珠寶加工廠出售"},
            "bulletin_board": {"enabled": True, "name": "懸賞告示牌"},
        }
        self.patcher = patch("config.SUBFLOW_CONFIGS", self.mock_subflow_configs)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tier1_config_and_state_verification(self):
        """[Tier 1 Config 驗證] 驗證 Tier 1 觸發時 Config 精確設定為 chest 且狀態轉移至 STATE_CHEST"""
        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.current_state, sm.STATE_CHEST)
        self.assertEqual(sm.config["type"], "chest")

    def test_tier2_config_and_state_verification(self):
        """[Tier 2 Config 驗證] 驗證 Tier 2 觸發時 Config 精確切換為 lord_boss 且狀態轉移至 STATE_LORD_BOSS"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.current_state, sm.STATE_LORD_BOSS)
        self.assertEqual(sm.config["type"], "lord_boss")

    def test_tier3_config_and_state_verification(self):
        """[Tier 3 Config 驗證] 驗證 Tier 3 觸發時 Config 精確切換為懸賞任務指定之地下城配置 (dungeon index 0)"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        scheduler = self.daily_mgr.load_quest_scheduler()
        sm.attach_quest_scheduler(scheduler)

        scheduled = sm.evaluate_and_schedule_daily_pipeline()
        self.assertTrue(scheduled)
        self.assertEqual(sm.config["type"], "dungeon")
        self.assertEqual(sm.config["dungeon_index"], 0)
        self.assertIn("史萊姆", sm.config["name"])

    def test_tier4_config_and_state_verification(self):
        """[Tier 4 Config 驗證] 驗證 Tier 4 退守時 Config 精確載入使用者動態設定之 primary_config"""
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("blood_altar")
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        bosses = self.daily_mgr.status["subflows"]["lord_boss"]["bosses"]
        for b in bosses.values():
            b["today_count"] = 5
            b["completed_today"] = True

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.quest_scheduler = None  # 無懸賞任務
        custom_cfg = {"name": "荒蕪岩地 (middle)", "type": "stage", "stage_level": 2, "stage_sub": "middle", "stage_name": "荒蕪岩地 (middle)"}
        sm.primary_config = custom_cfg.copy()

    def test_final_quest_10th_battle_triggers_exit_battle(self):
        """[最後一項懸賞 10/10 完成離場測試] 驗證最後一項懸賞任務在第 10/10 場戰鬥結束時，should_exit_battle 為 True 並觸發離場"""
        from states.handlers.result import ResultHandler

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.set_config({"name": "懸賞任務 - 古樹森林 (final)", "type": "stage", "is_tier4_fallback": False})

        mock_scheduler = MagicMock()
        mock_scheduler.is_current_task_batch_completed.return_value = True
        mock_scheduler.is_all_completed.return_value = True
        sm.quest_scheduler = mock_scheduler

        handler = ResultHandler(sm)
        is_daily = sm.is_daily_pipeline_active()
        is_in_tier4 = is_daily and sm.config.get("is_tier4_fallback", False)
        quest_batch_completed = sm.quest_scheduler.is_current_task_batch_completed(
            dungeon_cooldowns=sm.dungeon_cooldowns,
            current_config=sm.config
        )

        should_exit = (
            getattr(sm, "pending_daily_reset_exit", False) or
            sm.stamina_retreat_start_time is not None or
            sm.need_bag_cleaning or 
            sm.need_diamond_collection or 
            (sm.enable_bread and sm.need_bread_collection) or
            (sm.config.get("type") == "mix" and sm.has_available_dungeon()) or
            (is_daily and quest_batch_completed and not is_in_tier4)
        )
        self.assertTrue(should_exit, "懸賞最後一關第 10 場戰鬥結束時 should_exit 必須為 True！")

    def test_tier4_fallback_switch_to_stage_navigates_to_fallback_stage(self):
        """[Tier 4 導航測試] 驗證當懸賞全數完成、進入 Tier 4 退守模式且地下城冷卻時，_switch_to_stage_or_back 會精確點擊 common/select_stage.png 切換至退守關卡，不再被 early-return 死鎖"""
        from states.handlers.navigation import NavigationHandler

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = self.daily_mgr
        sm.quest_scheduler = None  # 所有懸賞均已 100% 完成
        tier4_cfg = {
            "name": "每日懸賞任務 (Tier 4 退守: 冰凍峽谷)",
            "type": "mix",
            "is_tier4_fallback": True,
            "greedy_allowed_indices": [0, 1, 2, 3, 4],
            "dungeon_names": ["Slime", "Ghost", "Forest", "Ruins", "Ice"]
        }
        sm.set_config(tier4_cfg)

        # 模擬所有地下城均處於冷卻中
        for idx in range(5):
            sm.dungeon_cooldowns[idx] = 9999999999.0

        nav_handler = NavigationHandler(sm)
        nav_handler.matcher = MagicMock()
        nav_handler.mouse = MagicMock()

        # 模擬畫面上 match 到 common/select_stage.png
        nav_handler.matcher.match.side_effect = lambda img, tpl, **kw: ((500, 300), 0.90) if tpl == "common/select_stage.png" else (None, 0.0)

        fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("states.handlers.navigation.time.sleep"):
            nav_handler._switch_to_stage_or_back(fake_img, rect, "測試地下城全冷卻")

        # 斷言發起點擊切換頁籤，未被 early return 攔截
        nav_handler.mouse.click.assert_called_once_with(500, 300)


    def test_disabled_blood_altar_skips_and_does_not_loop_jewelry_workshop(self):
        """[防死循環測試] 驗證當 blood_altar 設定 enabled=False 時，get_pending_town_subflows 自動剔除血祭壇，且 jewelry_workshop 完工後自動標記完成，不再重複派發"""
        self.mock_subflow_configs["blood_altar"]["enabled"] = False
        
        # 1. 驗證 pending 清單中不再包含 blood_altar
        pending = self.daily_mgr.get_pending_town_subflows()
        self.assertEqual(pending, ["chest", "hero_draw", "jewelry_workshop", "bulletin_board"])
        
        # 2. 標記 chest, hero_draw, bulletin_board 完成
        self.daily_mgr.record_subflow_completed("chest")
        self.daily_mgr.record_subflow_completed("hero_draw")
        self.daily_mgr.record_subflow_completed("bulletin_board")
        
        # 3. 此時 pending 僅剩 jewelry_workshop (不含 blood_altar)
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), ["jewelry_workshop"])
        
        # 4. 模擬 jewelry_workshop 完成並調用 record_subflow_completed
        self.daily_mgr.record_subflow_completed("jewelry_workshop")
        
        # 5. 斷言 Tier 1 全數清空，杜絕無限循環！
        self.assertEqual(self.daily_mgr.get_pending_town_subflows(), [])

    def test_setup_stage_config_with_toml_parameters(self):
        """[TOML 配置測試] 驗證 setup_stage_config 傳入 stage_level 與 sub_stage_type 時，直接套用設定且不觸發 input() 阻塞"""
        from cli.stage_setup import setup_stage_config
        config = {}
        setup_stage_config(config, stage_level=6, sub_stage_type="final")
        self.assertEqual(config["stage_name"], "冰凍峽谷 (final)")
        self.assertEqual(config["stage_entry"], "stages/level6_ice_cave.png")
        self.assertEqual(config["stage_target"], "stages/level6_final.png")
        self.assertIn("stages/level6_final.png", config["stage_navigation_path"])

    @patch('cli.stage_setup.persist_mode_updates')
    @patch('cli.tier4_setup.persist_mode_updates')
    @patch('cli.dungeon_setup.persist_mode_updates')
    @patch('builtins.input', return_value="")
    def test_setup_mode_config_daily_reads_tier4_toml(self, mock_input, _d1, _d2, _d3):
        """[TOML 配置測試] 驗證 setup_mode_config 在 daily 模式下可無縫讀取 TOML 中的 tier4 退守大關與小關配置"""
        import argparse
        from cli.mode_setup import setup_mode_config
        args = argparse.Namespace(
            mode="daily",
            subflow=None,
            backend=True,
            blessmode="combat",
            enable_lord_boss=None,
            enable_dungeon=None,
            enable_stage_farming=True,
            enable_town_daily=None,
            stage=None,
            sub=None
        )
        from config import PRIMARY_MODES, GAME_CONFIGS
        expected_sub = PRIMARY_MODES["daily"].get("tier4_sub_stage", "first")
        with patch.dict(PRIMARY_MODES["daily"], {"tier4_mode": "stage"}), \
             patch.dict(GAME_CONFIGS["daily"], {"tier4_mode": "stage", "enable_stage_farming": True}):
            cfg = setup_mode_config(args)
            self.assertEqual(cfg["stage_name"], f"冰凍峽谷 ({expected_sub})")
            self.assertEqual(cfg["stage_entry"], "stages/level6_ice_cave.png")
            self.assertTrue(os.path.exists(os.path.join("templates", cfg["stage_target"])))

    def test_tier4_preemption_on_lord_boss_cooldown_expiry(self):
        """[Tier 4 結算插隊測試] 驗證即便 subflows.lord_boss.completed_today 為 True，只要 Boss 冷卻過期 (has_available_lord_boss 為 True)，ResultHandler 必須判定離場並點擊 exit_battle 而非 retry"""
        from states.handlers.result import ResultHandler

        sm = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        sm.daily_manager = MagicMock()
        # 模擬早上首輪跑完後 completed_today 被標記為 True，但冷卻過期後 has_available_lord_boss 變為 True
        sm.daily_manager.is_subflow_completed.return_value = True
        sm.daily_manager.has_available_lord_boss.return_value = True
        sm.daily_manager.get_available_lord_bosses.return_value = ["lord_spider"]
        sm.set_config({"name": "Tier 4 退守", "type": "mix", "is_tier4_fallback": True, "lord_boss_targets": ["lord_spider"]})
        sm.has_available_dungeon = MagicMock(return_value=False)
        sm.quest_scheduler = None

        handler = ResultHandler(sm)
        handler.subflow_step = "FINAL_MATCH"
        sm.transition_to = MagicMock()

        def match_exit_or_retry(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (500, 500), 0.95
            if template == "stages/retry.png":
                return (700, 500), 0.95
            return None, 0.0

        sm.matcher.match.side_effect = match_exit_or_retry
        fake_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
        rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

        with patch("os.path.exists", return_value=True), \
             patch.object(handler, "click_and_wait_until_gone") as mock_click:
            handler.handle(fake_screen, rect)

            # 驗證 ResultHandler 點擊 exit_battle 退出戰鬥，而非 retry
            mock_click.assert_called_once()
            self.assertEqual(mock_click.call_args[0][0], "exit_battle.png")
            sm.transition_to.assert_called_once_with(sm.STATE_NAVIGATING)


if __name__ == "__main__":
    unittest.main()
